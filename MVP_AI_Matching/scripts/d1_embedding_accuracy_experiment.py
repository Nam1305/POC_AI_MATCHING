"""
Thực nghiệm đo độ chính xác Phase 2 (Stage 3 — Embedding, `embedder.py`):
liệu vector do Gemini (`gemini-embedding-001`) sinh ra từ
`ParsedCV.build_embed_text()` / `ParsedJD.build_embed_text()` có phản ánh
đúng mức độ liên quan ngữ nghĩa (cùng ngành nghề vs khác ngành nghề) hay
không.

Phương pháp
-----------
Dựng 12 domain nghề nghiệp qua chính schema production
(`app.schemas.ParsedCV` / `ParsedJD`) để `build_embed_text()` chạy đúng code
path thật — mỗi domain gồm 1 JD (title + responsibilities, văn phong dài
2-5 câu như prompt LLM thật quy định) + 2 biến thể CV (cùng nội dung ứng
viên, khác cách diễn đạt). Gọi Gemini embedding thật (kết quả cache theo
hash(text + model) tại `scripts/.d1_embed_cache.json`, chạy lại không tốn
thêm API call trừ khi corpus đổi), rồi đo bằng nhiều thang đo độc lập:

  1. Ma trận cosine domain × domain (12×12)
  2. Threshold sweep + confusion matrix (cùng phương pháp với D2, xem
     `d2_layer3_threshold_experiment.py`)
  3. AUC (Mann-Whitney U) — khả năng tách biệt tổng thể, không phụ thuộc
     1 threshold cụ thể
  4. Top-1 / Top-3 retrieval accuracy — mô phỏng đúng cách D1 được dùng
     thật: xếp hạng CV theo cosine cho 1 JD
  5. Paraphrase robustness — đổi văn phong (cùng domain) có ảnh hưởng vector
     ít hơn đổi domain hay không
  6. Margin/overlap giữa lớp positive và negative

Nhãn gốc (domain nào khớp domain nào) đến từ thiết kế corpus, độc lập với
số đo cosine. 3 cặp domain được cố tình chọn "gần nhau" (Backend Developer /
DevOps-SRE, Frontend Developer / UI-UX Designer, Data Scientist / Business
Analyst) để stress-test khả năng phân biệt, không chỉ toàn cặp domain dễ
đoán.

Chạy: python scripts/d1_embedding_accuracy_experiment.py (từ repo root, cần
GEMINI_API_KEY trong .env — lần đầu gọi 36 API call thật; các lần sau đọc
cache).
Output: docs/d1_embedding_accuracy_experiment.md + .xlsx
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from _xlsx_writer import write_xlsx  # type: ignore  # noqa: E402

from app.config import settings  # noqa: E402
from app.schemas import ParsedCV, ParsedJD, Project, WorkExperience  # noqa: E402
from app.services.embedder import _embed_sync  # noqa: E402
from app.services.scorer import cosine_sim  # noqa: E402

DOCS_DIR = REPO_ROOT / "docs"
REPORT_PATH = DOCS_DIR / "d1_embedding_accuracy_experiment.md"
XLSX_PATH = DOCS_DIR / "d1_embedding_accuracy_experiment.xlsx"
CACHE_PATH = Path(__file__).resolve().parent / ".d1_embed_cache.json"

SWEEP_START, SWEEP_END, SWEEP_STEP = 0, 100, 1  # quét 0.00 .. 0.99, bước 0.01

# Cặp domain "gần nhau" cố tình chọn để stress-test khả năng phân biệt —
# đây là các negative pair khó nhất trong corpus (2 domain khác nhau nhưng
# có overlap ngữ cảnh nghiệp vụ), báo cáo riêng ở mục 3.1 thay vì trộn lẫn
# vào 264 negative pair chung.
ADJACENT_DOMAIN_PAIRS: list[tuple[str, str]] = [
    ("Backend Developer", "DevOps / SRE"),
    ("Frontend Developer", "UI/UX Designer"),
    ("Data Scientist / ML Engineer", "Business Analyst"),
]


# ---------------------------------------------------------------------------
# Corpus — 12 domain, dựng qua schema production thật
# ---------------------------------------------------------------------------

@dataclass
class CVVariant:
    summary: str
    role: str
    company: str
    description: str
    project_name: str
    project_description: str

    def build_text(self) -> str:
        cv = ParsedCV(
            summary=self.summary,
            work_experience=[WorkExperience(
                role=self.role, company=self.company, description=self.description,
            )],
            projects=[Project(name=self.project_name, description=self.project_description)],
        )
        return cv.build_embed_text()


@dataclass
class Domain:
    key: str
    jd_title: str
    jd_responsibilities: str
    cv_a: CVVariant
    cv_b: CVVariant

    def jd_text(self) -> str:
        return ParsedJD(title=self.jd_title, responsibilities=self.jd_responsibilities).build_embed_text()


DOMAINS: list[Domain] = [
    Domain(
        key="Backend Developer",
        jd_title="Backend Developer",
        jd_responsibilities=(
            "We are looking for someone to own the checkout and payment processing "
            "services that power our online retail platform. You will design and "
            "maintain the systems that handle order creation, inventory reservation, "
            "and payment settlement across multiple currencies. The role involves "
            "working closely with the platform team to keep transaction throughput "
            "reliable during high-traffic sales events, and coordinating with finance "
            "to ensure every payment is reconciled correctly. You will also be "
            "responsible for designing internal APIs that other teams depend on for "
            "order status and refund workflows."
        ),
        cv_a=CVVariant(
            summary=(
                "Backend engineer with a background in building transaction-heavy "
                "services for online retail. Comfortable owning services end to end, "
                "from initial design through production incident response, with a "
                "strong focus on data correctness in payment flows."
            ),
            role="Backend Engineer", company="Company X",
            description=(
                "Owned the order and payment settlement service for a mid-size online "
                "marketplace, redesigning the checkout flow to reduce failed "
                "transactions during flash sales. Worked with the finance team to "
                "build a reconciliation pipeline that caught discrepancies between "
                "the payment gateway and internal ledger. Coordinated a migration of "
                "the inventory reservation logic to prevent overselling during "
                "high-traffic periods."
            ),
            project_name="Checkout Reliability Overhaul",
            project_description=(
                "Redesigned the order creation pipeline to isolate payment failures "
                "from inventory holds, cutting checkout errors during peak sales by a "
                "significant margin."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Software engineer focused on the transactional core of e-commerce "
                "platforms — order management, payment settlement, and inventory "
                "accuracy. Enjoys the operational side of the job: keeping payment "
                "systems dependable when traffic spikes."
            ),
            role="Software Engineer", company="Company Y",
            description=(
                "Maintained the payment and order subsystems for a growing online "
                "store, taking ownership of currency conversion edge cases and refund "
                "handling. Partnered with the accounting group to automate settlement "
                "reconciliation, reducing manual reviews. Helped the platform team "
                "keep checkout available during a major promotional event by "
                "reworking how inventory locks were held."
            ),
            project_name="Payment Reconciliation Automation",
            project_description=(
                "Built an automated pipeline that cross-checks payment gateway "
                "records against internal orders, surfacing mismatches for the "
                "finance team same-day instead of weekly."
            ),
        ),
    ),
    Domain(
        key="DevOps / SRE",
        jd_title="DevOps / Site Reliability Engineer",
        jd_responsibilities=(
            "We need someone to own the reliability of our production infrastructure "
            "and the pipelines that ship code to it. You will be responsible for "
            "keeping deployment processes fast and safe, reducing the blast radius of "
            "failed releases, and building the observability that lets other "
            "engineering teams understand system health at a glance. The role "
            "includes leading incident response when production issues occur and "
            "driving postmortems that prevent recurrence. You will also work with "
            "engineering leads across teams to plan capacity ahead of high-traffic "
            "events."
        ),
        cv_a=CVVariant(
            summary=(
                "Infrastructure engineer with a focus on production reliability and "
                "deployment safety. Spends most of the time on the boundary between "
                "development teams and the systems that run their code, aiming to "
                "make releases boring."
            ),
            role="Site Reliability Engineer", company="Company Z",
            description=(
                "Owned the deployment pipeline for a multi-team engineering "
                "organization, introducing staged rollouts that caught failing "
                "releases before they reached all users. Led incident response for "
                "production outages, and drove the postmortem process that reduced "
                "repeat incidents quarter over quarter. Built dashboards that gave "
                "every team visibility into their service's health without needing "
                "to ask infrastructure directly."
            ),
            project_name="Zero-Downtime Deployment Pipeline",
            project_description=(
                "Reworked the release process so that failed deployments "
                "automatically rolled back before customers were affected, replacing "
                "a manual rollback process that used to take significant time to "
                "trigger."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Reliability-focused engineer who has spent recent years making sure "
                "production systems stay up and releases go out safely. Comfortable "
                "being the first responder when something breaks and turning that "
                "into a fix that prevents the next one."
            ),
            role="Platform Reliability Engineer", company="Company W",
            description=(
                "Kept a growing set of production services healthy for a mid-size "
                "engineering team, building the alerting and dashboards that let "
                "other engineers self-serve on system health. Ran point on major "
                "incidents, coordinating across teams to restore service and writing "
                "up what needed to change afterward. Helped plan infrastructure "
                "capacity ahead of the company's biggest sales event of the year."
            ),
            project_name="Incident Response Runbook Automation",
            project_description=(
                "Turned a set of manual, tribal-knowledge incident procedures into "
                "automated runbooks, cutting the time it took new on-call engineers "
                "to resolve common incidents."
            ),
        ),
    ),
    Domain(
        key="Frontend Developer",
        jd_title="Frontend Developer",
        jd_responsibilities=(
            "You will build and maintain the customer-facing dashboards our users "
            "rely on to manage their accounts day to day. The role involves "
            "translating design mockups into responsive, accessible interfaces, and "
            "working closely with the design team to refine the user experience "
            "based on usability feedback. You will also be expected to improve the "
            "performance of pages that load large amounts of user data, and to help "
            "establish shared UI patterns other teams can reuse. Close collaboration "
            "with backend teams to shape the APIs the dashboard depends on is part of "
            "the job."
        ),
        cv_a=CVVariant(
            summary=(
                "Frontend engineer who enjoys turning design mockups into interfaces "
                "that feel fast and easy to use. Has spent the last few years focused "
                "on customer-facing dashboards with heavy data density."
            ),
            role="Frontend Engineer", company="Company A",
            description=(
                "Built and maintained the primary account dashboard for a "
                "subscription product, working directly with designers to iterate on "
                "layouts based on user testing sessions. Improved page load "
                "performance for data-heavy views by restructuring how data was "
                "fetched and rendered incrementally. Established a shared component "
                "library that other product teams adopted to keep the interface "
                "consistent."
            ),
            project_name="Dashboard Performance Rework",
            project_description=(
                "Cut the load time of the main account dashboard significantly by "
                "changing how large tables of user data were fetched and rendered."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "UI-focused engineer with experience building the screens customers "
                "use most often — account settings, usage dashboards, and billing "
                "views. Cares about the details that make an interface feel polished."
            ),
            role="Web Developer", company="Company B",
            description=(
                "Owned the customer usage dashboard for a SaaS product, collaborating "
                "with the design team to simplify a cluttered interface into "
                "something new users could understand without a tutorial. Worked "
                "with backend engineers to shape API responses so the dashboard "
                "could render faster. Contributed reusable UI components that "
                "reduced how long it took other teams to build new screens."
            ),
            project_name="Design System Component Library",
            project_description=(
                "Led the creation of a shared UI component library, reducing "
                "inconsistency across the product's several customer-facing screens."
            ),
        ),
    ),
    Domain(
        key="UI/UX Designer",
        jd_title="UI/UX Designer",
        jd_responsibilities=(
            "We are looking for a designer to shape the experience of our core SaaS "
            "product, from early concept sketches through polished, "
            "production-ready screens. You will run user research and usability "
            "sessions to understand where customers get stuck, and translate those "
            "findings into interface improvements. The role involves close "
            "collaboration with product managers to prioritize design work and with "
            "engineers to make sure what ships matches the intended experience. You "
            "will also help maintain and evolve the design system that keeps the "
            "product visually consistent as it grows."
        ),
        cv_a=CVVariant(
            summary=(
                "Product designer who enjoys the full arc of a design problem, from "
                "talking to users about what's confusing to shipping the screens "
                "that fix it. Has worked mostly on SaaS products with dense, "
                "data-heavy interfaces."
            ),
            role="Product Designer", company="Company C",
            description=(
                "Led the redesign of a SaaS product's core workflow after usability "
                "sessions revealed users were dropping off midway through setup. "
                "Worked closely with product managers to prioritize which design "
                "changes would have the biggest impact on activation. Maintained the "
                "company's design system, adding new patterns as the product grew "
                "into new areas."
            ),
            project_name="Onboarding Flow Redesign",
            project_description=(
                "Redesigned the new-user onboarding flow based on usability testing "
                "findings, reducing the number of users abandoning setup partway "
                "through."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "UX designer with a research-first approach, spending as much time "
                "talking to users as sketching screens. Most recent experience is in "
                "B2B software with complex, multi-step workflows."
            ),
            role="UX/UI Designer", company="Company D",
            description=(
                "Ran usability research for a business software product, uncovering "
                "the steps in the core workflow where users consistently got "
                "confused, then designed and validated fixes. Partnered with "
                "engineering to make sure implemented screens matched the intended "
                "interactions. Contributed to the shared design system so new "
                "features stayed visually consistent with the rest of the product."
            ),
            project_name="Design System Expansion",
            project_description=(
                "Extended the product's design system with new component patterns "
                "needed to support a growing set of features without visual drift."
            ),
        ),
    ),
    Domain(
        key="Data Scientist / ML Engineer",
        jd_title="Data Scientist / Machine Learning Engineer",
        jd_responsibilities=(
            "You will build the models that help the business understand which "
            "customers are at risk of leaving and why. The role involves working "
            "with large historical usage datasets to engineer features, training and "
            "validating predictive models, and translating model output into "
            "recommendations the business teams can act on. You will partner with "
            "product and marketing stakeholders to design experiments that test "
            "whether interventions actually reduce churn. Communicating findings "
            "clearly to non-technical stakeholders is a core part of the role, not "
            "an afterthought."
        ),
        cv_a=CVVariant(
            summary=(
                "Data scientist focused on customer behavior modeling, with recent "
                "work centered on predicting and reducing churn for a subscription "
                "business. Enjoys the full loop from raw usage data to a model "
                "stakeholders trust enough to act on."
            ),
            role="Data Scientist", company="Company E",
            description=(
                "Built a churn prediction model for a subscription product, "
                "engineering features from usage and support ticket history to "
                "identify at-risk accounts weeks before cancellation. Partnered with "
                "the marketing team to design and evaluate retention campaigns "
                "targeted at high-risk segments, using controlled experiments to "
                "measure actual impact. Presented findings regularly to "
                "non-technical stakeholders, turning model output into concrete "
                "recommendations."
            ),
            project_name="Customer Churn Early-Warning System",
            project_description=(
                "Built a model that flagged at-risk subscription customers weeks in "
                "advance, giving the retention team enough lead time to intervene "
                "before cancellation."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Machine learning engineer with experience turning customer usage "
                "data into predictions the business can act on, most recently "
                "focused on retention and churn for a subscription product."
            ),
            role="ML Engineer", company="Company F",
            description=(
                "Developed and maintained a predictive model estimating customer "
                "churn risk from product usage patterns, working with the data team "
                "to keep the underlying feature pipeline reliable as usage data "
                "grew. Designed experiments with the growth team to test whether "
                "proactive outreach to at-risk customers actually improved "
                "retention. Translated technical model results into a simple risk "
                "score that non-technical stakeholders used in their daily "
                "workflow."
            ),
            project_name="Retention Experiment Framework",
            project_description=(
                "Built a lightweight experimentation framework the growth team used "
                "to test retention interventions against the churn model's risk "
                "scores."
            ),
        ),
    ),
    Domain(
        key="Business Analyst",
        jd_title="Business Analyst",
        jd_responsibilities=(
            "You will work closely with stakeholders across the business to "
            "understand their processes, identify inefficiencies, and translate "
            "business needs into clear requirements for the teams that implement "
            "changes. The role involves analyzing operational and process data to "
            "find where the business is losing time or money, and presenting "
            "recommendations that non-technical leadership can act on. You will "
            "facilitate requirements-gathering sessions, document current and "
            "proposed workflows, and track whether implemented changes actually "
            "delivered the expected improvement."
        ),
        cv_a=CVVariant(
            summary=(
                "Business analyst experienced in mapping out operational processes "
                "and finding where they break down, then working with "
                "implementation teams to fix them. Comfortable moving between "
                "spreadsheets and stakeholder conversations."
            ),
            role="Business Analyst", company="Company G",
            description=(
                "Analyzed the order fulfillment process for a retail operation, "
                "identifying a bottleneck that was costing the business days of "
                "delay per order, and documented a redesigned workflow to fix it. "
                "Facilitated requirements-gathering sessions between operations "
                "staff and the implementation team to make sure the redesign "
                "matched real day-to-day needs. Tracked the rollout afterward to "
                "confirm the fulfillment delay had actually improved."
            ),
            project_name="Fulfillment Process Redesign",
            project_description=(
                "Documented and helped implement a redesigned order fulfillment "
                "workflow that removed a recurring bottleneck in the shipping "
                "process."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Process-focused analyst who enjoys digging into how a business "
                "actually operates day to day, then finding the gap between that "
                "and how it should operate. Recent work has centered on operational "
                "efficiency projects."
            ),
            role="Process Analyst", company="Company H",
            description=(
                "Studied the inventory management process for a growing retail "
                "business, uncovering inefficiencies that were leading to frequent "
                "stock discrepancies. Worked with department leads to gather "
                "requirements for a revised process and documented the current and "
                "future workflows for the implementation team. Measured the impact "
                "of the change after rollout to confirm the discrepancy rate had "
                "dropped."
            ),
            project_name="Inventory Process Audit",
            project_description=(
                "Led an audit of the inventory management workflow that surfaced "
                "the root cause of recurring stock discrepancies and informed a "
                "process redesign."
            ),
        ),
    ),
    Domain(
        key="QA / Test Automation Engineer",
        jd_title="QA / Test Automation Engineer",
        jd_responsibilities=(
            "You will be responsible for the quality of releases going out for a "
            "financial services product, where mistakes are expensive and hard to "
            "walk back. The role involves designing test strategies that catch "
            "regressions before they reach production, building and maintaining "
            "automated test suites, and working closely with engineering to make "
            "testing part of the development process rather than a separate step "
            "at the end. You will also investigate production issues to understand "
            "whether better test coverage could have caught them earlier."
        ),
        cv_a=CVVariant(
            summary=(
                "QA engineer with a background in financial software, where the "
                "cost of a missed bug is high enough that testing has to be taken "
                "seriously. Focused on building automated coverage that catches "
                "regressions early rather than relying on manual checks before "
                "release."
            ),
            role="QA Automation Engineer", company="Company I",
            description=(
                "Built and maintained the automated test suite for a financial "
                "services platform, focusing coverage on the transaction and "
                "reconciliation flows where bugs were most costly. Worked with "
                "engineering to integrate testing earlier in the development "
                "process instead of treating it as a final gate before release. "
                "Investigated several production incidents to identify gaps in "
                "test coverage and closed them to prevent recurrence."
            ),
            project_name="Regression Suite Overhaul",
            project_description=(
                "Rebuilt the automated regression suite for the core transaction "
                "flow, catching a class of bugs that had previously reached "
                "production undetected."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Test automation engineer who has spent recent years on quality "
                "for a product where reliability really matters — a financial "
                "platform where bugs directly affect customer money."
            ),
            role="Software QA Engineer", company="Company J",
            description=(
                "Owned test coverage for the payment reconciliation module of a "
                "financial product, designing automated tests that ran on every "
                "code change instead of only before release. Partnered with "
                "developers to shift testing earlier in the workflow, reducing the "
                "number of issues found late in the release cycle. Reviewed "
                "production incidents to figure out which ones automated tests "
                "could have caught, and prioritized closing those gaps."
            ),
            project_name="Continuous Testing Pipeline",
            project_description=(
                "Set up automated tests to run on every pull request for the "
                "payment module, catching issues before they reached the release "
                "branch instead of after."
            ),
        ),
    ),
    Domain(
        key="Mobile Developer",
        jd_title="Mobile Developer (iOS/Android)",
        jd_responsibilities=(
            "You will build and maintain the rider-facing mobile app that connects "
            "passengers with drivers in real time. The role involves working on "
            "features that depend on live location data and need to stay "
            "responsive under unreliable network conditions, since many users are "
            "on the move. You will collaborate with backend teams to design the "
            "APIs that power trip matching and live tracking, and with the design "
            "team to keep the app easy to use for a broad range of users. "
            "Performance and reliability matter here more than most apps, since a "
            "broken trip request has real-world consequences for someone waiting "
            "on the street."
        ),
        cv_a=CVVariant(
            summary=(
                "Mobile engineer with experience building consumer apps that "
                "depend on real-time location and need to stay reliable on flaky "
                "mobile networks. Most recent work has been on a ride-hailing "
                "style app used by a broad, non-technical user base."
            ),
            role="Mobile Engineer", company="Company K",
            description=(
                "Built the live trip-tracking feature for a ride-hailing app, "
                "handling the edge cases that come with unreliable mobile networks "
                "and background location updates. Worked with backend engineers to "
                "design an API for trip matching that stayed responsive even "
                "during high-demand periods like rush hour. Improved app stability "
                "for lower-end devices, which made up a meaningful share of the "
                "user base."
            ),
            project_name="Real-Time Trip Tracking",
            project_description=(
                "Built the feature showing riders their driver's live location, "
                "designed to degrade gracefully instead of breaking when the "
                "connection dropped mid-trip."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "iOS/Android developer with a focus on location-based consumer "
                "apps where reliability under poor network conditions is part of "
                "the job, not an edge case. Comes from a background building for a "
                "mobile-first, sometimes non-technical audience."
            ),
            role="App Developer", company="Company L",
            description=(
                "Maintained the trip request and matching flow for a ride-hailing "
                "app, working through the reliability challenges of real-time "
                "location updates over unstable mobile connections. Partnered "
                "with the backend team to keep the trip-matching API fast during "
                "peak demand windows. Worked with design to simplify the trip "
                "request flow for users unfamiliar with app-based services."
            ),
            project_name="Offline-Tolerant Trip Requests",
            project_description=(
                "Reworked the trip request flow to queue and retry automatically "
                "when the connection dropped, instead of forcing the rider to "
                "start over."
            ),
        ),
    ),
    Domain(
        key="Technical Recruiter",
        jd_title="Technical Recruiter",
        jd_responsibilities=(
            "You will own the hiring pipeline for engineering roles, from "
            "sourcing candidates through offer negotiation. The role involves "
            "partnering closely with engineering managers to understand what each "
            "role actually needs, not just the job description, and translating "
            "that into a sourcing and screening strategy. You will manage "
            "candidates through the process, keep the pipeline moving without "
            "sacrificing quality, and represent the company well throughout what "
            "is often a candidate's first real impression of the organization. "
            "Tracking pipeline metrics to spot where candidates are dropping off "
            "is part of the job."
        ),
        cv_a=CVVariant(
            summary=(
                "Technical recruiter who has spent the last few years hiring for "
                "engineering teams, from individual contributors through senior "
                "roles. Focused on understanding what a hiring manager actually "
                "needs rather than just working off the job description."
            ),
            role="Technical Recruiter", company="Company M",
            description=(
                "Owned full-cycle recruiting for a growing engineering "
                "organization, partnering with hiring managers to refine role "
                "requirements before sourcing began. Managed candidates through "
                "the interview process, working to keep the pipeline moving while "
                "protecting the quality bar the team cared about. Tracked drop-off "
                "at each pipeline stage and used that data to fix a screening step "
                "that was losing strong candidates."
            ),
            project_name="Interview Process Redesign",
            project_description=(
                "Reworked the technical interview process after pipeline data "
                "showed strong candidates were dropping off at a particular "
                "stage, improving the offer-acceptance rate."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Recruiter focused on engineering hiring, comfortable managing a "
                "high-volume pipeline while still giving each candidate a good "
                "experience. Enjoys the partnership side of the job — working with "
                "hiring managers to figure out what a role really needs."
            ),
            role="Talent Acquisition Specialist", company="Company N",
            description=(
                "Ran the hiring pipeline for several engineering teams "
                "simultaneously, working with each hiring manager to align on "
                "role requirements before sourcing candidates. Kept candidates "
                "informed and moving through the process without letting quality "
                "slip under pipeline volume pressure. Analyzed where in the "
                "process candidates were dropping off and adjusted the screening "
                "approach based on what the data showed."
            ),
            project_name="Candidate Pipeline Analytics",
            project_description=(
                "Built a simple tracking process for pipeline drop-off by stage, "
                "which surfaced a screening bottleneck the team hadn't noticed."
            ),
        ),
    ),
    Domain(
        key="Business Development Representative",
        jd_title="Business Development Representative",
        jd_responsibilities=(
            "You will be responsible for generating and qualifying new business "
            "opportunities for our B2B SaaS product. The role involves researching "
            "target accounts, reaching out to prospective customers, and "
            "understanding enough about their business to know whether our "
            "product is actually a good fit before handing off to the account "
            "executive team. You will need to handle rejection well, keep a "
            "disciplined outreach cadence, and continuously refine your pitch "
            "based on what resonates with different types of prospects. Accurate "
            "pipeline tracking and forecasting are expected as part of the role."
        ),
        cv_a=CVVariant(
            summary=(
                "Business development professional focused on the early stage of "
                "the B2B sales funnel — finding the right accounts and starting "
                "the conversation that eventually becomes a deal. Comfortable with "
                "a high-volume outreach cadence and quick at qualifying whether a "
                "prospect is worth pursuing."
            ),
            role="Business Development Representative", company="Company O",
            description=(
                "Generated and qualified new business opportunities for a B2B "
                "SaaS product, researching target accounts before reaching out to "
                "make sure outreach felt relevant rather than generic. Refined the "
                "outreach pitch over time based on which messaging actually got "
                "prospects to respond. Handed off qualified opportunities to "
                "account executives with enough context that the next "
                "conversation didn't start from zero."
            ),
            project_name="Outbound Cadence Optimization",
            project_description=(
                "Tested and refined the outbound messaging sequence, improving "
                "the rate at which cold outreach turned into a qualified "
                "conversation."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Sales development professional experienced in the top of the "
                "funnel for B2B software — sourcing accounts, starting "
                "conversations, and figuring out quickly whether there's a real "
                "fit before involving the rest of the sales team."
            ),
            role="Sales Development Representative", company="Company P",
            description=(
                "Owned outbound prospecting for a B2B software product, "
                "researching accounts to prioritize outreach toward companies "
                "that actually matched the ideal customer profile. Kept a "
                "disciplined follow-up cadence with prospects and tracked "
                "pipeline activity closely enough to forecast handoffs to account "
                "executives accurately. Iterated on the pitch based on which "
                "angles resonated with different industries."
            ),
            project_name="Ideal Customer Profile Refinement",
            project_description=(
                "Worked with sales leadership to sharpen the ideal customer "
                "profile based on which prospects actually converted, improving "
                "how outreach time was targeted."
            ),
        ),
    ),
    Domain(
        key="Cost Accountant",
        jd_title="Cost Accountant",
        jd_responsibilities=(
            "You will be responsible for tracking and controlling production "
            "costs across our manufacturing operation. The role involves "
            "analyzing cost data to identify where the business is overspending "
            "relative to budget, working with plant management to understand the "
            "operational reasons behind cost variances, and preparing reports "
            "that give leadership a clear picture of production economics. You "
            "will also be involved in setting standard costs for new products and "
            "reviewing them periodically as production processes change."
        ),
        cv_a=CVVariant(
            summary=(
                "Cost accountant with experience in manufacturing environments, "
                "focused on making sure production spend stays aligned with "
                "budget and that variances get explained rather than just "
                "reported."
            ),
            role="Cost Accountant", company="Company Q",
            description=(
                "Tracked production costs across several manufacturing lines, "
                "identifying a recurring variance that turned out to be caused by "
                "an outdated standard cost assumption. Worked with plant "
                "management to understand the operational drivers behind cost "
                "overruns before reporting them to leadership. Reviewed and "
                "updated standard costs for a set of products after a change in "
                "the production process made the old figures inaccurate."
            ),
            project_name="Standard Cost Revision Project",
            project_description=(
                "Led a review of standard costs across a product line after "
                "production changes made existing figures outdated, correcting a "
                "persistent budget variance."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Manufacturing-focused accountant who spends most of the time in "
                "production cost data, looking for where actual spend diverges "
                "from plan and why. Works closely with plant operations to get "
                "past the numbers to the underlying cause."
            ),
            role="Manufacturing Accountant", company="Company R",
            description=(
                "Prepared monthly cost variance reports for a manufacturing "
                "plant, digging into the operational side with plant supervisors "
                "whenever a variance couldn't be explained by the numbers alone. "
                "Helped set standard costs for several new product lines, "
                "coordinating with operations to make sure assumptions matched "
                "actual production conditions. Presented production economics to "
                "leadership in a way that connected cost trends to specific "
                "operational decisions."
            ),
            project_name="Cost Variance Investigation Process",
            project_description=(
                "Built a lightweight process for investigating cost variances "
                "with plant management before they were reported, reducing how "
                "often reported variances turned out to be data errors."
            ),
        ),
    ),
    Domain(
        key="Content Marketing Specialist",
        jd_title="Content Marketing Specialist",
        jd_responsibilities=(
            "You will own the content strategy that drives brand awareness and "
            "customer acquisition for our e-commerce business. The role involves "
            "planning and producing content across channels, understanding what "
            "resonates with our target customer, and using performance data to "
            "double down on what works. You will collaborate with the design and "
            "growth teams to align content with broader marketing campaigns, and "
            "be comfortable adjusting strategy based on what the numbers say "
            "rather than sticking to a fixed content calendar out of habit."
        ),
        cv_a=CVVariant(
            summary=(
                "Content marketer with experience growing brand awareness and "
                "driving acquisition for an e-commerce business. Spends as much "
                "time looking at performance data as writing, using it to figure "
                "out what to make more of."
            ),
            role="Content Marketing Specialist", company="Company S",
            description=(
                "Owned the content calendar for an e-commerce brand, producing "
                "content across channels aimed at both awareness and direct "
                "customer acquisition. Used performance data to identify which "
                "content formats were actually driving traffic and sales, "
                "shifting strategy away from formats that looked good but "
                "underperformed. Collaborated with the design team to align "
                "content with seasonal marketing campaigns."
            ),
            project_name="Content Performance Overhaul",
            project_description=(
                "Rebuilt the content strategy around performance data instead of "
                "a fixed calendar, shifting investment toward the formats that "
                "were actually driving customer acquisition."
            ),
        ),
        cv_b=CVVariant(
            summary=(
                "Marketing professional focused on content and brand growth for "
                "online retail, comfortable moving between planning a content "
                "calendar and digging into the analytics behind why something "
                "worked or didn't."
            ),
            role="Marketing Specialist", company="Company T",
            description=(
                "Produced content across multiple channels for an online retail "
                "brand, working with the growth team to make sure content efforts "
                "supported broader acquisition campaigns rather than running "
                "separately. Regularly reviewed content performance data to "
                "reallocate effort toward higher-performing formats. Partnered "
                "with design to keep content visually consistent with the "
                "brand's other marketing materials."
            ),
            project_name="Cross-Channel Content Calendar",
            project_description=(
                "Built a unified content calendar spanning multiple channels, "
                "replacing a previously disconnected process and making it "
                "easier to align content with active marketing campaigns."
            ),
        ),
    ),
]


# ---------------------------------------------------------------------------
# Embedding — gọi Gemini thật, cache theo hash(text + model)
# ---------------------------------------------------------------------------

def _cache_key(text: str) -> str:
    return hashlib.sha256(f"{settings.gemini_embed_model}::{text}".encode()).hexdigest()


def _load_cache() -> dict[str, list[float]]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, list[float]]) -> None:
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")


def embed_all(texts: dict[str, str]) -> tuple[dict[str, list[float]], int, int]:
    """texts: {label: text}. Trả về (vectors theo label, số cache-hit, số API call mới)."""
    cache = _load_cache()
    vectors: dict[str, list[float]] = {}
    hits = misses = 0
    for i, (label, text) in enumerate(texts.items(), start=1):
        key = _cache_key(text)
        if key in cache:
            vectors[label] = cache[key]
            hits += 1
            print(f"  [{i}/{len(texts)}] {label} — cache hit")
        else:
            vectors[label] = _embed_sync(text)
            cache[key] = vectors[label]
            misses += 1
            print(f"  [{i}/{len(texts)}] {label} — gọi Gemini API")
    _save_cache(cache)
    return vectors, hits, misses


# ---------------------------------------------------------------------------
# Thang đo 1-2: threshold sweep + confusion matrix (cùng pattern D2)
# ---------------------------------------------------------------------------

@dataclass
class SweepRow:
    threshold: float
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 1.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / total if total else 1.0

    @property
    def error_rate(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.fp + self.fn) / total if total else 0.0


def sweep_thresholds(pos: list[float], neg: list[float]) -> list[SweepRow]:
    rows = []
    for i in range(SWEEP_START, SWEEP_END, SWEEP_STEP):
        t = i / 100
        tp = sum(1 for c in pos if c >= t)
        fn = len(pos) - tp
        fp = sum(1 for c in neg if c >= t)
        tn = len(neg) - fp
        rows.append(SweepRow(t, tp, fp, tn, fn))
    return rows


# ---------------------------------------------------------------------------
# Thang đo 3: AUC qua Mann-Whitney U (thuần Python, không phụ thuộc numpy/scipy)
# ---------------------------------------------------------------------------

def auc_mann_whitney(pos: list[float], neg: list[float]) -> float:
    combined = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg], key=lambda x: x[0])
    n = len(combined)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2  # 1-indexed, trung bình hạng cho các giá trị bằng nhau
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    rank_sum_pos = sum(r for (_, label), r in zip(combined, ranks) if label == 1)
    n_pos, n_neg = len(pos), len(neg)
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2
    return u / (n_pos * n_neg)


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _text_stats(text: str) -> tuple[int, int, int]:
    """(số ký tự, số từ, số câu ước lượng) — số câu đếm thô qua dấu . ! ?"""
    chars = len(text)
    words = len(text.split())
    sentences = max(sum(text.count(c) for c in ".!?"), 1)
    return chars, words, sentences


_TEXT_LABELS = (("jd", "JD"), ("cv_a", "CV variant A"), ("cv_b", "CV variant B"))


def render_corpus_texts_md(domains: list[Domain], texts: dict[str, str]) -> str:
    """In toàn bộ text thật đưa đi embed (nguyên văn output build_embed_text())
    kèm số ký tự/từ/câu, để đối chiếu bằng mắt với build_embed_text() thật và
    với độ dài mà prompt LLM (parser.py) quy định (summary 2-3 câu, work
    experience description 2-4 câu, JD responsibilities 2-5 câu)."""
    blocks = []
    for d in domains:
        blocks.append(f"### {d.key}")
        for key, label in _TEXT_LABELS:
            text = texts[f"{key}::{d.key}"]
            chars, words, sentences = _text_stats(text)
            blocks.append(
                f"**{label}** — {chars} ký tự, {words} từ, ~{sentences} câu "
                f"(nguyên văn output `build_embed_text()`):\n\n```\n{text}\n```"
            )
    return "\n\n".join(blocks)


def corpus_stats_table_md(domains: list[Domain], texts: dict[str, str]) -> str:
    lines = ["| Domain | Loại | Ký tự | Từ | Câu (ước lượng) |", "| --- | --- | --- | --- | --- |"]
    for d in domains:
        for key, label in _TEXT_LABELS:
            c, w, s = _text_stats(texts[f"{key}::{d.key}"])
            lines.append(f"| {d.key} | {label} | {c} | {w} | {s} |")
    return "\n".join(lines)


def corpus_texts_sheet_rows(domains: list[Domain], texts: dict[str, str]) -> list[list]:
    rows = [["Domain", "Loại", "Ký tự", "Từ", "Câu (ước lượng)", "Text đầy đủ (build_embed_text())"]]
    for d in domains:
        for key, label in _TEXT_LABELS:
            text = texts[f"{key}::{d.key}"]
            c, w, s = _text_stats(text)
            rows.append([d.key, label, c, w, s, text])
    return rows


def render_domain_matrix(domains: list[Domain], vectors: dict[str, list[float]]) -> str:
    header = "| JD \\ CV | " + " | ".join(d.key for d in domains) + " |"
    sep = "| --- | " + " | ".join("---" for _ in domains) + " |"
    lines = [header, sep]
    for jd in domains:
        row = [jd.key]
        for cv in domains:
            c_a = cosine_sim(vectors[f"jd::{jd.key}"], vectors[f"cv_a::{cv.key}"])
            c_b = cosine_sim(vectors[f"jd::{jd.key}"], vectors[f"cv_b::{cv.key}"])
            avg = (c_a + c_b) / 2
            cell = f"**{avg:.3f}**" if jd.key == cv.key else f"{avg:.3f}"
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def domain_matrix_sheet_rows(domains: list[Domain], vectors: dict[str, list[float]]) -> list[list]:
    rows = [["JD \\ CV"] + [d.key for d in domains]]
    for jd in domains:
        row = [jd.key]
        for cv in domains:
            c_a = cosine_sim(vectors[f"jd::{jd.key}"], vectors[f"cv_a::{cv.key}"])
            c_b = cosine_sim(vectors[f"jd::{jd.key}"], vectors[f"cv_b::{cv.key}"])
            row.append(round((c_a + c_b) / 2, 3))
        rows.append(row)
    return rows


def render_sweep_table(rows: list[SweepRow]) -> str:
    lines = [
        "| Threshold | TP | FP | TN | FN | Precision | Recall | F1 | Accuracy | |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    best_f1 = max(r.f1 for r in rows)
    for r in rows:
        mark = "**← F1 cao nhất**" if abs(r.f1 - best_f1) < 1e-9 else ""
        lines.append(
            f"| {r.threshold:.2f} | {r.tp} | {r.fp} | {r.tn} | {r.fn} | "
            f"{r.precision:.3f} | {r.recall:.3f} | {r.f1:.3f} | {r.accuracy:.3f} | {mark} |"
        )
    return "\n".join(lines)


def sweep_sheet_rows(rows: list[SweepRow]) -> list[list]:
    out = [["Threshold", "TP", "FP", "TN", "FN", "Precision", "Recall", "F1", "Accuracy"]]
    for r in rows:
        out.append([r.threshold, r.tp, r.fp, r.tn, r.fn,
                    round(r.precision, 3), round(r.recall, 3), round(r.f1, 3), round(r.accuracy, 3)])
    return out


def main() -> None:
    print(f"Đang chuẩn bị embed {len(DOMAINS)} domain × (1 JD + 2 CV) = {len(DOMAINS) * 3} đoạn text...")

    texts: dict[str, str] = {}
    for d in DOMAINS:
        texts[f"jd::{d.key}"] = d.jd_text()
        texts[f"cv_a::{d.key}"] = d.cv_a.build_text()
        texts[f"cv_b::{d.key}"] = d.cv_b.build_text()

    vectors, hits, misses = embed_all(texts)
    print(f"Xong: {hits} lấy từ cache, {misses} gọi API mới.\n")

    # --- Positive / negative pairs ---
    positive: list[tuple[str, str, float]] = []   # (jd_domain, cv_label, cosine)
    negative: list[tuple[str, str, float]] = []
    for jd in DOMAINS:
        jd_vec = vectors[f"jd::{jd.key}"]
        for cv in DOMAINS:
            for variant in ("cv_a", "cv_b"):
                cos = cosine_sim(jd_vec, vectors[f"{variant}::{cv.key}"])
                if jd.key == cv.key:
                    positive.append((jd.key, f"{cv.key} ({variant})", cos))
                else:
                    negative.append((jd.key, f"{cv.key} ({variant})", cos))

    pos_cosines = [c for _, _, c in positive]
    neg_cosines = [c for _, _, c in negative]

    # --- Threshold sweep + AUC ---
    rows = sweep_thresholds(pos_cosines, neg_cosines)
    best = max(rows, key=lambda r: r.f1)
    auc = auc_mann_whitney(pos_cosines, neg_cosines)

    # --- Top-1 / Top-3 retrieval ---
    top1_hits = top3_hits = 0
    retrieval_rows: list[list] = [["JD domain", "Rank-1 CV domain", "Rank-1 cosine", "Đúng top-1?", "Đúng trong top-3?"]]
    for jd in DOMAINS:
        jd_vec = vectors[f"jd::{jd.key}"]
        candidates = []
        for cv in DOMAINS:
            for variant in ("cv_a", "cv_b"):
                cos = cosine_sim(jd_vec, vectors[f"{variant}::{cv.key}"])
                candidates.append((cv.key, variant, cos))
        candidates.sort(key=lambda x: x[2], reverse=True)
        top1 = candidates[0][0] == jd.key
        top3 = any(c[0] == jd.key for c in candidates[:3])
        top1_hits += int(top1)
        top3_hits += int(top3)
        retrieval_rows.append([jd.key, candidates[0][0], round(candidates[0][2], 3),
                                "✅" if top1 else "❌", "✅" if top3 else "❌"])
    top1_acc = top1_hits / len(DOMAINS)
    top3_acc = top3_hits / len(DOMAINS)

    # --- Paraphrase robustness ---
    within_domain = [cosine_sim(vectors[f"cv_a::{d.key}"], vectors[f"cv_b::{d.key}"]) for d in DOMAINS]
    cross_domain_cv = [
        cosine_sim(vectors[f"cv_a::{a.key}"], vectors[f"cv_a::{b.key}"])
        for idx, a in enumerate(DOMAINS) for b in DOMAINS[idx + 1:]
    ]
    within_min, within_mean = min(within_domain), sum(within_domain) / len(within_domain)
    cross_max, cross_mean = max(cross_domain_cv), sum(cross_domain_cv) / len(cross_domain_cv)
    paraphrase_ok = sum(1 for w in within_domain if w > cross_max)

    # --- Margin / overlap ---
    pos_min, pos_max = min(pos_cosines), max(pos_cosines)
    neg_min, neg_max = min(neg_cosines), max(neg_cosines)
    pos_mean = sum(pos_cosines) / len(pos_cosines)
    neg_mean = sum(neg_cosines) / len(neg_cosines)
    margin = pos_min - neg_max
    confusable_pos = sum(1 for c in pos_cosines if c <= neg_max)
    confusable_neg = sum(1 for c in neg_cosines if c >= pos_min)

    # Cặp domain "gần nhau" — negative pair khó nhất trong corpus, cả 2 chiều.
    adjacent_detail: list[tuple[str, str, float]] = []
    for dom_a, dom_b in ADJACENT_DOMAIN_PAIRS:
        for jd_key, cv_key in ((dom_a, dom_b), (dom_b, dom_a)):
            jd_vec = vectors[f"jd::{jd_key}"]
            cos_a = cosine_sim(jd_vec, vectors[f"cv_a::{cv_key}"])
            cos_b = cosine_sim(jd_vec, vectors[f"cv_b::{cv_key}"])
            adjacent_detail.append((jd_key, cv_key, (cos_a + cos_b) / 2))
    adjacent_sheet = [["JD domain", "CV domain (gần nhau)", "Cosine trung bình"]] + [
        [a, b, round(c, 3)] for a, b, c in adjacent_detail
    ]
    adjacent_max = max(c for _, _, c in adjacent_detail)
    adjacent_above_margin = sum(1 for _, _, c in adjacent_detail if c >= pos_min)

    positive_sheet = [["JD domain", "CV (variant)", "Cosine"]] + [[a, b, round(c, 3)] for a, b, c in positive]
    negative_sheet = [["JD domain", "CV (variant)", "Cosine"]] + [[a, b, round(c, 3)] for a, b, c in negative]
    paraphrase_sheet = [["Domain", "cosine(CV_A, CV_B) cùng domain"]] + [
        [d.key, round(w, 3)] for d, w in zip(DOMAINS, within_domain)
    ]
    summary_sheet = [
        ["Metric", "Giá trị"],
        ["Số domain", len(DOMAINS)],
        ["Số positive pairs", len(positive)],
        ["Số negative pairs", len(negative)],
        ["AUC (Mann-Whitney)", round(auc, 4)],
        ["F1 tốt nhất", round(best.f1, 3)],
        ["Threshold F1 tốt nhất", best.threshold],
        ["Precision @ threshold tốt nhất", round(best.precision, 3)],
        ["Recall @ threshold tốt nhất", round(best.recall, 3)],
        ["Top-1 retrieval accuracy", round(top1_acc, 3)],
        ["Top-3 retrieval accuracy", round(top3_acc, 3)],
        ["Positive cosine mean", round(pos_mean, 3)],
        ["Positive cosine min", round(pos_min, 3)],
        ["Negative cosine mean", round(neg_mean, 3)],
        ["Negative cosine max", round(neg_max, 3)],
        ["Margin (pos_min - neg_max)", round(margin, 3)],
        ["Positive pairs rơi vào vùng chồng lấn", confusable_pos],
        ["Negative pairs rơi vào vùng chồng lấn", confusable_neg],
        ["Paraphrase cosine trung bình (cùng domain)", round(within_mean, 3)],
        ["Cross-domain CV-CV cosine trung bình", round(cross_mean, 3)],
        ["Paraphrase > mọi cross-domain CV-CV?", f"{paraphrase_ok}/{len(DOMAINS)}"],
    ]

    report = f"""# Thực nghiệm: độ chính xác Phase 2 (Stage 3 — Embedding)

