"""
Stage 2 — Structured Extraction via LLM (Trích xuất thông tin có cấu trúc)

File này nhận văn bản thô của CV/JD (đã được pdf_extractor.py làm sạch) và
dùng LLM để trích xuất thành các model Pydantic có cấu trúc (ParsedCV /
ParsedJD), phục vụ cho scorer.py (chấm điểm) và evaluator.py (nhận xét).

LLM dùng để trích xuất được chọn qua .env LLM_PROVIDER (xem llm_client.py):
  - Anthropic Claude (dùng cho production, chất lượng cao)
  - Groq Llama       (miễn phí, dùng cho dev/fallback)

Các hàm ở đây đều là async để không chặn FastAPI; lời gọi SDK đồng bộ được
đẩy sang thread executor (bên trong llm_client.py).

Các cải tiến giúp kết quả trích xuất đáng tin cậy hơn:
  - Trường WorkExperience.start được LLM trích xuất dạng chuỗi, sau đó
    Python tự tính số tháng (không giao việc tính toán cho LLM, tránh sai số)
  - Sau lần parse đầu tiên có bước kiểm tra tính đầy đủ (completeness
    check): nếu work_experience hoặc skills bị rỗng, tự động gọi lại với
    prompt tập trung hơn (retry prompt)
  - Retry prompt ngắn gọn, tập trung vào đúng phần bị thiếu → độ chính xác cao hơn
  - Các lượt retry chạy song song qua asyncio.gather để không tốn thêm thời gian
"""

from __future__ import annotations

import asyncio

from app.schemas import ParsedCV, ParsedJD, WorkExperience
from app.services import location_service
from app.services.llm_client import call_llm_json


# ---------------------------------------------------------------------------
# Prompts — các mẫu prompt gửi cho LLM (giữ nguyên tiếng Anh vì đây là chỉ
# thị gửi thẳng cho model, không phải nội dung hiển thị cho người dùng)
# ---------------------------------------------------------------------------

