import sys
import os
import asyncio
import httpx
import re
import json

# Thêm đường dẫn thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.parser import parse_jd, parse_cv
from app.services.embedder import embed
from app.services.scorer import calculate_score_with_rules
from app.services.evaluator import evaluate_cv_for_job
from app.services.pdf_extractor import extract_text
from app.schemas import ParsedJD, ParsedCV

# Định nghĩa 3 JDs theo yêu cầu của user:
# 1. .NET Backend Developer, yêu cầu 3 năm kinh nghiệm
# 2. ReactJS Frontend Developer, tự viết mô tả (yêu cầu 2 năm kinh nghiệm)
# 3. AI Engineer, yêu cầu 2 năm kinh nghiệm

JD_DOTNET_TEXT = """
Job Title: Senior .NET Backend Developer
We are looking for a Senior .NET Backend Developer to join our team.
Required Experience: At least 3 years of professional experience in backend development.
Technical Skills:
- Strong proficiency in C# and .NET Core / ASP.NET Core (must-have)
- Hands-on experience with Entity Framework Core (must-have)
- Deep understanding of SQL Server, database design, and query optimization (important)
- Experience building RESTful APIs (important)
- Familiarity with Docker and containerization (nice-to-have)
Preferred Skills:
- Cloud experience (AWS or GCP)
- Familiarity with CI/CD pipelines
- Experience with microservices architecture
Education: Bachelor's degree in Computer Science, Software Engineering, or related field.
"""

JD_REACT_TEXT = """
Job Title: ReactJS Frontend Developer
We are looking for a ReactJS Frontend Developer to build and optimize our web applications.
Required Experience: At least 2 years of professional experience in frontend development.
Technical Skills:
- Expert knowledge of React (ReactJS) and JavaScript (ES6+) (must-have)
- Proficiency in TypeScript (important)
- Strong skills in HTML5, CSS3, and modern CSS layout techniques (important)
- Experience with Tailwind CSS (nice-to-have)
Preferred Skills:
- Experience with Next.js framework
- State management library (Redux, Zustand)
- Webpack/Vite bundlers
- Responsive and mobile-first design principles
Education: Bachelor's degree in IT, Computer Science, or equivalent.
"""

JD_AI_TEXT = """
Job Title: AI Engineer
We are looking for an AI Engineer to design and implement machine learning models.
Required Experience: At least 2 years of professional experience in AI/ML engineering.
Technical Skills:
- Strong programming skills in Python (must-have)
- Core understanding of Machine Learning and Deep Learning algorithms (must-have)
- Proficiency in PyTorch or TensorFlow framework (must-have)
- Experience with pandas, numpy, and data preprocessing (important)
- Experience with Natural Language Processing (NLP) or Computer Vision (important)
Preferred Skills:
- Experience with LLM prompt engineering, fine-tuning, and RAG architectures
- Experience with Docker
- Experience with FastAPI or Flask to deploy models
- Familiarity with Git version control
Education: Bachelor's or Master's degree in Computer Science, Data Science, AI, or related field.
"""

JDS = [
    {
        "id": "jd_dotnet",
        "name": "dotnet_backend",
        "text": JD_DOTNET_TEXT
    },
    {
        "id": "jd_react",
        "name": "react_frontend",
        "text": JD_REACT_TEXT
    },
    {
        "id": "jd_ai",
        "name": "ai_engineer",
        "text": JD_AI_TEXT
    }
]

async def fetch_file(url: str, client: httpx.AsyncClient) -> tuple[bytes, str]:
    last_exc = None
    for attempt in range(3):
        try:
            resp = await client.get(url, follow_redirects=True, timeout=30.0)
            resp.raise_for_status()
            break
        except (httpx.TransportError, httpx.ConnectError) as e:
            last_exc = e
            await asyncio.sleep(1.5 * (attempt + 1))
    else:
        raise last_exc

    filename = ""
    cd = resp.headers.get("content-disposition", "")
    if cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd, re.IGNORECASE)
        if m:
            filename = m.group(1).strip().strip('"\'')

    if not filename:
        filename = url.split("?")[0].rstrip("/").split("/")[-1]

    if "." not in filename.rsplit("/", 1)[-1]:
        ct = resp.headers.get("content-type", "")
        ext = ".docx" if ("wordprocessingml" in ct or "docx" in ct) else ".pdf"
        filename += ext

    return resp.content, filename