Sinh tự động bởi `scripts/d1_embedding_accuracy_experiment.py`. Kiểm chứng
bằng số liệu xem vector do `gemini-embedding-001` sinh ra từ
`ParsedCV.build_embed_text()` / `ParsedJD.build_embed_text()` (xem
[`app/services/embedder.py`](../app/services/embedder.py),
[`app/schemas.py`](../app/schemas.py)) có phản ánh đúng mức độ liên quan
ngữ nghĩa (cùng ngành nghề vs khác ngành nghề) hay không.

## 1. Phương pháp

- **Corpus**: {len(DOMAINS)} domain nghề nghiệp, mỗi domain gồm 1 JD (title +
  responsibilities, 2-5 câu, không liệt kê tên công nghệ trần trụi — đúng
  quy ước `build_embed_text()` hiện dùng) và 2 biến thể CV cùng nội dung ứng
  viên nhưng diễn đạt khác nhau. Text dựng qua chính schema production
  (`ParsedCV`/`ParsedJD`), không viết tay chuỗi mô phỏng, để đo đúng code
  path thật.
- 3 cặp domain được **cố tình chọn gần nhau** để stress-test khả năng phân
  biệt: Backend Developer / DevOps-SRE, Frontend Developer / UI-UX Designer,
  Data Scientist / Business Analyst.
