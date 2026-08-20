# Thực nghiệm: độ chính xác Phase 2 (Stage 3 — Embedding)

Sinh tự động bởi `scripts/d1_embedding_accuracy_experiment.py`. Kiểm chứng
bằng số liệu xem vector do `gemini-embedding-001` sinh ra từ
`ParsedCV.build_embed_text()` / `ParsedJD.build_embed_text()` (xem
[`app/services/embedder.py`](../app/services/embedder.py),
[`app/schemas.py`](../app/schemas.py)) có phản ánh đúng mức độ liên quan
ngữ nghĩa (cùng ngành nghề vs khác ngành nghề) hay không.

## 1. Phương pháp

- **Corpus**: 12 domain nghề nghiệp, mỗi domain gồm 1 JD (title +
  responsibilities, 2-5 câu, không liệt kê tên công nghệ trần trụi — đúng
  quy ước `build_embed_text()` hiện dùng) và 2 biến thể CV cùng nội dung ứng
  viên nhưng diễn đạt khác nhau. Text dựng qua chính schema production
  (`ParsedCV`/`ParsedJD`), không viết tay chuỗi mô phỏng, để đo đúng code
  path thật.
- 3 cặp domain được **cố tình chọn gần nhau** để stress-test khả năng phân
  biệt: Backend Developer / DevOps-SRE, Frontend Developer / UI-UX Designer,
  Data Scientist / Business Analyst.
- Gọi Gemini embedding **thật** cho 36 đoạn text duy nhất (cache
  theo hash text+model tại `scripts/.d1_embed_cache.json`), tính `cosine_sim`
  (hàm gốc trong `scorer.py`) cho mọi cặp JD×CV.
- **Positive pairs** (24): JD và CV cùng domain. **Negative
  pairs** (264): JD và CV khác domain. Nhãn đến từ thiết kế
  corpus, độc lập với cosine đo được.
- Lần chạy này: 36 vector lấy từ cache, 0 vector gọi API mới.

## 2. Corpus — text thật đưa đi embed

Toàn bộ 36 đoạn text dưới đây là **nguyên văn output của
`build_embed_text()`** (gọi trực tiếp trên object `ParsedCV`/`ParsedJD` thật,
không viết tay) — đúng những gì `embedder.embed()` nhận vào ở production. Đối
chiếu với quy định độ dài trong prompt LLM hiện dùng (`app/services/parser.py`):
summary CV 2-3 câu, mô tả work_experience 2-4 câu, responsibilities của JD
2-5 câu — bảng số liệu dưới đây cho thấy corpus nằm trong đúng khoảng đó.

### 2.1 Thống kê độ dài

| Domain | Loại | Ký tự | Từ | Câu (ước lượng) |
| --- | --- | --- | --- | --- |
| Backend Developer | JD | 611 | 89 | 4 |
| Backend Developer | CV variant A | 886 | 123 | 6 |
| Backend Developer | CV variant B | 845 | 115 | 6 |
| DevOps / SRE | JD | 591 | 89 | 4 |
| DevOps / SRE | CV variant A | 917 | 128 | 6 |
| DevOps / SRE | CV variant B | 879 | 130 | 6 |
| Frontend Developer | JD | 583 | 94 | 4 |
| Frontend Developer | CV variant A | 781 | 116 | 6 |
| Frontend Developer | CV variant B | 773 | 114 | 6 |
| UI/UX Designer | JD | 590 | 89 | 4 |
| UI/UX Designer | CV variant A | 762 | 115 | 6 |
| UI/UX Designer | CV variant B | 755 | 111 | 6 |
| Data Scientist / ML Engineer | JD | 603 | 88 | 4 |
| Data Scientist / ML Engineer | CV variant A | 907 | 127 | 6 |
| Data Scientist / ML Engineer | CV variant B | 837 | 119 | 5 |
| Business Analyst | JD | 582 | 77 | 3 |
| Business Analyst | CV variant A | 856 | 117 | 6 |
| Business Analyst | CV variant B | 815 | 120 | 6 |
| QA / Test Automation Engineer | JD | 566 | 87 | 3 |
| QA / Test Automation Engineer | CV variant A | 901 | 135 | 6 |
| QA / Test Automation Engineer | CV variant B | 823 | 127 | 5 |
| Mobile Developer | JD | 645 | 106 | 4 |
| Mobile Developer | CV variant A | 844 | 128 | 6 |
| Mobile Developer | CV variant B | 815 | 120 | 6 |
| Technical Recruiter | JD | 629 | 92 | 4 |
| Technical Recruiter | CV variant A | 889 | 127 | 6 |
| Technical Recruiter | CV variant B | 860 | 125 | 6 |
| Business Development Representative | JD | 623 | 92 | 4 |
| Business Development Representative | CV variant A | 911 | 131 | 6 |
| Business Development Representative | CV variant B | 869 | 122 | 5 |
| Cost Accountant | JD | 534 | 76 | 3 |
| Cost Accountant | CV variant A | 830 | 120 | 5 |
| Cost Accountant | CV variant B | 943 | 135 | 6 |
| Content Marketing Specialist | JD | 558 | 84 | 3 |
| Content Marketing Specialist | CV variant A | 863 | 123 | 6 |
| Content Marketing Specialist | CV variant B | 854 | 115 | 5 |

### 2.2 Toàn văn từng đoạn text

### Backend Developer

