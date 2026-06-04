Luồng dữ liệu (end-to-end)

[HR nhập JD]
→ .NET gọi POST /ai/parse-jd (raw text)
→ AI Service: LLM extract → ParsedJD + embedding
→ .NET lưu vào DB

[Ứng viên nộp CV]
→ .NET gọi POST /ai/parse-cv (file PDF/DOCX)
→ AI Service: PDF extract → LLM parse → ParsedCV + embedding
→ .NET lưu vào DB

[HR xem ranking]
→ .NET load ParsedCV + ParsedJD + embeddings từ DB
→ .NET gọi POST /ai/score
→ AI Service: tính 5 chiều → final_score
→ .NET lưu + hiển thị

[HR đổi weights]
→ .NET gọi POST /ai/recalculate (scores + weights mới)
→ AI Service: tính lại final_score (KHÔNG gọi LLM)
→ .NET batch UPDATE

[HR tìm kiếm bằng tiếng tự nhiên]
→ .NET gọi POST /ai/search (query + danh sách ứng viên)
→ AI Service: embed query → cosine sim → filter → rerank → explain
→ .NET hiển thị