- Gọi Gemini embedding **thật** cho {len(texts)} đoạn text duy nhất (cache
  theo hash text+model tại `scripts/.d1_embed_cache.json`), tính `cosine_sim`
  (hàm gốc trong `scorer.py`) cho mọi cặp JD×CV.
- **Positive pairs** ({len(positive)}): JD và CV cùng domain. **Negative
  pairs** ({len(negative)}): JD và CV khác domain. Nhãn đến từ thiết kế
  corpus, độc lập với cosine đo được.
- Lần chạy này: {hits} vector lấy từ cache, {misses} vector gọi API mới.

## 2. Corpus — text thật đưa đi embed

Toàn bộ {len(texts)} đoạn text dưới đây là **nguyên văn output của
`build_embed_text()`** (gọi trực tiếp trên object `ParsedCV`/`ParsedJD` thật,
không viết tay) — đúng những gì `embedder.embed()` nhận vào ở production. Đối
chiếu với quy định độ dài trong prompt LLM hiện dùng (`app/services/parser.py`):
summary CV 2-3 câu, mô tả work_experience 2-4 câu, responsibilities của JD
2-5 câu — bảng số liệu dưới đây cho thấy corpus nằm trong đúng khoảng đó.

### 2.1 Thống kê độ dài

{corpus_stats_table_md(DOMAINS, texts)}