**JD** — 611 ký tự, 89 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
Backend Developer
We are looking for someone to own the checkout and payment processing services that power our online retail platform. You will design and maintain the systems that handle order creation, inventory reservation, and payment settlement across multiple currencies. The role involves working closely with the platform team to keep transaction throughput reliable during high-traffic sales events, and coordinating with finance to ensure every payment is reconciled correctly. You will also be responsible for designing internal APIs that other teams depend on for order status and refund workflows.
```

**CV variant A** — 886 ký tự, 123 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Backend engineer with a background in building transaction-heavy services for online retail. Comfortable owning services end to end, from initial design through production incident response, with a strong focus on data correctness in payment flows.
Backend Engineer at Company X: Owned the order and payment settlement service for a mid-size online marketplace, redesigning the checkout flow to reduce failed transactions during flash sales. Worked with the finance team to build a reconciliation pipeline that caught discrepancies between the payment gateway and internal ledger. Coordinated a migration of the inventory reservation logic to prevent overselling during high-traffic periods.
Project: Checkout Reliability Overhaul Redesigned the order creation pipeline to isolate payment failures from inventory holds, cutting checkout errors during peak sales by a significant margin.
```

**CV variant B** — 845 ký tự, 115 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Software engineer focused on the transactional core of e-commerce platforms — order management, payment settlement, and inventory accuracy. Enjoys the operational side of the job: keeping payment systems dependable when traffic spikes.
Software Engineer at Company Y: Maintained the payment and order subsystems for a growing online store, taking ownership of currency conversion edge cases and refund handling. Partnered with the accounting group to automate settlement reconciliation, reducing manual reviews. Helped the platform team keep checkout available during a major promotional event by reworking how inventory locks were held.
Project: Payment Reconciliation Automation Built an automated pipeline that cross-checks payment gateway records against internal orders, surfacing mismatches for the finance team same-day instead of weekly.
```

### DevOps / SRE

**JD** — 591 ký tự, 89 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
DevOps / Site Reliability Engineer
We need someone to own the reliability of our production infrastructure and the pipelines that ship code to it. You will be responsible for keeping deployment processes fast and safe, reducing the blast radius of failed releases, and building the observability that lets other engineering teams understand system health at a glance. The role includes leading incident response when production issues occur and driving postmortems that prevent recurrence. You will also work with engineering leads across teams to plan capacity ahead of high-traffic events.
```

**CV variant A** — 917 ký tự, 128 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Infrastructure engineer with a focus on production reliability and deployment safety. Spends most of the time on the boundary between development teams and the systems that run their code, aiming to make releases boring.
Site Reliability Engineer at Company Z: Owned the deployment pipeline for a multi-team engineering organization, introducing staged rollouts that caught failing releases before they reached all users. Led incident response for production outages, and drove the postmortem process that reduced repeat incidents quarter over quarter. Built dashboards that gave every team visibility into their service's health without needing to ask infrastructure directly.
Project: Zero-Downtime Deployment Pipeline Reworked the release process so that failed deployments automatically rolled back before customers were affected, replacing a manual rollback process that used to take significant time to trigger.
```

**CV variant B** — 879 ký tự, 130 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Reliability-focused engineer who has spent recent years making sure production systems stay up and releases go out safely. Comfortable being the first responder when something breaks and turning that into a fix that prevents the next one.
Platform Reliability Engineer at Company W: Kept a growing set of production services healthy for a mid-size engineering team, building the alerting and dashboards that let other engineers self-serve on system health. Ran point on major incidents, coordinating across teams to restore service and writing up what needed to change afterward. Helped plan infrastructure capacity ahead of the company's biggest sales event of the year.
Project: Incident Response Runbook Automation Turned a set of manual, tribal-knowledge incident procedures into automated runbooks, cutting the time it took new on-call engineers to resolve common incidents.
```

### Frontend Developer

**JD** — 583 ký tự, 94 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
Frontend Developer
You will build and maintain the customer-facing dashboards our users rely on to manage their accounts day to day. The role involves translating design mockups into responsive, accessible interfaces, and working closely with the design team to refine the user experience based on usability feedback. You will also be expected to improve the performance of pages that load large amounts of user data, and to help establish shared UI patterns other teams can reuse. Close collaboration with backend teams to shape the APIs the dashboard depends on is part of the job.
```

**CV variant A** — 781 ký tự, 116 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Frontend engineer who enjoys turning design mockups into interfaces that feel fast and easy to use. Has spent the last few years focused on customer-facing dashboards with heavy data density.
Frontend Engineer at Company A: Built and maintained the primary account dashboard for a subscription product, working directly with designers to iterate on layouts based on user testing sessions. Improved page load performance for data-heavy views by restructuring how data was fetched and rendered incrementally. Established a shared component library that other product teams adopted to keep the interface consistent.
Project: Dashboard Performance Rework Cut the load time of the main account dashboard significantly by changing how large tables of user data were fetched and rendered.
```