# Prompt chính để trích xuất toàn bộ thông tin từ CV: tên, tóm tắt, kỹ năng,
# kinh nghiệm làm việc, học vấn, dự án, chứng chỉ, ngôn ngữ, và địa chỉ liên
# hệ (candidate_location) — kèm quy tắc chuyển đổi định dạng ngày tháng.
CV_EXTRACT_PROMPT = """Extract information from the CV text below.
Return ONLY valid JSON. No explanation, no markdown fences.

JSON structure:
{
  "is_resume": true or false — true ONLY if this document is an actual CV/resume/personal profile written by or about ONE specific job candidate (contains, or is clearly meant to contain, their identity plus skills/work history/education). false for anything else the text below might be — e.g. a research paper, academic article, book excerpt, invoice, contract, news article, product manual, blog post, or any document that is not a personal candidate profile. When false, still fill every other field below (leave them empty/[] if nothing genuinely CV-like is present — do NOT invent a candidate).
  "name": "candidate full name or empty string",
  "summary": "professional summary / objective or empty string",
  "skills": ["flat list of all technical skill names, normalized and split (e.g. extract 'React' and 'CSS' instead of 'ReactJS/CSS3')"],
  "work_experience": [
    {
      "company": "company name",
      "role": "job title / position",
      "start": "YYYY-MM",
      "end": "YYYY-MM or present",
      "is_current": true or false,
      "tech_stack": ["all technologies / tools used in this role"],
      "description": "key responsibilities and achievements (2-4 sentences)"
    }
  ],
  "education": [
    {
      "institution": "school or university name",
      "degree": "MUST be exactly one of: high_school, associate, bachelor, master, phd, other",
      "degree_raw": "exact degree text from CV (e.g. 'Bachelor of Software Engineering')",
      "major": "field of study or empty string"
    }
  ],
  "projects": [
    {
      "name": "project name",
      "tech_stack": ["technologies used"],
      "description": "what the project does and your contribution"
    }
  ],
  "certifications": ["Certificate Name 1", "Certificate Name 2"],
  "languages": ["English - TOEIC 835", "Vietnamese - Native"],
  "candidate_location": {
    "raw_address": "address exactly as written in the CV header/contact info block (near name, email, phone), or null if no address is present anywhere",
    "willing_to_relocate": "true ONLY if the CV explicitly states something like 'open to relocate' / 'sẵn sàng chuyển nơi làm việc', otherwise null"
  }
}

CANDIDATE_LOCATION RULES (critical — do not hallucinate):
- raw_address: extract ONLY from the CV's header/contact info block (near name,
  email, phone). Copy it as-is — do not clean, normalize, or reformat it.
  Do NOT derive an address from phone number area code, university location,
  or company locations in work history. If no address is stated in the
  contact block, use null.
- willing_to_relocate: null unless the CV explicitly states willingness to
  relocate. Never infer this from context (e.g. don't assume "true" just
  because the candidate lists an out-of-city address).

DATE CONVERSION RULES (apply to every start/end field):
Convert any date format found in the CV to YYYY-MM. Examples:
  "Jan 2021" / "January 2021"         → "2021-01"
  "06/2021" / "2021/06" / "2021.06"   → "2021-06"
  "Mar. 2022" / "March, 2022"         → "2022-03"
  "Q2 2020" / "Summer 2020"           → "2020-06"  (use mid-quarter/season month)
  "2019" (year only)                  → "2019-01"
  "Tháng 3/2021" / "T3/2021" / "3/2021" → "2021-03"  (Vietnamese formats)
  "09-2023" / "09.2023"               → "2023-09"
  Any of: "Present", "Now", "Current", "To date", "Ongoing",
          "Hiện tại", "Nay", "Đến nay", "Till now"  → "present"
  Missing or unknown date             → ""

GENERAL RULES:
- Extract ALL work experiences, even internships and part-time roles.
- For skills: scan the entire CV — skills section, work experience, projects, summary.
- Do NOT calculate months — only provide start and end date strings.
- If a field has no data, use [] for arrays or "" for strings.

SKILL NORMALIZATION & EXTRACTION RULES (applies to "skills" and every "tech_stack"):
- Normalize technology names to their standard canonical spelling and casing
  (e.g. "React" not "ReactJS", "Node.js" not "NodeJS", "JavaScript" not "JS",
  "TypeScript" not "TS", "PostgreSQL" not "Postgres", "Kubernetes" not "K8s",
  "AWS" not "Amazon Web Services").
- Remove version numbers and minor release suffixes unless they name a
  distinct tool (e.g. "Python 3.10" -> "Python", "Java 17" -> "Java",
  "Vue 3" -> "Vue", "React v18" -> "React").
- Split compound or slash-separated skills into separate list items (e.g.
  "HTML/CSS" -> "HTML", "CSS"; "C#/.NET" -> "C#", ".NET";
  "CI/CD (Jenkins, GitLab)" -> "CI/CD", "Jenkins", "GitLab").
- When a specific sub-service or sub-tool is mentioned, also include its
  base/parent technology (e.g. "AWS S3" or "AWS EC2" -> also include "AWS";
  "Docker Compose" -> also include "Docker").
- Emit ONLY concrete, matchable technical skills. Do NOT extract generic
  soft skills or competencies ("programming", "teamwork", "problem solving",
  "communication", "quick learner").

CV text:
"""


# Prompt retry tập trung: chỉ trích xuất lại work_experience khi lần parse
# đầu tiên trả về rỗng (CV_EXTRACT_PROMPT có thể bỏ sót nếu CV dài/phức tạp).
WORK_EXP_RETRY_PROMPT = """The CV below contains work experience that needs to be extracted.
Focus ONLY on the employment / work history section.
Return ONLY valid JSON — no explanation, no markdown.

{
  "work_experience": [
    {
      "company": "company name",
      "role": "job title",
      "start": "YYYY-MM or empty string",
      "end": "YYYY-MM or present or empty string",
      "is_current": true or false,
      "tech_stack": ["technologies used"],
      "description": "responsibilities and achievements"
    }
  ]
}

Include ALL jobs — full-time, part-time, internships, freelance.

DATE CONVERSION — convert any format to YYYY-MM:
  "Jan 2021" / "01/2021" / "1/2021"   → "2021-01"
  "Tháng 3/2021" / "T3/2021" / "3/2021" → "2021-03"
  "2019" (year only)                  → "2019-01"
  "Mar. 2022" / "March 2022"          → "2022-03"
  "Q1 2020" / "Spring 2020"           → "2020-03"
  "Present" / "Now" / "Hiện tại" / "Nay" / "Đến nay" → "present"
  Unknown or missing                  → ""

CV text:
"""