### 2.2 Toàn văn từng đoạn text

{render_corpus_texts_md(DOMAINS, texts)}

## 3. Ma trận cosine domain × domain (đường chéo = cùng domain)

{render_domain_matrix(DOMAINS, vectors)}

## 4. Cặp domain gần nhau — stress test khả năng phân biệt

3 cặp domain được cố tình chọn có overlap ngữ cảnh nghiệp vụ (không phải cặp
domain xa nhau dễ đoán): Backend Developer / DevOps-SRE, Frontend Developer /
UI-UX Designer, Data Scientist / Business Analyst. Đây là các negative pair
**khó nhất** trong toàn bộ corpus — cosine của chúng nên vẫn thấp hơn
`pos_min` ({pos_min:.3f}) nếu embedding thực sự phân biệt được domain thay vì
chỉ bám overlap từ vựng nghiệp vụ.

| JD domain | CV domain (gần nhau) | Cosine trung bình |
| --- | --- | --- |
{chr(10).join(f"| {a} | {b} | {c:.3f} |" for a, b, c in adjacent_detail)}

Cosine cao nhất trong nhóm này: **{adjacent_max:.3f}**. {adjacent_above_margin}/{len(adjacent_detail)}
cặp có cosine ≥ `pos_min` (tức có thể lẫn với 1 positive pair thật nếu chỉ
xét riêng cosine, không xét ngữ cảnh domain).