**CV variant B** — 773 ký tự, 114 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
UI-focused engineer with experience building the screens customers use most often — account settings, usage dashboards, and billing views. Cares about the details that make an interface feel polished.
Web Developer at Company B: Owned the customer usage dashboard for a SaaS product, collaborating with the design team to simplify a cluttered interface into something new users could understand without a tutorial. Worked with backend engineers to shape API responses so the dashboard could render faster. Contributed reusable UI components that reduced how long it took other teams to build new screens.
Project: Design System Component Library Led the creation of a shared UI component library, reducing inconsistency across the product's several customer-facing screens.
```

### UI/UX Designer

**JD** — 590 ký tự, 89 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
UI/UX Designer
We are looking for a designer to shape the experience of our core SaaS product, from early concept sketches through polished, production-ready screens. You will run user research and usability sessions to understand where customers get stuck, and translate those findings into interface improvements. The role involves close collaboration with product managers to prioritize design work and with engineers to make sure what ships matches the intended experience. You will also help maintain and evolve the design system that keeps the product visually consistent as it grows.
```

**CV variant A** — 762 ký tự, 115 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Product designer who enjoys the full arc of a design problem, from talking to users about what's confusing to shipping the screens that fix it. Has worked mostly on SaaS products with dense, data-heavy interfaces.
Product Designer at Company C: Led the redesign of a SaaS product's core workflow after usability sessions revealed users were dropping off midway through setup. Worked closely with product managers to prioritize which design changes would have the biggest impact on activation. Maintained the company's design system, adding new patterns as the product grew into new areas.
Project: Onboarding Flow Redesign Redesigned the new-user onboarding flow based on usability testing findings, reducing the number of users abandoning setup partway through.
```

**CV variant B** — 755 ký tự, 111 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
UX designer with a research-first approach, spending as much time talking to users as sketching screens. Most recent experience is in B2B software with complex, multi-step workflows.
UX/UI Designer at Company D: Ran usability research for a business software product, uncovering the steps in the core workflow where users consistently got confused, then designed and validated fixes. Partnered with engineering to make sure implemented screens matched the intended interactions. Contributed to the shared design system so new features stayed visually consistent with the rest of the product.
Project: Design System Expansion Extended the product's design system with new component patterns needed to support a growing set of features without visual drift.
```

### Data Scientist / ML Engineer

**JD** — 603 ký tự, 88 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
Data Scientist / Machine Learning Engineer
You will build the models that help the business understand which customers are at risk of leaving and why. The role involves working with large historical usage datasets to engineer features, training and validating predictive models, and translating model output into recommendations the business teams can act on. You will partner with product and marketing stakeholders to design experiments that test whether interventions actually reduce churn. Communicating findings clearly to non-technical stakeholders is a core part of the role, not an afterthought.
```

**CV variant A** — 907 ký tự, 127 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Data scientist focused on customer behavior modeling, with recent work centered on predicting and reducing churn for a subscription business. Enjoys the full loop from raw usage data to a model stakeholders trust enough to act on.
Data Scientist at Company E: Built a churn prediction model for a subscription product, engineering features from usage and support ticket history to identify at-risk accounts weeks before cancellation. Partnered with the marketing team to design and evaluate retention campaigns targeted at high-risk segments, using controlled experiments to measure actual impact. Presented findings regularly to non-technical stakeholders, turning model output into concrete recommendations.
Project: Customer Churn Early-Warning System Built a model that flagged at-risk subscription customers weeks in advance, giving the retention team enough lead time to intervene before cancellation.
```

**CV variant B** — 837 ký tự, 119 từ, ~5 câu (nguyên văn output `build_embed_text()`):

```
Machine learning engineer with experience turning customer usage data into predictions the business can act on, most recently focused on retention and churn for a subscription product.
ML Engineer at Company F: Developed and maintained a predictive model estimating customer churn risk from product usage patterns, working with the data team to keep the underlying feature pipeline reliable as usage data grew. Designed experiments with the growth team to test whether proactive outreach to at-risk customers actually improved retention. Translated technical model results into a simple risk score that non-technical stakeholders used in their daily workflow.
Project: Retention Experiment Framework Built a lightweight experimentation framework the growth team used to test retention interventions against the churn model's risk scores.
```

### Business Analyst

**JD** — 582 ký tự, 77 từ, ~3 câu (nguyên văn output `build_embed_text()`):

```
Business Analyst
You will work closely with stakeholders across the business to understand their processes, identify inefficiencies, and translate business needs into clear requirements for the teams that implement changes. The role involves analyzing operational and process data to find where the business is losing time or money, and presenting recommendations that non-technical leadership can act on. You will facilitate requirements-gathering sessions, document current and proposed workflows, and track whether implemented changes actually delivered the expected improvement.
```

**CV variant A** — 856 ký tự, 117 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Business analyst experienced in mapping out operational processes and finding where they break down, then working with implementation teams to fix them. Comfortable moving between spreadsheets and stakeholder conversations.
Business Analyst at Company G: Analyzed the order fulfillment process for a retail operation, identifying a bottleneck that was costing the business days of delay per order, and documented a redesigned workflow to fix it. Facilitated requirements-gathering sessions between operations staff and the implementation team to make sure the redesign matched real day-to-day needs. Tracked the rollout afterward to confirm the fulfillment delay had actually improved.
Project: Fulfillment Process Redesign Documented and helped implement a redesigned order fulfillment workflow that removed a recurring bottleneck in the shipping process.
```

**CV variant B** — 815 ký tự, 120 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Process-focused analyst who enjoys digging into how a business actually operates day to day, then finding the gap between that and how it should operate. Recent work has centered on operational efficiency projects.
Process Analyst at Company H: Studied the inventory management process for a growing retail business, uncovering inefficiencies that were leading to frequent stock discrepancies. Worked with department leads to gather requirements for a revised process and documented the current and future workflows for the implementation team. Measured the impact of the change after rollout to confirm the discrepancy rate had dropped.
Project: Inventory Process Audit Led an audit of the inventory management workflow that surfaced the root cause of recurring stock discrepancies and informed a process redesign.
```