def generate_markdown_report(jd_info, parsed_jd, cv_name, parsed_cv, score_res, eval_res, url):
    # Format skills match
    skills_table = "| Kỹ năng | Yêu cầu (JD) | Trạng thái | Điểm trọng số |\n|:---|:---|:---|:---|\n"
    for detail in eval_res.skill_details:
        status_map = {
            "matched": "✅ Khớp",
            "missing_must_have": "❌ Thiếu (Bắt buộc)",
            "missing_preferred": "⚠️ Thiếu (Ưu tiên)"
        }
        skills_table += f"| {detail.skill} | {'Bắt buộc (3)' if detail.weight >= 3 else ('Quan trọng (2)' if detail.weight == 2 else 'Ưu tiên (1)')} | {status_map.get(detail.status, detail.status)} | {detail.weight} |\n"

    # Format work experience entries
    exp_details = ""
    for exp in parsed_cv.work_experience:
        tech = ", ".join(exp.tech_stack) if exp.tech_stack else "Không ghi nhận"
        exp_details += f"### {exp.role} tại {exp.company}\n"
        exp_details += f"- **Thời gian:** {exp.start} -> {exp.end} ({exp.months} tháng)\n"
        exp_details += f"- **Công nghệ:** {tech}\n"
        exp_details += f"- **Mô tả:** {exp.description}\n\n"

    # Penalties
    penalties_section = ""
    if score_res.get("penalty_applied", 0.0) > 0:
        penalties_section += f"### ⚠️ Các điểm phạt áp dụng (Penalties)\n"
        penalties_section += f"- **Tỷ lệ phạt tổng cộng:** {score_res['penalty_applied'] * 100}%\n"
        penalties_section += f"- **Lý do phạt:**\n"
        for reason in score_res.get("penalty_reasons", []):
            penalties_section += f"  - {reason}\n"
    else:
        penalties_section += "*Không áp dụng điểm phạt cứng.*\n"

    md = f"""# Báo cáo đánh giá mức độ phù hợp ứng viên: {parsed_cv.name or cv_name}

## 1. Thông tin chung
- **Vị trí ứng tuyển:** {parsed_jd.title} ({jd_info['name']})
- **Ứng viên:** {parsed_cv.name or cv_name}
- **URL CV:** [{cv_name}]({url})
- **Tổng số năm kinh nghiệm:** {parsed_cv.total_exp_years} năm ({parsed_cv.total_exp_months} tháng)
- **Học vấn cao nhất:** {parsed_cv.education[0].degree_raw if parsed_cv.education else "Không rõ"}

---

## 2. Kết quả chấm điểm định lượng (Scores Breakdown)
| Chỉ tiêu | Điểm số (Thang 100) | Trọng số áp dụng |
|:---|:---|:---|
| **D1. Độ tương đồng ngữ nghĩa (Semantic)** | {score_res['scores'].get('semantic', 0.0)}% | 30% |
| **D2. Mức độ trùng khớp kỹ năng (Skills)** | {score_res['scores'].get('skills', 0.0)}% | 35% |
| **D3. Kinh nghiệm làm việc (Experience)** | {score_res['scores'].get('experience', 0.0)}% | 20% |
| **D4. Trình độ học vấn (Education)** | {score_res['scores'].get('education', 0.0)}% | 10% |
| **D5. Khớp từ khóa (Keywords)** | {score_res['scores'].get('keywords', 0.0)}% | 5% |
| **ĐIỂM SỐ CUỐI CÙNG (FINAL SCORE)** | **{score_res['final_score']:.1f} / 100** | **100%** |

{penalties_section}

---

## 3. Phân tích chi tiết mức độ phù hợp (Qualitative Analysis)

### 3.1 Kỹ năng (Skills)
- **Tỷ lệ khớp kỹ năng:** {eval_res.skill_match_rate}%
- **Danh sách chi tiết:**
{skills_table}

- **Kỹ năng ưu tiên còn thiếu:** {", ".join(eval_res.missing_preferred) if eval_res.missing_preferred else "Không có"}
- **Kỹ năng bổ trợ (Bonus Skills):** {", ".join(eval_res.bonus_skills) if eval_res.bonus_skills else "Không có"}

### 3.2 Kinh nghiệm và Seniority
- **Đánh giá kinh nghiệm:** {eval_res.experience_detail} (Mức độ: {eval_res.experience_verdict})
- **Đánh giá cấp bậc (Seniority):** {eval_res.seniority_detail} (Mức độ: {eval_res.seniority_match})

### 3.3 Học vấn
- **Kết luận bằng cấp:** {eval_res.education_verdict} (Yêu cầu JD: {parsed_jd.education_degree or "Không yêu cầu"})

---

## 4. Nhận xét định tính từ AI (Recruiter Narrative Summary)
{eval_res.narrative}

---

## 5. Khuyến nghị tuyển dụng (Recommendation)
**KẾT LUẬN:** **{eval_res.recommendation.upper()}**

---
*Báo cáo được tạo tự động bởi hệ thống AI Matching.*
"""
    return md