# Prompt retry tập trung: chỉ trích xuất lại danh sách skills khi lần parse
# đầu tiên trả về rỗng.
SKILLS_RETRY_PROMPT = """Extract ALL technical skills from the CV below.
Scan every section: skills/technologies section, work experience, projects, summary.
Return ONLY valid JSON — no explanation, no markdown.

{
  "skills": ["skill1", "skill2", "skill3", ...]
}

Include: programming languages, frameworks, libraries, databases, tools, cloud platforms, DevOps tools.
Each skill should be a single clean string (e.g. "Python", "React", "PostgreSQL").

SKILL NORMALIZATION RULES:
- Normalize to standard canonical spelling/casing (e.g. "React" not "ReactJS",
  "Node.js" not "NodeJS", "JavaScript" not "JS", "PostgreSQL" not "Postgres").
- Strip version numbers unless they name a distinct tool ("Python 3.10" -> "Python").
- Split compound/slash-separated skills into separate items ("HTML/CSS" -> "HTML", "CSS").
- For sub-services/sub-tools, also include the base technology ("AWS S3" -> also "AWS").
- Do NOT extract generic soft skills (e.g. "teamwork", "problem solving").

CV text:
"""


# Prompt chính để trích xuất toàn bộ thông tin từ JD: tiêu đề công việc, kỹ
# năng bắt buộc/ưu tiên (kèm trọng số và nhóm OR-alternatives), số năm kinh
# nghiệm tối thiểu, bằng cấp yêu cầu, và địa điểm/hình thức làm việc.
JD_EXTRACT_PROMPT = """Extract structured information from the Job Description below.
Return ONLY valid JSON. No explanation, no markdown.

JSON structure:
{
  "title": "job title",
  "responsibilities": "role summary and key responsibilities/business context (2-5 sentences) — scope of the role, what the person will own/do, team or domain context. Do NOT list specific skills, tools, or technologies here (those go in required_skills/preferred_skills/nice_to_have_skills). Empty string if the JD gives nothing beyond a skills list.",
  "required_skills": [
    {"skill": "skill name", "weight": 1 or 2 or 3, "alternatives": ["interchangeable skill names"]}
  ],
  "preferred_skills": ["skills carrying a strong preference cue (see REQUIRED vs PREFERRED vs NICE-TO-HAVE below)"],
  "nice_to_have_skills": ["skills carrying a weaker, bonus-only cue (see REQUIRED vs PREFERRED vs NICE-TO-HAVE below)"],
  "min_experience_years": integer (0 if not specified),
  "education_degree": "bachelor or master or phd or associate or high_school or other or null — the MINIMUM accepted level (see EDUCATION rules below)",
  "work_location": {
    "city": "MUST be exactly one of: Ha Noi, Ho Chi Minh, Da Nang",
    "raw_address": "ONLY the street/district/building portion (street name, house number, district, ward, building), WITHOUT the city name — city goes in the separate 'city' field above, never repeat it here. Empty string if the JD states no more than a city.",
    "work_mode": "onsite or hybrid or remote"
  }
}

STRUCTURED FIELDS TAKE PRIORITY OVER PROSE (critical):
This JD text is machine-generated by concatenating fixed database fields, in
this order (any line is OMITTED ENTIRELY — not left blank — when that field
is empty on the job-posting form, so don't expect all of them to be present):
Job Title, Work Type, Location, Education, Required Skills, Preferred
Skills, Nice to Have Skills, Experience Requirement, Responsibilities,
Requirements, Benefits. All but the last three are structured values chosen
from a picker/enum on the job-posting form — trust them over anything
inferred from the free-text Responsibilities/Requirements/Benefits blocks
that follow:
  - "Work Type: X" → maps directly to work_mode (see WORK_MODE below); only
    infer work_mode from prose if this line is absent.
  - "Location: X" → the city name is the LAST comma-separated segment of
    this line; read city from there instead of guessing from prose. Put
    everything BEFORE that last segment into raw_address (street/district/
    building) — the two fields are stored separately downstream (BE .NET's
    company_branch table has separate address/city columns), so raw_address
    must never repeat the city segment.
  - "Education: X[, Y, ...]" → see EDUCATION rules below.
  - "Required Skills: X, Y, Z" / "Preferred Skills: X, Y, Z" / "Nice to Have
    Skills: X, Y, Z" → three independent, already-tiered tag lists picked by
    the employer through a skill picker (any of the three lines may be
    absent if that list is empty). These skill names are ALREADY canonical
    (they come from the same standardized skill taxonomy the matching engine
    uses) — copy them into required_skills / preferred_skills /
    nice_to_have_skills VERBATIM, do not rephrase or re-normalize them.
    Trust the tier each line already assigns: every skill from "Required
    Skills:" → required_skills (weight 3); every skill from "Preferred
    Skills:" → preferred_skills; every skill from "Nice to Have Skills:" →
    nice_to_have_skills. Do NOT re-run the prose-based REQUIRED vs PREFERRED
    vs NICE-TO-HAVE heuristic on these already-tagged skills, and do NOT let
    a Requirements/Responsibilities bullet move a skill that already appears
    in one of these three lines to a different tier.

    DUPLICATE PREVENTION (critical — this is the ONLY safeguard against
    double-counting a skill across tiers, there is no de-duplication step
    downstream in code, so getting this right here matters): after copying
    the three tag lines verbatim, separately scan the Responsibilities/
    Requirements prose for skills the employer wants but that are NOT
    already one of the tag-list skills. Before adding any such prose-found
    skill, check it against ALL THREE tag lists (case-insensitively, and
    treating obvious spelling/format variants as the same skill — e.g.
    "ReactJS" vs "React.js" vs "React", "Node" vs "Node.js", "Postgres" vs
    "PostgreSQL"). If it matches (or is a clear variant of) a skill already
    present in ANY of the three lists, DO NOT add it again anywhere — the
    tag list already covers it, at its already-assigned tier. Only add a
    prose-found skill as a brand-new entry when it names a genuinely
    different skill that no tag line covers, and classify that new entry
    using the REQUIRED vs PREFERRED vs NICE-TO-HAVE heuristic below. Every
    skill name must end up in exactly ONE of the three output lists, never
    more than one.
  - "Experience Requirement: X" → see EXPERIENCE PARSING below; trust this
    field over qualitative statements elsewhere in the prose (e.g. "fresh
    graduates are welcome" describes who may apply, it does not lower or
    override a stated minimum).

WORK_MODE (critical):
If a "Work Type: X" line is present, map it directly:
  Hybrid → "hybrid", Remote → "remote", Onsite/On-site/OnSite → "onsite"
Only when that line is absent, infer from explicit signals in the prose:
  - "remote" if the JD says things like "remote", "work from home", "làm việc từ xa", "100% remote", "WFH"
  - "hybrid" if the JD says "hybrid", "kết hợp", "2-3 days in office", "part remote"
  - "onsite" if the JD says "onsite", "tại văn phòng", "on-site", "full-time in office"
If there is truly no signal anywhere, default to "onsite" — this is a heuristic
assumption (most unlabeled JDs in this market are onsite), not a neutral guess.

EDUCATION (critical):
The "Education: X[, Y, ...]" line may list MORE THAN ONE accepted degree —
it is a multi-select of acceptable options, not a combined/stacked
requirement. Map each term (Vietnamese or English) to the enum:
  THPT / Trung học phổ thông     → high_school
  Trung cấp / Cao đẳng           → associate
  Đại học / Cử nhân / Bachelor   → bachelor
  Thạc sĩ / Master               → master
  Tiến sĩ / PhD / Doctor         → phd
education_degree represents the MINIMUM accepted bar ("X or above"), so when
multiple terms are listed, output the LOWEST one among them — e.g.
"THPT, Thạc sĩ, Tiến sĩ" → "high_school" (NOT "phd"): any of the three is
accepted, so the real floor is the easiest one. If the Education line is
absent, fall back to a degree requirement stated in the Requirements prose;
if none anywhere, use null.

EXPERIENCE PARSING (critical):
"Experience Requirement: X" is free text, not a number. Convert it:
  "2 years" / "2+ years" / "at least 2 years"        → 2
  "1-3 years" / "1 to 3 years"                        → 1  (lower bound of the range)
  "Không yêu cầu kinh nghiệm" / "No experience required" /
  "Fresher" / "Mới ra trường" / empty                 → 0
Trust this field as the stated minimum; do not let unrelated prose elsewhere
in the JD raise or lower it.

REQUIRED vs PREFERRED vs NICE-TO-HAVE (critical — do not mix; applies ONLY to
skills mined from the Responsibilities/Requirements prose — skills already
tiered by the "Required Skills:" / "Preferred Skills:" / "Nice to Have
Skills:" lines are NEVER reclassified here, see STRUCTURED FIELDS above):
Classify each skill mention by the cue words attached to THAT mention, not
by which top-level section it physically sits in — a single "Requirements:"
block commonly mixes mandatory items with individually-flagged softer ones
(e.g. "Japanese: N3 certification or above is an advantage" is one bullet
inside a "Requirements:" list, but the phrase "is an advantage" makes that
specific skill preferred, not the whole section).
- required_skills = skill mentions with no softening qualifier, or explicit
  "Required"/"Must have"/"Mandatory" cues.
- preferred_skills = skill mentions carrying a genuine-preference cue
  anywhere in their own sentence/bullet: "Preferred", "Desirable",
  "advantage" / "a plus", "ưu tiên", "ưu tiên nếu có". These read as "we'd
  rather hire someone who has this."
- nice_to_have_skills = skill mentions carrying a weaker, explicitly-optional
  bonus cue: "Nice to have", "Bonus", "Optional", "cộng điểm nếu có", "có thì
  càng tốt", "if you happen to have X". These read as "this won't affect the
  decision, it's just a perk" — a notch below preferred_skills.
Put each into exactly ONE of the three lists, NEVER duplicate a skill across
lists, and NEVER put a softened mention into required_skills even when the
bullet lives inside a "Requirements:" heading. When a cue is ambiguous
between preferred and nice-to-have, default to preferred_skills (the safer,
more established bucket).

WHAT COUNTS AS A SKILL (critical — the #1 source of inconsistent extraction):
- Testing-activity nouns and other named disciplines/practices ("API testing",
  "manual testing", "regression testing", "UI/UX testing", "code review",
  "unit testing") ARE valid skill entries — they name a matchable discipline.
- Process/methodology words alone ("SDLC", "STLC", "Agile", "Scrum", "defect
  lifecycle") and category-level nouns without a named product ("relational
  databases", "cloud platform", "version control") are NOT valid skill
  entries, even under a "Required" heading — they're too generic to match
  against a CV skill list.
- Ability/duty sentences ("ability to design test cases", "good knowledge of
  X", "understanding of Y") are never a skill entry themselves — extract
  only an embedded concrete noun (discipline, tool, technology), if any.

ALTERNATIVES / OR-GROUPS (critical):
When a requirement lists skills as interchangeable options — "A, B, or C",
"A / B", "experience with A or B", "one of A, B" — emit ONE required_skills entry
whose "skill" is the first option and "alternatives" holds the rest. Do NOT split
an OR-group into separate entries.
  "React.js, TypeScript, or Vue.js"  → {"skill": "React.js", "weight": 3, "alternatives": ["TypeScript", "Vue.js"]}
  "Bootstrap or Tailwind CSS"        → {"skill": "Bootstrap", "weight": 3, "alternatives": ["Tailwind CSS"]}
A skill that stands on its own (not an option) has "alternatives": [].

Weight guide (required_skills only): 3 = must-have / core, 2 = important, 1 = minor.
Reserve weight 3 for skills the JD truly mandates; do not mark everything as 3.

SKILL NORMALIZATION & STRUCTURE RULES:
- Standardize skill names to their canonical form (e.g. "React", "Node.js",
  "JavaScript", "TypeScript", "Python", "Kubernetes", "Docker", "PostgreSQL", "AWS").
- Strip version constraints from the skill name itself (e.g. "Python 3.x" ->
  skill "Python"; "Java 8+" -> skill "Java"; "Vue 3" -> skill "Vue").
- Split compound or slash-separated skills. If the options are interchangeable,
  represent them via "alternatives" rather than as one compound string
  (e.g. "React/Vue" -> {"skill": "React", "weight": 3, "alternatives": ["Vue"]}).
- For a sub-service/sub-tool, also ensure the base technology is extractable
  (e.g. "AWS S3" -> extract "AWS").

Emit ONLY concrete, matchable skills (languages, frameworks, tools, platforms,
certifications, standardized language levels like "JLPT N3"). Do NOT emit generic
competencies or soft skills — "programming fundamentals", "problem solving",
"teamwork", "communication", "self-learning", "responsibility" — in
required_skills, preferred_skills, or nice_to_have_skills; a concrete
language/tool requirement already implies them.

BENEFITS EXCLUSION (critical):
Ignore the Benefits block entirely when extracting required_skills /
preferred_skills / nice_to_have_skills — it describes compensation/allowance
tiers, not hiring requirements, even when it mentions skill-like terms (e.g. a
"N1"/"N2" allowance amount does not mean N1/N2 is required or preferred if
only N3 was actually asked for in Requirements).

JD text:
"""