### QA / Test Automation Engineer

**JD** — 566 ký tự, 87 từ, ~3 câu (nguyên văn output `build_embed_text()`):

```
QA / Test Automation Engineer
You will be responsible for the quality of releases going out for a financial services product, where mistakes are expensive and hard to walk back. The role involves designing test strategies that catch regressions before they reach production, building and maintaining automated test suites, and working closely with engineering to make testing part of the development process rather than a separate step at the end. You will also investigate production issues to understand whether better test coverage could have caught them earlier.
```

**CV variant A** — 901 ký tự, 135 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
QA engineer with a background in financial software, where the cost of a missed bug is high enough that testing has to be taken seriously. Focused on building automated coverage that catches regressions early rather than relying on manual checks before release.
QA Automation Engineer at Company I: Built and maintained the automated test suite for a financial services platform, focusing coverage on the transaction and reconciliation flows where bugs were most costly. Worked with engineering to integrate testing earlier in the development process instead of treating it as a final gate before release. Investigated several production incidents to identify gaps in test coverage and closed them to prevent recurrence.
Project: Regression Suite Overhaul Rebuilt the automated regression suite for the core transaction flow, catching a class of bugs that had previously reached production undetected.
```

**CV variant B** — 823 ký tự, 127 từ, ~5 câu (nguyên văn output `build_embed_text()`):

```
Test automation engineer who has spent recent years on quality for a product where reliability really matters — a financial platform where bugs directly affect customer money.
Software QA Engineer at Company J: Owned test coverage for the payment reconciliation module of a financial product, designing automated tests that ran on every code change instead of only before release. Partnered with developers to shift testing earlier in the workflow, reducing the number of issues found late in the release cycle. Reviewed production incidents to figure out which ones automated tests could have caught, and prioritized closing those gaps.
Project: Continuous Testing Pipeline Set up automated tests to run on every pull request for the payment module, catching issues before they reached the release branch instead of after.
```

### Mobile Developer

**JD** — 645 ký tự, 106 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
Mobile Developer (iOS/Android)
You will build and maintain the rider-facing mobile app that connects passengers with drivers in real time. The role involves working on features that depend on live location data and need to stay responsive under unreliable network conditions, since many users are on the move. You will collaborate with backend teams to design the APIs that power trip matching and live tracking, and with the design team to keep the app easy to use for a broad range of users. Performance and reliability matter here more than most apps, since a broken trip request has real-world consequences for someone waiting on the street.
```

**CV variant A** — 844 ký tự, 128 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Mobile engineer with experience building consumer apps that depend on real-time location and need to stay reliable on flaky mobile networks. Most recent work has been on a ride-hailing style app used by a broad, non-technical user base.
Mobile Engineer at Company K: Built the live trip-tracking feature for a ride-hailing app, handling the edge cases that come with unreliable mobile networks and background location updates. Worked with backend engineers to design an API for trip matching that stayed responsive even during high-demand periods like rush hour. Improved app stability for lower-end devices, which made up a meaningful share of the user base.
Project: Real-Time Trip Tracking Built the feature showing riders their driver's live location, designed to degrade gracefully instead of breaking when the connection dropped mid-trip.
```

**CV variant B** — 815 ký tự, 120 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
iOS/Android developer with a focus on location-based consumer apps where reliability under poor network conditions is part of the job, not an edge case. Comes from a background building for a mobile-first, sometimes non-technical audience.
App Developer at Company L: Maintained the trip request and matching flow for a ride-hailing app, working through the reliability challenges of real-time location updates over unstable mobile connections. Partnered with the backend team to keep the trip-matching API fast during peak demand windows. Worked with design to simplify the trip request flow for users unfamiliar with app-based services.
Project: Offline-Tolerant Trip Requests Reworked the trip request flow to queue and retry automatically when the connection dropped, instead of forcing the rider to start over.
```

### Technical Recruiter

**JD** — 629 ký tự, 92 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
Technical Recruiter
You will own the hiring pipeline for engineering roles, from sourcing candidates through offer negotiation. The role involves partnering closely with engineering managers to understand what each role actually needs, not just the job description, and translating that into a sourcing and screening strategy. You will manage candidates through the process, keep the pipeline moving without sacrificing quality, and represent the company well throughout what is often a candidate's first real impression of the organization. Tracking pipeline metrics to spot where candidates are dropping off is part of the job.
```

**CV variant A** — 889 ký tự, 127 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Technical recruiter who has spent the last few years hiring for engineering teams, from individual contributors through senior roles. Focused on understanding what a hiring manager actually needs rather than just working off the job description.
Technical Recruiter at Company M: Owned full-cycle recruiting for a growing engineering organization, partnering with hiring managers to refine role requirements before sourcing began. Managed candidates through the interview process, working to keep the pipeline moving while protecting the quality bar the team cared about. Tracked drop-off at each pipeline stage and used that data to fix a screening step that was losing strong candidates.
Project: Interview Process Redesign Reworked the technical interview process after pipeline data showed strong candidates were dropping off at a particular stage, improving the offer-acceptance rate.
```