## 5. Threshold sweep — confusion matrix trên {len(positive)} positive / {len(negative)} negative

{render_sweep_table(rows)}

**F1 cao nhất = {best.f1:.3f} tại threshold {best.threshold:.2f}**
(precision {best.precision:.3f}, recall {best.recall:.3f}, accuracy {best.accuracy:.3f}).

## 6. AUC (Mann-Whitney U)

**AUC = {auc:.4f}** — xác suất 1 cặp JD-CV cùng domain (positive) có cosine
cao hơn 1 cặp khác domain (negative) chọn ngẫu nhiên, không phụ thuộc vào
việc chọn threshold nào. AUC = 1.0 là tách biệt hoàn hảo, AUC = 0.5 là
không tốt hơn đoán ngẫu nhiên.

## 7. Top-1 / Top-3 retrieval accuracy

Với mỗi JD, xếp hạng toàn bộ {len(DOMAINS) * 2} CV (2 biến thể × {len(DOMAINS)}
domain) theo cosine giảm dần — mô phỏng đúng cách D1 được dùng thật (rank CV
cho 1 JD), khác với threshold sweep chỉ đo phân loại cặp đơn lẻ.

- **Top-1 accuracy = {top1_acc:.3f}** ({top1_hits}/{len(DOMAINS)}) — tỉ lệ JD
  có CV cùng domain xếp hạng 1.