# ---------------------------------------------------------------------------
# Retry helpers — gọi lại LLM với prompt tập trung khi lần parse đầu thiếu dữ liệu
# ---------------------------------------------------------------------------

async def _retry_work_experience(cv_text: str) -> list[WorkExperience]:
    """
    Trích xuất lại riêng phần work_experience khi lần parse đầy đủ ban đầu
    bị thiếu (trả về rỗng). Mọi lỗi (LLM lỗi, JSON không hợp lệ, item không
    validate được theo schema WorkExperience) đều bị nuốt và bỏ qua item đó
    — không làm fail toàn bộ quá trình parse CV.
    """
    try:
        raw   = await call_llm_json(WORK_EXP_RETRY_PROMPT, cv_text)
        items = raw.get("work_experience", []) if isinstance(raw, dict) else []
        result: list[WorkExperience] = []
        for item in items:
            try:
                result.append(WorkExperience.model_validate(item))
            except Exception:
                pass
        return result
    except Exception:
        return []


async def _retry_skills(cv_text: str) -> list[str]:
    """
    Trích xuất lại riêng danh sách skills khi lần parse đầy đủ ban đầu bị
    thiếu (trả về rỗng). Mọi lỗi đều bị nuốt, trả về [] thay vì raise.
    """
    try:
        raw   = await call_llm_json(SKILLS_RETRY_PROMPT, cv_text)
        items = raw.get("skills", []) if isinstance(raw, dict) else []
        return [s for s in items if isinstance(s, str)]
    except Exception:
        return []