**CV variant B** — 860 ký tự, 125 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Recruiter focused on engineering hiring, comfortable managing a high-volume pipeline while still giving each candidate a good experience. Enjoys the partnership side of the job — working with hiring managers to figure out what a role really needs.
Talent Acquisition Specialist at Company N: Ran the hiring pipeline for several engineering teams simultaneously, working with each hiring manager to align on role requirements before sourcing candidates. Kept candidates informed and moving through the process without letting quality slip under pipeline volume pressure. Analyzed where in the process candidates were dropping off and adjusted the screening approach based on what the data showed.
Project: Candidate Pipeline Analytics Built a simple tracking process for pipeline drop-off by stage, which surfaced a screening bottleneck the team hadn't noticed.
```

### Business Development Representative

**JD** — 623 ký tự, 92 từ, ~4 câu (nguyên văn output `build_embed_text()`):

```
Business Development Representative
You will be responsible for generating and qualifying new business opportunities for our B2B SaaS product. The role involves researching target accounts, reaching out to prospective customers, and understanding enough about their business to know whether our product is actually a good fit before handing off to the account executive team. You will need to handle rejection well, keep a disciplined outreach cadence, and continuously refine your pitch based on what resonates with different types of prospects. Accurate pipeline tracking and forecasting are expected as part of the role.
```

**CV variant A** — 911 ký tự, 131 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Business development professional focused on the early stage of the B2B sales funnel — finding the right accounts and starting the conversation that eventually becomes a deal. Comfortable with a high-volume outreach cadence and quick at qualifying whether a prospect is worth pursuing.
Business Development Representative at Company O: Generated and qualified new business opportunities for a B2B SaaS product, researching target accounts before reaching out to make sure outreach felt relevant rather than generic. Refined the outreach pitch over time based on which messaging actually got prospects to respond. Handed off qualified opportunities to account executives with enough context that the next conversation didn't start from zero.
Project: Outbound Cadence Optimization Tested and refined the outbound messaging sequence, improving the rate at which cold outreach turned into a qualified conversation.
```

**CV variant B** — 869 ký tự, 122 từ, ~5 câu (nguyên văn output `build_embed_text()`):

```
Sales development professional experienced in the top of the funnel for B2B software — sourcing accounts, starting conversations, and figuring out quickly whether there's a real fit before involving the rest of the sales team.
Sales Development Representative at Company P: Owned outbound prospecting for a B2B software product, researching accounts to prioritize outreach toward companies that actually matched the ideal customer profile. Kept a disciplined follow-up cadence with prospects and tracked pipeline activity closely enough to forecast handoffs to account executives accurately. Iterated on the pitch based on which angles resonated with different industries.
Project: Ideal Customer Profile Refinement Worked with sales leadership to sharpen the ideal customer profile based on which prospects actually converted, improving how outreach time was targeted.
```

### Cost Accountant

**JD** — 534 ký tự, 76 từ, ~3 câu (nguyên văn output `build_embed_text()`):

```
Cost Accountant
You will be responsible for tracking and controlling production costs across our manufacturing operation. The role involves analyzing cost data to identify where the business is overspending relative to budget, working with plant management to understand the operational reasons behind cost variances, and preparing reports that give leadership a clear picture of production economics. You will also be involved in setting standard costs for new products and reviewing them periodically as production processes change.
```

**CV variant A** — 830 ký tự, 120 từ, ~5 câu (nguyên văn output `build_embed_text()`):

```
Cost accountant with experience in manufacturing environments, focused on making sure production spend stays aligned with budget and that variances get explained rather than just reported.
Cost Accountant at Company Q: Tracked production costs across several manufacturing lines, identifying a recurring variance that turned out to be caused by an outdated standard cost assumption. Worked with plant management to understand the operational drivers behind cost overruns before reporting them to leadership. Reviewed and updated standard costs for a set of products after a change in the production process made the old figures inaccurate.
Project: Standard Cost Revision Project Led a review of standard costs across a product line after production changes made existing figures outdated, correcting a persistent budget variance.
```