- **Top-3 accuracy = {top3_acc:.3f}** ({top3_hits}/{len(DOMAINS)}) — tỉ lệ JD
  có ít nhất 1 CV cùng domain nằm trong top-3.

{chr(10).join(f"- {r[0]}: rank-1 = {r[1]} (cosine {r[2]}) — top-1 {r[3]}, top-3 {r[4]}" for r in retrieval_rows[1:])}

## 8. Paraphrase robustness — đổi văn phong vs đổi domain

- Cosine trung bình khi **đổi văn phong, giữ nguyên domain** (CV_A vs CV_B
  cùng domain): **{within_mean:.3f}** (min {within_min:.3f}).
- Cosine trung bình khi **đổi domain** (CV_A domain này vs CV_A domain khác):
  **{cross_mean:.3f}** (max {cross_max:.3f}).
- {paraphrase_ok}/{len(DOMAINS)} domain có cosine paraphrase (cùng domain, khác
  văn phong) **cao hơn mọi** cặp cross-domain CV-CV — nếu đạt {len(DOMAINS)}/{len(DOMAINS)}
  nghĩa là đổi cách diễn đạt luôn ảnh hưởng vector ít hơn đổi ngành nghề, đúng
  kỳ vọng của một embedding nắm bắt ngữ nghĩa thay vì chỉ bám từ vựng bề mặt.

