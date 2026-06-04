# =============================================================================
# Full API Test — chạy từng endpoint theo pipeline thực tế
# Yêu cầu: server đang chạy tại localhost:8000
#
# Cách chạy:
#   cd d:\AIMatchingCV\MVP_AI_Matching
#   .\tests\test_api_full.ps1
# =============================================================================

$BASE = "http://localhost:8000/ai"
$CV_PATH = "..\POC_CV_Matching\CVs\backend_developer_1.pdf"

# Màu output
function OK   { Write-Host "  [OK] $args" -ForegroundColor Green }
function FAIL { Write-Host "  [FAIL] $args" -ForegroundColor Red }
function STEP { Write-Host "`n=== $args ===" -ForegroundColor Cyan }

# --- Helpers ---
function Assert-Range($val, $min, $max, $label) {
    if ($val -ge $min -and $val -le $max) { OK "$label = $val (in [$min, $max])" }
    else { FAIL "$label = $val NOT in [$min, $max]" }
}
function Assert-Len($arr, $expected, $label) {
    if ($arr.Count -eq $expected) { OK "$label length = $expected" }
    else { FAIL "$label length = $($arr.Count), expected $expected" }
}

# =============================================================================
# Step 0 — Health check
# =============================================================================
STEP "Step 0 — Health check"
try {
    $h = Invoke-RestMethod -Uri "http://localhost:8000/health"
    if ($h.status -eq "ok") { OK "Server is up" }
    else { FAIL "Unexpected health response: $h" }
} catch {
    FAIL "Server not reachable: $_"
    Write-Host "  → Chạy: cd MVP_AI_Matching; python -m uvicorn app.main:app --reload" -ForegroundColor Yellow
    exit 1
}

# =============================================================================
# Step 1 — POST /ai/parse-jd
# =============================================================================
STEP "Step 1 — POST /ai/parse-jd"
$jd_text = Get-Content -Path ".\sample_data\jd_sample.txt" -Raw
$body = @{ jd_text = $jd_text } | ConvertTo-Json