**CV variant B** — 943 ký tự, 135 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Manufacturing-focused accountant who spends most of the time in production cost data, looking for where actual spend diverges from plan and why. Works closely with plant operations to get past the numbers to the underlying cause.
Manufacturing Accountant at Company R: Prepared monthly cost variance reports for a manufacturing plant, digging into the operational side with plant supervisors whenever a variance couldn't be explained by the numbers alone. Helped set standard costs for several new product lines, coordinating with operations to make sure assumptions matched actual production conditions. Presented production economics to leadership in a way that connected cost trends to specific operational decisions.
Project: Cost Variance Investigation Process Built a lightweight process for investigating cost variances with plant management before they were reported, reducing how often reported variances turned out to be data errors.
```

### Content Marketing Specialist

**JD** — 558 ký tự, 84 từ, ~3 câu (nguyên văn output `build_embed_text()`):

```
Content Marketing Specialist
You will own the content strategy that drives brand awareness and customer acquisition for our e-commerce business. The role involves planning and producing content across channels, understanding what resonates with our target customer, and using performance data to double down on what works. You will collaborate with the design and growth teams to align content with broader marketing campaigns, and be comfortable adjusting strategy based on what the numbers say rather than sticking to a fixed content calendar out of habit.
```

**CV variant A** — 863 ký tự, 123 từ, ~6 câu (nguyên văn output `build_embed_text()`):

```
Content marketer with experience growing brand awareness and driving acquisition for an e-commerce business. Spends as much time looking at performance data as writing, using it to figure out what to make more of.
Content Marketing Specialist at Company S: Owned the content calendar for an e-commerce brand, producing content across channels aimed at both awareness and direct customer acquisition. Used performance data to identify which content formats were actually driving traffic and sales, shifting strategy away from formats that looked good but underperformed. Collaborated with the design team to align content with seasonal marketing campaigns.
Project: Content Performance Overhaul Rebuilt the content strategy around performance data instead of a fixed calendar, shifting investment toward the formats that were actually driving customer acquisition.
```

**CV variant B** — 854 ký tự, 115 từ, ~5 câu (nguyên văn output `build_embed_text()`):

```
Marketing professional focused on content and brand growth for online retail, comfortable moving between planning a content calendar and digging into the analytics behind why something worked or didn't.
Marketing Specialist at Company T: Produced content across multiple channels for an online retail brand, working with the growth team to make sure content efforts supported broader acquisition campaigns rather than running separately. Regularly reviewed content performance data to reallocate effort toward higher-performing formats. Partnered with design to keep content visually consistent with the brand's other marketing materials.
Project: Cross-Channel Content Calendar Built a unified content calendar spanning multiple channels, replacing a previously disconnected process and making it easier to align content with active marketing campaigns.
```

## 3. Ma trận cosine domain × domain (đường chéo = cùng domain)

| JD \ CV | Backend Developer | DevOps / SRE | Frontend Developer | UI/UX Designer | Data Scientist / ML Engineer | Business Analyst | QA / Test Automation Engineer | Mobile Developer | Technical Recruiter | Business Development Representative | Cost Accountant | Content Marketing Specialist |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Backend Developer | **0.784** | 0.616 | 0.594 | 0.564 | 0.580 | 0.588 | 0.604 | 0.623 | 0.559 | 0.567 | 0.533 | 0.574 |
| DevOps / SRE | 0.633 | **0.759** | 0.578 | 0.557 | 0.592 | 0.585 | 0.627 | 0.615 | 0.593 | 0.554 | 0.558 | 0.552 |
| Frontend Developer | 0.607 | 0.588 | **0.777** | 0.605 | 0.566 | 0.554 | 0.587 | 0.591 | 0.575 | 0.569 | 0.565 | 0.551 |
| UI/UX Designer | 0.555 | 0.556 | 0.639 | **0.720** | 0.583 | 0.556 | 0.554 | 0.570 | 0.558 | 0.544 | 0.538 | 0.537 |
| Data Scientist / ML Engineer | 0.577 | 0.587 | 0.572 | 0.586 | **0.787** | 0.561 | 0.576 | 0.600 | 0.593 | 0.548 | 0.551 | 0.570 |
| Business Analyst | 0.583 | 0.555 | 0.562 | 0.582 | 0.597 | **0.747** | 0.582 | 0.560 | 0.568 | 0.564 | 0.602 | 0.561 |
| QA / Test Automation Engineer | 0.624 | 0.623 | 0.586 | 0.570 | 0.576 | 0.562 | **0.794** | 0.586 | 0.581 | 0.545 | 0.578 | 0.536 |
| Mobile Developer | 0.582 | 0.567 | 0.573 | 0.555 | 0.549 | 0.539 | 0.554 | **0.776** | 0.559 | 0.534 | 0.509 | 0.512 |
| Technical Recruiter | 0.588 | 0.597 | 0.576 | 0.544 | 0.568 | 0.541 | 0.588 | 0.574 | **0.803** | 0.585 | 0.534 | 0.522 |
| Business Development Representative | 0.542 | 0.541 | 0.558 | 0.561 | 0.532 | 0.556 | 0.548 | 0.532 | 0.574 | **0.768** | 0.548 | 0.547 |
| Cost Accountant | 0.551 | 0.546 | 0.534 | 0.525 | 0.526 | 0.588 | 0.566 | 0.503 | 0.521 | 0.529 | **0.815** | 0.554 |
| Content Marketing Specialist | 0.579 | 0.546 | 0.552 | 0.548 | 0.579 | 0.564 | 0.556 | 0.531 | 0.563 | 0.563 | 0.563 | **0.780** |

## 4. Cặp domain gần nhau — stress test khả năng phân biệt

3 cặp domain được cố tình chọn có overlap ngữ cảnh nghiệp vụ (không phải cặp
domain xa nhau dễ đoán): Backend Developer / DevOps-SRE, Frontend Developer /
UI-UX Designer, Data Scientist / Business Analyst. Đây là các negative pair
**khó nhất** trong toàn bộ corpus — cosine của chúng nên vẫn thấp hơn
`pos_min` (0.718) nếu embedding thực sự phân biệt được domain thay vì
chỉ bám overlap từ vựng nghiệp vụ.

| JD domain | CV domain (gần nhau) | Cosine trung bình |
| --- | --- | --- |
| Backend Developer | DevOps / SRE | 0.616 |
| DevOps / SRE | Backend Developer | 0.633 |
| Frontend Developer | UI/UX Designer | 0.605 |
| UI/UX Designer | Frontend Developer | 0.639 |
| Data Scientist / ML Engineer | Business Analyst | 0.561 |
| Business Analyst | Data Scientist / ML Engineer | 0.597 |

Cosine cao nhất trong nhóm này: **0.639**. 0/6
cặp có cosine ≥ `pos_min` (tức có thể lẫn với 1 positive pair thật nếu chỉ
xét riêng cosine, không xét ngữ cảnh domain).

## 5. Threshold sweep — confusion matrix trên 24 positive / 264 negative

| Threshold | TP | FP | TN | FN | Precision | Recall | F1 | Accuracy | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.01 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.02 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.03 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.04 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.05 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.06 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.07 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.08 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.09 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.10 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.11 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.12 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.13 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.14 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.15 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.16 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.17 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.18 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.19 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.20 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.21 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.22 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.23 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.24 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.25 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.26 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.27 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.28 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.29 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.30 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.31 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.32 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.33 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.34 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.35 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.36 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.37 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.38 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.39 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.40 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.41 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.42 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.43 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.44 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.45 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.46 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.47 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.48 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.49 | 24 | 264 | 0 | 0 | 0.083 | 1.000 | 0.154 | 0.083 |  |
| 0.50 | 24 | 263 | 1 | 0 | 0.084 | 1.000 | 0.154 | 0.087 |  |
| 0.51 | 24 | 259 | 5 | 0 | 0.085 | 1.000 | 0.156 | 0.101 |  |
| 0.52 | 24 | 256 | 8 | 0 | 0.086 | 1.000 | 0.158 | 0.111 |  |
| 0.53 | 24 | 244 | 20 | 0 | 0.090 | 1.000 | 0.164 | 0.153 |  |
| 0.54 | 24 | 220 | 44 | 0 | 0.098 | 1.000 | 0.179 | 0.236 |  |
| 0.55 | 24 | 192 | 72 | 0 | 0.111 | 1.000 | 0.200 | 0.333 |  |
| 0.56 | 24 | 149 | 115 | 0 | 0.139 | 1.000 | 0.244 | 0.483 |  |
| 0.57 | 24 | 111 | 153 | 0 | 0.178 | 1.000 | 0.302 | 0.615 |  |
| 0.58 | 24 | 79 | 185 | 0 | 0.233 | 1.000 | 0.378 | 0.726 |  |
| 0.59 | 24 | 45 | 219 | 0 | 0.348 | 1.000 | 0.516 | 0.844 |  |
| 0.60 | 24 | 27 | 237 | 0 | 0.471 | 1.000 | 0.640 | 0.906 |  |
| 0.61 | 24 | 17 | 247 | 0 | 0.585 | 1.000 | 0.738 | 0.941 |  |
| 0.62 | 24 | 12 | 252 | 0 | 0.667 | 1.000 | 0.800 | 0.958 |  |
| 0.63 | 24 | 4 | 260 | 0 | 0.857 | 1.000 | 0.923 | 0.986 |  |
| 0.64 | 24 | 2 | 262 | 0 | 0.923 | 1.000 | 0.960 | 0.993 |  |
| 0.65 | 24 | 2 | 262 | 0 | 0.923 | 1.000 | 0.960 | 0.993 |  |
| 0.66 | 24 | 0 | 264 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | **← F1 cao nhất** |
| 0.67 | 24 | 0 | 264 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | **← F1 cao nhất** |
| 0.68 | 24 | 0 | 264 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | **← F1 cao nhất** |
| 0.69 | 24 | 0 | 264 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | **← F1 cao nhất** |
| 0.70 | 24 | 0 | 264 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | **← F1 cao nhất** |
| 0.71 | 24 | 0 | 264 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | **← F1 cao nhất** |
| 0.72 | 23 | 0 | 264 | 1 | 1.000 | 0.958 | 0.979 | 0.997 |  |
| 0.73 | 20 | 0 | 264 | 4 | 1.000 | 0.833 | 0.909 | 0.986 |  |
| 0.74 | 16 | 0 | 264 | 8 | 1.000 | 0.667 | 0.800 | 0.972 |  |
| 0.75 | 16 | 0 | 264 | 8 | 1.000 | 0.667 | 0.800 | 0.972 |  |
| 0.76 | 16 | 0 | 264 | 8 | 1.000 | 0.667 | 0.800 | 0.972 |  |
| 0.77 | 15 | 0 | 264 | 9 | 1.000 | 0.625 | 0.769 | 0.969 |  |
| 0.78 | 12 | 0 | 264 | 12 | 1.000 | 0.500 | 0.667 | 0.958 |  |
| 0.79 | 11 | 0 | 264 | 13 | 1.000 | 0.458 | 0.629 | 0.955 |  |
| 0.80 | 8 | 0 | 264 | 16 | 1.000 | 0.333 | 0.500 | 0.944 |  |
| 0.81 | 6 | 0 | 264 | 18 | 1.000 | 0.250 | 0.400 | 0.938 |  |
| 0.82 | 2 | 0 | 264 | 22 | 1.000 | 0.083 | 0.154 | 0.924 |  |
| 0.83 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.84 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.85 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.86 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.87 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.88 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.89 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.90 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.91 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.92 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.93 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.94 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.95 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.96 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.97 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.98 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |
| 0.99 | 0 | 0 | 264 | 24 | 1.000 | 0.000 | 0.000 | 0.917 |  |

**F1 cao nhất = 1.000 tại threshold 0.66**
(precision 1.000, recall 1.000, accuracy 1.000).

## 6. AUC (Mann-Whitney U)

**AUC = 1.0000** — xác suất 1 cặp JD-CV cùng domain (positive) có cosine
cao hơn 1 cặp khác domain (negative) chọn ngẫu nhiên, không phụ thuộc vào
việc chọn threshold nào. AUC = 1.0 là tách biệt hoàn hảo, AUC = 0.5 là
không tốt hơn đoán ngẫu nhiên.

## 7. Top-1 / Top-3 retrieval accuracy

Với mỗi JD, xếp hạng toàn bộ 24 CV (2 biến thể × 12
domain) theo cosine giảm dần — mô phỏng đúng cách D1 được dùng thật (rank CV
cho 1 JD), khác với threshold sweep chỉ đo phân loại cặp đơn lẻ.

- **Top-1 accuracy = 1.000** (12/12) — tỉ lệ JD
  có CV cùng domain xếp hạng 1.
- **Top-3 accuracy = 1.000** (12/12) — tỉ lệ JD
  có ít nhất 1 CV cùng domain nằm trong top-3.

- Backend Developer: rank-1 = Backend Developer (cosine 0.828) — top-1 ✅, top-3 ✅
- DevOps / SRE: rank-1 = DevOps / SRE (cosine 0.78) — top-1 ✅, top-3 ✅
- Frontend Developer: rank-1 = Frontend Developer (cosine 0.818) — top-1 ✅, top-3 ✅
- UI/UX Designer: rank-1 = UI/UX Designer (cosine 0.722) — top-1 ✅, top-3 ✅
- Data Scientist / ML Engineer: rank-1 = Data Scientist / ML Engineer (cosine 0.804) — top-1 ✅, top-3 ✅
- Business Analyst: rank-1 = Business Analyst (cosine 0.774) — top-1 ✅, top-3 ✅
- QA / Test Automation Engineer: rank-1 = QA / Test Automation Engineer (cosine 0.794) — top-1 ✅, top-3 ✅
- Mobile Developer: rank-1 = Mobile Developer (cosine 0.791) — top-1 ✅, top-3 ✅
- Technical Recruiter: rank-1 = Technical Recruiter (cosine 0.822) — top-1 ✅, top-3 ✅
- Business Development Representative: rank-1 = Business Development Representative (cosine 0.806) — top-1 ✅, top-3 ✅
- Cost Accountant: rank-1 = Cost Accountant (cosine 0.818) — top-1 ✅, top-3 ✅
- Content Marketing Specialist: rank-1 = Content Marketing Specialist (cosine 0.82) — top-1 ✅, top-3 ✅

## 8. Paraphrase robustness — đổi văn phong vs đổi domain

- Cosine trung bình khi **đổi văn phong, giữ nguyên domain** (CV_A vs CV_B
  cùng domain): **0.871** (min 0.806).
- Cosine trung bình khi **đổi domain** (CV_A domain này vs CV_A domain khác):
  **0.681** (max 0.764).
- 12/12 domain có cosine paraphrase (cùng domain, khác
  văn phong) **cao hơn mọi** cặp cross-domain CV-CV — nếu đạt 12/12
  nghĩa là đổi cách diễn đạt luôn ảnh hưởng vector ít hơn đổi ngành nghề, đúng
  kỳ vọng của một embedding nắm bắt ngữ nghĩa thay vì chỉ bám từ vựng bề mặt.

## 9. Margin / overlap giữa 2 lớp

| Metric | Positive (cùng domain) | Negative (khác domain) |
| --- | --- | --- |
| Mean | 0.776 | 0.566 |
| Min | 0.718 | 0.495 |
| Max | 0.828 | 0.656 |

Margin (min(positive) − max(negative)) = **0.062**
(không chồng lấn — tách biệt hoàn toàn).
0 positive pairs rơi vào vùng chồng lấn (cosine ≤ max(negative));
0 negative pairs rơi vào vùng chồng lấn (cosine ≥ min(positive)).

**Ghi chú phụ (không phải kết luận chính của Phase 2):** `COSINE_MIN`/
`COSINE_MAX` mặc định trong `app/config.py` hiện là 0.0/1.0 (không kéo giãn).
Nếu muốn D1 tận dụng hết thang điểm 0-1 sau khi cosine đã tách biệt tốt ở
thực nghiệm này, có thể cân nhắc hiệu chỉnh 2 hằng số đó theo phân phối
positive/negative quan sát được ở mục 9 — đây là việc của tầng scoring
(`normalize_cosine` trong `scorer.py`), nằm ngoài phạm vi Phase 2/embedding.

## 10. Kết luận

Embedding tách biệt tốt cặp cùng-domain khỏi khác-domain trên corpus này (AUC 1.0000, margin dương).
Top-1 retrieval accuracy 1.000 cho thấy khi dùng D1 để xếp hạng CV
cho 1 JD, CV đúng domain luôn xuất hiện ở
vị trí đầu — kể cả với 3 cặp domain cố tình chọn gần nhau (Backend/DevOps,
Frontend/UI-UX, Data Scientist/Business Analyst).

---
*Tái tạo báo cáo này: `python scripts/d1_embedding_accuracy_experiment.py`
(cần `GEMINI_API_KEY` trong `.env`; lần đầu gọi 36 API call thật,
các lần sau đọc cache `scripts/.d1_embed_cache.json`).*