## 9. Margin / overlap giữa 2 lớp

| Metric | Positive (cùng domain) | Negative (khác domain) |
| --- | --- | --- |
| Mean | {pos_mean:.3f} | {neg_mean:.3f} |
| Min | {pos_min:.3f} | {neg_min:.3f} |
| Max | {pos_max:.3f} | {neg_max:.3f} |

Margin (min(positive) − max(negative)) = **{margin:.3f}**
({"không chồng lấn — tách biệt hoàn toàn" if margin > 0 else "có vùng chồng lấn"}).
{confusable_pos} positive pairs rơi vào vùng chồng lấn (cosine ≤ max(negative));
{confusable_neg} negative pairs rơi vào vùng chồng lấn (cosine ≥ min(positive)).

**Ghi chú phụ (không phải kết luận chính của Phase 2):** `COSINE_MIN`/
`COSINE_MAX` mặc định trong `app/config.py` hiện là 0.0/1.0 (không kéo giãn).
Nếu muốn D1 tận dụng hết thang điểm 0-1 sau khi cosine đã tách biệt tốt ở
thực nghiệm này, có thể cân nhắc hiệu chỉnh 2 hằng số đó theo phân phối
positive/negative quan sát được ở mục 9 — đây là việc của tầng scoring
(`normalize_cosine` trong `scorer.py`), nằm ngoài phạm vi Phase 2/embedding.