async def _geocode(address: str) -> tuple[float, float] | tuple[None, None]:
    """
    Geocode một địa chỉ (candidate_location của CV hoặc work_location của
    JD) đúng 1 lần tại thời điểm parse — vì lat/lng là thuộc tính gắn liền
    với chính CV/JD đó (giống như embedding), không cần tính lại mỗi lần
    chấm điểm (score).

    location_service.geocode là hàm đồng bộ/blocking (gọi HTTP ra ngoài),
    nên được chạy trong 1 thread riêng (asyncio.to_thread) để không chặn
    event loop. Nếu thất bại (lỗi mạng, không tìm thấy địa chỉ) trả về
    (None, None) — không bao giờ làm fail lời gọi parse, theo đúng cách xử
    lý lỗi từng-phần-tử (per-item error tolerance) đã dùng ở những chỗ khác.
    """
    if not address or not address.strip():
        return None, None
    try:
        result = await asyncio.to_thread(location_service.geocode, address)
    except Exception:
        result = None
    if result is None:
        return None, None
    return result["lat"], result["lng"]


# ---------------------------------------------------------------------------
# Public API — CV / JD parsing (hàm public để main.py / các module khác gọi)
# ---------------------------------------------------------------------------

async def parse_cv(cv_text: str) -> ParsedCV:
    """
    Trích xuất CV có cấu trúc (ParsedCV) từ văn bản thô.

    Luồng xử lý:
      1. Gọi LLM trích xuất đầy đủ (CV_EXTRACT_PROMPT)
      2. Kiểm tra tính đầy đủ — work_experience và skills là 2 trường quan
         trọng nhất, không được để rỗng
      3. Nếu 1 trong 2 (hoặc cả 2) bị rỗng, chạy song song các prompt retry
         tập trung tương ứng
      4. Gộp kết quả retry vào object CV (chỉ ghi đè nếu retry ra kết quả
         khác rỗng, tránh mất dữ liệu nếu retry cũng thất bại)
      5. Geocode candidate_location.raw_address đúng 1 lần (lat/lng được
         lưu lại cùng CV, giống cv_embedding — không tính lại lúc chấm điểm)
    """
    raw = await call_llm_json(CV_EXTRACT_PROMPT, cv_text)
    cv  = ParsedCV.model_validate(raw)

    # Document isn't a CV at all (e.g. a research paper) — retrying to
    # squeeze work_experience/skills out of it would just waste LLM calls.
    if not cv.is_resume:
        return cv

    needs_exp    = not cv.work_experience
    needs_skills = not cv.skills

    if needs_exp or needs_skills:
        # Build only the tasks we actually need
        retry_coros = []
        if needs_exp:
            retry_coros.append(_retry_work_experience(cv_text))
        if needs_skills:
            retry_coros.append(_retry_skills(cv_text))

        results = await asyncio.gather(*retry_coros, return_exceptions=True)

        idx = 0
        if needs_exp:
            if isinstance(results[idx], list) and results[idx]:
                cv.work_experience = results[idx]
            idx += 1
        if needs_skills:
            if isinstance(results[idx], list) and results[idx]:
                cv.skills = results[idx]

    if cv.candidate_location.raw_address:
        cv.candidate_location.lat, cv.candidate_location.lng = await _geocode(
            cv.candidate_location.raw_address
        )

    return cv


async def parse_jd(jd_text: str) -> ParsedJD:
    """
    Trích xuất JD có cấu trúc (ParsedJD) từ văn bản thô, sau đó geocode
    work_location đúng 1 lần (lat/lng được lưu lại cùng JD, giống
    jd_embedding — không tính lại lúc chấm điểm).

    company_branch (BE .NET) lưu address và city thành 2 cột riêng, nên
    raw_address ở đây có thể chỉ là số nhà/đường (không tự chứa city) —
    nối raw_address + city thành 1 chuỗi trước khi geocode để Nominatim đủ
    ngữ cảnh xác định đúng vị trí. Nếu JD không nêu địa chỉ cụ thể, dùng
    city làm địa chỉ dự phòng (như cũ).
    """
    raw = await call_llm_json(JD_EXTRACT_PROMPT, jd_text)
    jd  = ParsedJD.model_validate(raw)

    raw_address, city = jd.work_location.raw_address, jd.work_location.city
    address = f"{raw_address}, {city}" if raw_address else city
    jd.work_location.lat, jd.work_location.lng = await _geocode(address)

    return jd