Write-Host "  Sending JD text ($($jd_text.Length) chars) to /ai/parse-jd..." -ForegroundColor Gray
$jd_result = Invoke-RestMethod -Uri "$BASE/parse-jd" -Method POST `
    -ContentType "application/json" -Body $body

OK "Title: $($jd_result.parsed_jd.title)"
OK "Required skills: $($jd_result.parsed_jd.required_skills.Count)"
OK "Min exp years: $($jd_result.parsed_jd.min_experience_years)"
Assert-Len $jd_result.embedding 384 "JD embedding"
Assert-Range $jd_result.parsed_jd.min_experience_years 0 20 "min_experience_years"

$parsed_jd = $jd_result.parsed_jd
$jd_embedding = $jd_result.embedding

# =============================================================================
# Step 2 — POST /ai/parse-cv
# =============================================================================
STEP "Step 2 — POST /ai/parse-cv (file upload)"

if (-not (Test-Path $CV_PATH)) {
    Write-Host "  CV file not found at $CV_PATH, trying alternative..." -ForegroundColor Yellow
    $CV_PATH = "..\POC_CV_Matching\CVs\ai_engineer_1.pdf"
}

Write-Host "  Uploading: $CV_PATH" -ForegroundColor Gray

# multipart/form-data upload
$boundary = [System.Guid]::NewGuid().ToString()
$fileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $CV_PATH))
$filename  = [System.IO.Path]::GetFileName($CV_PATH)

$body_parts  = "--$boundary`r`n"
$body_parts += "Content-Disposition: form-data; name=`"cv_file`"; filename=`"$filename`"`r`n"
$body_parts += "Content-Type: application/pdf`r`n`r`n"
$bodyBytes   = [System.Text.Encoding]::UTF8.GetBytes($body_parts)
$endBytes    = [System.Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")

$multipart = $bodyBytes + $fileBytes + $endBytes

$cv_result = Invoke-RestMethod -Uri "$BASE/parse-cv" -Method POST `
    -ContentType "multipart/form-data; boundary=$boundary" -Body $multipart

OK "cv_raw_text length: $($cv_result.cv_raw_text.Length) chars"
OK "Skills found: $($cv_result.parsed_cv.skills -join ', ')"
OK "Work experience entries: $($cv_result.parsed_cv.work_experience.Count)"
Assert-Len $cv_result.embedding 384 "CV embedding"

if ($cv_result.cv_raw_text.Length -gt 50) { OK "Text extraction successful" }
else { FAIL "cv_raw_text too short — check PDF parsing" }

$parsed_cv   = $cv_result.parsed_cv
$cv_embedding = $cv_result.embedding
$cv_raw_text  = $cv_result.cv_raw_text

# =============================================================================
# Step 3 — POST /ai/score
# =============================================================================
STEP "Step 3 — POST /ai/score"

$score_body = @{
    parsed_cv    = $parsed_cv
    parsed_jd    = $parsed_jd
    cv_embedding = $cv_embedding
    jd_embedding = $jd_embedding
    cv_raw_text  = $cv_raw_text
    weights      = $null   # use server defaults
} | ConvertTo-Json -Depth 20

$score_result = Invoke-RestMethod -Uri "$BASE/score" -Method POST `
    -ContentType "application/json" -Body $score_body

Assert-Range $score_result.final_score 0 100 "final_score"
Assert-Range $score_result.scores.semantic   0 100 "D1 semantic"
Assert-Range $score_result.scores.skills     0 100 "D2 skills"
Assert-Range $score_result.scores.experience 0 100 "D3 experience"
Assert-Range $score_result.scores.education  0 100 "D4 education"
Assert-Range $score_result.scores.keywords   0 100 "D5 keywords"

Write-Host ""
Write-Host "  ┌──────────────────────────────────────────┐" -ForegroundColor White
Write-Host "  │  Final Score : $($score_result.final_score.ToString('F1').PadLeft(6))/100               │" -ForegroundColor White
Write-Host "  │  Semantic    : $($score_result.scores.semantic.ToString('F1').PadLeft(6))%                │" -ForegroundColor White
Write-Host "  │  Skills      : $($score_result.scores.skills.ToString('F1').PadLeft(6))%                │" -ForegroundColor White
Write-Host "  │  Experience  : $($score_result.scores.experience.ToString('F1').PadLeft(6))%                │" -ForegroundColor White
Write-Host "  │  Education   : $($score_result.scores.education.ToString('F1').PadLeft(6))%                │" -ForegroundColor White
Write-Host "  │  Keywords    : $($score_result.scores.keywords.ToString('F1').PadLeft(6))%                │" -ForegroundColor White
Write-Host "  └──────────────────────────────────────────┘" -ForegroundColor White

$scores_breakdown = $score_result.scores

# =============================================================================
# Step 4 — POST /ai/recalculate (đổi weights, không gọi LLM)
# =============================================================================
STEP "Step 4 — POST /ai/recalculate"

$recalc_body = @{
    applications = @(
        @{ id = "test-app-001"; scores = $scores_breakdown },
        @{ id = "test-app-002"; scores = @{
            semantic=70.0; skills=80.0; experience=60.0; education=100.0; keywords=50.0
        }},
        @{ id = "test-app-003"; scores = @{
            semantic=85.0; skills=55.0; experience=90.0; education=50.0; keywords=75.0
        }}
    )
    weights = @{
        semantic=0.20; skills=0.50; experience=0.15; education=0.10; keywords=0.05
    }
} | ConvertTo-Json -Depth 10

$recalc_result = Invoke-RestMethod -Uri "$BASE/recalculate" -Method POST `
    -ContentType "application/json" -Body $recalc_body

Assert-Len $recalc_result.results 3 "Recalculate results"
foreach ($r in $recalc_result.results) {
    Assert-Range $r.final_score 0 100 "  App $($r.id) new score"
}

# Kiểm tra score thay đổi khi weights thay đổi
$original = $score_result.final_score
$new_score = ($recalc_result.results | Where-Object { $_.id -eq "test-app-001" }).final_score
if ($original -ne $new_score) {
    OK "Score changed after weight update: $original → $new_score"
} else {
    Write-Host "  [WARN] Score unchanged (possible if proportions stayed same)" -ForegroundColor Yellow
}

# =============================================================================
# Step 5 — POST /ai/search (NL query)
# =============================================================================
STEP "Step 5 — POST /ai/search"

# Build 3 mock applications: cv_embedding từ step 2 + 2 mock entries
$mock_cv2 = @{
    skills = @("React", "JavaScript", "CSS")
    work_experience = @(@{
        company="Frontend Co"; role="Frontend Developer"; months=24;
        end="present"; is_current=$true; tech_stack=@("React","JavaScript");
        description="Built React SPAs"
    })
    education = @(@{ institution="FPT"; degree="bachelor"; major="IT" })
    projects = @(); certifications = @(); languages = @(); awards = @()
    skill_details = @(); contact = @{}
}
$mock_cv3 = @{
    skills = @("Python", "Machine Learning", "TensorFlow", "pandas")
    work_experience = @(@{
        company="AI Lab"; role="ML Engineer"; months=36;
        end="present"; is_current=$true; tech_stack=@("Python","TensorFlow");
        description="Built ML pipelines and model training"
    })
    education = @(@{ institution="Bach Khoa"; degree="master"; major="CS" })
    projects = @(); certifications = @(); languages = @(); awards = @()
    skill_details = @(); contact = @{}
}

# Generate simple random embeddings for mock apps
$rand_emb2 = (1..384 | ForEach-Object { [Math]::Round((Get-Random -Minimum -1.0 -Maximum 1.0), 4) })
$rand_emb3 = (1..384 | ForEach-Object { [Math]::Round((Get-Random -Minimum -1.0 -Maximum 1.0), 4) })

$search_body = @{
    query = "Find .NET developer with at least 1 year experience"
    top_n_reasons = 2
    applications = @(
        @{ id = "real-cv-001"; cv_embedding = $cv_embedding; final_score = $score_result.final_score; parsed_cv = $parsed_cv },
        @{ id = "mock-cv-002"; cv_embedding = $rand_emb2;    final_score = 65.0;                       parsed_cv = $mock_cv2 },
        @{ id = "mock-cv-003"; cv_embedding = $rand_emb3;    final_score = 72.0;                       parsed_cv = $mock_cv3 }
    )
} | ConvertTo-Json -Depth 20

Write-Host "  Query: 'Find .NET developer with at least 1 year experience'" -ForegroundColor Gray
Write-Host "  Running NL search (LLM + embedding)..." -ForegroundColor Gray

$search_result = Invoke-RestMethod -Uri "$BASE/search" -Method POST `
    -ContentType "application/json" -Body $search_body

OK "Query parsed: $($search_result.query_parsed | ConvertTo-Json -Compress)"
OK "Results returned: $($search_result.results.Count)"

foreach ($r in $search_result.results) {
    $reason = if ($r.match_reason) { "→ $($r.match_reason)" } else { "(no reason)" }
    Write-Host ("  #{0,-15} score={1,6:F1}  sim={2,5:F3}  {3}" -f `
        $r.id, $r.combined_score, $r.similarity_score, $reason) -ForegroundColor White
}

# =============================================================================
# Summary
# =============================================================================
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " ALL STEPS COMPLETED" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Endpoints tested: /parse-jd, /parse-cv, /score, /recalculate, /search"
Write-Host " CV used: $CV_PATH"
Write-Host " JD: $($parsed_jd.title)"
Write-Host " Final match score: $($score_result.final_score)/100"