## 10. Kết luận

{"Embedding tách biệt tốt cặp cùng-domain khỏi khác-domain trên corpus này (AUC " + f"{auc:.4f}" + ", margin dương)." if margin > 0 and auc > 0.9 else "Embedding có xu hướng tách biệt cặp cùng-domain khỏi khác-domain (AUC " + f"{auc:.4f}" + f"), nhưng còn {confusable_pos + confusable_neg} pair rơi vào vùng chồng lấn — xem mục 9 để biết cặp nào."}
Top-1 retrieval accuracy {top1_acc:.3f} cho thấy khi dùng D1 để xếp hạng CV
cho 1 JD, CV đúng domain {"luôn" if top1_acc == 1.0 else "thường"} xuất hiện ở
vị trí đầu — kể cả với 3 cặp domain cố tình chọn gần nhau (Backend/DevOps,
Frontend/UI-UX, Data Scientist/Business Analyst).

---
*Tái tạo báo cáo này: `python scripts/d1_embedding_accuracy_experiment.py`
(cần `GEMINI_API_KEY` trong `.env`; lần đầu gọi {len(texts)} API call thật,
các lần sau đọc cache `scripts/.d1_embed_cache.json`).*
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    write_xlsx(XLSX_PATH, {
        "Summary": summary_sheet,
        "Corpus texts": corpus_texts_sheet_rows(DOMAINS, texts),
        "Domain Matrix": domain_matrix_sheet_rows(DOMAINS, vectors),
        "Adjacent domains (stress test)": adjacent_sheet,
        "Positive pairs": positive_sheet,
        "Negative pairs": negative_sheet,
        "Threshold sweep": sweep_sheet_rows(rows),
        "Retrieval (top-1/top-3)": retrieval_rows,
        "Paraphrase robustness": paraphrase_sheet,
    })

    print(f"Đã ghi báo cáo vào {REPORT_PATH}")
    print(f"Đã ghi Excel vào {XLSX_PATH}")
    print(f"AUC = {auc:.4f} | F1 tốt nhất = {best.f1:.3f} @ threshold={best.threshold:.2f}")
    print(f"Top-1 accuracy = {top1_acc:.3f} | Top-3 accuracy = {top3_acc:.3f}")


if __name__ == "__main__":
    main()