async def main():
    os.makedirs("result_test", exist_ok=True)
    
    # Đọc danh sách các URL CV
    with open("docs/cv_url.md", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]
        
    print(f"Loaded {len(urls)} CV URLs from docs/cv_url.md")
    
    async with httpx.AsyncClient() as client:
        # 1. Phân tích và tạo vector nhúng (embedding) cho các JD
        parsed_jds = {}
        jd_embeddings = {}
        for jd_info in JDS:
            jd_id = jd_info["id"]
            jd_text = jd_info["text"]
            print(f"Parsing JD: {jd_info['name']}...")
            try:
                parsed_jd = await parse_jd(jd_text)
                jd_emb = await embed(parsed_jd.build_embed_text())
                parsed_jds[jd_id] = parsed_jd
                jd_embeddings[jd_id] = jd_emb
                print(f"JD parsed successfully: {parsed_jd.title}")
            except Exception as e:
                print(f"Failed to parse JD {jd_info['name']}: {e}")
                
        # 2. Phân tích và tạo vector nhúng cho các CV
        parsed_cvs = {}
        cv_embeddings = {}
        cv_raw_texts = {}
        cv_names = {}
        
        for idx, url in enumerate(urls, 1):
            print(f"[{idx}/{len(urls)}] Processing CV from URL: {url}")
            try:
                # Lấy tên file từ URL
                file_name_from_url = url.split("/")[-1].split("?")[0]
                cv_name = file_name_from_url.replace(".pdf", "").replace(".docx", "")
                cv_names[url] = cv_name
                
                # Download
                file_bytes, filename = await fetch_file(url, client)
                # Trích xuất text
                raw_text = extract_text(file_bytes, filename)
                if not raw_text.strip():
                    raise ValueError("Extracted text is empty")
                
                # Phân tích cú pháp CV bằng LLM
                parsed_cv = await parse_cv(raw_text)
                # Tạo vector nhúng CV
                cv_emb = await embed(parsed_cv.build_embed_text())
                
                parsed_cvs[url] = parsed_cv
                cv_embeddings[url] = cv_emb
                cv_raw_texts[url] = raw_text
                print(f"CV parsed successfully: {parsed_cv.name or cv_name}")
            except Exception as e:
                print(f"Error processing CV at {url}: {e}")
                
        # 3. So khớp từng cặp JD-CV và lưu kết quả
        total_runs = 0
        for jd_info in JDS:
            jd_id = jd_info["id"]
            jd_name = jd_info["name"]
            
            if jd_id not in parsed_jds:
                print(f"Skipping JD {jd_name} due to prior parsing failure")
                continue
                
            parsed_jd = parsed_jds[jd_id]
            jd_emb = jd_embeddings[jd_id]
            
            for url in urls:
                if url not in parsed_cvs:
                    print(f"Skipping CV {url} due to prior parsing failure")
                    continue
                    
                parsed_cv = parsed_cvs[url]
                cv_emb = cv_embeddings[url]
                raw_text = cv_raw_texts[url]
                cv_name = cv_names[url]
                
                print(f"Matching {jd_name} ↔ {parsed_cv.name or cv_name}...")
                
                try:
                    score_res = calculate_score_with_rules(
                        parsed_cv=parsed_cv,
                        parsed_jd=parsed_jd,
                        cv_embedding=cv_emb,
                        jd_embedding=jd_emb,
                        cv_raw_text=raw_text,
                        use_role_fit=False
                    )
                    
                    eval_res = await evaluate_cv_for_job(parsed_cv, parsed_jd)
                    
                    # Tạo nội dung báo cáo Markdown
                    report_md = generate_markdown_report(
                        jd_info, parsed_jd, cv_name, parsed_cv, score_res, eval_res, url
                    )
                    
                    # Ghi ra file
                    file_path = f"result_test/{jd_name}_vs_{cv_name}.md"
                    with open(file_path, "w", encoding="utf-8") as rf:
                        rf.write(report_md)
                    print(f"Saved report to {file_path}")
                    total_runs += 1
                except Exception as e:
                    print(f"Failed to match {jd_name} with {cv_name}: {e}")
                    
        print(f"\nDone! Generated {total_runs} reports in result_test/ directory.")

if __name__ == "__main__":
    asyncio.run(main())
