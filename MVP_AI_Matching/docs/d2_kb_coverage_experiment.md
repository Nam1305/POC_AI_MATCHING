# Thực nghiệm: độ phủ của skill_data.json và skill_implies.json (D2)

Sinh tự động bởi `scripts/d2_kb_coverage_experiment.py`. Đối tượng đo: 2 file
dữ liệu tĩnh làm nền cho Layer 1/2 của D2 Skill Scoring —
[`app/data/skill_data.json`](../app/data/skill_data.json) (9736
entries) và [`app/data/skill_implies.json`](../app/data/skill_implies.json)
(1680 entries), xem đặc tả pipeline ở
[`app/services/skill_matcher.py`](../app/services/skill_matcher.py) và
[`docs/thesis_report.md` mục 3.5](thesis_report.md#35-d2--chi-tiết-pipeline-so-khớp-kỹ-năng-skill_matcherpy).

**Tổng cộng 2000 test case** (1000 cho Phần A, 1000
cho Phần B), xây từ tri thức miền (domain knowledge) **độc lập với nội dung 2
file** — nếu suy ngược test case từ chính file thì độ phủ đương nhiên đạt
100%, không đo được gì. Một test case MISS ở đây **không phải lỗi thuật
toán** (đã kiểm chứng riêng ở `d2_layer3_threshold_experiment.py`) — nó chỉ ra
đúng khoảng trống dữ liệu cần bổ sung qua `app/data/add_*_skills.py`.

## PHẦN A — Độ phủ của skill_data.json (Layer 1 — canonical hóa)

**Câu hỏi:** với tên kỹ năng viết theo phong cách output LLM thật (Title
Case, dấu chấm, viết tắt phổ biến — không phải định dạng key SO-tag của
skill_data.json), bao nhiêu % được nhận diện?

**Phương pháp:** 617 tên kỹ năng viết tay từ tri thức miền, phủ
37 nhóm công nghệ thường gặp trong CV/JD thật (ngôn ngữ, frontend,
backend, mobile, database, cloud/devops, dịch vụ AWS/Azure/GCP cụ thể,
BI/ERP/CRM, embedded/IoT, blockchain, data/ML/AI, testing, tool, khái niệm quy
trình...), cộng thêm 383 test case **biến thể định dạng** của chính các
mục đã có (space↔dash, bỏ dấu chấm, đổi kiểu viết hoa, space↔underscore — xem
`_pad_to_target()`) để đạt đúng cỡ mẫu tròn 1000; mỗi biến thể vẫn là
1 cách viết thật một CV/JD khác có thể tạo ra cho cùng 1 kỹ năng, nên đây vẫn
là phép thử hợp lệ (độ mạnh của `to_stackoverflow_format()` trước biến thiên
định dạng), không phải số liệu đệm vô nghĩa. Với mỗi tên, lặp lại đúng cơ chế
tra cứu `to_stackoverflow_format()` + tra `SKILL_DATA`, tách 3 kết quả: khớp
qua **key tự-canonical** (value=null — chính key đã là tên chuẩn), khớp qua
**synonym** (value≠null — key trỏ sang 1 canonical khác), hoặc **không tìm
thấy** ở bất kỳ biến thể định dạng nào.

### A.1 Độ phủ theo nhóm công nghệ

| Nhóm | Số case | Tìm thấy | Độ phủ |
| --- | --- | --- | --- |
| Ngôn ngữ | 25 | 25 | 100.0% |
| Frontend | 24 | 24 | 100.0% |
| Backend Node | 10 | 10 | 100.0% |
| Python stack | 20 | 20 | 100.0% |
| Java stack | 15 | 15 | 100.0% |
| .NET stack | 15 | 15 | 100.0% |
| PHP/Ruby | 8 | 8 | 100.0% |
| Mobile | 15 | 15 | 100.0% |
| Database | 20 | 20 | 100.0% |
| Cloud/DevOps | 25 | 25 | 100.0% |
| Data/ML/AI | 22 | 22 | 100.0% |
| Testing/QA | 14 | 14 | 100.0% |
| Tool/VCS | 12 | 12 | 100.0% |
| Khái niệm/Process | 16 | 16 | 100.0% |
| Game/Emerging | 14 | 14 | 100.0% |
| Network/Security | 16 | 16 | 100.0% |
| CMS/Ecommerce | 8 | 8 | 100.0% |
| Monitoring | 10 | 10 | 100.0% |
| Message Queue | 6 | 6 | 100.0% |
| Design/PM | 10 | 6 | 60.0% |
| OS | 6 | 5 | 83.3% |
| Cloud hosting | 8 | 8 | 100.0% |
| Data warehouse | 6 | 6 | 100.0% |
| Build/Testing bổ sung | 9 | 9 | 100.0% |
| Quy trình/khác | 16 | 16 | 100.0% |
| AWS services | 36 | 30 | 83.3% |
| Azure services | 30 | 24 | 80.0% |
| GCP services | 30 | 17 | 56.7% |
| BI/ERP/CRM | 24 | 24 | 100.0% |
| Embedded/IoT | 14 | 14 | 100.0% |
| Blockchain | 11 | 11 | 100.0% |
| AR/VR/Graphics | 10 | 10 | 100.0% |
| Networking protocol | 14 | 14 | 100.0% |
| Ngôn ngữ/tool hiếm | 20 | 19 | 95.0% |
| Python stack bổ sung | 34 | 33 | 97.1% |
| JS/TS stack bổ sung | 30 | 30 | 100.0% |
| Testing/QA bổ sung | 14 | 14 | 100.0% |
| Biến thể định dạng (bổ sung tới 1000) | 383 | 336 | 87.7% |

### A.2 Tổng hợp

| Chỉ số | Giá trị |
| --- | --- |
| Tổng test case | 1000 |
| Tìm thấy | 921 (92.1%) |
| — qua key tự-canonical (value=null) | 575 |
| — qua synonym (value≠null) | 346 |
| Không tìm thấy | 79 (7.9%) |
| **Độ phủ skill_data.json** | **92.1%** |

### A.3 Danh sách MISS (không tìm thấy ở bất kỳ biến thể nào)

- `Asana` (Design/PM)
- `Monday.com` (Design/PM)
- `Notion` (Design/PM)
- `Miro` (Design/PM)
- `Red Hat Linux` (OS)
- `Amazon Neptune` (AWS services)
- `Amazon DocumentDB` (AWS services)
- `AWS AppSync` (AWS services)
- `AWS Amplify` (AWS services)
- `AWS CloudTrail` (AWS services)
- `AWS Systems Manager` (AWS services)
- `Azure Event Hub` (Azure services)
- `Azure Container Instances` (Azure services)
- `Azure DevOps Pipelines` (Azure services)
- `Azure Front Door` (Azure services)
- `Azure Resource Manager` (Azure services)
- `Azure Batch` (Azure services)
- `Pub/Sub` (GCP services)
- `Cloud CDN` (GCP services)
- `Cloud Pub/Sub` (GCP services)
- `Cloud Load Balancing` (GCP services)
- `Cloud Logging` (GCP services)
- `Cloud Armor` (GCP services)
- `Cloud Endpoints` (GCP services)
- `Anthos` (GCP services)
- `Cloud Data Fusion` (GCP services)
- `Cloud Natural Language API` (GCP services)
- `Cloud Vision API` (GCP services)
- `Cloud Text-to-Speech` (GCP services)
- `Firebase Hosting` (GCP services)
- `Nim Lang` (Ngôn ngữ/tool hiếm)
- `Black Formatter` (Python stack bổ sung)
- `Feature_Flags` (Biến thể định dạng (bổ sung tới 1000))
- `CLOUD-LOAD-BALANCING` (Biến thể định dạng (bổ sung tới 1000))
- `React_Query` (Biến thể định dạng (bổ sung tới 1000))
- `Design_Patterns` (Biến thể định dạng (bổ sung tới 1000))
- `REST_API` (Biến thể định dạng (bổ sung tới 1000))
- `Code_Review` (Biến thể định dạng (bổ sung tới 1000))
- `azure event hub` (Biến thể định dạng (bổ sung tới 1000))
- `Firebase_Hosting` (Biến thể định dạng (bổ sung tới 1000))
- `Azure_Functions_App` (Biến thể định dạng (bổ sung tới 1000))
- `Automation_Testing` (Biến thể định dạng (bổ sung tới 1000))
- `Cloud-Natural-Language-API` (Biến thể định dạng (bổ sung tới 1000))
- `AWS AMPLIFY` (Biến thể định dạng (bổ sung tới 1000))
- `Cloud_Natural_Language_API` (Biến thể định dạng (bổ sung tới 1000))
- `cLOUD tEXT-TO-sPEECH` (Biến thể định dạng (bổ sung tới 1000))
- `Cocoa_Touch` (Biến thể định dạng (bổ sung tới 1000))
- `Azure_DevOps_Pipelines` (Biến thể định dạng (bổ sung tới 1000))
- `Azure_Data_Factory` (Biến thể định dạng (bổ sung tới 1000))
- `aws-amplify` (Biến thể định dạng (bổ sung tới 1000))
- `Salesforce_Lightning` (Biến thể định dạng (bổ sung tới 1000))
- `Data_Warehouse` (Biến thể định dạng (bổ sung tới 1000))
- `cloud-pub/sub` (Biến thể định dạng (bổ sung tới 1000))
- `cloud-logging` (Biến thể định dạng (bổ sung tới 1000))
- `Sinonjs` (Biến thể định dạng (bổ sung tới 1000))
- `Cloud_Build` (Biến thể định dạng (bổ sung tới 1000))
- `CLOUD-ARMOR` (Biến thể định dạng (bổ sung tới 1000))
- `AZURE FRONT DOOR` (Biến thể định dạng (bổ sung tới 1000))
- `aZURE fRONT dOOR` (Biến thể định dạng (bổ sung tới 1000))
- `azure devops pipelines` (Biến thể định dạng (bổ sung tới 1000))
- `Framer_Motion` (Biến thể định dạng (bổ sung tới 1000))
- `Spring_Security` (Biến thể định dạng (bổ sung tới 1000))
- `Data_Analysis` (Biến thể định dạng (bổ sung tới 1000))
- `AZURE BATCH` (Biến thể định dạng (bổ sung tới 1000))
- `AWS-CloudTrail` (Biến thể định dạng (bổ sung tới 1000))
- `Cloud_Text-to-Speech` (Biến thể định dạng (bổ sung tới 1000))
- `Amazon_SQS` (Biến thể định dạng (bổ sung tới 1000))
- `CLOUD ENDPOINTS` (Biến thể định dạng (bổ sung tới 1000))
- `Azure_Active_Directory` (Biến thể định dạng (bổ sung tới 1000))
- `FIREBASE-HOSTING` (Biến thể định dạng (bổ sung tới 1000))
- `Azure_Application_Insights` (Biến thể định dạng (bổ sung tới 1000))
- `Cloud Cdn` (Biến thể định dạng (bổ sung tới 1000))
- `Amazon_Web_Services` (Biến thể định dạng (bổ sung tới 1000))
- `Nx_Monorepo` (Biến thể định dạng (bổ sung tới 1000))
- `Rate_Limiting` (Biến thể định dạng (bổ sung tới 1000))
- `Unreal_Engine` (Biến thể định dạng (bổ sung tới 1000))
- `CLOUD VISION API` (Biến thể định dạng (bổ sung tới 1000))
- `Azure_App_Service` (Biến thể định dạng (bổ sung tới 1000))
- `cLOUD dATA fUSION` (Biến thể định dạng (bổ sung tới 1000))

### A.4 Toàn bộ 1000 test case

<details>
<summary>Xem đầy đủ (bấm để mở)</summary>

| Nhóm | Tên kỹ năng (đầu vào) | Kết quả tra cứu | Key khớp | Canonical |
| --- | --- | --- | --- | --- |
| Ngôn ngữ | `Python` | ✅ synonym | `python` | `python` |
| Ngôn ngữ | `Java` | ✅ synonym | `java` | `java` |
| Ngôn ngữ | `JavaScript` | ✅ synonym | `javascript` | `javascript` |
| Ngôn ngữ | `TypeScript` | ✅ synonym | `typescript` | `typescript` |
| Ngôn ngữ | `C#` | ✅ synonym | `c#` | `c#` |
| Ngôn ngữ | `C++` | ✅ synonym | `c++` | `c++` |
| Ngôn ngữ | `C` | ✅ self-canonical | `c` | `c` |
| Ngôn ngữ | `Go` | ✅ synonym | `go` | `go` |
| Ngôn ngữ | `Golang` | ✅ synonym | `golang` | `go` |
| Ngôn ngữ | `Rust` | ✅ self-canonical | `rust` | `rust` |
| Ngôn ngữ | `Kotlin` | ✅ self-canonical | `kotlin` | `kotlin` |
| Ngôn ngữ | `Swift` | ✅ synonym | `swift` | `swift` |
| Ngôn ngữ | `PHP` | ✅ self-canonical | `php` | `php` |
| Ngôn ngữ | `Ruby` | ✅ self-canonical | `ruby` | `ruby` |
| Ngôn ngữ | `Scala` | ✅ self-canonical | `scala` | `scala` |
| Ngôn ngữ | `Perl` | ✅ synonym | `perl` | `perl` |
| Ngôn ngữ | `R Programming` | ✅ synonym | `r-programming` | `r` |
| Ngôn ngữ | `MATLAB` | ✅ synonym | `matlab` | `matlab` |
| Ngôn ngữ | `Dart` | ✅ synonym | `dart` | `dart` |
| Ngôn ngữ | `Elixir` | ✅ synonym | `elixir` | `elixir` |
| Ngôn ngữ | `Erlang` | ✅ self-canonical | `erlang` | `erlang` |
| Ngôn ngữ | `Haskell` | ✅ self-canonical | `haskell` | `haskell` |
| Ngôn ngữ | `Objective-C` | ✅ synonym | `objective-c` | `objective-c` |
| Ngôn ngữ | `Visual Basic` | ✅ self-canonical | `visual-basic` | `visual-basic` |
| Ngôn ngữ | `F#` | ✅ synonym | `f#` | `f#` |
| Frontend | `HTML5` | ✅ synonym | `html5` | `html` |
| Frontend | `CSS3` | ✅ synonym | `css3` | `css` |
| Frontend | `React` | ✅ synonym | `react` | `reactjs` |
| Frontend | `React.js` | ✅ synonym | `react.js` | `reactjs` |
| Frontend | `ReactJS` | ✅ synonym | `reactjs` | `reactjs` |
| Frontend | `Vue.js` | ✅ synonym | `vue.js` | `vue.js` |
| Frontend | `VueJS` | ✅ synonym | `vuejs` | `vue.js` |
| Frontend | `Angular` | ✅ synonym | `angular` | `angular` |
| Frontend | `AngularJS` | ✅ synonym | `angularjs` | `angularjs` |
| Frontend | `Svelte` | ✅ synonym | `svelte` | `svelte` |
| Frontend | `jQuery` | ✅ synonym | `jquery` | `jquery` |
| Frontend | `Next.js` | ✅ synonym | `next.js` | `next.js` |
| Frontend | `NextJS` | ✅ synonym | `nextjs` | `next.js` |
| Frontend | `Nuxt.js` | ✅ synonym | `nuxt.js` | `nuxt.js` |
| Frontend | `Redux` | ✅ synonym | `redux` | `redux` |
| Frontend | `Redux Toolkit` | ✅ synonym | `redux-toolkit` | `redux-toolkit` |
| Frontend | `MobX` | ✅ self-canonical | `mobx` | `mobx` |
| Frontend | `Webpack` | ✅ self-canonical | `webpack` | `webpack` |
| Frontend | `Vite` | ✅ synonym | `vite` | `vite` |
| Frontend | `Babel` | ✅ synonym | `babel` | `babeljs` |
| Frontend | `Sass` | ✅ synonym | `sass` | `sass` |
| Frontend | `Tailwind CSS` | ✅ synonym | `tailwind-css` | `tailwind-css` |
| Frontend | `Bootstrap` | ✅ self-canonical | `bootstrap` | `bootstrap` |
| Frontend | `Material UI` | ✅ synonym | `material-ui` | `material-ui` |
| Backend Node | `Node.js` | ✅ synonym | `node.js` | `node.js` |
| Backend Node | `NodeJS` | ✅ synonym | `nodejs` | `node.js` |
| Backend Node | `Express.js` | ✅ synonym | `express.js` | `express` |
| Backend Node | `ExpressJS` | ✅ synonym | `expressjs` | `express` |
| Backend Node | `NestJS` | ✅ self-canonical | `nestjs` | `nestjs` |
| Backend Node | `Fastify` | ✅ self-canonical | `fastify` | `fastify` |
| Backend Node | `Koa` | ✅ self-canonical | `koa` | `koa` |
| Backend Node | `GraphQL` | ✅ self-canonical | `graphql` | `graphql` |
| Backend Node | `Apollo Client` | ✅ self-canonical | `apollo-client` | `apollo-client` |
| Backend Node | `Socket.IO` | ✅ synonym | `socket.io` | `socket.io` |
| Python stack | `Django` | ✅ self-canonical | `django` | `django` |
| Python stack | `Flask` | ✅ synonym | `flask` | `flask` |
| Python stack | `FastAPI` | ✅ self-canonical | `fastapi` | `fastapi` |
| Python stack | `Pandas` | ✅ synonym | `pandas` | `pandas` |
| Python stack | `NumPy` | ✅ synonym | `numpy` | `numpy` |
| Python stack | `SciPy` | ✅ self-canonical | `scipy` | `scipy` |
| Python stack | `Scikit-learn` | ✅ synonym | `scikit-learn` | `scikit-learn` |
| Python stack | `TensorFlow` | ✅ synonym | `tensorflow` | `tensorflow` |
| Python stack | `PyTorch` | ✅ self-canonical | `pytorch` | `pytorch` |
| Python stack | `Keras` | ✅ self-canonical | `keras` | `keras` |
| Python stack | `OpenCV` | ✅ synonym | `opencv` | `opencv` |
| Python stack | `Matplotlib` | ✅ synonym | `matplotlib` | `matplotlib` |
| Python stack | `Seaborn` | ✅ self-canonical | `seaborn` | `seaborn` |
| Python stack | `Celery` | ✅ self-canonical | `celery` | `celery` |
| Python stack | `SQLAlchemy` | ✅ self-canonical | `sqlalchemy` | `sqlalchemy` |
| Python stack | `Pydantic` | ✅ self-canonical | `pydantic` | `pydantic` |
| Python stack | `Streamlit` | ✅ self-canonical | `streamlit` | `streamlit` |
| Python stack | `Scrapy` | ✅ synonym | `scrapy` | `scrapy` |
| Python stack | `BeautifulSoup` | ✅ synonym | `beautifulsoup` | `beautifulsoup` |
| Python stack | `Jupyter Notebook` | ✅ synonym | `jupyter-notebook` | `jupyter-notebook` |
| Java stack | `Spring` | ✅ synonym | `spring` | `spring` |
| Java stack | `Spring Boot` | ✅ self-canonical | `spring-boot` | `spring-boot` |
| Java stack | `Spring MVC` | ✅ synonym | `spring-mvc` | `spring-mvc` |
| Java stack | `Spring Security` | ✅ synonym | `spring-security` | `spring-security` |
| Java stack | `Hibernate` | ✅ self-canonical | `hibernate` | `hibernate` |
| Java stack | `Maven` | ✅ synonym | `maven` | `maven` |
| Java stack | `Gradle` | ✅ self-canonical | `gradle` | `gradle` |
| Java stack | `JUnit` | ✅ self-canonical | `junit` | `junit` |
| Java stack | `Kotlin Coroutines` | ✅ synonym | `kotlin-coroutines` | `kotlin-coroutines` |
| Java stack | `JSP` | ✅ self-canonical | `jsp` | `jsp` |
| Java stack | `Servlets` | ✅ synonym | `servlets` | `servlets` |
| Java stack | `JPA` | ✅ synonym | `jpa` | `jpa` |
| Java stack | `Struts` | ✅ self-canonical | `struts` | `struts` |
| Java stack | `Grails` | ✅ synonym | `grails` | `grails` |
| Java stack | `Tomcat` | ✅ synonym | `tomcat` | `tomcat` |
| .NET stack | `.NET` | ✅ synonym | `.net` | `.net` |
| .NET stack | `.NET Core` | ✅ synonym | `.net-core` | `.net-core` |
| .NET stack | `ASP.NET` | ✅ synonym | `asp.net` | `asp.net` |
| .NET stack | `ASP.NET Core` | ✅ synonym | `asp.net-core` | `asp.net-core` |
| .NET stack | `ASP.NET MVC` | ✅ synonym | `asp.net-mvc` | `asp.net-mvc` |
| .NET stack | `Entity Framework` | ✅ synonym | `entity-framework` | `entity-framework` |
| .NET stack | `Entity Framework Core` | ✅ synonym | `entity-framework-core` | `entity-framework-core` |
| .NET stack | `LINQ` | ✅ synonym | `linq` | `linq` |
| .NET stack | `WPF` | ✅ self-canonical | `wpf` | `wpf` |
| .NET stack | `WinForms` | ✅ synonym | `winforms` | `winforms` |
| .NET stack | `Xamarin` | ✅ self-canonical | `xamarin` | `xamarin` |
| .NET stack | `Xamarin.Forms` | ✅ synonym | `xamarin.forms` | `xamarin.forms` |
| .NET stack | `Blazor` | ✅ synonym | `blazor` | `blazor` |
| .NET stack | `WCF` | ✅ synonym | `wcf` | `wcf` |
| .NET stack | `NHibernate` | ✅ self-canonical | `nhibernate` | `nhibernate` |
| PHP/Ruby | `Laravel` | ✅ self-canonical | `laravel` | `laravel` |
| PHP/Ruby | `Symfony` | ✅ self-canonical | `symfony` | `symfony` |
| PHP/Ruby | `CodeIgniter` | ✅ synonym | `codeigniter` | `codeigniter` |
| PHP/Ruby | `CakePHP` | ✅ synonym | `cakephp` | `cakephp` |
| PHP/Ruby | `WordPress` | ✅ synonym | `wordpress` | `wordpress` |
| PHP/Ruby | `Composer` | ✅ synonym | `composer` | `composer-php` |
| PHP/Ruby | `Ruby on Rails` | ✅ synonym | `ruby-on-rails` | `ruby-on-rails` |
| PHP/Ruby | `RSpec` | ✅ self-canonical | `rspec` | `rspec` |
| Mobile | `Android` | ✅ self-canonical | `android` | `android` |
| Mobile | `iOS` | ✅ self-canonical | `ios` | `ios` |
| Mobile | `Flutter` | ✅ synonym | `flutter` | `flutter` |
| Mobile | `React Native` | ✅ synonym | `react-native` | `react-native` |
| Mobile | `SwiftUI` | ✅ synonym | `swiftui` | `swiftui` |
| Mobile | `Android Studio` | ✅ synonym | `android-studio` | `android-studio` |
| Mobile | `Cocoa Touch` | ✅ synonym | `cocoa-touch` | `cocoa-touch` |
| Mobile | `Objective-C` | ✅ synonym | `objective-c` | `objective-c` |
| Mobile | `Jetpack Compose` | ✅ synonym | `jetpack-compose` | `android-jetpack-compose` |
| Mobile | `Ionic Framework` | ✅ synonym | `ionic-framework` | `ionic-framework` |
| Mobile | `Cordova` | ✅ synonym | `cordova` | `cordova` |
| Mobile | `Xamarin.Android` | ✅ synonym | `xamarin.android` | `xamarin.android` |
| Mobile | `Xamarin.iOS` | ✅ synonym | `xamarin.ios` | `xamarin.ios` |
| Mobile | `Kivy` | ✅ self-canonical | `kivy` | `kivy` |
| Mobile | `Unity` | ✅ synonym | `unity` | `unity-game-engine` |
| Database | `MySQL` | ✅ synonym | `mysql` | `mysql` |
| Database | `PostgreSQL` | ✅ synonym | `postgresql` | `postgresql` |
| Database | `MongoDB` | ✅ synonym | `mongodb` | `mongodb` |
| Database | `Redis` | ✅ self-canonical | `redis` | `redis` |
| Database | `SQLite` | ✅ synonym | `sqlite` | `sqlite` |
| Database | `SQL Server` | ✅ synonym | `sql-server` | `sql-server` |
| Database | `Oracle Database` | ✅ self-canonical | `oracle-database` | `oracle-database` |
| Database | `Elasticsearch` | ✅ synonym | `elasticsearch` | `elasticsearch` |
| Database | `Cassandra` | ✅ synonym | `cassandra` | `cassandra` |
| Database | `DynamoDB` | ✅ self-canonical | `dynamodb` | `dynamodb` |
| Database | `Firebase` | ✅ self-canonical | `firebase` | `firebase` |
| Database | `MariaDB` | ✅ self-canonical | `mariadb` | `mariadb` |
| Database | `Neo4j` | ✅ synonym | `neo4j` | `neo4j` |
| Database | `InfluxDB` | ✅ self-canonical | `influxdb` | `influxdb` |
| Database | `CouchDB` | ✅ self-canonical | `couchdb` | `couchdb` |
| Database | `Snowflake` | ✅ synonym | `snowflake` | `snowflake-cloud-data-platform` |
| Database | `BigQuery` | ✅ self-canonical | `bigquery` | `bigquery` |
| Database | `Supabase` | ✅ synonym | `supabase` | `supabase` |
| Database | `T-SQL` | ✅ synonym | `t-sql` | `t-sql` |
| Database | `PL/SQL` | ✅ self-canonical | `pl/sql` | `pl/sql` |
| Cloud/DevOps | `AWS` | ✅ self-canonical | `aws` | `aws` |
| Cloud/DevOps | `Amazon Web Services` | ✅ synonym | `amazon-web-services` | `aws` |
| Cloud/DevOps | `Azure` | ✅ self-canonical | `azure` | `azure` |
| Cloud/DevOps | `Microsoft Azure` | ✅ synonym | `microsoft-azure` | `azure` |
| Cloud/DevOps | `Google Cloud Platform` | ✅ synonym | `google-cloud-platform` | `gcp` |
| Cloud/DevOps | `GCP` | ✅ self-canonical | `gcp` | `gcp` |
| Cloud/DevOps | `Docker` | ✅ synonym | `docker` | `docker` |
| Cloud/DevOps | `Kubernetes` | ✅ synonym | `kubernetes` | `kubernetes` |
| Cloud/DevOps | `Docker Compose` | ✅ self-canonical | `docker-compose` | `docker-compose` |
| Cloud/DevOps | `Terraform` | ✅ self-canonical | `terraform` | `terraform` |
| Cloud/DevOps | `Ansible` | ✅ synonym | `ansible` | `ansible` |
| Cloud/DevOps | `Jenkins` | ✅ synonym | `jenkins` | `jenkins-ci` |
| Cloud/DevOps | `GitLab CI` | ✅ self-canonical | `gitlab-ci` | `gitlab-ci` |
| Cloud/DevOps | `GitHub Actions` | ✅ self-canonical | `github-actions` | `github-actions` |
| Cloud/DevOps | `CircleCI` | ✅ self-canonical | `circleci` | `circleci` |
| Cloud/DevOps | `Travis CI` | ✅ synonym | `travis-ci` | `travis-ci` |
| Cloud/DevOps | `Nginx` | ✅ self-canonical | `nginx` | `nginx` |
| Cloud/DevOps | `Apache` | ✅ synonym | `apache` | `apache` |
| Cloud/DevOps | `Linux` | ✅ synonym | `linux` | `linux` |
| Cloud/DevOps | `Bash` | ✅ synonym | `bash` | `bash` |
| Cloud/DevOps | `Shell Scripting` | ✅ synonym | `shell-scripting` | `shell` |
| Cloud/DevOps | `Prometheus` | ✅ self-canonical | `prometheus` | `prometheus` |
| Cloud/DevOps | `Grafana` | ✅ self-canonical | `grafana` | `grafana` |
| Cloud/DevOps | `Kubernetes Helm` | ✅ synonym | `kubernetes-helm` | `kubernetes-helm` |
| Cloud/DevOps | `Vagrant` | ✅ self-canonical | `vagrant` | `vagrant` |
| Data/ML/AI | `Machine Learning` | ✅ self-canonical | `machine-learning` | `machine-learning` |
| Data/ML/AI | `Deep Learning` | ✅ synonym | `deep-learning` | `deep-learning` |
| Data/ML/AI | `Natural Language Processing` | ✅ synonym | `natural-language-processing` | `nlp` |
| Data/ML/AI | `Computer Vision` | ✅ synonym | `computer-vision` | `computer-vision` |
| Data/ML/AI | `Data Analysis` | ✅ self-canonical | `data-analysis` | `data-analysis` |
| Data/ML/AI | `Data Visualization` | ✅ synonym | `data-visualization` | `visualization` |
| Data/ML/AI | `Neural Networks` | ✅ synonym | `neural-networks` | `neural-network` |
| Data/ML/AI | `Power BI` | ✅ self-canonical | `powerbi` | `powerbi` |
| Data/ML/AI | `Tableau` | ✅ synonym | `tableau` | `tableau-api` |
| Data/ML/AI | `Excel` | ✅ synonym | `excel` | `excel` |
| Data/ML/AI | `Airflow` | ✅ synonym | `airflow` | `airflow` |
| Data/ML/AI | `Kafka` | ✅ synonym | `kafka` | `apache-kafka` |
| Data/ML/AI | `Apache Spark` | ✅ synonym | `apache-spark` | `apache-spark` |
| Data/ML/AI | `Hadoop` | ✅ synonym | `hadoop` | `hadoop` |
| Data/ML/AI | `OpenAI` | ✅ self-canonical | `openai` | `openai` |
| Data/ML/AI | `ChatGPT` | ✅ self-canonical | `chatgpt` | `chatgpt` |
| Data/ML/AI | `LLM` | ✅ synonym | `llm` | `large-language-model` |
| Data/ML/AI | `LangChain` | ✅ self-canonical | `langchain` | `langchain` |
| Data/ML/AI | `Hugging Face` | ✅ synonym | `hugging-face` | `huggingface` |
| Data/ML/AI | `Prompt Engineering` | ✅ self-canonical | `prompt-engineering` | `prompt-engineering` |
| Data/ML/AI | `Vector Database` | ✅ self-canonical | `vector-database` | `vector-database` |
| Data/ML/AI | `RAG` | ✅ self-canonical | `rag` | `rag` |
| Testing/QA | `Selenium` | ✅ synonym | `selenium` | `selenium-webdriver` |
| Testing/QA | `Cypress` | ✅ synonym | `cypress` | `cypress` |
| Testing/QA | `Jest` | ✅ synonym | `jest` | `jestjs` |
| Testing/QA | `Mocha` | ✅ synonym | `mocha` | `mocha.js` |
| Testing/QA | `PyTest` | ✅ synonym | `pytest` | `pytest` |
| Testing/QA | `Postman` | ✅ self-canonical | `postman` | `postman` |
| Testing/QA | `TestNG` | ✅ self-canonical | `testng` | `testng` |
| Testing/QA | `Cucumber` | ✅ self-canonical | `cucumber` | `cucumber` |
| Testing/QA | `Appium` | ✅ self-canonical | `appium` | `appium` |
| Testing/QA | `Robot Framework` | ✅ self-canonical | `robot-framework` | `robot-framework` |
| Testing/QA | `Unit Testing` | ✅ synonym | `unit-testing` | `unit-testing` |
| Testing/QA | `Integration Testing` | ✅ synonym | `integration-testing` | `integration-testing` |
| Testing/QA | `Automation Testing` | ✅ self-canonical | `automation-testing` | `automation-testing` |
| Testing/QA | `Performance Testing` | ✅ synonym | `performance-testing` | `performance-testing` |
| Tool/VCS | `Git` | ✅ synonym | `git` | `git` |
| Tool/VCS | `GitHub` | ✅ self-canonical | `github` | `github` |
| Tool/VCS | `GitLab` | ✅ self-canonical | `gitlab` | `gitlab` |
| Tool/VCS | `Bitbucket` | ✅ self-canonical | `bitbucket` | `bitbucket` |
| Tool/VCS | `Jira` | ✅ self-canonical | `jira` | `jira` |
| Tool/VCS | `Confluence` | ✅ self-canonical | `confluence` | `confluence` |
| Tool/VCS | `Figma` | ✅ self-canonical | `figma` | `figma` |
| Tool/VCS | `Adobe XD` | ✅ self-canonical | `adobe-xd` | `adobe-xd` |
| Tool/VCS | `Photoshop` | ✅ self-canonical | `photoshop` | `photoshop` |
| Tool/VCS | `Visual Studio Code` | ✅ synonym | `visual-studio-code` | `visual-studio-code` |
| Tool/VCS | `npm` | ✅ synonym | `npm` | `npm` |
| Tool/VCS | `Yarn` | ✅ self-canonical | `yarn` | `yarn` |
| Khái niệm/Process | `Object-Oriented Programming` | ✅ synonym | `object-oriented-programming` | `oop` |
| Khái niệm/Process | `Design Patterns` | ✅ synonym | `design-patterns` | `design-patterns` |
| Khái niệm/Process | `Data Structures` | ✅ synonym | `data-structures` | `data-structures` |
| Khái niệm/Process | `Algorithms` | ✅ synonym | `algorithms` | `algorithm` |
| Khái niệm/Process | `Agile` | ✅ synonym | `agile` | `agile` |
| Khái niệm/Process | `Scrum` | ✅ self-canonical | `scrum` | `scrum` |
| Khái niệm/Process | `CI/CD` | ✅ self-canonical | `ci/cd` | `ci/cd` |
| Khái niệm/Process | `TDD` | ✅ synonym | `tdd` | `tdd` |
| Khái niệm/Process | `Microservices` | ✅ self-canonical | `microservices` | `microservices` |
| Khái niệm/Process | `REST API` | ✅ synonym | `rest-api` | `rest` |
| Khái niệm/Process | `RESTful API` | ✅ synonym | `restful-api` | `rest` |
| Khái niệm/Process | `SOAP` | ✅ self-canonical | `soap` | `soap` |
| Khái niệm/Process | `gRPC` | ✅ self-canonical | `grpc` | `grpc` |
| Khái niệm/Process | `WebSocket` | ✅ synonym | `websocket` | `websocket` |
| Khái niệm/Process | `OAuth2` | ✅ synonym | `oauth2` | `oauth-2.0` |
| Khái niệm/Process | `JWT` | ✅ synonym | `jwt` | `jwt` |
| Game/Emerging | `Unreal Engine` | ✅ self-canonical | `unreal-engine` | `unreal-engine` |
| Game/Emerging | `Blockchain` | ✅ self-canonical | `blockchain` | `blockchain` |
| Game/Emerging | `Solidity` | ✅ self-canonical | `solidity` | `solidity` |
| Game/Emerging | `IoT` | ✅ self-canonical | `iot` | `iot` |
| Game/Emerging | `WebGL` | ✅ self-canonical | `webgl` | `webgl` |
| Game/Emerging | `Three.js` | ✅ self-canonical | `three.js` | `three.js` |
| Game/Emerging | `Prisma` | ✅ self-canonical | `prisma` | `prisma` |
| Game/Emerging | `tRPC` | ✅ self-canonical | `trpc` | `trpc` |
| Game/Emerging | `Zustand` | ✅ self-canonical | `zustand` | `zustand` |
| Game/Emerging | `WebAssembly` | ✅ synonym | `webassembly` | `webassembly` |
| Game/Emerging | `Deno` | ✅ self-canonical | `deno` | `deno` |
| Game/Emerging | `Bun` | ✅ self-canonical | `bun` | `bun` |
| Game/Emerging | `Web3` | ✅ self-canonical | `web3` | `web3` |
| Game/Emerging | `Edge Computing` | ✅ self-canonical | `edge-computing` | `edge-computing` |
| Network/Security | `TCP/IP` | ✅ self-canonical | `tcp/ip` | `tcp/ip` |
| Network/Security | `HTTP` | ✅ self-canonical | `http` | `http` |
| Network/Security | `HTTPS` | ✅ self-canonical | `https` | `https` |
| Network/Security | `SSL` | ✅ synonym | `ssl` | `ssl` |
| Network/Security | `TLS` | ✅ synonym | `tls` | `ssl` |
| Network/Security | `OAuth` | ✅ self-canonical | `oauth` | `oauth` |
| Network/Security | `SAML` | ✅ self-canonical | `saml` | `saml` |
| Network/Security | `LDAP` | ✅ self-canonical | `ldap` | `ldap` |
| Network/Security | `Active Directory` | ✅ synonym | `active-directory` | `active-directory` |
| Network/Security | `Firewall` | ✅ self-canonical | `firewall` | `firewall` |
| Network/Security | `VPN` | ✅ self-canonical | `vpn` | `vpn` |
| Network/Security | `Penetration Testing` | ✅ self-canonical | `penetration-testing` | `penetration-testing` |
| Network/Security | `OWASP` | ✅ self-canonical | `owasp` | `owasp` |
| Network/Security | `Encryption` | ✅ synonym | `encryption` | `encryption` |
| Network/Security | `Single Sign-On` | ✅ synonym | `single-sign-on` | `single-sign-on` |
| Network/Security | `Two-Factor Authentication` | ✅ self-canonical | `two-factor-authentication` | `two-factor-authentication` |
| CMS/Ecommerce | `Shopify` | ✅ self-canonical | `shopify` | `shopify` |
| CMS/Ecommerce | `Magento` | ✅ synonym | `magento` | `magento` |
| CMS/Ecommerce | `WooCommerce` | ✅ self-canonical | `woocommerce` | `woocommerce` |
| CMS/Ecommerce | `Drupal` | ✅ self-canonical | `drupal` | `drupal` |
| CMS/Ecommerce | `Joomla` | ✅ self-canonical | `joomla` | `joomla` |
| CMS/Ecommerce | `Wix` | ✅ self-canonical | `wix` | `wix` |
| CMS/Ecommerce | `Webflow` | ✅ self-canonical | `webflow` | `webflow` |
| CMS/Ecommerce | `Elementor` | ✅ self-canonical | `elementor` | `elementor` |
| Monitoring | `Datadog` | ✅ self-canonical | `datadog` | `datadog` |
| Monitoring | `New Relic` | ✅ self-canonical | `new-relic` | `new-relic` |
| Monitoring | `Splunk` | ✅ self-canonical | `splunk` | `splunk` |
| Monitoring | `ELK Stack` | ✅ synonym | `elk-stack` | `elastic-stack` |
| Monitoring | `Nagios` | ✅ self-canonical | `nagios` | `nagios` |
| Monitoring | `Zabbix` | ✅ self-canonical | `zabbix` | `zabbix` |
| Monitoring | `Sentry` | ✅ self-canonical | `sentry` | `sentry` |
| Monitoring | `PagerDuty` | ✅ self-canonical | `pagerduty` | `pagerduty` |
| Monitoring | `Kibana` | ✅ self-canonical | `kibana` | `kibana` |
| Monitoring | `Logstash` | ✅ self-canonical | `logstash` | `logstash` |
| Message Queue | `RabbitMQ` | ✅ self-canonical | `rabbitmq` | `rabbitmq` |
| Message Queue | `ActiveMQ` | ✅ self-canonical | `activemq` | `activemq` |
| Message Queue | `ZeroMQ` | ✅ self-canonical | `zeromq` | `zeromq` |
| Message Queue | `Apache Kafka` | ✅ synonym | `apache-kafka` | `apache-kafka` |
| Message Queue | `Amazon SQS` | ✅ synonym | `amazon-sqs` | `sqs` |
| Message Queue | `Message Queue` | ✅ self-canonical | `message-queue` | `message-queue` |
| Design/PM | `Sketch` | ✅ self-canonical | `sketch` | `sketch` |
| Design/PM | `InVision` | ✅ self-canonical | `invision` | `invision` |
| Design/PM | `Zeplin` | ✅ self-canonical | `zeplin` | `zeplin` |
| Design/PM | `Canva` | ✅ self-canonical | `canva` | `canva` |
| Design/PM | `Trello` | ✅ self-canonical | `trello` | `trello` |
| Design/PM | `Asana` | ❌ KHÔNG tìm thấy | — | `asana` |
| Design/PM | `Monday.com` | ❌ KHÔNG tìm thấy | — | `monday.com` |
| Design/PM | `Notion` | ❌ KHÔNG tìm thấy | — | `notion` |
| Design/PM | `Miro` | ❌ KHÔNG tìm thấy | — | `miro` |
| Design/PM | `Slack` | ✅ self-canonical | `slack` | `slack` |
| OS | `Windows` | ✅ synonym | `windows` | `windows` |
| OS | `macOS` | ✅ synonym | `macos` | `macos` |
| OS | `Ubuntu` | ✅ synonym | `ubuntu` | `ubuntu` |
| OS | `CentOS` | ✅ self-canonical | `centos` | `centos` |
| OS | `Windows Server` | ✅ self-canonical | `windows-server` | `windows-server` |
| OS | `Red Hat Linux` | ❌ KHÔNG tìm thấy | — | `red hat linux` |
| Cloud hosting | `Heroku` | ✅ self-canonical | `heroku` | `heroku` |
| Cloud hosting | `Vercel` | ✅ synonym | `vercel` | `vercel` |
| Cloud hosting | `Netlify` | ✅ self-canonical | `netlify` | `netlify` |
| Cloud hosting | `DigitalOcean` | ✅ self-canonical | `digitalocean` | `digitalocean` |
| Cloud hosting | `Linode` | ✅ self-canonical | `linode` | `linode` |
| Cloud hosting | `Cloudflare` | ✅ self-canonical | `cloudflare` | `cloudflare` |
| Cloud hosting | `CDN` | ✅ self-canonical | `cdn` | `cdn` |
| Cloud hosting | `Serverless` | ✅ self-canonical | `serverless` | `serverless` |
| Data warehouse | `Data Warehouse` | ✅ synonym | `data-warehouse` | `data-warehouse` |
| Data warehouse | `Data Lake` | ✅ self-canonical | `data-lake` | `data-lake` |
| Data warehouse | `Redshift` | ✅ self-canonical | `redshift` | `redshift` |
| Data warehouse | `Databricks` | ✅ self-canonical | `databricks` | `databricks` |
| Data warehouse | `dbt` | ✅ self-canonical | `dbt` | `dbt` |
| Data warehouse | `Delta Lake` | ✅ self-canonical | `delta-lake` | `delta-lake` |
| Build/Testing bổ sung | `ESLint` | ✅ self-canonical | `eslint` | `eslint` |
| Build/Testing bổ sung | `Prettier` | ✅ self-canonical | `prettier` | `prettier` |
| Build/Testing bổ sung | `pnpm` | ✅ self-canonical | `pnpm` | `pnpm` |
| Build/Testing bổ sung | `ts-node` | ✅ self-canonical | `ts-node` | `ts-node` |
| Build/Testing bổ sung | `SWC` | ✅ self-canonical | `swc` | `swc` |
| Build/Testing bổ sung | `Playwright` | ✅ self-canonical | `playwright` | `playwright` |
| Build/Testing bổ sung | `Enzyme` | ✅ self-canonical | `enzyme` | `enzyme` |
| Build/Testing bổ sung | `Vitest` | ✅ self-canonical | `vitest` | `vitest` |
| Build/Testing bổ sung | `Storybook` | ✅ self-canonical | `storybook` | `storybook` |
| Quy trình/khác | `Kanban` | ✅ self-canonical | `kanban` | `kanban` |
| Quy trình/khác | `Waterfall` | ✅ self-canonical | `waterfall` | `waterfall` |
| Quy trình/khác | `Code Review` | ✅ self-canonical | `code-review` | `code-review` |
| Quy trình/khác | `Pair Programming` | ✅ self-canonical | `pair-programming` | `pair-programming` |
| Quy trình/khác | `Continuous Integration` | ✅ synonym | `continuous-integration` | `ci-cd` |
| Quy trình/khác | `Continuous Deployment` | ✅ self-canonical | `continuous-deployment` | `continuous-deployment` |
| Quy trình/khác | `Load Balancing` | ✅ synonym | `load-balancing` | `load-balancing` |
| Quy trình/khác | `Caching` | ✅ synonym | `caching` | `caching` |
| Quy trình/khác | `Fault Tolerance` | ✅ self-canonical | `fault-tolerance` | `fault-tolerance` |
| Quy trình/khác | `High Availability` | ✅ synonym | `high-availability` | `high-availability` |
| Quy trình/khác | `Scalability` | ✅ self-canonical | `scalability` | `scalability` |
| Quy trình/khác | `System Design` | ✅ self-canonical | `system-design` | `system-design` |
| Quy trình/khác | `API Gateway` | ✅ self-canonical | `api-gateway` | `api-gateway` |
| Quy trình/khác | `Rate Limiting` | ✅ synonym | `rate-limiting` | `rate-limiting` |
| Quy trình/khác | `Feature Flags` | ✅ self-canonical | `feature-flags` | `feature-flags` |
| Quy trình/khác | `Chaos Engineering` | ✅ self-canonical | `chaos-engineering` | `chaos-engineering` |
| AWS services | `Amazon EC2` | ✅ self-canonical | `amazon-ec2` | `amazon-ec2` |
| AWS services | `Amazon S3` | ✅ self-canonical | `amazon-s3` | `amazon-s3` |
| AWS services | `Amazon RDS` | ✅ self-canonical | `amazon-rds` | `amazon-rds` |
| AWS services | `AWS Lambda` | ✅ self-canonical | `aws-lambda` | `aws-lambda` |
| AWS services | `Amazon SQS` | ✅ synonym | `amazon-sqs` | `sqs` |
| AWS services | `Amazon SNS` | ✅ self-canonical | `amazon-sns` | `amazon-sns` |
| AWS services | `Amazon CloudFront` | ✅ self-canonical | `amazon-cloudfront` | `amazon-cloudfront` |
| AWS services | `Amazon Route 53` | ✅ self-canonical | `amazon-route-53` | `amazon-route-53` |
| AWS services | `AWS IAM` | ✅ self-canonical | `aws-iam` | `aws-iam` |
| AWS services | `Amazon ECS` | ✅ self-canonical | `amazon-ecs` | `amazon-ecs` |
| AWS services | `Amazon EKS` | ✅ self-canonical | `amazon-eks` | `amazon-eks` |
| AWS services | `AWS Fargate` | ✅ self-canonical | `aws-fargate` | `aws-fargate` |
| AWS services | `Amazon CloudWatch` | ✅ self-canonical | `amazon-cloudwatch` | `amazon-cloudwatch` |
| AWS services | `AWS CodePipeline` | ✅ self-canonical | `aws-codepipeline` | `aws-codepipeline` |
| AWS services | `AWS CodeBuild` | ✅ self-canonical | `aws-codebuild` | `aws-codebuild` |
| AWS services | `AWS CodeDeploy` | ✅ self-canonical | `aws-codedeploy` | `aws-codedeploy` |
| AWS services | `Amazon Kinesis` | ✅ self-canonical | `amazon-kinesis` | `amazon-kinesis` |
| AWS services | `AWS Glue` | ✅ self-canonical | `aws-glue` | `aws-glue` |
| AWS services | `Amazon Athena` | ✅ self-canonical | `amazon-athena` | `amazon-athena` |
| AWS services | `Amazon SageMaker` | ✅ self-canonical | `amazon-sagemaker` | `amazon-sagemaker` |
| AWS services | `AWS Elastic Beanstalk` | ✅ self-canonical | `aws-elastic-beanstalk` | `aws-elastic-beanstalk` |
| AWS services | `Amazon API Gateway` | ✅ self-canonical | `amazon-api-gateway` | `amazon-api-gateway` |
| AWS services | `AWS Step Functions` | ✅ self-canonical | `aws-step-functions` | `aws-step-functions` |
| AWS services | `AWS Secrets Manager` | ✅ self-canonical | `aws-secrets-manager` | `aws-secrets-manager` |
| AWS services | `AWS KMS` | ✅ self-canonical | `aws-kms` | `aws-kms` |
| AWS services | `Amazon VPC` | ✅ self-canonical | `amazon-vpc` | `amazon-vpc` |
| AWS services | `Amazon Aurora` | ✅ self-canonical | `amazon-aurora` | `amazon-aurora` |
| AWS services | `Amazon ElastiCache` | ✅ self-canonical | `amazon-elasticache` | `amazon-elasticache` |
| AWS services | `Amazon Neptune` | ❌ KHÔNG tìm thấy | — | `amazon neptune` |
| AWS services | `Amazon DocumentDB` | ❌ KHÔNG tìm thấy | — | `amazon documentdb` |
| AWS services | `AWS AppSync` | ❌ KHÔNG tìm thấy | — | `aws appsync` |
| AWS services | `AWS Amplify` | ❌ KHÔNG tìm thấy | — | `aws amplify` |
| AWS services | `Amazon Cognito` | ✅ self-canonical | `amazon-cognito` | `amazon-cognito` |
| AWS services | `AWS CloudTrail` | ❌ KHÔNG tìm thấy | — | `aws cloudtrail` |
| AWS services | `AWS Systems Manager` | ❌ KHÔNG tìm thấy | — | `aws systems manager` |
| AWS services | `Amazon EMR` | ✅ self-canonical | `amazon-emr` | `amazon-emr` |
| Azure services | `Azure SQL Database` | ✅ self-canonical | `azure-sql-database` | `azure-sql-database` |
| Azure services | `Azure Cosmos DB` | ✅ self-canonical | `azure-cosmos-db` | `azure-cosmos-db` |
| Azure services | `Azure Kubernetes Service` | ✅ self-canonical | `azure-kubernetes-service` | `azure-kubernetes-service` |
| Azure services | `Azure Blob Storage` | ✅ self-canonical | `azure-blob-storage` | `azure-blob-storage` |
| Azure services | `Azure Active Directory` | ✅ self-canonical | `azure-active-directory` | `azure-active-directory` |
| Azure services | `Azure App Service` | ✅ self-canonical | `azure-app-service` | `azure-app-service` |
| Azure services | `Azure Data Factory` | ✅ self-canonical | `azure-data-factory` | `azure-data-factory` |
| Azure services | `Azure Synapse Analytics` | ✅ self-canonical | `azure-synapse-analytics` | `azure-synapse-analytics` |
| Azure services | `Azure Monitor` | ✅ self-canonical | `azure-monitor` | `azure-monitor` |
| Azure services | `Azure Logic Apps` | ✅ self-canonical | `azure-logic-apps` | `azure-logic-apps` |
| Azure services | `Azure Service Bus` | ✅ self-canonical | `azure-service-bus` | `azure-service-bus` |
| Azure services | `Azure Event Hub` | ❌ KHÔNG tìm thấy | — | `azure event hub` |
| Azure services | `Azure Key Vault` | ✅ self-canonical | `azure-key-vault` | `azure-key-vault` |
| Azure services | `Azure Container Instances` | ❌ KHÔNG tìm thấy | — | `azure container instances` |
| Azure services | `Azure Data Lake` | ✅ self-canonical | `azure-data-lake` | `azure-data-lake` |
| Azure services | `Azure Databricks` | ✅ self-canonical | `azure-databricks` | `azure-databricks` |
| Azure services | `Azure Virtual Machines` | ✅ self-canonical | `azure-virtual-machines` | `azure-virtual-machines` |
| Azure services | `Azure DevOps Pipelines` | ❌ KHÔNG tìm thấy | — | `azure devops pipelines` |
| Azure services | `Azure API Management` | ✅ self-canonical | `azure-api-management` | `azure-api-management` |
| Azure services | `Azure Functions App` | ✅ synonym | `azure-functions-app` | `azure-functions` |
| Azure services | `Azure Front Door` | ❌ KHÔNG tìm thấy | — | `azure front door` |
| Azure services | `Azure Cognitive Services` | ✅ self-canonical | `azure-cognitive-services` | `azure-cognitive-services` |
| Azure services | `Azure Machine Learning` | ✅ self-canonical | `azure-machine-learning` | `azure-machine-learning` |
| Azure services | `Azure Resource Manager` | ❌ KHÔNG tìm thấy | — | `azure resource manager` |
| Azure services | `Azure DNS` | ✅ self-canonical | `azure-dns` | `azure-dns` |
| Azure services | `Azure CDN` | ✅ self-canonical | `azure-cdn` | `azure-cdn` |
| Azure services | `Azure Application Insights` | ✅ self-canonical | `azure-application-insights` | `azure-application-insights` |
| Azure services | `Azure Service Fabric` | ✅ self-canonical | `azure-service-fabric` | `azure-service-fabric` |
| Azure services | `Azure Batch` | ❌ KHÔNG tìm thấy | — | `azure batch` |
| Azure services | `Azure Notification Hubs` | ✅ self-canonical | `azure-notification-hubs` | `azure-notification-hubs` |
| GCP services | `Cloud Run` | ✅ self-canonical | `cloud-run` | `cloud-run` |
| GCP services | `Cloud Functions` | ✅ synonym | `cloud-functions` | `google-cloud-functions` |
| GCP services | `Cloud Storage` | ✅ self-canonical | `cloud-storage` | `cloud-storage` |
| GCP services | `Compute Engine` | ✅ self-canonical | `compute-engine` | `compute-engine` |
| GCP services | `Cloud SQL` | ✅ self-canonical | `cloud-sql` | `cloud-sql` |
| GCP services | `Firestore` | ✅ self-canonical | `firestore` | `firestore` |
| GCP services | `Pub/Sub` | ❌ KHÔNG tìm thấy | — | `pub/sub` |
| GCP services | `Cloud Dataflow` | ✅ self-canonical | `cloud-dataflow` | `cloud-dataflow` |
| GCP services | `Cloud Dataproc` | ✅ self-canonical | `cloud-dataproc` | `cloud-dataproc` |
| GCP services | `Vertex AI` | ✅ self-canonical | `vertex-ai` | `vertex-ai` |
| GCP services | `GKE` | ✅ self-canonical | `gke` | `gke` |
| GCP services | `Cloud Build` | ✅ self-canonical | `cloud-build` | `cloud-build` |
| GCP services | `Cloud CDN` | ❌ KHÔNG tìm thấy | — | `cloud cdn` |
| GCP services | `Cloud Spanner` | ✅ self-canonical | `cloud-spanner` | `cloud-spanner` |
| GCP services | `Cloud Bigtable` | ✅ self-canonical | `cloud-bigtable` | `cloud-bigtable` |
| GCP services | `Cloud Pub/Sub` | ❌ KHÔNG tìm thấy | — | `cloud pub/sub` |
| GCP services | `Cloud IAM` | ✅ self-canonical | `cloud-iam` | `cloud-iam` |
| GCP services | `Cloud Load Balancing` | ❌ KHÔNG tìm thấy | — | `cloud load balancing` |
| GCP services | `Cloud Monitoring` | ✅ self-canonical | `cloud-monitoring` | `cloud-monitoring` |
| GCP services | `Cloud Logging` | ❌ KHÔNG tìm thấy | — | `cloud logging` |
| GCP services | `Cloud Armor` | ❌ KHÔNG tìm thấy | — | `cloud armor` |
| GCP services | `Cloud Endpoints` | ❌ KHÔNG tìm thấy | — | `cloud endpoints` |
| GCP services | `Anthos` | ❌ KHÔNG tìm thấy | — | `anthos` |
| GCP services | `App Engine` | ✅ self-canonical | `app-engine` | `app-engine` |
| GCP services | `Cloud Composer` | ✅ self-canonical | `cloud-composer` | `cloud-composer` |
| GCP services | `Cloud Data Fusion` | ❌ KHÔNG tìm thấy | — | `cloud data fusion` |
| GCP services | `Cloud Natural Language API` | ❌ KHÔNG tìm thấy | — | `cloud natural language api` |
| GCP services | `Cloud Vision API` | ❌ KHÔNG tìm thấy | — | `cloud vision api` |
| GCP services | `Cloud Text-to-Speech` | ❌ KHÔNG tìm thấy | — | `cloud text-to-speech` |
| GCP services | `Firebase Hosting` | ❌ KHÔNG tìm thấy | — | `firebase hosting` |
| BI/ERP/CRM | `SAP` | ✅ self-canonical | `sap` | `sap` |
| BI/ERP/CRM | `SAP ABAP` | ✅ self-canonical | `sap-abap` | `sap-abap` |
| BI/ERP/CRM | `SAP HANA` | ✅ self-canonical | `sap-hana` | `sap-hana` |
| BI/ERP/CRM | `SAP FICO` | ✅ self-canonical | `sap-fico` | `sap-fico` |
| BI/ERP/CRM | `SAP MM` | ✅ self-canonical | `sap-mm` | `sap-mm` |
| BI/ERP/CRM | `Salesforce` | ✅ synonym | `salesforce` | `salesforce` |
| BI/ERP/CRM | `Salesforce Apex` | ✅ synonym | `salesforce-apex` | `apex` |
| BI/ERP/CRM | `Salesforce Lightning` | ✅ self-canonical | `salesforce-lightning` | `salesforce-lightning` |
| BI/ERP/CRM | `Microsoft Dynamics 365` | ✅ self-canonical | `microsoft-dynamics-365` | `microsoft-dynamics-365` |
| BI/ERP/CRM | `Oracle NetSuite` | ✅ self-canonical | `oracle-netsuite` | `oracle-netsuite` |
| BI/ERP/CRM | `Odoo` | ✅ synonym | `odoo` | `odoo` |
| BI/ERP/CRM | `Zoho CRM` | ✅ self-canonical | `zoho-crm` | `zoho-crm` |
| BI/ERP/CRM | `HubSpot` | ✅ self-canonical | `hubspot` | `hubspot` |
| BI/ERP/CRM | `Looker` | ✅ self-canonical | `looker` | `looker` |
| BI/ERP/CRM | `Qlik Sense` | ✅ self-canonical | `qlik-sense` | `qlik-sense` |
| BI/ERP/CRM | `Sisense` | ✅ self-canonical | `sisense` | `sisense` |
| BI/ERP/CRM | `Domo` | ✅ self-canonical | `domo` | `domo` |
| BI/ERP/CRM | `Metabase` | ✅ self-canonical | `metabase` | `metabase` |
| BI/ERP/CRM | `Google Data Studio` | ✅ self-canonical | `google-data-studio` | `google-data-studio` |
| BI/ERP/CRM | `SSRS` | ✅ synonym | `ssrs` | `reporting-services` |
| BI/ERP/CRM | `SSIS` | ✅ synonym | `ssis` | `ssis` |
| BI/ERP/CRM | `SSAS` | ✅ synonym | `ssas` | `ssas` |
| BI/ERP/CRM | `Alteryx` | ✅ self-canonical | `alteryx` | `alteryx` |
| BI/ERP/CRM | `KNIME` | ✅ self-canonical | `knime` | `knime` |
| Embedded/IoT | `Arduino` | ✅ self-canonical | `arduino` | `arduino` |
| Embedded/IoT | `Raspberry Pi` | ✅ self-canonical | `raspberry-pi` | `raspberry-pi` |
| Embedded/IoT | `Embedded C` | ✅ self-canonical | `embedded-c` | `embedded-c` |
| Embedded/IoT | `RTOS` | ✅ self-canonical | `rtos` | `rtos` |
| Embedded/IoT | `FreeRTOS` | ✅ self-canonical | `freertos` | `freertos` |
| Embedded/IoT | `Microcontroller Programming` | ✅ self-canonical | `microcontroller-programming` | `microcontroller-programming` |
| Embedded/IoT | `ESP32` | ✅ self-canonical | `esp32` | `esp32` |
| Embedded/IoT | `STM32` | ✅ self-canonical | `stm32` | `stm32` |
| Embedded/IoT | `MQTT` | ✅ self-canonical | `mqtt` | `mqtt` |
| Embedded/IoT | `Zigbee` | ✅ self-canonical | `zigbee` | `zigbee` |
| Embedded/IoT | `LoRaWAN` | ✅ self-canonical | `lorawan` | `lorawan` |
| Embedded/IoT | `PLC Programming` | ✅ synonym | `plc-programming` | `plc` |
| Embedded/IoT | `SCADA` | ✅ self-canonical | `scada` | `scada` |
| Embedded/IoT | `Modbus` | ✅ self-canonical | `modbus` | `modbus` |
| Blockchain | `Ethereum` | ✅ self-canonical | `ethereum` | `ethereum` |
| Blockchain | `Smart Contract` | ✅ synonym | `smart-contract` | `smart-contracts` |
| Blockchain | `Hyperledger Fabric` | ✅ self-canonical | `hyperledger-fabric` | `hyperledger-fabric` |
| Blockchain | `Truffle` | ✅ self-canonical | `truffle` | `truffle` |
| Blockchain | `Hardhat` | ✅ self-canonical | `hardhat` | `hardhat` |
| Blockchain | `Web3.js` | ✅ self-canonical | `web3.js` | `web3.js` |
| Blockchain | `Ethers.js` | ✅ self-canonical | `ethers.js` | `ethers.js` |
| Blockchain | `MetaMask` | ✅ self-canonical | `metamask` | `metamask` |
| Blockchain | `NFT` | ✅ self-canonical | `nft` | `nft` |
| Blockchain | `DeFi` | ✅ self-canonical | `defi` | `defi` |
| Blockchain | `IPFS` | ✅ self-canonical | `ipfs` | `ipfs` |
| AR/VR/Graphics | `ARKit` | ✅ self-canonical | `arkit` | `arkit` |
| AR/VR/Graphics | `ARCore` | ✅ self-canonical | `arcore` | `arcore` |
| AR/VR/Graphics | `OpenGL` | ✅ self-canonical | `opengl` | `opengl` |
| AR/VR/Graphics | `DirectX` | ✅ self-canonical | `directx` | `directx` |
| AR/VR/Graphics | `Vulkan` | ✅ self-canonical | `vulkan` | `vulkan` |
| AR/VR/Graphics | `Blender` | ✅ self-canonical | `blender` | `blender` |
| AR/VR/Graphics | `Maya` | ✅ self-canonical | `maya` | `maya` |
| AR/VR/Graphics | `3ds Max` | ✅ self-canonical | `3ds-max` | `3ds-max` |
| AR/VR/Graphics | `Godot Engine` | ✅ synonym | `godot-engine` | `godot` |
| AR/VR/Graphics | `WebXR` | ✅ self-canonical | `webxr` | `webxr` |
| Networking protocol | `DNS` | ✅ synonym | `dns` | `dns` |
| Networking protocol | `DHCP` | ✅ self-canonical | `dhcp` | `dhcp` |
| Networking protocol | `FTP` | ✅ self-canonical | `ftp` | `ftp` |
| Networking protocol | `SFTP` | ✅ self-canonical | `sftp` | `sftp` |
| Networking protocol | `SMTP` | ✅ self-canonical | `smtp` | `smtp` |
| Networking protocol | `IMAP` | ✅ self-canonical | `imap` | `imap` |
| Networking protocol | `POP3` | ✅ self-canonical | `pop3` | `pop3` |
| Networking protocol | `SNMP` | ✅ self-canonical | `snmp` | `snmp` |
| Networking protocol | `VoIP` | ✅ self-canonical | `voip` | `voip` |
| Networking protocol | `SIP Protocol` | ✅ synonym | `sip-protocol` | `sip` |
| Networking protocol | `BGP` | ✅ self-canonical | `bgp` | `bgp` |
| Networking protocol | `OSPF` | ✅ self-canonical | `ospf` | `ospf` |
| Networking protocol | `IPsec` | ✅ self-canonical | `ipsec` | `ipsec` |
| Networking protocol | `MPLS` | ✅ self-canonical | `mpls` | `mpls` |
| Ngôn ngữ/tool hiếm | `COBOL` | ✅ self-canonical | `cobol` | `cobol` |
| Ngôn ngữ/tool hiếm | `Ada` | ✅ self-canonical | `ada` | `ada` |
| Ngôn ngữ/tool hiếm | `Prolog` | ✅ self-canonical | `prolog` | `prolog` |
| Ngôn ngữ/tool hiếm | `Scheme` | ✅ self-canonical | `scheme` | `scheme` |
| Ngôn ngữ/tool hiếm | `Common Lisp` | ✅ self-canonical | `common-lisp` | `common-lisp` |
| Ngôn ngữ/tool hiếm | `Racket` | ✅ synonym | `racket` | `racket` |
| Ngôn ngữ/tool hiếm | `OCaml` | ✅ self-canonical | `ocaml` | `ocaml` |
| Ngôn ngữ/tool hiếm | `Nim Lang` | ❌ KHÔNG tìm thấy | — | `nim lang` |
| Ngôn ngữ/tool hiếm | `Zig Lang` | ✅ synonym | `zig-lang` | `zig` |
| Ngôn ngữ/tool hiếm | `Crystal Lang` | ✅ self-canonical | `crystal-lang` | `crystal-lang` |
| Ngôn ngữ/tool hiếm | `D Language` | ✅ synonym | `d-language` | `d` |
| Ngôn ngữ/tool hiếm | `Pascal` | ✅ self-canonical | `pascal` | `pascal` |
| Ngôn ngữ/tool hiếm | `Smalltalk` | ✅ self-canonical | `smalltalk` | `smalltalk` |
| Ngôn ngữ/tool hiếm | `Tcl` | ✅ self-canonical | `tcl` | `tcl` |
| Ngôn ngữ/tool hiếm | `AWK` | ✅ synonym | `awk` | `awk` |
| Ngôn ngữ/tool hiếm | `Sed` | ✅ self-canonical | `sed` | `sed` |
| Ngôn ngữ/tool hiếm | `PowerShell Core` | ✅ synonym | `powershell-core` | `powershell` |
| Ngôn ngữ/tool hiếm | `Visual Basic .NET` | ✅ synonym | `visual-basic-net` | `vb.net` |
| Ngôn ngữ/tool hiếm | `Apex Language` | ✅ synonym | `apex-language` | `apex` |
| Ngôn ngữ/tool hiếm | `Vimscript` | ✅ synonym | `vimscript` | `vim` |
| Python stack bổ sung | `Pyramid` | ✅ self-canonical | `pyramid` | `pyramid` |
| Python stack bổ sung | `Bottle` | ✅ self-canonical | `bottle` | `bottle` |
| Python stack bổ sung | `Tornado Web` | ✅ synonym | `tornado-web` | `tornado` |
| Python stack bổ sung | `aiohttp` | ✅ self-canonical | `aiohttp` | `aiohttp` |
| Python stack bổ sung | `httpx` | ✅ self-canonical | `httpx` | `httpx` |
| Python stack bổ sung | `Requests` | ✅ synonym | `requests` | `python-requests` |
| Python stack bổ sung | `XGBoost` | ✅ self-canonical | `xgboost` | `xgboost` |
| Python stack bổ sung | `LightGBM` | ✅ self-canonical | `lightgbm` | `lightgbm` |
| Python stack bổ sung | `CatBoost` | ✅ self-canonical | `catboost` | `catboost` |
| Python stack bổ sung | `JAX` | ✅ self-canonical | `jax` | `jax` |
| Python stack bổ sung | `Pillow` | ✅ synonym | `pillow` | `python-imaging-library` |
| Python stack bổ sung | `spaCy` | ✅ self-canonical | `spacy` | `spacy` |
| Python stack bổ sung | `NLTK` | ✅ self-canonical | `nltk` | `nltk` |
| Python stack bổ sung | `Gensim` | ✅ self-canonical | `gensim` | `gensim` |
| Python stack bổ sung | `Transformers` | ✅ self-canonical | `transformers` | `transformers` |
| Python stack bổ sung | `Alembic` | ✅ self-canonical | `alembic` | `alembic` |
| Python stack bổ sung | `Marshmallow` | ✅ self-canonical | `marshmallow` | `marshmallow` |
| Python stack bổ sung | `Click` | ✅ synonym | `click` | `click` |
| Python stack bổ sung | `Typer` | ✅ self-canonical | `typer` | `typer` |
| Python stack bổ sung | `PyYAML` | ✅ synonym | `pyyaml` | `yaml` |
| Python stack bổ sung | `Django REST Framework` | ✅ synonym | `django-rest-framework` | `django-rest-framework` |
| Python stack bổ sung | `Django Channels` | ✅ self-canonical | `django-channels` | `django-channels` |
| Python stack bổ sung | `Dash` | ✅ self-canonical | `dash` | `dash` |
| Python stack bổ sung | `Gradio` | ✅ self-canonical | `gradio` | `gradio` |
| Python stack bổ sung | `Poetry` | ✅ synonym | `poetry` | `python-poetry` |
| Python stack bổ sung | `Black Formatter` | ❌ KHÔNG tìm thấy | — | `black formatter` |
| Python stack bổ sung | `Flake8` | ✅ self-canonical | `flake8` | `flake8` |
| Python stack bổ sung | `Mypy` | ✅ self-canonical | `mypy` | `mypy` |
| Python stack bổ sung | `Numba` | ✅ self-canonical | `numba` | `numba` |
| Python stack bổ sung | `Dask` | ✅ self-canonical | `dask` | `dask` |
| Python stack bổ sung | `Ray` | ✅ self-canonical | `ray` | `ray` |
| Python stack bổ sung | `Luigi` | ✅ self-canonical | `luigi` | `luigi` |
| Python stack bổ sung | `Prefect` | ✅ self-canonical | `prefect` | `prefect` |
| Python stack bổ sung | `Great Expectations` | ✅ self-canonical | `great-expectations` | `great-expectations` |
| JS/TS stack bổ sung | `Zod` | ✅ self-canonical | `zod` | `zod` |
| JS/TS stack bổ sung | `Yup` | ✅ self-canonical | `yup` | `yup` |
| JS/TS stack bổ sung | `Lodash` | ✅ synonym | `lodash` | `lodash` |
| JS/TS stack bổ sung | `Day.js` | ✅ self-canonical | `dayjs` | `dayjs` |
| JS/TS stack bổ sung | `date-fns` | ✅ self-canonical | `date-fns` | `date-fns` |
| JS/TS stack bổ sung | `Axios` | ✅ self-canonical | `axios` | `axios` |
| JS/TS stack bổ sung | `React Query` | ✅ self-canonical | `react-query` | `react-query` |
| JS/TS stack bổ sung | `TanStack Query` | ✅ self-canonical | `tanstack-query` | `tanstack-query` |
| JS/TS stack bổ sung | `SWR` | ✅ self-canonical | `swr` | `swr` |
| JS/TS stack bổ sung | `Recoil` | ✅ self-canonical | `recoil` | `recoil` |
| JS/TS stack bổ sung | `Jotai` | ✅ self-canonical | `jotai` | `jotai` |
| JS/TS stack bổ sung | `Framer Motion` | ✅ self-canonical | `framer-motion` | `framer-motion` |
| JS/TS stack bổ sung | `GSAP` | ✅ synonym | `gsap` | `gsap` |
| JS/TS stack bổ sung | `D3.js` | ✅ synonym | `d3.js` | `d3.js` |
| JS/TS stack bổ sung | `Chart.js` | ✅ synonym | `chart.js` | `chart.js` |
| JS/TS stack bổ sung | `Highcharts` | ✅ synonym | `highcharts` | `highcharts` |
| JS/TS stack bổ sung | `ApexCharts` | ✅ self-canonical | `apexcharts` | `apexcharts` |
| JS/TS stack bổ sung | `Puppeteer` | ✅ self-canonical | `puppeteer` | `puppeteer` |
| JS/TS stack bổ sung | `Turborepo` | ✅ self-canonical | `turborepo` | `turborepo` |
| JS/TS stack bổ sung | `Nx Monorepo` | ✅ self-canonical | `nx-monorepo` | `nx-monorepo` |
| JS/TS stack bổ sung | `Lerna` | ✅ self-canonical | `lerna` | `lerna` |
| JS/TS stack bổ sung | `Rollup.js` | ✅ self-canonical | `rollupjs` | `rollupjs` |
| JS/TS stack bổ sung | `Parcel Bundler` | ✅ self-canonical | `parcel-bundler` | `parcel-bundler` |
| JS/TS stack bổ sung | `esbuild` | ✅ self-canonical | `esbuild` | `esbuild` |
| JS/TS stack bổ sung | `Astro` | ✅ self-canonical | `astro` | `astro` |
| JS/TS stack bổ sung | `Remix` | ✅ self-canonical | `remix` | `remix` |
| JS/TS stack bổ sung | `SolidJS` | ✅ self-canonical | `solidjs` | `solidjs` |
| JS/TS stack bổ sung | `Qwik` | ✅ self-canonical | `qwik` | `qwik` |
| JS/TS stack bổ sung | `Alpine.js` | ✅ synonym | `alpine.js` | `alpine.js` |
| JS/TS stack bổ sung | `Preact` | ✅ self-canonical | `preact` | `preact` |
| Testing/QA bổ sung | `WebdriverIO` | ✅ self-canonical | `webdriverio` | `webdriverio` |
| Testing/QA bổ sung | `Karate DSL` | ✅ synonym | `karate-dsl` | `karate` |
| Testing/QA bổ sung | `Gatling` | ✅ self-canonical | `gatling` | `gatling` |
| Testing/QA bổ sung | `JMeter` | ✅ synonym | `jmeter` | `jmeter` |
| Testing/QA bổ sung | `LoadRunner` | ✅ synonym | `loadrunner` | `loadrunner` |
| Testing/QA bổ sung | `SoapUI` | ✅ self-canonical | `soapui` | `soapui` |
| Testing/QA bổ sung | `Katalon Studio` | ✅ self-canonical | `katalon-studio` | `katalon-studio` |
| Testing/QA bổ sung | `Testcontainers` | ✅ self-canonical | `testcontainers` | `testcontainers` |
| Testing/QA bổ sung | `Mockito` | ✅ self-canonical | `mockito` | `mockito` |
| Testing/QA bổ sung | `Chai.js` | ✅ self-canonical | `chai.js` | `chai.js` |
| Testing/QA bổ sung | `Sinon.js` | ✅ self-canonical | `sinon.js` | `sinon.js` |
| Testing/QA bổ sung | `Supertest` | ✅ self-canonical | `supertest` | `supertest` |
| Testing/QA bổ sung | `Locust` | ✅ self-canonical | `locust` | `locust` |
| Testing/QA bổ sung | `k6` | ✅ self-canonical | `k6` | `k6` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon ec2` | ✅ self-canonical | `amazon-ec2` | `amazon-ec2` |
| Biến thể định dạng (bổ sung tới 1000) | `UBUNTU` | ✅ synonym | `ubuntu` | `ubuntu` |
| Biến thể định dạng (bổ sung tới 1000) | `Feature_Flags` | ❌ KHÔNG tìm thấy | — | `feature_flags` |
| Biến thể định dạng (bổ sung tới 1000) | `AMAZON-VPC` | ✅ self-canonical | `amazon-vpc` | `amazon-vpc` |
| Biến thể định dạng (bổ sung tới 1000) | `NUXT.JS` | ✅ synonym | `nuxt.js` | `nuxt.js` |
| Biến thể định dạng (bổ sung tới 1000) | `php` | ✅ self-canonical | `php` | `php` |
| Biến thể định dạng (bổ sung tới 1000) | `appium` | ✅ self-canonical | `appium` | `appium` |
| Biến thể định dạng (bổ sung tới 1000) | `gOLANG` | ✅ synonym | `golang` | `go` |
| Biến thể định dạng (bổ sung tới 1000) | `DENO` | ✅ self-canonical | `deno` | `deno` |
| Biến thể định dạng (bổ sung tới 1000) | `load-balancing` | ✅ synonym | `load-balancing` | `load-balancing` |
| Biến thể định dạng (bổ sung tới 1000) | `Crystal-Lang` | ✅ self-canonical | `crystal-lang` | `crystal-lang` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon-aurora` | ✅ self-canonical | `amazon-aurora` | `amazon-aurora` |
| Biến thể định dạng (bổ sung tới 1000) | `Dayjs` | ✅ self-canonical | `dayjs` | `dayjs` |
| Biến thể định dạng (bổ sung tới 1000) | `CLOUD-LOAD-BALANCING` | ❌ KHÔNG tìm thấy | — | `cloud-load-balancing` |
| Biến thể định dạng (bổ sung tới 1000) | `visual-studio-code` | ✅ synonym | `visual-studio-code` | `visual-studio-code` |
| Biến thể định dạng (bổ sung tới 1000) | `nX mONOREPO` | ✅ self-canonical | `nx-monorepo` | `nx-monorepo` |
| Biến thể định dạng (bổ sung tới 1000) | `WIX` | ✅ self-canonical | `wix` | `wix` |
| Biến thể định dạng (bổ sung tới 1000) | `Nodejs` | ✅ synonym | `nodejs` | `node.js` |
| Biến thể định dạng (bổ sung tới 1000) | `NESTJS` | ✅ self-canonical | `nestjs` | `nestjs` |
| Biến thể định dạng (bổ sung tới 1000) | `perl` | ✅ synonym | `perl` | `perl` |
| Biến thể định dạng (bổ sung tới 1000) | `message-queue` | ✅ self-canonical | `message-queue` | `message-queue` |
| Biến thể định dạng (bổ sung tới 1000) | `Metamask` | ✅ self-canonical | `metamask` | `metamask` |
| Biến thể định dạng (bổ sung tới 1000) | `CATBOOST` | ✅ self-canonical | `catboost` | `catboost` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud-Functions` | ✅ synonym | `cloud-functions` | `google-cloud-functions` |
| Biến thể định dạng (bổ sung tới 1000) | `BLAZOR` | ✅ synonym | `blazor` | `blazor` |
| Biến thể định dạng (bổ sung tới 1000) | `HASKELL` | ✅ self-canonical | `haskell` | `haskell` |
| Biến thể định dạng (bổ sung tới 1000) | `React_Query` | ❌ KHÔNG tìm thấy | — | `react_query` |
| Biến thể định dạng (bổ sung tới 1000) | `swiftui` | ✅ synonym | `swiftui` | `swiftui` |
| Biến thể định dạng (bổ sung tới 1000) | `AMAZON-SNS` | ✅ self-canonical | `amazon-sns` | `amazon-sns` |
| Biến thể định dạng (bổ sung tới 1000) | `sMALLTALK` | ✅ self-canonical | `smalltalk` | `smalltalk` |
| Biến thể định dạng (bổ sung tới 1000) | `cordova` | ✅ synonym | `cordova` | `cordova` |
| Biến thể định dạng (bổ sung tới 1000) | `Design_Patterns` | ❌ KHÔNG tìm thấy | — | `design_patterns` |
| Biến thể định dạng (bổ sung tới 1000) | `REST_API` | ❌ KHÔNG tìm thấy | — | `rest_api` |
| Biến thể định dạng (bổ sung tới 1000) | `azure blob storage` | ✅ self-canonical | `azure-blob-storage` | `azure-blob-storage` |
| Biến thể định dạng (bổ sung tới 1000) | `tORNADO wEB` | ✅ synonym | `tornado-web` | `tornado` |
| Biến thể định dạng (bổ sung tới 1000) | `Chartjs` | ✅ synonym | `chartjs` | `chart.js` |
| Biến thể định dạng (bổ sung tới 1000) | `ssl` | ✅ synonym | `ssl` | `ssl` |
| Biến thể định dạng (bổ sung tới 1000) | `IOT` | ✅ self-canonical | `iot` | `iot` |
| Biến thể định dạng (bổ sung tới 1000) | `html5` | ✅ synonym | `html5` | `html` |
| Biến thể định dạng (bổ sung tới 1000) | `bootstrap` | ✅ self-canonical | `bootstrap` | `bootstrap` |
| Biến thể định dạng (bổ sung tới 1000) | `aMAZON eLASTIcACHE` | ✅ self-canonical | `amazon-elasticache` | `amazon-elasticache` |
| Biến thể định dạng (bổ sung tới 1000) | `NGINX` | ✅ self-canonical | `nginx` | `nginx` |
| Biến thể định dạng (bổ sung tới 1000) | `NEXTJS` | ✅ synonym | `nextjs` | `next.js` |
| Biến thể định dạng (bổ sung tới 1000) | `aZURE fUNCTIONS aPP` | ✅ synonym | `azure-functions-app` | `azure-functions` |
| Biến thể định dạng (bổ sung tới 1000) | `UNREAL ENGINE` | ✅ self-canonical | `unreal-engine` | `unreal-engine` |
| Biến thể định dạng (bổ sung tới 1000) | `DEEP-LEARNING` | ✅ synonym | `deep-learning` | `deep-learning` |
| Biến thể định dạng (bổ sung tới 1000) | `RSPEC` | ✅ self-canonical | `rspec` | `rspec` |
| Biến thể định dạng (bổ sung tới 1000) | `DATADOG` | ✅ self-canonical | `datadog` | `datadog` |
| Biến thể định dạng (bổ sung tới 1000) | `BEAUTIFULSOUP` | ✅ synonym | `beautifulsoup` | `beautifulsoup` |
| Biến thể định dạng (bổ sung tới 1000) | `Typescript` | ✅ synonym | `typescript` | `typescript` |
| Biến thể định dạng (bổ sung tới 1000) | `Sap Abap` | ✅ self-canonical | `sap-abap` | `sap-abap` |
| Biến thể định dạng (bổ sung tới 1000) | `streamlit` | ✅ self-canonical | `streamlit` | `streamlit` |
| Biến thể định dạng (bổ sung tới 1000) | `blender` | ✅ self-canonical | `blender` | `blender` |
| Biến thể định dạng (bổ sung tới 1000) | `cONTINUOUS iNTEGRATION` | ✅ synonym | `continuous-integration` | `ci-cd` |
| Biến thể định dạng (bổ sung tới 1000) | `gcp` | ✅ self-canonical | `gcp` | `gcp` |
| Biến thể định dạng (bổ sung tới 1000) | `recoil` | ✅ self-canonical | `recoil` | `recoil` |
| Biến thể định dạng (bổ sung tới 1000) | `SISENSE` | ✅ self-canonical | `sisense` | `sisense` |
| Biến thể định dạng (bổ sung tới 1000) | `Oracle Netsuite` | ✅ self-canonical | `oracle-netsuite` | `oracle-netsuite` |
| Biến thể định dạng (bổ sung tới 1000) | `sed` | ✅ self-canonical | `sed` | `sed` |
| Biến thể định dạng (bổ sung tới 1000) | `nx-monorepo` | ✅ self-canonical | `nx-monorepo` | `nx-monorepo` |
| Biến thể định dạng (bổ sung tới 1000) | `NEO4J` | ✅ synonym | `neo4j` | `neo4j` |
| Biến thể định dạng (bổ sung tới 1000) | `BOOTSTRAP` | ✅ self-canonical | `bootstrap` | `bootstrap` |
| Biến thể định dạng (bổ sung tới 1000) | `THREE.JS` | ✅ self-canonical | `three.js` | `three.js` |
| Biến thể định dạng (bổ sung tới 1000) | `FRAMER-MOTION` | ✅ self-canonical | `framer-motion` | `framer-motion` |
| Biến thể định dạng (bổ sung tới 1000) | `ROLLUP.JS` | ✅ self-canonical | `rollupjs` | `rollupjs` |
| Biến thể định dạng (bổ sung tới 1000) | `vISUAL bASIC .net` | ✅ synonym | `visual-basic-net` | `vb.net` |
| Biến thể định dạng (bổ sung tới 1000) | `react.js` | ✅ synonym | `react.js` | `reactjs` |
| Biến thể định dạng (bổ sung tới 1000) | `GIT` | ✅ synonym | `git` | `git` |
| Biến thể định dạng (bổ sung tới 1000) | `RACKET` | ✅ synonym | `racket` | `racket` |
| Biến thể định dạng (bổ sung tới 1000) | `Code_Review` | ❌ KHÔNG tìm thấy | — | `code_review` |
| Biến thể định dạng (bổ sung tới 1000) | `NODEJS` | ✅ synonym | `nodejs` | `node.js` |
| Biến thể định dạng (bổ sung tới 1000) | `apexcharts` | ✅ self-canonical | `apexcharts` | `apexcharts` |
| Biến thể định dạng (bổ sung tới 1000) | `bigquery` | ✅ self-canonical | `bigquery` | `bigquery` |
| Biến thể định dạng (bổ sung tới 1000) | `Stm32` | ✅ self-canonical | `stm32` | `stm32` |
| Biến thể định dạng (bổ sung tới 1000) | `BLOCKCHAIN` | ✅ self-canonical | `blockchain` | `blockchain` |
| Biến thể định dạng (bổ sung tới 1000) | `cloud run` | ✅ self-canonical | `cloud-run` | `cloud-run` |
| Biến thể định dạng (bổ sung tới 1000) | `wpf` | ✅ self-canonical | `wpf` | `wpf` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure-Application-Insights` | ✅ self-canonical | `azure-application-insights` | `azure-application-insights` |
| Biến thể định dạng (bổ sung tới 1000) | `Mongodb` | ✅ synonym | `mongodb` | `mongodb` |
| Biến thể định dạng (bổ sung tới 1000) | `great-expectations` | ✅ self-canonical | `great-expectations` | `great-expectations` |
| Biến thể định dạng (bổ sung tới 1000) | `R-PROGRAMMING` | ✅ synonym | `r-programming` | `r` |
| Biến thể định dạng (bổ sung tới 1000) | `circleci` | ✅ self-canonical | `circleci` | `circleci` |
| Biến thể định dạng (bổ sung tới 1000) | `tABLEAU` | ✅ synonym | `tableau` | `tableau-api` |
| Biến thể định dạng (bổ sung tới 1000) | `golang` | ✅ synonym | `golang` | `go` |
| Biến thể định dạng (bổ sung tới 1000) | `XAMARIN.ANDROID` | ✅ synonym | `xamarin.android` | `xamarin.android` |
| Biến thể định dạng (bổ sung tới 1000) | `integration testing` | ✅ synonym | `integration-testing` | `integration-testing` |
| Biến thể định dạng (bổ sung tới 1000) | `azure active directory` | ✅ self-canonical | `azure-active-directory` | `azure-active-directory` |
| Biến thể định dạng (bổ sung tới 1000) | `travis-ci` | ✅ synonym | `travis-ci` | `travis-ci` |
| Biến thể định dạng (bổ sung tới 1000) | `ethereum` | ✅ self-canonical | `ethereum` | `ethereum` |
| Biến thể định dạng (bổ sung tới 1000) | `pREACT` | ✅ self-canonical | `preact` | `preact` |
| Biến thể định dạng (bổ sung tới 1000) | `neo4j` | ✅ synonym | `neo4j` | `neo4j` |
| Biến thể định dạng (bổ sung tới 1000) | `ODOO` | ✅ synonym | `odoo` | `odoo` |
| Biến thể định dạng (bổ sung tới 1000) | `rEACTjs` | ✅ synonym | `reactjs` | `reactjs` |
| Biến thể định dạng (bổ sung tới 1000) | `cloud-spanner` | ✅ self-canonical | `cloud-spanner` | `cloud-spanner` |
| Biến thể định dạng (bổ sung tới 1000) | `PROLOG` | ✅ self-canonical | `prolog` | `prolog` |
| Biến thể định dạng (bổ sung tới 1000) | `IOS` | ✅ self-canonical | `ios` | `ios` |
| Biến thể định dạng (bổ sung tới 1000) | `mAGENTO` | ✅ synonym | `magento` | `magento` |
| Biến thể định dạng (bổ sung tới 1000) | `azure event hub` | ❌ KHÔNG tìm thấy | — | `azure event hub` |
| Biến thể định dạng (bổ sung tới 1000) | `Firebase_Hosting` | ❌ KHÔNG tìm thấy | — | `firebase_hosting` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure_Functions_App` | ❌ KHÔNG tìm thấy | — | `azure_functions_app` |
| Biến thể định dạng (bổ sung tới 1000) | `JEST` | ✅ synonym | `jest` | `jestjs` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon-elasticache` | ✅ self-canonical | `amazon-elasticache` | `amazon-elasticache` |
| Biến thể định dạng (bổ sung tới 1000) | `MACHINE LEARNING` | ✅ self-canonical | `machine-learning` | `machine-learning` |
| Biến thể định dạng (bổ sung tới 1000) | `MARSHMALLOW` | ✅ self-canonical | `marshmallow` | `marshmallow` |
| Biến thể định dạng (bổ sung tới 1000) | `aMAZON sAGEmAKER` | ✅ self-canonical | `amazon-sagemaker` | `amazon-sagemaker` |
| Biến thể định dạng (bổ sung tới 1000) | `terraform` | ✅ self-canonical | `terraform` | `terraform` |
| Biến thể định dạng (bổ sung tới 1000) | `flake8` | ✅ self-canonical | `flake8` | `flake8` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure-App-Service` | ✅ self-canonical | `azure-app-service` | `azure-app-service` |
| Biến thể định dạng (bổ sung tới 1000) | `Automation_Testing` | ❌ KHÔNG tìm thấy | — | `automation_testing` |
| Biến thể định dạng (bổ sung tới 1000) | `COMPUTE ENGINE` | ✅ self-canonical | `compute-engine` | `compute-engine` |
| Biến thể định dạng (bổ sung tới 1000) | `dATA wAREHOUSE` | ✅ synonym | `data-warehouse` | `data-warehouse` |
| Biến thể định dạng (bổ sung tới 1000) | `puppeteer` | ✅ self-canonical | `puppeteer` | `puppeteer` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud-Natural-Language-API` | ❌ KHÔNG tìm thấy | — | `cloud-natural-language-api` |
| Biến thể định dạng (bổ sung tới 1000) | `Voip` | ✅ self-canonical | `voip` | `voip` |
| Biến thể định dạng (bổ sung tới 1000) | `kibana` | ✅ self-canonical | `kibana` | `kibana` |
| Biến thể định dạng (bổ sung tới 1000) | `DJANGO-REST-FRAMEWORK` | ✅ synonym | `django-rest-framework` | `django-rest-framework` |
| Biến thể định dạng (bổ sung tới 1000) | `aZURE mONITOR` | ✅ self-canonical | `azure-monitor` | `azure-monitor` |
| Biến thể định dạng (bổ sung tới 1000) | `jenkins` | ✅ synonym | `jenkins` | `jenkins-ci` |
| Biến thể định dạng (bổ sung tới 1000) | `Chatgpt` | ✅ self-canonical | `chatgpt` | `chatgpt` |
| Biến thể định dạng (bổ sung tới 1000) | `AWS AMPLIFY` | ❌ KHÔNG tìm thấy | — | `aws amplify` |
| Biến thể định dạng (bổ sung tới 1000) | `dEEP lEARNING` | ✅ synonym | `deep-learning` | `deep-learning` |
| Biến thể định dạng (bổ sung tới 1000) | `OAUTH` | ✅ self-canonical | `oauth` | `oauth` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud_Natural_Language_API` | ❌ KHÔNG tìm thấy | — | `cloud_natural_language_api` |
| Biến thể định dạng (bổ sung tới 1000) | `.net-core` | ✅ synonym | `.net-core` | `.net-core` |
| Biến thể định dạng (bổ sung tới 1000) | `AMAZON CLOUDWATCH` | ✅ self-canonical | `amazon-cloudwatch` | `amazon-cloudwatch` |
| Biến thể định dạng (bổ sung tới 1000) | `struts` | ✅ self-canonical | `struts` | `struts` |
| Biến thể định dạng (bổ sung tới 1000) | `nft` | ✅ self-canonical | `nft` | `nft` |
| Biến thể định dạng (bổ sung tới 1000) | `jetpack compose` | ✅ synonym | `jetpack-compose` | `android-jetpack-compose` |
| Biến thể định dạng (bổ sung tới 1000) | `OBJECTIVE-C` | ✅ synonym | `objective-c` | `objective-c` |
| Biến thể định dạng (bổ sung tới 1000) | `3ds-max` | ✅ self-canonical | `3ds-max` | `3ds-max` |
| Biến thể định dạng (bổ sung tới 1000) | `web3.js` | ✅ self-canonical | `web3.js` | `web3.js` |
| Biến thể định dạng (bổ sung tới 1000) | `JUPYTER NOTEBOOK` | ✅ synonym | `jupyter-notebook` | `jupyter-notebook` |
| Biến thể định dạng (bổ sung tới 1000) | `SOLIDITY` | ✅ self-canonical | `solidity` | `solidity` |
| Biến thể định dạng (bổ sung tới 1000) | `code-review` | ✅ self-canonical | `code-review` | `code-review` |
| Biến thể định dạng (bổ sung tới 1000) | `databricks` | ✅ self-canonical | `databricks` | `databricks` |
| Biến thể định dạng (bổ sung tới 1000) | `axios` | ✅ self-canonical | `axios` | `axios` |
| Biến thể định dạng (bổ sung tới 1000) | `loadrunner` | ✅ synonym | `loadrunner` | `loadrunner` |
| Biến thể định dạng (bổ sung tới 1000) | `asp.net-core` | ✅ synonym | `asp.net-core` | `asp.net-core` |
| Biến thể định dạng (bổ sung tới 1000) | `VISUAL-STUDIO-CODE` | ✅ synonym | `visual-studio-code` | `visual-studio-code` |
| Biến thể định dạng (bổ sung tới 1000) | `nESTjs` | ✅ self-canonical | `nestjs` | `nestjs` |
| Biến thể định dạng (bổ sung tới 1000) | `cLOUD tEXT-TO-sPEECH` | ❌ KHÔNG tìm thấy | — | `cloud text-to-speech` |
| Biến thể định dạng (bổ sung tới 1000) | `PERL` | ✅ synonym | `perl` | `perl` |
| Biến thể định dạng (bổ sung tới 1000) | `cODEiGNITER` | ✅ synonym | `codeigniter` | `codeigniter` |
| Biến thể định dạng (bổ sung tới 1000) | `mARSHMALLOW` | ✅ self-canonical | `marshmallow` | `marshmallow` |
| Biến thể định dạng (bổ sung tới 1000) | `compute engine` | ✅ self-canonical | `compute-engine` | `compute-engine` |
| Biến thể định dạng (bổ sung tới 1000) | `Cocoa_Touch` | ❌ KHÔNG tìm thấy | — | `cocoa_touch` |
| Biến thể định dạng (bổ sung tới 1000) | `Kotlin-Coroutines` | ✅ synonym | `kotlin-coroutines` | `kotlin-coroutines` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure_DevOps_Pipelines` | ❌ KHÔNG tìm thấy | — | `azure_devops_pipelines` |
| Biến thể định dạng (bổ sung tới 1000) | `PLC-PROGRAMMING` | ✅ synonym | `plc-programming` | `plc` |
| Biến thể định dạng (bổ sung tới 1000) | `CASSANDRA` | ✅ synonym | `cassandra` | `cassandra` |
| Biến thể định dạng (bổ sung tới 1000) | `AMAZON-EMR` | ✅ self-canonical | `amazon-emr` | `amazon-emr` |
| Biến thể định dạng (bổ sung tới 1000) | `DOMO` | ✅ self-canonical | `domo` | `domo` |
| Biến thể định dạng (bổ sung tới 1000) | `vector database` | ✅ self-canonical | `vector-database` | `vector-database` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure_Data_Factory` | ❌ KHÔNG tìm thấy | — | `azure_data_factory` |
| Biến thể định dạng (bổ sung tới 1000) | `BOTTLE` | ✅ self-canonical | `bottle` | `bottle` |
| Biến thể định dạng (bổ sung tới 1000) | `ZUSTAND` | ✅ self-canonical | `zustand` | `zustand` |
| Biến thể định dạng (bổ sung tới 1000) | `aZURE kUBERNETES sERVICE` | ✅ self-canonical | `azure-kubernetes-service` | `azure-kubernetes-service` |
| Biến thể định dạng (bổ sung tới 1000) | `Dbt` | ✅ self-canonical | `dbt` | `dbt` |
| Biến thể định dạng (bổ sung tới 1000) | `celery` | ✅ self-canonical | `celery` | `celery` |
| Biến thể định dạng (bổ sung tới 1000) | `DOCKER` | ✅ synonym | `docker` | `docker` |
| Biến thể định dạng (bổ sung tới 1000) | `soapui` | ✅ self-canonical | `soapui` | `soapui` |
| Biến thể định dạng (bổ sung tới 1000) | `dOCKER` | ✅ synonym | `docker` | `docker` |
| Biến thể định dạng (bổ sung tới 1000) | `Aws Codepipeline` | ✅ self-canonical | `aws-codepipeline` | `aws-codepipeline` |
| Biến thể định dạng (bổ sung tới 1000) | `SYMFONY` | ✅ self-canonical | `symfony` | `symfony` |
| Biến thể định dạng (bổ sung tới 1000) | `blockchain` | ✅ self-canonical | `blockchain` | `blockchain` |
| Biến thể định dạng (bổ sung tới 1000) | `apache-kafka` | ✅ synonym | `apache-kafka` | `apache-kafka` |
| Biến thể định dạng (bổ sung tới 1000) | `redshift` | ✅ self-canonical | `redshift` | `redshift` |
| Biến thể định dạng (bổ sung tới 1000) | `arkIT` | ✅ self-canonical | `arkit` | `arkit` |
| Biến thể định dạng (bổ sung tới 1000) | `cONFLUENCE` | ✅ self-canonical | `confluence` | `confluence` |
| Biến thể định dạng (bổ sung tới 1000) | `excel` | ✅ synonym | `excel` | `excel` |
| Biến thể định dạng (bổ sung tới 1000) | `VAGRANT` | ✅ self-canonical | `vagrant` | `vagrant` |
| Biến thể định dạng (bổ sung tới 1000) | `CHART.JS` | ✅ synonym | `chart.js` | `chart.js` |
| Biến thể định dạng (bổ sung tới 1000) | `tANsTACK qUERY` | ✅ self-canonical | `tanstack-query` | `tanstack-query` |
| Biến thể định dạng (bổ sung tới 1000) | `aws-amplify` | ❌ KHÔNG tìm thấy | — | `aws-amplify` |
| Biến thể định dạng (bổ sung tới 1000) | `wordpress` | ✅ synonym | `wordpress` | `wordpress` |
| Biến thể định dạng (bổ sung tới 1000) | `elasticsearch` | ✅ synonym | `elasticsearch` | `elasticsearch` |
| Biến thể định dạng (bổ sung tới 1000) | `ANGULAR` | ✅ synonym | `angular` | `angular` |
| Biến thể định dạng (bổ sung tới 1000) | `Salesforce_Lightning` | ❌ KHÔNG tìm thấy | — | `salesforce_lightning` |
| Biến thể định dạng (bổ sung tới 1000) | `Data_Warehouse` | ❌ KHÔNG tìm thấy | — | `data_warehouse` |
| Biến thể định dạng (bổ sung tới 1000) | `dns` | ✅ synonym | `dns` | `dns` |
| Biến thể định dạng (bổ sung tới 1000) | `knime` | ✅ self-canonical | `knime` | `knime` |
| Biến thể định dạng (bổ sung tới 1000) | `cloud-pub/sub` | ❌ KHÔNG tìm thấy | — | `cloud-pub/sub` |
| Biến thể định dạng (bổ sung tới 1000) | `Smtp` | ✅ self-canonical | `smtp` | `smtp` |
| Biến thể định dạng (bổ sung tới 1000) | `cloud-logging` | ❌ KHÔNG tìm thấy | — | `cloud-logging` |
| Biến thể định dạng (bổ sung tới 1000) | `SALESFORCE` | ✅ synonym | `salesforce` | `salesforce` |
| Biến thể định dạng (bổ sung tới 1000) | `MATPLOTLIB` | ✅ synonym | `matplotlib` | `matplotlib` |
| Biến thể định dạng (bổ sung tới 1000) | `Sinonjs` | ❌ KHÔNG tìm thấy | — | `sinonjs` |
| Biến thể định dạng (bổ sung tới 1000) | `mysql` | ✅ synonym | `mysql` | `mysql` |
| Biến thể định dạng (bổ sung tới 1000) | `tCL` | ✅ self-canonical | `tcl` | `tcl` |
| Biến thể định dạng (bổ sung tới 1000) | `Tornado-Web` | ✅ synonym | `tornado-web` | `tornado` |
| Biến thể định dạng (bổ sung tới 1000) | `DATA VISUALIZATION` | ✅ synonym | `data-visualization` | `visualization` |
| Biến thể định dạng (bổ sung tới 1000) | `wEB3.JS` | ✅ self-canonical | `web3.js` | `web3.js` |
| Biến thể định dạng (bổ sung tới 1000) | `RABBITMQ` | ✅ self-canonical | `rabbitmq` | `rabbitmq` |
| Biến thể định dạng (bổ sung tới 1000) | `pytorch` | ✅ self-canonical | `pytorch` | `pytorch` |
| Biến thể định dạng (bổ sung tới 1000) | `kUBERNETES hELM` | ✅ synonym | `kubernetes-helm` | `kubernetes-helm` |
| Biến thể định dạng (bổ sung tới 1000) | `matlab` | ✅ synonym | `matlab` | `matlab` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud_Build` | ❌ KHÔNG tìm thấy | — | `cloud_build` |
| Biến thể định dạng (bổ sung tới 1000) | `bEAUTIFULsOUP` | ✅ synonym | `beautifulsoup` | `beautifulsoup` |
| Biến thể định dạng (bổ sung tới 1000) | `Ospf` | ✅ self-canonical | `ospf` | `ospf` |
| Biến thể định dạng (bổ sung tới 1000) | `JETPACK-COMPOSE` | ✅ synonym | `jetpack-compose` | `android-jetpack-compose` |
| Biến thể định dạng (bổ sung tới 1000) | `AWS-CodeDeploy` | ✅ self-canonical | `aws-codedeploy` | `aws-codedeploy` |
| Biến thể định dạng (bổ sung tới 1000) | `cOUCHdb` | ✅ self-canonical | `couchdb` | `couchdb` |
| Biến thể định dạng (bổ sung tới 1000) | `testcontainers` | ✅ self-canonical | `testcontainers` | `testcontainers` |
| Biến thể định dạng (bổ sung tới 1000) | `javascript` | ✅ synonym | `javascript` | `javascript` |
| Biến thể định dạng (bổ sung tới 1000) | `Visual Basic .Net` | ✅ synonym | `visual-basic-net` | `vb.net` |
| Biến thể định dạng (bổ sung tới 1000) | `Zoho Crm` | ✅ self-canonical | `zoho-crm` | `zoho-crm` |
| Biến thể định dạng (bổ sung tới 1000) | `apache` | ✅ synonym | `apache` | `apache` |
| Biến thể định dạng (bổ sung tới 1000) | `TCL` | ✅ self-canonical | `tcl` | `tcl` |
| Biến thể định dạng (bổ sung tới 1000) | `REDIS` | ✅ self-canonical | `redis` | `redis` |
| Biến thể định dạng (bổ sung tới 1000) | `WEBDRIVERIO` | ✅ self-canonical | `webdriverio` | `webdriverio` |
| Biến thể định dạng (bổ sung tới 1000) | `DEFI` | ✅ self-canonical | `defi` | `defi` |
| Biến thể định dạng (bổ sung tới 1000) | `http` | ✅ self-canonical | `http` | `http` |
| Biến thể định dạng (bổ sung tới 1000) | `JENKINS` | ✅ synonym | `jenkins` | `jenkins-ci` |
| Biến thể định dạng (bổ sung tới 1000) | `TanStack-Query` | ✅ self-canonical | `tanstack-query` | `tanstack-query` |
| Biến thể định dạng (bổ sung tới 1000) | `xamarin` | ✅ self-canonical | `xamarin` | `xamarin` |
| Biến thể định dạng (bổ sung tới 1000) | `sTORYBOOK` | ✅ self-canonical | `storybook` | `storybook` |
| Biến thể định dạng (bổ sung tới 1000) | `SWIFT` | ✅ synonym | `swift` | `swift` |
| Biến thể định dạng (bổ sung tới 1000) | `sqlite` | ✅ synonym | `sqlite` | `sqlite` |
| Biến thể định dạng (bổ sung tới 1000) | `Ios` | ✅ self-canonical | `ios` | `ios` |
| Biến thể định dạng (bổ sung tới 1000) | `CHATGPT` | ✅ self-canonical | `chatgpt` | `chatgpt` |
| Biến thể định dạng (bổ sung tới 1000) | `azure-service-bus` | ✅ self-canonical | `azure-service-bus` | `azure-service-bus` |
| Biến thể định dạng (bổ sung tới 1000) | `D3.JS` | ✅ synonym | `d3.js` | `d3.js` |
| Biến thể định dạng (bổ sung tới 1000) | `Apex-Language` | ✅ synonym | `apex-language` | `apex` |
| Biến thể định dạng (bổ sung tới 1000) | `aPEXcHARTS` | ✅ self-canonical | `apexcharts` | `apexcharts` |
| Biến thể định dạng (bổ sung tới 1000) | `grails` | ✅ synonym | `grails` | `grails` |
| Biến thể định dạng (bổ sung tới 1000) | `Expressjs` | ✅ synonym | `expressjs` | `express` |
| Biến thể định dạng (bổ sung tới 1000) | `parcel bundler` | ✅ self-canonical | `parcel-bundler` | `parcel-bundler` |
| Biến thể định dạng (bổ sung tới 1000) | `Matlab` | ✅ synonym | `matlab` | `matlab` |
| Biến thể định dạng (bổ sung tới 1000) | `VITE` | ✅ synonym | `vite` | `vite` |
| Biến thể định dạng (bổ sung tới 1000) | `aws` | ✅ self-canonical | `aws` | `aws` |
| Biến thể định dạng (bổ sung tới 1000) | `AMAZON-ATHENA` | ✅ self-canonical | `amazon-athena` | `amazon-athena` |
| Biến thể định dạng (bổ sung tới 1000) | `PAGERDUTY` | ✅ self-canonical | `pagerduty` | `pagerduty` |
| Biến thể định dạng (bổ sung tới 1000) | `DIGITALOCEAN` | ✅ self-canonical | `digitalocean` | `digitalocean` |
| Biến thể định dạng (bổ sung tới 1000) | `Scada` | ✅ self-canonical | `scada` | `scada` |
| Biến thể định dạng (bổ sung tới 1000) | `arduino` | ✅ self-canonical | `arduino` | `arduino` |
| Biến thể định dạng (bổ sung tới 1000) | `ENTITY-FRAMEWORK` | ✅ synonym | `entity-framework` | `entity-framework` |
| Biến thể định dạng (bổ sung tới 1000) | `CLOUD-ARMOR` | ❌ KHÔNG tìm thấy | — | `cloud-armor` |
| Biến thể định dạng (bổ sung tới 1000) | `cLOUD sPANNER` | ✅ self-canonical | `cloud-spanner` | `cloud-spanner` |
| Biến thể định dạng (bổ sung tới 1000) | `ENTITY-FRAMEWORK-CORE` | ✅ synonym | `entity-framework-core` | `entity-framework-core` |
| Biến thể định dạng (bổ sung tới 1000) | `sql sERVER` | ✅ synonym | `sql-server` | `sql-server` |
| Biến thể định dạng (bổ sung tới 1000) | `AZURE FRONT DOOR` | ❌ KHÔNG tìm thấy | — | `azure front door` |
| Biến thể định dạng (bổ sung tới 1000) | `cLOUD bIGTABLE` | ✅ self-canonical | `cloud-bigtable` | `cloud-bigtable` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure-Notification-Hubs` | ✅ self-canonical | `azure-notification-hubs` | `azure-notification-hubs` |
| Biến thể định dạng (bổ sung tới 1000) | `spring security` | ✅ synonym | `spring-security` | `spring-security` |
| Biến thể định dạng (bổ sung tới 1000) | `nEO4J` | ✅ synonym | `neo4j` | `neo4j` |
| Biến thể định dạng (bổ sung tới 1000) | `embedded c` | ✅ self-canonical | `embedded-c` | `embedded-c` |
| Biến thể định dạng (bổ sung tới 1000) | `hIBERNATE` | ✅ self-canonical | `hibernate` | `hibernate` |
| Biến thể định dạng (bổ sung tới 1000) | `activemq` | ✅ self-canonical | `activemq` | `activemq` |
| Biến thể định dạng (bổ sung tới 1000) | `aZURE fRONT dOOR` | ❌ KHÔNG tìm thấy | — | `azure front door` |
| Biến thể định dạng (bổ sung tới 1000) | `socket.io` | ✅ synonym | `socket.io` | `socket.io` |
| Biến thể định dạng (bổ sung tới 1000) | `Sap Mm` | ✅ self-canonical | `sap-mm` | `sap-mm` |
| Biến thể định dạng (bổ sung tới 1000) | `azure devops pipelines` | ❌ KHÔNG tìm thấy | — | `azure devops pipelines` |
| Biến thể định dạng (bổ sung tới 1000) | `Framer_Motion` | ❌ KHÔNG tìm thấy | — | `framer_motion` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon cloudwatch` | ✅ self-canonical | `amazon-cloudwatch` | `amazon-cloudwatch` |
| Biến thể định dạng (bổ sung tới 1000) | `jotai` | ✅ self-canonical | `jotai` | `jotai` |
| Biến thể định dạng (bổ sung tới 1000) | `SCHEME` | ✅ self-canonical | `scheme` | `scheme` |
| Biến thể định dạng (bổ sung tới 1000) | `Spring_Security` | ❌ KHÔNG tìm thấy | — | `spring_security` |
| Biến thể định dạng (bổ sung tới 1000) | `influxdb` | ✅ self-canonical | `influxdb` | `influxdb` |
| Biến thể định dạng (bổ sung tới 1000) | `SUPERTEST` | ✅ self-canonical | `supertest` | `supertest` |
| Biến thể định dạng (bổ sung tới 1000) | `vite` | ✅ synonym | `vite` | `vite` |
| Biến thể định dạng (bổ sung tới 1000) | `spring` | ✅ synonym | `spring` | `spring` |
| Biến thể định dạng (bổ sung tới 1000) | `oBJECT-oRIENTED pROGRAMMING` | ✅ synonym | `object-oriented-programming` | `oop` |
| Biến thể định dạng (bổ sung tới 1000) | `Adobe Xd` | ✅ self-canonical | `adobe-xd` | `adobe-xd` |
| Biến thể định dạng (bổ sung tới 1000) | `poetry` | ✅ synonym | `poetry` | `python-poetry` |
| Biến thể định dạng (bổ sung tới 1000) | `sap hana` | ✅ self-canonical | `sap-hana` | `sap-hana` |
| Biến thể định dạng (bổ sung tới 1000) | `TENSORFLOW` | ✅ synonym | `tensorflow` | `tensorflow` |
| Biến thể định dạng (bổ sung tới 1000) | `c++` | ✅ synonym | `c++` | `c++` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon sagemaker` | ✅ self-canonical | `amazon-sagemaker` | `amazon-sagemaker` |
| Biến thể định dạng (bổ sung tới 1000) | `Jmeter` | ✅ synonym | `jmeter` | `jmeter` |
| Biến thể định dạng (bổ sung tới 1000) | `Common-Lisp` | ✅ self-canonical | `common-lisp` | `common-lisp` |
| Biến thể định dạng (bổ sung tới 1000) | `vUEjs` | ✅ synonym | `vuejs` | `vue.js` |
| Biến thể định dạng (bổ sung tới 1000) | `oauth2` | ✅ synonym | `oauth2` | `oauth-2.0` |
| Biến thể định dạng (bổ sung tới 1000) | `Ftp` | ✅ self-canonical | `ftp` | `ftp` |
| Biến thể định dạng (bổ sung tới 1000) | `pYDANTIC` | ✅ self-canonical | `pydantic` | `pydantic` |
| Biến thể định dạng (bổ sung tới 1000) | `Data_Analysis` | ❌ KHÔNG tìm thấy | — | `data_analysis` |
| Biến thể định dạng (bổ sung tới 1000) | `AZURE BATCH` | ❌ KHÔNG tìm thấy | — | `azure batch` |
| Biến thể định dạng (bổ sung tới 1000) | `AZURE API MANAGEMENT` | ✅ self-canonical | `azure-api-management` | `azure-api-management` |
| Biến thể định dạng (bổ sung tới 1000) | `AWS-CloudTrail` | ❌ KHÔNG tìm thấy | — | `aws-cloudtrail` |
| Biến thể định dạng (bổ sung tới 1000) | `apache-spark` | ✅ synonym | `apache-spark` | `apache-spark` |
| Biến thể định dạng (bổ sung tới 1000) | `requests` | ✅ synonym | `requests` | `python-requests` |
| Biến thể định dạng (bổ sung tới 1000) | `CONTINUOUS INTEGRATION` | ✅ synonym | `continuous-integration` | `ci-cd` |
| Biến thể định dạng (bổ sung tới 1000) | `ssas` | ✅ synonym | `ssas` | `ssas` |
| Biến thể định dạng (bổ sung tới 1000) | `automation testing` | ✅ self-canonical | `automation-testing` | `automation-testing` |
| Biến thể định dạng (bổ sung tới 1000) | `DATA WAREHOUSE` | ✅ synonym | `data-warehouse` | `data-warehouse` |
| Biến thể định dạng (bổ sung tới 1000) | `DELTA LAKE` | ✅ self-canonical | `delta-lake` | `delta-lake` |
| Biến thể định dạng (bổ sung tới 1000) | `AWS-CODEDEPLOY` | ✅ self-canonical | `aws-codedeploy` | `aws-codedeploy` |
| Biến thể định dạng (bổ sung tới 1000) | `aZURE aCTIVE dIRECTORY` | ✅ self-canonical | `azure-active-directory` | `azure-active-directory` |
| Biến thể định dạng (bổ sung tới 1000) | `Dns` | ✅ synonym | `dns` | `dns` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud_Text-to-Speech` | ❌ KHÔNG tìm thấy | — | `cloud_text-to-speech` |
| Biến thể định dạng (bổ sung tới 1000) | `ELASTICSEARCH` | ✅ synonym | `elasticsearch` | `elasticsearch` |
| Biến thể định dạng (bổ sung tới 1000) | `solidjs` | ✅ self-canonical | `solidjs` | `solidjs` |
| Biến thể định dạng (bổ sung tới 1000) | `OAUTH2` | ✅ synonym | `oauth2` | `oauth-2.0` |
| Biến thể định dạng (bổ sung tới 1000) | `aws gLUE` | ✅ self-canonical | `aws-glue` | `aws-glue` |
| Biến thể định dạng (bổ sung tới 1000) | `Plc Programming` | ✅ synonym | `plc-programming` | `plc` |
| Biến thể định dạng (bổ sung tới 1000) | `Amazon_SQS` | ❌ KHÔNG tìm thấy | — | `amazon_sqs` |
| Biến thể định dạng (bổ sung tới 1000) | `CLOUD ENDPOINTS` | ❌ KHÔNG tìm thấy | — | `cloud endpoints` |
| Biến thể định dạng (bổ sung tới 1000) | `tableau` | ✅ synonym | `tableau` | `tableau-api` |
| Biến thể định dạng (bổ sung tới 1000) | `Wcf` | ✅ synonym | `wcf` | `wcf` |
| Biến thể định dạng (bổ sung tới 1000) | `nUXT.JS` | ✅ synonym | `nuxt.js` | `nuxt.js` |
| Biến thể định dạng (bổ sung tới 1000) | `jmeter` | ✅ synonym | `jmeter` | `jmeter` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure_Active_Directory` | ❌ KHÔNG tìm thấy | — | `azure_active_directory` |
| Biến thể định dạng (bổ sung tới 1000) | `zeromq` | ✅ self-canonical | `zeromq` | `zeromq` |
| Biến thể định dạng (bổ sung tới 1000) | `fAULT tOLERANCE` | ✅ self-canonical | `fault-tolerance` | `fault-tolerance` |
| Biến thể định dạng (bổ sung tới 1000) | `go` | ✅ synonym | `go` | `go` |
| Biến thể định dạng (bổ sung tới 1000) | `express.js` | ✅ synonym | `express.js` | `express` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud Iam` | ✅ self-canonical | `cloud-iam` | `cloud-iam` |
| Biến thể định dạng (bổ sung tới 1000) | `d-language` | ✅ synonym | `d-language` | `d` |
| Biến thể định dạng (bổ sung tới 1000) | `HUBSPOT` | ✅ self-canonical | `hubspot` | `hubspot` |
| Biến thể định dạng (bổ sung tới 1000) | `asp.net cORE` | ✅ synonym | `asp.net-core` | `asp.net-core` |
| Biến thể định dạng (bổ sung tới 1000) | `CHAOS ENGINEERING` | ✅ self-canonical | `chaos-engineering` | `chaos-engineering` |
| Biến thể định dạng (bổ sung tới 1000) | `AXIOS` | ✅ self-canonical | `axios` | `axios` |
| Biến thể định dạng (bổ sung tới 1000) | `ALGORITHMS` | ✅ synonym | `algorithms` | `algorithm` |
| Biến thể định dạng (bổ sung tới 1000) | `FIREBASE-HOSTING` | ❌ KHÔNG tìm thấy | — | `firebase-hosting` |
| Biến thể định dạng (bổ sung tới 1000) | `swr` | ✅ self-canonical | `swr` | `swr` |
| Biến thể định dạng (bổ sung tới 1000) | `CYPRESS` | ✅ synonym | `cypress` | `cypress` |
| Biến thể định dạng (bổ sung tới 1000) | `redux toolkit` | ✅ synonym | `redux-toolkit` | `redux-toolkit` |
| Biến thể định dạng (bổ sung tới 1000) | `ANDROID STUDIO` | ✅ synonym | `android-studio` | `android-studio` |
| Biến thể định dạng (bổ sung tới 1000) | `Powershell Core` | ✅ synonym | `powershell-core` | `powershell` |
| Biến thể định dạng (bổ sung tới 1000) | `pROMPT eNGINEERING` | ✅ self-canonical | `prompt-engineering` | `prompt-engineering` |
| Biến thể định dạng (bổ sung tới 1000) | `ZEROMQ` | ✅ self-canonical | `zeromq` | `zeromq` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure_Application_Insights` | ❌ KHÔNG tìm thấy | — | `azure_application_insights` |
| Biến thể định dạng (bổ sung tới 1000) | `Cloud Cdn` | ❌ KHÔNG tìm thấy | — | `cloud cdn` |
| Biến thể định dạng (bổ sung tới 1000) | `Aws Fargate` | ✅ self-canonical | `aws-fargate` | `aws-fargate` |
| Biến thể định dạng (bổ sung tới 1000) | `Travis-CI` | ✅ synonym | `travis-ci` | `travis-ci` |
| Biến thể định dạng (bổ sung tới 1000) | `juNIT` | ✅ self-canonical | `junit` | `junit` |
| Biến thể định dạng (bổ sung tới 1000) | `Amazon_Web_Services` | ❌ KHÔNG tìm thấy | — | `amazon_web_services` |
| Biến thể định dạng (bổ sung tới 1000) | `plc programming` | ✅ synonym | `plc-programming` | `plc` |
| Biến thể định dạng (bổ sung tới 1000) | `DAY.JS` | ✅ self-canonical | `dayjs` | `dayjs` |
| Biến thể định dạng (bổ sung tới 1000) | `PENETRATION-TESTING` | ✅ self-canonical | `penetration-testing` | `penetration-testing` |
| Biến thể định dạng (bổ sung tới 1000) | `Nx_Monorepo` | ❌ KHÔNG tìm thấy | — | `nx_monorepo` |
| Biến thể định dạng (bổ sung tới 1000) | `Rate_Limiting` | ❌ KHÔNG tìm thấy | — | `rate_limiting` |
| Biến thể định dạng (bổ sung tới 1000) | `tls` | ✅ synonym | `tls` | `ssl` |
| Biến thể định dạng (bổ sung tới 1000) | `NUMPY` | ✅ synonym | `numpy` | `numpy` |
| Biến thể định dạng (bổ sung tới 1000) | `REDUX` | ✅ synonym | `redux` | `redux` |
| Biến thể định dạng (bổ sung tới 1000) | `AWS-CODEBUILD` | ✅ self-canonical | `aws-codebuild` | `aws-codebuild` |
| Biến thể định dạng (bổ sung tới 1000) | `arcore` | ✅ self-canonical | `arcore` | `arcore` |
| Biến thể định dạng (bổ sung tới 1000) | `zustand` | ✅ self-canonical | `zustand` | `zustand` |
| Biến thể định dạng (bổ sung tới 1000) | `prometheus` | ✅ self-canonical | `prometheus` | `prometheus` |
| Biến thể định dạng (bổ sung tới 1000) | `CELERY` | ✅ self-canonical | `celery` | `celery` |
| Biến thể định dạng (bổ sung tới 1000) | `ELK-Stack` | ✅ synonym | `elk-stack` | `elastic-stack` |
| Biến thể định dạng (bổ sung tới 1000) | `ray` | ✅ self-canonical | `ray` | `ray` |
| Biến thể định dạng (bổ sung tới 1000) | `Dhcp` | ✅ self-canonical | `dhcp` | `dhcp` |
| Biến thể định dạng (bổ sung tới 1000) | `cOMPUTE eNGINE` | ✅ self-canonical | `compute-engine` | `compute-engine` |
| Biến thể định dạng (bổ sung tới 1000) | `computer-vision` | ✅ synonym | `computer-vision` | `computer-vision` |
| Biến thể định dạng (bổ sung tới 1000) | `TS-NODE` | ✅ self-canonical | `ts-node` | `ts-node` |
| Biến thể định dạng (bổ sung tới 1000) | `sinon.js` | ✅ self-canonical | `sinon.js` | `sinon.js` |
| Biến thể định dạng (bổ sung tới 1000) | `3DS MAX` | ✅ self-canonical | `3ds-max` | `3ds-max` |
| Biến thể định dạng (bổ sung tới 1000) | `Data-Visualization` | ✅ synonym | `data-visualization` | `visualization` |
| Biến thể định dạng (bổ sung tới 1000) | `VERCEL` | ✅ synonym | `vercel` | `vercel` |
| Biến thể định dạng (bổ sung tới 1000) | `TRAVIS-CI` | ✅ synonym | `travis-ci` | `travis-ci` |
| Biến thể định dạng (bổ sung tới 1000) | `playwright` | ✅ self-canonical | `playwright` | `playwright` |
| Biến thể định dạng (bổ sung tới 1000) | `azure data lake` | ✅ self-canonical | `azure-data-lake` | `azure-data-lake` |
| Biến thể định dạng (bổ sung tới 1000) | `Ssrs` | ✅ synonym | `ssrs` | `reporting-services` |
| Biến thể định dạng (bổ sung tới 1000) | `agile` | ✅ synonym | `agile` | `agile` |
| Biến thể định dạng (bổ sung tới 1000) | `cocoa touch` | ✅ synonym | `cocoa-touch` | `cocoa-touch` |
| Biến thể định dạng (bổ sung tới 1000) | `deep learning` | ✅ synonym | `deep-learning` | `deep-learning` |
| Biến thể định dạng (bổ sung tới 1000) | `RESTFUL-API` | ✅ synonym | `restful-api` | `rest` |
| Biến thể định dạng (bổ sung tới 1000) | `CHAI.JS` | ✅ self-canonical | `chai.js` | `chai.js` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon-athena` | ✅ self-canonical | `amazon-athena` | `amazon-athena` |
| Biến thể định dạng (bổ sung tới 1000) | `katalon-studio` | ✅ self-canonical | `katalon-studio` | `katalon-studio` |
| Biến thể định dạng (bổ sung tới 1000) | `AZURE-SYNAPSE-ANALYTICS` | ✅ self-canonical | `azure-synapse-analytics` | `azure-synapse-analytics` |
| Biến thể định dạng (bổ sung tới 1000) | `WINDOWS SERVER` | ✅ self-canonical | `windows-server` | `windows-server` |
| Biến thể định dạng (bổ sung tới 1000) | `erlang` | ✅ self-canonical | `erlang` | `erlang` |
| Biến thể định dạng (bổ sung tới 1000) | `Unreal_Engine` | ❌ KHÔNG tìm thấy | — | `unreal_engine` |
| Biến thể định dạng (bổ sung tới 1000) | `selenium` | ✅ synonym | `selenium` | `selenium-webdriver` |
| Biến thể định dạng (bổ sung tới 1000) | `amazon-emr` | ✅ self-canonical | `amazon-emr` | `amazon-emr` |
| Biến thể định dạng (bổ sung tới 1000) | `openai` | ✅ self-canonical | `openai` | `openai` |
| Biến thể định dạng (bổ sung tới 1000) | `aws fargate` | ✅ self-canonical | `aws-fargate` | `aws-fargate` |
| Biến thể định dạng (bổ sung tới 1000) | `CLOUD VISION API` | ❌ KHÔNG tìm thấy | — | `cloud vision api` |
| Biến thể định dạng (bổ sung tới 1000) | `SHOPIFY` | ✅ self-canonical | `shopify` | `shopify` |
| Biến thể định dạng (bổ sung tới 1000) | `CLOUD-COMPOSER` | ✅ self-canonical | `cloud-composer` | `cloud-composer` |
| Biến thể định dạng (bổ sung tới 1000) | `APPIUM` | ✅ self-canonical | `appium` | `appium` |
| Biến thể định dạng (bổ sung tới 1000) | `kERAS` | ✅ self-canonical | `keras` | `keras` |
| Biến thể định dạng (bổ sung tới 1000) | `mongodb` | ✅ synonym | `mongodb` | `mongodb` |
| Biến thể định dạng (bổ sung tới 1000) | `ldap` | ✅ self-canonical | `ldap` | `ldap` |
| Biến thể định dạng (bổ sung tới 1000) | `qwik` | ✅ self-canonical | `qwik` | `qwik` |
| Biến thể định dạng (bổ sung tới 1000) | `numba` | ✅ self-canonical | `numba` | `numba` |
| Biến thể định dạng (bổ sung tới 1000) | `salesforce-lightning` | ✅ self-canonical | `salesforce-lightning` | `salesforce-lightning` |
| Biến thể định dạng (bổ sung tới 1000) | `Azure_App_Service` | ❌ KHÔNG tìm thấy | — | `azure_app_service` |
| Biến thể định dạng (bổ sung tới 1000) | `visual-basic` | ✅ self-canonical | `visual-basic` | `visual-basic` |
| Biến thể định dạng (bổ sung tới 1000) | `LOCUST` | ✅ self-canonical | `locust` | `locust` |
| Biến thể định dạng (bổ sung tới 1000) | `cLOUD dATA fUSION` | ❌ KHÔNG tìm thấy | — | `cloud data fusion` |
| Biến thể định dạng (bổ sung tới 1000) | `SAP-MM` | ✅ self-canonical | `sap-mm` | `sap-mm` |

</details>

## PHẦN B — Độ phủ của skill_implies.json (Layer 2 — entailment)

**Câu hỏi:** với các quan hệ "biết X thì biết Y" đã biết rộng rãi trong giới
lập trình (framework kéo theo ngôn ngữ/thư viện nền), bao nhiêu % thực sự có
trong skill_implies.json để Layer 2 tự động suy ra, thay vì phải dựa vào JD
liệt kê tường minh cả framework lẫn ngôn ngữ nền?

**Phương pháp:** 291 cặp (skill con, skill cha kỳ vọng) viết tay từ tri
thức miền, phủ Python/JS-TS/Java/.NET/PHP-Ruby/Mobile/dịch vụ AWS-Azure-GCP cụ
thể/BI-ERP/Embedded-IoT/Blockchain/DB driver và một nhóm thư viện hiện đại
(Prisma, tRPC, Zustand...) mà độ phủ **không chắc chắn trước**, cộng thêm
709 test case **biến thể định dạng của phía CON** (cha và quan hệ giữ
nguyên — xem `_pad_pairs_to_target()`) để đạt đúng cỡ mẫu tròn 1000.
Với mỗi cặp: canonical hóa cả 2 phía qua skill_data.json (Layer 1), rồi tra
`SKILL_IMPLIES[con_canonical]` có chứa `cha_canonical` không.

### B.1 Tổng hợp

| Chỉ số | Giá trị |
| --- | --- |
| Tổng test case | 1000 |
| Có trong skill_implies.json | 920 (92.0%) |
| KHÔNG có | 80 (8.0%) |
| **Độ phủ skill_implies.json** | **92.0%** |

### B.2 Danh sách MISS (quan hệ kỳ vọng nhưng chưa có trong file)

- `cx_Oracle` → `Oracle Database` (cx_Oracle là driver Python cho Oracle) — canonical: `cx_oracle` → `oracle-database`
- `Pub/Sub` → `Google Cloud Platform` (Pub/Sub là dịch vụ messaging của GCP) — canonical: `pub/sub` → `gcp`
- `Salesforce Apex` → `Salesforce` (Apex là ngôn ngữ lập trình của Salesforce) — canonical: `apex` → `salesforce`
- `Salesforce Lightning` → `Salesforce` (Lightning là framework UI của Salesforce) — canonical: `salesforce-lightning` → `salesforce`
- `SSRS` → `SQL Server` (SSRS là công cụ reporting của SQL Server) — canonical: `reporting-services` → `sql-server`
- `SSIS` → `SQL Server` (SSIS là công cụ ETL của SQL Server) — canonical: `ssis` → `sql-server`
- `SSAS` → `SQL Server` (SSAS là công cụ phân tích của SQL Server) — canonical: `ssas` → `sql-server`
- `Firebase Hosting` → `Firebase` (Firebase Hosting là dịch vụ của Firebase) — canonical: `firebase hosting` → `firebase`
- `sALESFORCE aPEX` → `Salesforce` (Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex')) — canonical: `apex` → `salesforce`
- `Entity_Framework_Core` → `Entity Framework` (EF Core là thế hệ mới của EF (biến thể định dạng của 'Entity Framework Core')) — canonical: `entity_framework_core` → `entity-framework`
- `ssas` → `SQL Server` (SSAS là công cụ phân tích của SQL Server (biến thể định dạng của 'SSAS')) — canonical: `ssas` → `sql-server`
- `Chaijs` → `JavaScript` (Chai là assertion library cho JavaScript (biến thể định dạng của 'Chai.js')) — canonical: `chaijs` → `javascript`
- `Amazon_VPC` → `AWS` (VPC là dịch vụ mạng ảo của AWS (biến thể định dạng của 'Amazon VPC')) — canonical: `amazon_vpc` → `aws`
- `Amazon_EKS` → `AWS` (EKS là dịch vụ Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS')) — canonical: `amazon_eks` → `aws`
- `AWS_Elastic_Beanstalk` → `AWS` (Elastic Beanstalk là PaaS của AWS (biến thể định dạng của 'AWS Elastic Beanstalk')) — canonical: `aws_elastic_beanstalk` → `aws`
- `AWS_CodePipeline` → `AWS` (CodePipeline là dịch vụ CI/CD của AWS (biến thể định dạng của 'AWS CodePipeline')) — canonical: `aws_codepipeline` → `aws`
- `React_Native` → `JavaScript` (React Native viết bằng JavaScript (biến thể định dạng của 'React Native')) — canonical: `react_native` → `javascript`
- `Spring_Security` → `Spring` (Spring Security là module của Spring (biến thể định dạng của 'Spring Security')) — canonical: `spring_security` → `spring`
- `Amazon_EC2` → `AWS` (EC2 là dịch vụ compute của AWS (biến thể định dạng của 'Amazon EC2')) — canonical: `amazon_ec2` → `aws`
- `Django_Channels` → `Django` (Channels là extension của Django (biến thể định dạng của 'Django Channels')) — canonical: `django_channels` → `django`
- `Redux_Thunk` → `Redux` (Redux Thunk là middleware của Redux (biến thể định dạng của 'Redux Thunk')) — canonical: `redux_thunk` → `redux`
- `Amazon_Route_53` → `AWS` (Route 53 là dịch vụ DNS của AWS (biến thể định dạng của 'Amazon Route 53')) — canonical: `amazon_route_53` → `aws`
- `PUB/SUB` → `Google Cloud Platform` (Pub/Sub là dịch vụ messaging của GCP (biến thể định dạng của 'Pub/Sub')) — canonical: `pub/sub` → `gcp`
- `CX_ORACLE` → `Oracle Database` (cx_Oracle là driver Python cho Oracle (biến thể định dạng của 'cx_Oracle')) — canonical: `cx_oracle` → `oracle-database`
- `Amazon_Athena` → `AWS` (Athena là dịch vụ query serverless của AWS (biến thể định dạng của 'Amazon Athena')) — canonical: `amazon_athena` → `aws`
- `Smart_Contract` → `Solidity` (Smart contract trên Ethereum thường viết bằng Solidity (biến thể định dạng của 'Smart Contract')) — canonical: `smart_contract` → `solidity`
- `Cloud_Functions` → `Google Cloud Platform` (Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Cloud Functions')) — canonical: `cloud_functions` → `gcp`
- `pUB/sUB` → `Google Cloud Platform` (Pub/Sub là dịch vụ messaging của GCP (biến thể định dạng của 'Pub/Sub')) — canonical: `pub/sub` → `gcp`
- `Amazon_S3` → `AWS` (S3 là dịch vụ storage của AWS (biến thể định dạng của 'Amazon S3')) — canonical: `amazon_s3` → `aws`
- `ssis` → `SQL Server` (SSIS là công cụ ETL của SQL Server (biến thể định dạng của 'SSIS')) — canonical: `ssis` → `sql-server`
- `Kafka_Streams` → `Apache Kafka` (Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams')) — canonical: `kafka_streams` → `apache-kafka`
- `Azure_Key_Vault` → `Azure` (Key Vault là dịch vụ quản lý secret của Azure (biến thể định dạng của 'Azure Key Vault')) — canonical: `azure_key_vault` → `azure`
- `Azure_App_Service` → `Azure` (App Service là PaaS của Azure (biến thể định dạng của 'Azure App Service')) — canonical: `azure_app_service` → `azure`
- `fIREBASE hOSTING` → `Firebase` (Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting')) — canonical: `firebase hosting` → `firebase`
- `Cloud_Spanner` → `Google Cloud Platform` (Cloud Spanner là dịch vụ database phân tán của GCP (biến thể định dạng của 'Cloud Spanner')) — canonical: `cloud_spanner` → `gcp`
- `Amazon_API_Gateway` → `AWS` (API Gateway là dịch vụ quản lý API của AWS (biến thể định dạng của 'Amazon API Gateway')) — canonical: `amazon_api_gateway` → `aws`
- `Firebase-Hosting` → `Firebase` (Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting')) — canonical: `firebase-hosting` → `firebase`
- `Azure_Blob_Storage` → `Azure` (Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage')) — canonical: `azure_blob_storage` → `azure`
- `Azure_Data_Factory` → `Azure` (Data Factory là dịch vụ ETL của Azure (biến thể định dạng của 'Azure Data Factory')) — canonical: `azure_data_factory` → `azure`
- `Azure_DNS` → `Azure` (Azure DNS là dịch vụ DNS của Azure (biến thể định dạng của 'Azure DNS')) — canonical: `azure_dns` → `azure`
- `Salesforce-Apex` → `Salesforce` (Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex')) — canonical: `apex` → `salesforce`
- `Azure_Logic_Apps` → `Azure` (Logic Apps là dịch vụ workflow của Azure (biến thể định dạng của 'Azure Logic Apps')) — canonical: `azure_logic_apps` → `azure`
- `Framer_Motion` → `React` (Framer Motion là animation library của React (biến thể định dạng của 'Framer Motion')) — canonical: `framer_motion` → `reactjs`
- `AWS_Lambda` → `AWS` (Lambda là dịch vụ serverless của AWS (biến thể định dạng của 'AWS Lambda')) — canonical: `aws_lambda` → `aws`
- `Entity_Framework` → `C#` (EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework')) — canonical: `entity_framework` → `c#`
- `firebase-hosting` → `Firebase` (Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting')) — canonical: `firebase-hosting` → `firebase`
- `Docker_Compose` → `Docker` (Docker Compose là tính năng của Docker (biến thể định dạng của 'Docker Compose')) — canonical: `docker_compose` → `docker`
- `Django_REST_Framework` → `Django` (DRF là extension của Django (biến thể định dạng của 'Django REST Framework')) — canonical: `django_rest_framework` → `django`
- `Azure_Functions` → `Azure` (Azure Functions là dịch vụ serverless của Azure (biến thể định dạng của 'Azure Functions')) — canonical: `azure_functions` → `azure`
- `React_Query` → `React` (React Query là data-fetching library của React (biến thể định dạng của 'React Query')) — canonical: `react_query` → `reactjs`
- `Ruby_on_Rails` → `Ruby` (Rails là framework của Ruby (biến thể định dạng của 'Ruby on Rails')) — canonical: `ruby_on_rails` → `ruby`
- `Chakra_UI` → `React` (Chakra UI là component library cho React (biến thể định dạng của 'Chakra UI')) — canonical: `chakra_ui` → `reactjs`
- `cx_oracle` → `Oracle Database` (cx_Oracle là driver Python cho Oracle (biến thể định dạng của 'cx_Oracle')) — canonical: `cx_oracle` → `oracle-database`
- `Apollo_Server` → `Node.js` (Apollo Server chạy trên Node.js (biến thể định dạng của 'Apollo Server')) — canonical: `apollo_server` → `node.js`
- `Azure_Machine_Learning` → `Azure` (Azure ML là dịch vụ ML của Azure (biến thể định dạng của 'Azure Machine Learning')) — canonical: `azure_machine_learning` → `azure`
- `SAP_ABAP` → `SAP` (ABAP là ngôn ngữ lập trình của SAP (biến thể định dạng của 'SAP ABAP')) — canonical: `sap_abap` → `sap`
- `Cloud_Build` → `Google Cloud Platform` (Cloud Build là dịch vụ CI/CD của GCP (biến thể định dạng của 'Cloud Build')) — canonical: `cloud_build` → `gcp`
- `Azure_Data_Lake` → `Azure` (Data Lake là dịch vụ lưu trữ big data của Azure (biến thể định dạng của 'Azure Data Lake')) — canonical: `azure_data_lake` → `azure`
- `SALESFORCE APEX` → `Salesforce` (Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex')) — canonical: `apex` → `salesforce`
- `AWS_Fargate` → `AWS` (Fargate là dịch vụ serverless container của AWS (biến thể định dạng của 'AWS Fargate')) — canonical: `aws_fargate` → `aws`
- `Cloud_Dataproc` → `Apache Spark` (Dataproc chạy Spark/Hadoop quản lý (biến thể định dạng của 'Cloud Dataproc')) — canonical: `cloud_dataproc` → `apache-spark`
- `Amazon_Kinesis` → `AWS` (Kinesis là dịch vụ streaming của AWS (biến thể định dạng của 'Amazon Kinesis')) — canonical: `amazon_kinesis` → `aws`
- `Tornado_Web` → `Python` (Python framework (biến thể định dạng của 'Tornado Web')) — canonical: `tornado_web` → `python`
- `Azure_Monitor` → `Azure` (Azure Monitor là dịch vụ monitoring của Azure (biến thể định dạng của 'Azure Monitor')) — canonical: `azure_monitor` → `azure`
- `Sinonjs` → `JavaScript` (Sinon là mocking library cho JavaScript (biến thể định dạng của 'Sinon.js')) — canonical: `sinonjs` → `javascript`
- `Azure_Databricks` → `Apache Spark` (Azure Databricks chạy trên nền Spark (biến thể định dạng của 'Azure Databricks')) — canonical: `azure_databricks` → `apache-spark`
- `Compute_Engine` → `Google Cloud Platform` (Compute Engine là dịch vụ compute của GCP (biến thể định dạng của 'Compute Engine')) — canonical: `compute_engine` → `gcp`
- `SALESFORCE-APEX` → `Salesforce` (Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex')) — canonical: `apex` → `salesforce`
- `XamarinForms` → `Xamarin` (Xamarin.Forms là module của Xamarin (biến thể định dạng của 'Xamarin.Forms')) — canonical: `xamarinforms` → `xamarin`
- `Spring_Boot` → `Java` (Spring Boot chạy trên Java (biến thể định dạng của 'Spring Boot')) — canonical: `spring_boot` → `java`
- `Kotlin_Coroutines` → `Kotlin` (Coroutines là tính năng của Kotlin (biến thể định dạng của 'Kotlin Coroutines')) — canonical: `kotlin_coroutines` → `kotlin`
- `salesforce-apex` → `Salesforce` (Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex')) — canonical: `apex` → `salesforce`
- `Ssrs` → `SQL Server` (SSRS là công cụ reporting của SQL Server (biến thể định dạng của 'SSRS')) — canonical: `reporting-services` → `sql-server`
- `Amazon_RDS` → `AWS` (RDS là dịch vụ database của AWS (biến thể định dạng của 'Amazon RDS')) — canonical: `amazon_rds` → `aws`
- `Amazon_ECS` → `AWS` (ECS là dịch vụ container orchestration của AWS (biến thể định dạng của 'Amazon ECS')) — canonical: `amazon_ecs` → `aws`
- `Cloud_Bigtable` → `Google Cloud Platform` (Bigtable là dịch vụ NoSQL của GCP (biến thể định dạng của 'Cloud Bigtable')) — canonical: `cloud_bigtable` → `gcp`
- `ASP.NET_Core` → `ASP.NET` (ASP.NET Core là thế hệ mới của ASP.NET (biến thể định dạng của 'ASP.NET Core')) — canonical: `asp.net_core` → `asp.net`
- `Angular_Material` → `Angular` (Angular Material là component library của Angular (biến thể định dạng của 'Angular Material')) — canonical: `angular_material` → `angular`
- `FIREBASE HOSTING` → `Firebase` (Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting')) — canonical: `firebase hosting` → `firebase`
- `SAP_HANA` → `SAP` (HANA là database platform của SAP (biến thể định dạng của 'SAP HANA')) — canonical: `sap_hana` → `sap`

### B.3 Toàn bộ 1000 test case

<details>
<summary>Xem đầy đủ (bấm để mở)</summary>

| Con | Cha kỳ vọng | Lý do | Con (canonical) | Cha (canonical) | Có trong skill_implies.json? |
| --- | --- | --- | --- | --- | --- |
| `Django` | `Python` | Python framework | `django` | `python` | ✅ CÓ |
| `Flask` | `Python` | Python framework | `flask` | `python` | ✅ CÓ |
| `FastAPI` | `Python` | Python framework | `fastapi` | `python` | ✅ CÓ |
| `Pandas` | `Python` | Python library | `pandas` | `python` | ✅ CÓ |
| `NumPy` | `Python` | Python library | `numpy` | `python` | ✅ CÓ |
| `SciPy` | `Python` | Python library | `scipy` | `python` | ✅ CÓ |
| `Matplotlib` | `Python` | Python library | `matplotlib` | `python` | ✅ CÓ |
| `Scikit-learn` | `Python` | Python library | `scikit-learn` | `python` | ✅ CÓ |
| `PyTorch` | `Python` | Python library | `pytorch` | `python` | ✅ CÓ |
| `TensorFlow` | `Python` | Python library | `tensorflow` | `python` | ✅ CÓ |
| `Keras` | `TensorFlow` | Keras chạy trên TensorFlow backend | `keras` | `tensorflow` | ✅ CÓ |
| `Celery` | `Python` | Python library | `celery` | `python` | ✅ CÓ |
| `PySpark` | `Python` | Python API của Spark | `pyspark` | `python` | ✅ CÓ |
| `PySpark` | `Apache Spark` | Python API của Spark | `pyspark` | `apache-spark` | ✅ CÓ |
| `SQLAlchemy` | `Python` | Python ORM | `sqlalchemy` | `python` | ✅ CÓ |
| `Streamlit` | `Python` | Python framework | `streamlit` | `python` | ✅ CÓ |
| `Scrapy` | `Python` | Python framework | `scrapy` | `python` | ✅ CÓ |
| `BeautifulSoup` | `Python` | Python library | `beautifulsoup` | `python` | ✅ CÓ |
| `Jinja2` | `Python` | Python template engine | `jinja2` | `python` | ✅ CÓ |
| `PyTest` | `Python` | Python test framework | `pytest` | `python` | ✅ CÓ |
| `React` | `JavaScript` | JS library | `reactjs` | `javascript` | ✅ CÓ |
| `Vue.js` | `JavaScript` | JS framework | `vue.js` | `javascript` | ✅ CÓ |
| `Angular` | `TypeScript` | Angular viết bằng/yêu cầu TypeScript | `angular` | `typescript` | ✅ CÓ |
| `Angular` | `JavaScript` | Angular chạy trên JavaScript runtime | `angular` | `javascript` | ✅ CÓ |
| `Next.js` | `React` | Next.js là meta-framework của React | `next.js` | `reactjs` | ✅ CÓ |
| `Next.js` | `JavaScript` | Next.js chạy trên JavaScript | `next.js` | `javascript` | ✅ CÓ |
| `Nuxt.js` | `Vue.js` | Nuxt.js là meta-framework của Vue | `nuxt.js` | `vue.js` | ✅ CÓ |
| `Express` | `Node.js` | Express chạy trên Node.js | `express` | `node.js` | ✅ CÓ |
| `Express` | `JavaScript` | Express chạy trên JavaScript | `express` | `javascript` | ✅ CÓ |
| `NestJS` | `TypeScript` | NestJS viết bằng TypeScript | `nestjs` | `typescript` | ✅ CÓ |
| `NestJS` | `Node.js` | NestJS chạy trên Node.js | `nestjs` | `node.js` | ✅ CÓ |
| `Redux` | `JavaScript` | State library cho JS | `redux` | `javascript` | ✅ CÓ |
| `Redux Toolkit` | `Redux` | Redux Toolkit là bộ công cụ chính thức của Redux | `redux-toolkit` | `redux` | ✅ CÓ |
| `jQuery` | `JavaScript` | JS library | `jquery` | `javascript` | ✅ CÓ |
| `TypeScript` | `JavaScript` | TypeScript biên dịch ra JavaScript | `typescript` | `javascript` | ✅ CÓ |
| `Node.js` | `JavaScript` | Node.js chạy JavaScript phía server | `node.js` | `javascript` | ✅ CÓ |
| `Svelte` | `JavaScript` | JS framework | `svelte` | `javascript` | ✅ CÓ |
| `Gatsby` | `React` | Gatsby là static site generator dựa trên React | `gatsby` | `reactjs` | ✅ CÓ |
| `React Native` | `React` | React Native dựa trên React | `react-native` | `reactjs` | ✅ CÓ |
| `React Native` | `JavaScript` | React Native viết bằng JavaScript | `react-native` | `javascript` | ✅ CÓ |
| `Vuex` | `Vue.js` | Vuex là state management của Vue | `vuex` | `vue.js` | ✅ CÓ |
| `Material UI` | `React` | Material UI là component library cho React | `material-ui` | `reactjs` | ✅ CÓ |
| `Styled Components` | `React` | Styled Components dùng cho React | `styled-components` | `reactjs` | ✅ CÓ |
| `Ember.js` | `JavaScript` | JS framework | `ember.js` | `javascript` | ✅ CÓ |
| `Backbone.js` | `JavaScript` | JS framework | `backbone.js` | `javascript` | ✅ CÓ |
| `Vite` | `JavaScript` | Build tool cho JS | `vite` | `javascript` | ✅ CÓ |
| `Spring Boot` | `Spring` | Spring Boot là module của Spring | `spring-boot` | `spring` | ✅ CÓ |
| `Spring Boot` | `Java` | Spring Boot chạy trên Java | `spring-boot` | `java` | ✅ CÓ |
| `Spring MVC` | `Spring` | Spring MVC là module của Spring | `spring-mvc` | `spring` | ✅ CÓ |
| `Spring Security` | `Spring` | Spring Security là module của Spring | `spring-security` | `spring` | ✅ CÓ |
| `Hibernate` | `Java` | Hibernate là ORM cho Java | `hibernate` | `java` | ✅ CÓ |
| `Maven` | `Java` | Maven là build tool cho Java | `maven` | `java` | ✅ CÓ |
| `JUnit` | `Java` | JUnit là test framework cho Java | `junit` | `java` | ✅ CÓ |
| `Kotlin` | `Java` | Kotlin chạy trên JVM, tương tác với Java | `kotlin` | `java` | ✅ CÓ |
| `Kotlin Coroutines` | `Kotlin` | Coroutines là tính năng của Kotlin | `kotlin-coroutines` | `kotlin` | ✅ CÓ |
| `Grails` | `Java` | Grails chạy trên JVM | `grails` | `java` | ✅ CÓ |
| `ASP.NET Core` | `ASP.NET` | ASP.NET Core là thế hệ mới của ASP.NET | `asp.net-core` | `asp.net` | ✅ CÓ |
| `ASP.NET Core` | `C#` | ASP.NET Core viết bằng C# | `asp.net-core` | `c#` | ✅ CÓ |
| `ASP.NET MVC` | `ASP.NET` | ASP.NET MVC là module của ASP.NET | `asp.net-mvc` | `asp.net` | ✅ CÓ |
| `Entity Framework` | `C#` | EF là ORM cho .NET/C# | `entity-framework` | `c#` | ✅ CÓ |
| `Entity Framework Core` | `Entity Framework` | EF Core là thế hệ mới của EF | `entity-framework-core` | `entity-framework` | ✅ CÓ |
| `WPF` | `C#` | WPF là UI framework của .NET/C# | `wpf` | `c#` | ✅ CÓ |
| `WinForms` | `C#` | WinForms là UI framework của .NET/C# | `winforms` | `c#` | ✅ CÓ |
| `Xamarin` | `C#` | Xamarin viết bằng C# | `xamarin` | `c#` | ✅ CÓ |
| `Xamarin.Forms` | `Xamarin` | Xamarin.Forms là module của Xamarin | `xamarin.forms` | `xamarin` | ✅ CÓ |
| `Blazor` | `C#` | Blazor viết bằng C# | `blazor` | `c#` | ✅ CÓ |
| `Blazor WebAssembly` | `Blazor` | Blazor WASM là chế độ chạy của Blazor | `blazor-webassembly` | `blazor` | ✅ CÓ |
| `LINQ` | `C#` | LINQ là tính năng ngôn ngữ của C#/.NET | `linq` | `c#` | ✅ CÓ |
| `Laravel` | `PHP` | Laravel là framework PHP | `laravel` | `php` | ✅ CÓ |
| `Symfony` | `PHP` | Symfony là framework PHP | `symfony` | `php` | ✅ CÓ |
| `CodeIgniter` | `PHP` | CodeIgniter là framework PHP | `codeigniter` | `php` | ✅ CÓ |
| `WordPress` | `PHP` | WordPress viết bằng PHP | `wordpress` | `php` | ✅ CÓ |
| `Ruby on Rails` | `Ruby` | Rails là framework của Ruby | `ruby-on-rails` | `ruby` | ✅ CÓ |
| `RSpec` | `Ruby` | RSpec là test framework của Ruby | `rspec` | `ruby` | ✅ CÓ |
| `Flutter` | `Dart` | Flutter viết bằng Dart | `flutter` | `dart` | ✅ CÓ |
| `SwiftUI` | `Swift` | SwiftUI là UI framework của Swift | `swiftui` | `swift` | ✅ CÓ |
| `Xamarin.Android` | `Xamarin` | Xamarin.Android là module của Xamarin | `xamarin.android` | `xamarin` | ✅ CÓ |
| `Xamarin.iOS` | `Xamarin` | Xamarin.iOS là module của Xamarin | `xamarin.ios` | `xamarin` | ✅ CÓ |
| `Cocoa Touch` | `Objective-C` | Cocoa Touch gắn với Objective-C/iOS | `cocoa-touch` | `objective-c` | ✅ CÓ |
| `Jetpack Compose` | `Android` | Jetpack Compose là UI toolkit của Android | `android-jetpack-compose` | `android` | ✅ CÓ |
| `Kubernetes` | `Docker` | K8s thường điều phối container Docker | `kubernetes` | `docker` | ✅ CÓ |
| `Docker Compose` | `Docker` | Docker Compose là tính năng của Docker | `docker-compose` | `docker` | ✅ CÓ |
| `Kubernetes Helm` | `Kubernetes` | Helm là package manager của Kubernetes | `kubernetes-helm` | `kubernetes` | ✅ CÓ |
| `Spark Streaming` | `Apache Spark` | Spark Streaming là module của Spark | `spark-streaming` | `apache-spark` | ✅ CÓ |
| `Kibana` | `Elasticsearch` | Kibana dùng để visualize dữ liệu Elasticsearch | `kibana` | `elasticsearch` | ✅ CÓ |
| `Logstash` | `Elasticsearch` | Logstash thuộc ELK stack cùng Elasticsearch | `logstash` | `elasticsearch` | ✅ CÓ |
| `GitHub` | `Git` | GitHub là dịch vụ hosting cho Git | `github` | `git` | ✅ CÓ |
| `GitLab` | `Git` | GitLab là dịch vụ hosting cho Git | `gitlab` | `git` | ✅ CÓ |
| `Terraform Provider AWS` | `Terraform` | Provider là module mở rộng của Terraform | `terraform-provider-aws` | `terraform` | ✅ CÓ |
| `Kubectl` | `Kubernetes` | kubectl là CLI điều khiển Kubernetes | `kubectl` | `kubernetes` | ✅ CÓ |
| `psycopg2` | `PostgreSQL` | psycopg2 là driver Python cho PostgreSQL | `psycopg2` | `postgresql` | ✅ CÓ |
| `PyMongo` | `MongoDB` | PyMongo là driver Python cho MongoDB | `pymongo` | `mongodb` | ✅ CÓ |
| `PyMySQL` | `MySQL` | PyMySQL là driver Python cho MySQL | `pymysql` | `mysql` | ✅ CÓ |
| `cx_Oracle` | `Oracle Database` | cx_Oracle là driver Python cho Oracle | `cx_oracle` | `oracle-database` | ❌ KHÔNG |
| `JDBC` | `Java` | JDBC là API kết nối DB của Java | `jdbc` | `java` | ✅ CÓ |
| `Prisma` | `Node.js` | Prisma là ORM phổ biến cho Node.js/TypeScript | `prisma` | `node.js` | ✅ CÓ |
| `tRPC` | `TypeScript` | tRPC dựa trên type-safety của TypeScript | `trpc` | `typescript` | ✅ CÓ |
| `Chakra UI` | `React` | Chakra UI là component library cho React | `chakra-ui` | `reactjs` | ✅ CÓ |
| `Redux Saga` | `Redux` | Redux Saga là middleware của Redux | `redux-saga` | `redux` | ✅ CÓ |
| `Redux Thunk` | `Redux` | Redux Thunk là middleware của Redux | `redux-thunk` | `redux` | ✅ CÓ |
| `Apollo Client` | `GraphQL` | Apollo Client là client cho GraphQL | `apollo-client` | `graphql` | ✅ CÓ |
| `Apollo Server` | `Node.js` | Apollo Server chạy trên Node.js | `apollo-server` | `node.js` | ✅ CÓ |
| `Zustand` | `React` | Zustand là state library phổ biến cho React | `zustand` | `reactjs` | ✅ CÓ |
| `LangChain` | `Python` | LangChain thường dùng qua Python SDK | `langchain` | `python` | ✅ CÓ |
| `ESLint` | `JavaScript` | ESLint là linter cho JavaScript | `eslint` | `javascript` | ✅ CÓ |
| `Prettier` | `JavaScript` | Prettier là formatter cho JavaScript | `prettier` | `javascript` | ✅ CÓ |
| `Yarn` | `Node.js` | Yarn là package manager của Node.js | `yarn` | `node.js` | ✅ CÓ |
| `npm` | `Node.js` | npm là package manager mặc định của Node.js | `npm` | `node.js` | ✅ CÓ |
| `Sequelize.js` | `Node.js` | Sequelize là ORM cho Node.js | `sequelize.js` | `node.js` | ✅ CÓ |
| `Mongoose` | `Node.js` | Mongoose là ODM cho Node.js | `mongoose` | `node.js` | ✅ CÓ |
| `Passport.js` | `Node.js` | Passport là middleware auth của Node.js | `passport.js` | `node.js` | ✅ CÓ |
| `Socket.IO` | `Node.js` | Socket.IO thường chạy trên Node.js server | `socket.io` | `node.js` | ✅ CÓ |
| `React Router` | `React` | React Router là routing library của React | `react-router` | `reactjs` | ✅ CÓ |
| `React Hook Form` | `React` | React Hook Form là form library của React | `react-hook-form` | `reactjs` | ✅ CÓ |
| `Formik` | `React` | Formik là form library của React | `formik` | `reactjs` | ✅ CÓ |
| `Angular Material` | `Angular` | Angular Material là component library của Angular | `angular-material` | `angular` | ✅ CÓ |
| `WooCommerce` | `WordPress` | WooCommerce là plugin ecommerce của WordPress | `woocommerce` | `wordpress` | ✅ CÓ |
| `Elementor` | `WordPress` | Elementor là page builder plugin của WordPress | `elementor` | `wordpress` | ✅ CÓ |
| `Drupal` | `PHP` | Drupal là CMS viết bằng PHP | `drupal` | `php` | ✅ CÓ |
| `Magento` | `PHP` | Magento là nền tảng ecommerce viết bằng PHP | `magento` | `php` | ✅ CÓ |
| `dbt` | `SQL` | dbt biên dịch transformation thành SQL | `dbt` | `sql` | ✅ CÓ |
| `Databricks` | `Apache Spark` | Databricks là nền tảng quản lý Spark | `databricks` | `apache-spark` | ✅ CÓ |
| `Redshift` | `AWS` | Redshift là data warehouse dịch vụ của AWS | `redshift` | `aws` | ✅ CÓ |
| `BigQuery` | `Google Cloud Platform` | BigQuery là data warehouse dịch vụ của GCP | `bigquery` | `gcp` | ✅ CÓ |
| `Istio` | `Kubernetes` | Istio là service mesh chạy trên Kubernetes | `istio` | `kubernetes` | ✅ CÓ |
| `ArgoCD` | `Kubernetes` | ArgoCD là công cụ GitOps triển khai lên Kubernetes | `argocd` | `kubernetes` | ✅ CÓ |
| `AWS Lambda` | `AWS` | Lambda là dịch vụ serverless của AWS | `aws-lambda` | `aws` | ✅ CÓ |
| `Azure Functions` | `Azure` | Azure Functions là dịch vụ serverless của Azure | `azure-functions` | `azure` | ✅ CÓ |
| `Google Cloud Functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `CloudFormation` | `AWS` | CloudFormation là IaC dịch vụ của AWS | `cloudformation` | `aws` | ✅ CÓ |
| `Azure DevOps` | `Azure` | Azure DevOps là bộ công cụ CI/CD của Azure | `azure-devops` | `azure` | ✅ CÓ |
| `Playwright` | `JavaScript` | Playwright là test framework cho JavaScript | `playwright` | `javascript` | ✅ CÓ |
| `Jest` | `JavaScript` | Jest là test framework cho JavaScript | `jestjs` | `javascript` | ✅ CÓ |
| `Enzyme` | `React` | Enzyme là test utility cho React | `enzyme` | `reactjs` | ✅ CÓ |
| `Core Data` | `Swift` | Core Data là framework persistence của Apple dùng với Swift | `core-data` | `swift` | ✅ CÓ |
| `Combine` | `Swift` | Combine là framework reactive của Apple dùng với Swift | `combine` | `swift` | ✅ CÓ |
| `Vitest` | `JavaScript` | Vitest là test framework cho JavaScript/Vite | `vitest` | `javascript` | ✅ CÓ |
| `Storybook` | `JavaScript` | Storybook là công cụ dựng UI component cho JavaScript | `storybook` | `javascript` | ✅ CÓ |
| `Vercel` | `Next.js` | Vercel là nền tảng deploy chính thức của Next.js | `vercel` | `next.js` | ✅ CÓ |
| `Elasticsearch` | `Java` | Elasticsearch viết bằng Java | `elasticsearch` | `java` | ✅ CÓ |
| `Cassandra` | `Java` | Cassandra viết bằng Java | `cassandra` | `java` | ✅ CÓ |
| `Kafka Streams` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka | `apache-kafka-streams` | `apache-kafka` | ✅ CÓ |
| `Micronaut` | `Java` | Micronaut là framework Java | `micronaut` | `java` | ✅ CÓ |
| `Quarkus` | `Java` | Quarkus là framework Java | `quarkus` | `java` | ✅ CÓ |
| `Dropwizard` | `Java` | Dropwizard là framework Java | `dropwizard` | `java` | ✅ CÓ |
| `Ktor` | `Kotlin` | Ktor là framework web viết bằng Kotlin | `ktor` | `kotlin` | ✅ CÓ |
| `Retrofit` | `Java` | Retrofit là HTTP client cho Java/Android | `retrofit` | `java` | ✅ CÓ |
| `OkHttp` | `Java` | OkHttp là HTTP client cho Java/Android | `okhttp` | `java` | ✅ CÓ |
| `Room` | `Android` | Room là thư viện persistence của Android | `android-room` | `android` | ✅ CÓ |
| `ViewModel` | `Android` | ViewModel là thành phần kiến trúc của Android | `viewmodel` | `android` | ✅ CÓ |
| `Amazon EC2` | `AWS` | EC2 là dịch vụ compute của AWS | `amazon-ec2` | `aws` | ✅ CÓ |
| `Amazon S3` | `AWS` | S3 là dịch vụ storage của AWS | `amazon-s3` | `aws` | ✅ CÓ |
| `Amazon RDS` | `AWS` | RDS là dịch vụ database của AWS | `amazon-rds` | `aws` | ✅ CÓ |
| `Amazon SQS` | `AWS` | SQS là dịch vụ message queue của AWS | `sqs` | `aws` | ✅ CÓ |
| `Amazon SNS` | `AWS` | SNS là dịch vụ notification của AWS | `amazon-sns` | `aws` | ✅ CÓ |
| `Amazon CloudFront` | `AWS` | CloudFront là dịch vụ CDN của AWS | `amazon-cloudfront` | `aws` | ✅ CÓ |
| `Amazon Route 53` | `AWS` | Route 53 là dịch vụ DNS của AWS | `amazon-route-53` | `aws` | ✅ CÓ |
| `AWS IAM` | `AWS` | IAM là dịch vụ quản lý quyền của AWS | `aws-iam` | `aws` | ✅ CÓ |
| `Amazon ECS` | `AWS` | ECS là dịch vụ container orchestration của AWS | `amazon-ecs` | `aws` | ✅ CÓ |
| `Amazon EKS` | `AWS` | EKS là dịch vụ Kubernetes quản lý của AWS | `amazon-eks` | `aws` | ✅ CÓ |
| `Amazon EKS` | `Kubernetes` | EKS là Kubernetes quản lý của AWS | `amazon-eks` | `kubernetes` | ✅ CÓ |
| `AWS Fargate` | `AWS` | Fargate là dịch vụ serverless container của AWS | `aws-fargate` | `aws` | ✅ CÓ |
| `Amazon CloudWatch` | `AWS` | CloudWatch là dịch vụ monitoring của AWS | `amazon-cloudwatch` | `aws` | ✅ CÓ |
| `AWS CodePipeline` | `AWS` | CodePipeline là dịch vụ CI/CD của AWS | `aws-codepipeline` | `aws` | ✅ CÓ |
| `AWS CodeBuild` | `AWS` | CodeBuild là dịch vụ build của AWS | `aws-codebuild` | `aws` | ✅ CÓ |
| `AWS CodeDeploy` | `AWS` | CodeDeploy là dịch vụ deploy của AWS | `aws-codedeploy` | `aws` | ✅ CÓ |
| `Amazon Kinesis` | `AWS` | Kinesis là dịch vụ streaming của AWS | `amazon-kinesis` | `aws` | ✅ CÓ |
| `AWS Glue` | `AWS` | Glue là dịch vụ ETL của AWS | `aws-glue` | `aws` | ✅ CÓ |
| `Amazon Athena` | `AWS` | Athena là dịch vụ query serverless của AWS | `amazon-athena` | `aws` | ✅ CÓ |
| `Amazon SageMaker` | `AWS` | SageMaker là dịch vụ ML của AWS | `amazon-sagemaker` | `aws` | ✅ CÓ |
| `AWS Elastic Beanstalk` | `AWS` | Elastic Beanstalk là PaaS của AWS | `aws-elastic-beanstalk` | `aws` | ✅ CÓ |
| `Amazon API Gateway` | `AWS` | API Gateway là dịch vụ quản lý API của AWS | `amazon-api-gateway` | `aws` | ✅ CÓ |
| `AWS Step Functions` | `AWS` | Step Functions là dịch vụ workflow của AWS | `aws-step-functions` | `aws` | ✅ CÓ |
| `AWS Secrets Manager` | `AWS` | Secrets Manager là dịch vụ quản lý secret của AWS | `aws-secrets-manager` | `aws` | ✅ CÓ |
| `AWS KMS` | `AWS` | KMS là dịch vụ quản lý key mã hóa của AWS | `aws-kms` | `aws` | ✅ CÓ |
| `Amazon VPC` | `AWS` | VPC là dịch vụ mạng ảo của AWS | `amazon-vpc` | `aws` | ✅ CÓ |
| `Amazon Aurora` | `AWS` | Aurora là dịch vụ database của AWS | `amazon-aurora` | `aws` | ✅ CÓ |
| `Amazon ElastiCache` | `AWS` | ElastiCache là dịch vụ cache của AWS | `amazon-elasticache` | `aws` | ✅ CÓ |
| `Amazon Cognito` | `AWS` | Cognito là dịch vụ authentication của AWS | `amazon-cognito` | `aws` | ✅ CÓ |
| `Amazon EMR` | `AWS` | EMR là dịch vụ big data của AWS | `amazon-emr` | `aws` | ✅ CÓ |
| `Azure SQL Database` | `Azure` | Azure SQL Database là dịch vụ database của Azure | `azure-sql-database` | `azure` | ✅ CÓ |
| `Azure Cosmos DB` | `Azure` | Cosmos DB là dịch vụ NoSQL của Azure | `azure-cosmos-db` | `azure` | ✅ CÓ |
| `Azure Kubernetes Service` | `Azure` | AKS là dịch vụ Kubernetes quản lý của Azure | `azure-kubernetes-service` | `azure` | ✅ CÓ |
| `Azure Kubernetes Service` | `Kubernetes` | AKS là Kubernetes quản lý của Azure | `azure-kubernetes-service` | `kubernetes` | ✅ CÓ |
| `Azure Blob Storage` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure | `azure-blob-storage` | `azure` | ✅ CÓ |
| `Azure Active Directory` | `Azure` | Azure AD là dịch vụ định danh của Azure | `azure-active-directory` | `azure` | ✅ CÓ |
| `Azure App Service` | `Azure` | App Service là PaaS của Azure | `azure-app-service` | `azure` | ✅ CÓ |
| `Azure Data Factory` | `Azure` | Data Factory là dịch vụ ETL của Azure | `azure-data-factory` | `azure` | ✅ CÓ |
| `Azure Synapse Analytics` | `Azure` | Synapse Analytics là data warehouse của Azure | `azure-synapse-analytics` | `azure` | ✅ CÓ |
| `Azure Monitor` | `Azure` | Azure Monitor là dịch vụ monitoring của Azure | `azure-monitor` | `azure` | ✅ CÓ |
| `Azure Logic Apps` | `Azure` | Logic Apps là dịch vụ workflow của Azure | `azure-logic-apps` | `azure` | ✅ CÓ |
| `Azure Service Bus` | `Azure` | Service Bus là dịch vụ message queue của Azure | `azure-service-bus` | `azure` | ✅ CÓ |
| `Azure Key Vault` | `Azure` | Key Vault là dịch vụ quản lý secret của Azure | `azure-key-vault` | `azure` | ✅ CÓ |
| `Azure Data Lake` | `Azure` | Data Lake là dịch vụ lưu trữ big data của Azure | `azure-data-lake` | `azure` | ✅ CÓ |
| `Azure Databricks` | `Azure` | Azure Databricks tích hợp Spark trên Azure | `azure-databricks` | `azure` | ✅ CÓ |
| `Azure Databricks` | `Apache Spark` | Azure Databricks chạy trên nền Spark | `azure-databricks` | `apache-spark` | ✅ CÓ |
| `Azure Virtual Machines` | `Azure` | VM là dịch vụ compute của Azure | `azure-virtual-machines` | `azure` | ✅ CÓ |
| `Azure API Management` | `Azure` | API Management là dịch vụ quản lý API của Azure | `azure-api-management` | `azure` | ✅ CÓ |
| `Azure Cognitive Services` | `Azure` | Cognitive Services là dịch vụ AI của Azure | `azure-cognitive-services` | `azure` | ✅ CÓ |
| `Azure Machine Learning` | `Azure` | Azure ML là dịch vụ ML của Azure | `azure-machine-learning` | `azure` | ✅ CÓ |
| `Azure DNS` | `Azure` | Azure DNS là dịch vụ DNS của Azure | `azure-dns` | `azure` | ✅ CÓ |
| `Azure CDN` | `Azure` | Azure CDN là dịch vụ CDN của Azure | `azure-cdn` | `azure` | ✅ CÓ |
| `Azure Application Insights` | `Azure` | Application Insights là dịch vụ APM của Azure | `azure-application-insights` | `azure` | ✅ CÓ |
| `Azure Service Fabric` | `Azure` | Service Fabric là nền tảng microservices của Azure | `azure-service-fabric` | `azure` | ✅ CÓ |
| `Azure Notification Hubs` | `Azure` | Notification Hubs là dịch vụ push notification của Azure | `azure-notification-hubs` | `azure` | ✅ CÓ |
| `Cloud Run` | `Google Cloud Platform` | Cloud Run là dịch vụ serverless container của GCP | `cloud-run` | `gcp` | ✅ CÓ |
| `Cloud Functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `Cloud Storage` | `Google Cloud Platform` | Cloud Storage là dịch vụ lưu trữ của GCP | `cloud-storage` | `gcp` | ✅ CÓ |
| `Compute Engine` | `Google Cloud Platform` | Compute Engine là dịch vụ compute của GCP | `compute-engine` | `gcp` | ✅ CÓ |
| `Cloud SQL` | `Google Cloud Platform` | Cloud SQL là dịch vụ database của GCP | `cloud-sql` | `gcp` | ✅ CÓ |
| `Firestore` | `Google Cloud Platform` | Firestore là dịch vụ NoSQL của GCP | `firestore` | `gcp` | ✅ CÓ |
| `Pub/Sub` | `Google Cloud Platform` | Pub/Sub là dịch vụ messaging của GCP | `pub/sub` | `gcp` | ❌ KHÔNG |
| `Cloud Dataflow` | `Google Cloud Platform` | Dataflow là dịch vụ xử lý dữ liệu của GCP | `cloud-dataflow` | `gcp` | ✅ CÓ |
| `Cloud Dataproc` | `Google Cloud Platform` | Dataproc là dịch vụ Spark/Hadoop quản lý của GCP | `cloud-dataproc` | `gcp` | ✅ CÓ |
| `Cloud Dataproc` | `Apache Spark` | Dataproc chạy Spark/Hadoop quản lý | `cloud-dataproc` | `apache-spark` | ✅ CÓ |
| `Vertex AI` | `Google Cloud Platform` | Vertex AI là dịch vụ ML của GCP | `vertex-ai` | `gcp` | ✅ CÓ |
| `GKE` | `Google Cloud Platform` | GKE là dịch vụ Kubernetes quản lý của GCP | `gke` | `gcp` | ✅ CÓ |
| `GKE` | `Kubernetes` | GKE là Kubernetes quản lý của GCP | `gke` | `kubernetes` | ✅ CÓ |
| `Cloud Build` | `Google Cloud Platform` | Cloud Build là dịch vụ CI/CD của GCP | `cloud-build` | `gcp` | ✅ CÓ |
| `Cloud Spanner` | `Google Cloud Platform` | Cloud Spanner là dịch vụ database phân tán của GCP | `cloud-spanner` | `gcp` | ✅ CÓ |
| `Cloud Bigtable` | `Google Cloud Platform` | Bigtable là dịch vụ NoSQL của GCP | `cloud-bigtable` | `gcp` | ✅ CÓ |
| `Cloud IAM` | `Google Cloud Platform` | Cloud IAM là dịch vụ quản lý quyền của GCP | `cloud-iam` | `gcp` | ✅ CÓ |
| `Cloud Monitoring` | `Google Cloud Platform` | Cloud Monitoring là dịch vụ monitoring của GCP | `cloud-monitoring` | `gcp` | ✅ CÓ |
| `App Engine` | `Google Cloud Platform` | App Engine là PaaS của GCP | `app-engine` | `gcp` | ✅ CÓ |
| `Cloud Composer` | `Google Cloud Platform` | Cloud Composer là dịch vụ Airflow quản lý của GCP | `cloud-composer` | `gcp` | ✅ CÓ |
| `Cloud Composer` | `Airflow` | Cloud Composer là Airflow quản lý trên GCP | `cloud-composer` | `airflow` | ✅ CÓ |
| `SAP ABAP` | `SAP` | ABAP là ngôn ngữ lập trình của SAP | `sap-abap` | `sap` | ✅ CÓ |
| `SAP HANA` | `SAP` | HANA là database platform của SAP | `sap-hana` | `sap` | ✅ CÓ |
| `SAP FICO` | `SAP` | FICO là module tài chính của SAP | `sap-fico` | `sap` | ✅ CÓ |
| `SAP MM` | `SAP` | MM là module quản lý vật tư của SAP | `sap-mm` | `sap` | ✅ CÓ |
| `Salesforce Apex` | `Salesforce` | Apex là ngôn ngữ lập trình của Salesforce | `apex` | `salesforce` | ❌ KHÔNG |
| `Salesforce Lightning` | `Salesforce` | Lightning là framework UI của Salesforce | `salesforce-lightning` | `salesforce` | ❌ KHÔNG |
| `SSRS` | `SQL Server` | SSRS là công cụ reporting của SQL Server | `reporting-services` | `sql-server` | ❌ KHÔNG |
| `SSIS` | `SQL Server` | SSIS là công cụ ETL của SQL Server | `ssis` | `sql-server` | ❌ KHÔNG |
| `SSAS` | `SQL Server` | SSAS là công cụ phân tích của SQL Server | `ssas` | `sql-server` | ❌ KHÔNG |
| `Looker` | `SQL` | Looker dùng LookML dựa trên SQL | `looker` | `sql` | ✅ CÓ |
| `Google Data Studio` | `Google Cloud Platform` | Data Studio tích hợp hệ sinh thái GCP | `google-data-studio` | `gcp` | ✅ CÓ |
| `Firebase Hosting` | `Firebase` | Firebase Hosting là dịch vụ của Firebase | `firebase hosting` | `firebase` | ❌ KHÔNG |
| `FreeRTOS` | `Embedded C` | FreeRTOS thường viết bằng Embedded C | `freertos` | `embedded-c` | ✅ CÓ |
| `ESP32` | `Embedded C` | Lập trình ESP32 thường dùng Embedded C | `esp32` | `embedded-c` | ✅ CÓ |
| `STM32` | `Embedded C` | Lập trình STM32 thường dùng Embedded C | `stm32` | `embedded-c` | ✅ CÓ |
| `Arduino` | `C++` | Arduino sketch dựa trên C++ | `arduino` | `c++` | ✅ CÓ |
| `MQTT` | `IoT` | MQTT là giao thức truyền thông phổ biến trong IoT | `mqtt` | `iot` | ✅ CÓ |
| `Raspberry Pi` | `Linux` | Raspberry Pi thường chạy hệ điều hành Linux | `raspberry-pi` | `linux` | ✅ CÓ |
| `Smart Contract` | `Solidity` | Smart contract trên Ethereum thường viết bằng Solidity | `smart-contracts` | `solidity` | ✅ CÓ |
| `Truffle` | `Solidity` | Truffle là framework phát triển Solidity | `truffle` | `solidity` | ✅ CÓ |
| `Hardhat` | `Solidity` | Hardhat là framework phát triển Solidity | `hardhat` | `solidity` | ✅ CÓ |
| `Web3.js` | `JavaScript` | Web3.js là thư viện JavaScript | `web3.js` | `javascript` | ✅ CÓ |
| `Ethers.js` | `JavaScript` | Ethers.js là thư viện JavaScript | `ethers.js` | `javascript` | ✅ CÓ |
| `ARKit` | `Swift` | ARKit thường dùng qua Swift trên iOS | `arkit` | `swift` | ✅ CÓ |
| `ARCore` | `Android` | ARCore thường dùng trên nền tảng Android | `arcore` | `android` | ✅ CÓ |
| `Godot Engine` | `GDScript` | Godot Engine dùng ngôn ngữ script riêng GDScript | `godot` | `gdscript` | ✅ CÓ |
| `WebXR` | `JavaScript` | WebXR là API JavaScript cho AR/VR trên web | `webxr` | `javascript` | ✅ CÓ |
| `Pyramid` | `Python` | Python framework | `pyramid` | `python` | ✅ CÓ |
| `Bottle` | `Python` | Python framework | `bottle` | `python` | ✅ CÓ |
| `Tornado Web` | `Python` | Python framework | `tornado` | `python` | ✅ CÓ |
| `aiohttp` | `Python` | Python library | `aiohttp` | `python` | ✅ CÓ |
| `XGBoost` | `Python` | Python library phổ biến qua API Python | `xgboost` | `python` | ✅ CÓ |
| `LightGBM` | `Python` | Python library phổ biến qua API Python | `lightgbm` | `python` | ✅ CÓ |
| `JAX` | `Python` | Python library | `jax` | `python` | ✅ CÓ |
| `Pillow` | `Python` | Python library | `python-imaging-library` | `python` | ✅ CÓ |
| `spaCy` | `Python` | Python library | `spacy` | `python` | ✅ CÓ |
| `NLTK` | `Python` | Python library | `nltk` | `python` | ✅ CÓ |
| `Gensim` | `Python` | Python library | `gensim` | `python` | ✅ CÓ |
| `Transformers` | `Python` | Hugging Face Transformers là Python library | `transformers` | `python` | ✅ CÓ |
| `Django REST Framework` | `Django` | DRF là extension của Django | `django-rest-framework` | `django` | ✅ CÓ |
| `Django Channels` | `Django` | Channels là extension của Django | `django-channels` | `django` | ✅ CÓ |
| `Dash` | `Python` | Dash là Python framework cho dashboard | `dash` | `python` | ✅ CÓ |
| `Gradio` | `Python` | Gradio là Python library | `gradio` | `python` | ✅ CÓ |
| `React Query` | `React` | React Query là data-fetching library của React | `react-query` | `reactjs` | ✅ CÓ |
| `TanStack Query` | `React` | TanStack Query là data-fetching library của React | `tanstack-query` | `reactjs` | ✅ CÓ |
| `SWR` | `React` | SWR là data-fetching library của React | `swr` | `reactjs` | ✅ CÓ |
| `Recoil` | `React` | Recoil là state library của React | `recoil` | `reactjs` | ✅ CÓ |
| `Jotai` | `React` | Jotai là state library của React | `jotai` | `reactjs` | ✅ CÓ |
| `Framer Motion` | `React` | Framer Motion là animation library của React | `framer-motion` | `reactjs` | ✅ CÓ |
| `D3.js` | `JavaScript` | D3.js là thư viện visualization của JavaScript | `d3.js` | `javascript` | ✅ CÓ |
| `Turborepo` | `JavaScript` | Turborepo là monorepo tool cho hệ sinh thái JS | `turborepo` | `javascript` | ✅ CÓ |
| `Nx Monorepo` | `JavaScript` | Nx là monorepo tool cho hệ sinh thái JS | `nx-monorepo` | `javascript` | ✅ CÓ |
| `Astro` | `JavaScript` | Astro là framework JavaScript | `astro` | `javascript` | ✅ CÓ |
| `Remix` | `React` | Remix là meta-framework của React | `remix` | `reactjs` | ✅ CÓ |
| `SolidJS` | `JavaScript` | SolidJS là framework JavaScript | `solidjs` | `javascript` | ✅ CÓ |
| `Qwik` | `JavaScript` | Qwik là framework JavaScript | `qwik` | `javascript` | ✅ CÓ |
| `Preact` | `React` | Preact là bản thay thế nhẹ của React | `preact` | `reactjs` | ✅ CÓ |
| `WebdriverIO` | `JavaScript` | WebdriverIO là test framework cho JavaScript | `webdriverio` | `javascript` | ✅ CÓ |
| `Testcontainers` | `Docker` | Testcontainers chạy test bằng container Docker | `testcontainers` | `docker` | ✅ CÓ |
| `Mockito` | `Java` | Mockito là mocking framework cho Java | `mockito` | `java` | ✅ CÓ |
| `Chai.js` | `JavaScript` | Chai là assertion library cho JavaScript | `chai.js` | `javascript` | ✅ CÓ |
| `Sinon.js` | `JavaScript` | Sinon là mocking library cho JavaScript | `sinon.js` | `javascript` | ✅ CÓ |
| `Supertest` | `Node.js` | Supertest dùng để test HTTP server Node.js | `supertest` | `node.js` | ✅ CÓ |
| `k6` | `JavaScript` | k6 dùng script JavaScript để load test | `k6` | `javascript` | ✅ CÓ |
| `JMeter` | `Java` | JMeter viết bằng Java | `jmeter` | `java` | ✅ CÓ |
| `next.js` | `React` | Next.js là meta-framework của React (biến thể định dạng của 'Next.js') | `next.js` | `reactjs` | ✅ CÓ |
| `GOOGLE-CLOUD-FUNCTIONS` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Google Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `wordpress` | `PHP` | WordPress viết bằng PHP (biến thể định dạng của 'WordPress') | `wordpress` | `php` | ✅ CÓ |
| `cLOUD mONITORING` | `Google Cloud Platform` | Cloud Monitoring là dịch vụ monitoring của GCP (biến thể định dạng của 'Cloud Monitoring') | `cloud-monitoring` | `gcp` | ✅ CÓ |
| `spring-security` | `Spring` | Spring Security là module của Spring (biến thể định dạng của 'Spring Security') | `spring-security` | `spring` | ✅ CÓ |
| `sap-abap` | `SAP` | ABAP là ngôn ngữ lập trình của SAP (biến thể định dạng của 'SAP ABAP') | `sap-abap` | `sap` | ✅ CÓ |
| `cloud dataproc` | `Google Cloud Platform` | Dataproc là dịch vụ Spark/Hadoop quản lý của GCP (biến thể định dạng của 'Cloud Dataproc') | `cloud-dataproc` | `gcp` | ✅ CÓ |
| `RASPBERRY-PI` | `Linux` | Raspberry Pi thường chạy hệ điều hành Linux (biến thể định dạng của 'Raspberry Pi') | `raspberry-pi` | `linux` | ✅ CÓ |
| `Azure-Service-Bus` | `Azure` | Service Bus là dịch vụ message queue của Azure (biến thể định dạng của 'Azure Service Bus') | `azure-service-bus` | `azure` | ✅ CÓ |
| `Amazon-Kinesis` | `AWS` | Kinesis là dịch vụ streaming của AWS (biến thể định dạng của 'Amazon Kinesis') | `amazon-kinesis` | `aws` | ✅ CÓ |
| `ASPNET MVC` | `ASP.NET` | ASP.NET MVC là module của ASP.NET (biến thể định dạng của 'ASP.NET MVC') | `asp.net-mvc` | `asp.net` | ✅ CÓ |
| `DBT` | `SQL` | dbt biên dịch transformation thành SQL (biến thể định dạng của 'dbt') | `dbt` | `sql` | ✅ CÓ |
| `ARCORE` | `Android` | ARCore thường dùng trên nền tảng Android (biến thể định dạng của 'ARCore') | `arcore` | `android` | ✅ CÓ |
| `pYsPARK` | `Python` | Python API của Spark (biến thể định dạng của 'PySpark') | `pyspark` | `python` | ✅ CÓ |
| `Wordpress` | `PHP` | WordPress viết bằng PHP (biến thể định dạng của 'WordPress') | `wordpress` | `php` | ✅ CÓ |
| `WINFORMS` | `C#` | WinForms là UI framework của .NET/C# (biến thể định dạng của 'WinForms') | `winforms` | `c#` | ✅ CÓ |
| `google-cloud-functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Google Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `PYSPARK` | `Apache Spark` | Python API của Spark (biến thể định dạng của 'PySpark') | `pyspark` | `apache-spark` | ✅ CÓ |
| `Jdbc` | `Java` | JDBC là API kết nối DB của Java (biến thể định dạng của 'JDBC') | `jdbc` | `java` | ✅ CÓ |
| `django` | `Python` | Python framework (biến thể định dạng của 'Django') | `django` | `python` | ✅ CÓ |
| `sALESFORCE aPEX` | `Salesforce` | Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex') | `apex` | `salesforce` | ❌ KHÔNG |
| `Amazon-CloudWatch` | `AWS` | CloudWatch là dịch vụ monitoring của AWS (biến thể định dạng của 'Amazon CloudWatch') | `amazon-cloudwatch` | `aws` | ✅ CÓ |
| `Entity_Framework_Core` | `Entity Framework` | EF Core là thế hệ mới của EF (biến thể định dạng của 'Entity Framework Core') | `entity_framework_core` | `entity-framework` | ❌ KHÔNG |
| `Jax` | `Python` | Python library (biến thể định dạng của 'JAX') | `jax` | `python` | ✅ CÓ |
| `Azure-Key-Vault` | `Azure` | Key Vault là dịch vụ quản lý secret của Azure (biến thể định dạng của 'Azure Key Vault') | `azure-key-vault` | `azure` | ✅ CÓ |
| `Azure-Application-Insights` | `Azure` | Application Insights là dịch vụ APM của Azure (biến thể định dạng của 'Azure Application Insights') | `azure-application-insights` | `azure` | ✅ CÓ |
| `ssas` | `SQL Server` | SSAS là công cụ phân tích của SQL Server (biến thể định dạng của 'SSAS') | `ssas` | `sql-server` | ❌ KHÔNG |
| `core-data` | `Swift` | Core Data là framework persistence của Apple dùng với Swift (biến thể định dạng của 'Core Data') | `core-data` | `swift` | ✅ CÓ |
| `kOTLIN cOROUTINES` | `Kotlin` | Coroutines là tính năng của Kotlin (biến thể định dạng của 'Kotlin Coroutines') | `kotlin-coroutines` | `kotlin` | ✅ CÓ |
| `blazor webassembly` | `Blazor` | Blazor WASM là chế độ chạy của Blazor (biến thể định dạng của 'Blazor WebAssembly') | `blazor-webassembly` | `blazor` | ✅ CÓ |
| `PRETTIER` | `JavaScript` | Prettier là formatter cho JavaScript (biến thể định dạng của 'Prettier') | `prettier` | `javascript` | ✅ CÓ |
| `aZURE kUBERNETES sERVICE` | `Azure` | AKS là dịch vụ Kubernetes quản lý của Azure (biến thể định dạng của 'Azure Kubernetes Service') | `azure-kubernetes-service` | `azure` | ✅ CÓ |
| `google cloud functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Google Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `REDUX TOOLKIT` | `Redux` | Redux Toolkit là bộ công cụ chính thức của Redux (biến thể định dạng của 'Redux Toolkit') | `redux-toolkit` | `redux` | ✅ CÓ |
| `AMAZON ATHENA` | `AWS` | Athena là dịch vụ query serverless của AWS (biến thể định dạng của 'Amazon Athena') | `amazon-athena` | `aws` | ✅ CÓ |
| `preact` | `React` | Preact là bản thay thế nhẹ của React (biến thể định dạng của 'Preact') | `preact` | `reactjs` | ✅ CÓ |
| `KTOR` | `Kotlin` | Ktor là framework web viết bằng Kotlin (biến thể định dạng của 'Ktor') | `ktor` | `kotlin` | ✅ CÓ |
| `MONGOOSE` | `Node.js` | Mongoose là ODM cho Node.js (biến thể định dạng của 'Mongoose') | `mongoose` | `node.js` | ✅ CÓ |
| `FASTAPI` | `Python` | Python framework (biến thể định dạng của 'FastAPI') | `fastapi` | `python` | ✅ CÓ |
| `azure-monitor` | `Azure` | Azure Monitor là dịch vụ monitoring của Azure (biến thể định dạng của 'Azure Monitor') | `azure-monitor` | `azure` | ✅ CÓ |
| `aws-codepipeline` | `AWS` | CodePipeline là dịch vụ CI/CD của AWS (biến thể định dạng của 'AWS CodePipeline') | `aws-codepipeline` | `aws` | ✅ CÓ |
| `amazon eks` | `Kubernetes` | EKS là Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon-eks` | `kubernetes` | ✅ CÓ |
| `scikit-learn` | `Python` | Python library (biến thể định dạng của 'Scikit-learn') | `scikit-learn` | `python` | ✅ CÓ |
| `PANDAS` | `Python` | Python library (biến thể định dạng của 'Pandas') | `pandas` | `python` | ✅ CÓ |
| `PYMYSQL` | `MySQL` | PyMySQL là driver Python cho MySQL (biến thể định dạng của 'PyMySQL') | `pymysql` | `mysql` | ✅ CÓ |
| `pyspark` | `Python` | Python API của Spark (biến thể định dạng của 'PySpark') | `pyspark` | `python` | ✅ CÓ |
| `amazon aurora` | `AWS` | Aurora là dịch vụ database của AWS (biến thể định dạng của 'Amazon Aurora') | `amazon-aurora` | `aws` | ✅ CÓ |
| `AZURE-ACTIVE-DIRECTORY` | `Azure` | Azure AD là dịch vụ định danh của Azure (biến thể định dạng của 'Azure Active Directory') | `azure-active-directory` | `azure` | ✅ CÓ |
| `gOOGLE dATA sTUDIO` | `Google Cloud Platform` | Data Studio tích hợp hệ sinh thái GCP (biến thể định dạng của 'Google Data Studio') | `google-data-studio` | `gcp` | ✅ CÓ |
| `wORDpRESS` | `PHP` | WordPress viết bằng PHP (biến thể định dạng của 'WordPress') | `wordpress` | `php` | ✅ CÓ |
| `Azure-Cosmos-DB` | `Azure` | Cosmos DB là dịch vụ NoSQL của Azure (biến thể định dạng của 'Azure Cosmos DB') | `azure-cosmos-db` | `azure` | ✅ CÓ |
| `RECOIL` | `React` | Recoil là state library của React (biến thể định dạng của 'Recoil') | `recoil` | `reactjs` | ✅ CÓ |
| `cELERY` | `Python` | Python library (biến thể định dạng của 'Celery') | `celery` | `python` | ✅ CÓ |
| `Azure-Active-Directory` | `Azure` | Azure AD là dịch vụ định danh của Azure (biến thể định dạng của 'Azure Active Directory') | `azure-active-directory` | `azure` | ✅ CÓ |
| `CLOUD-DATAPROC` | `Google Cloud Platform` | Dataproc là dịch vụ Spark/Hadoop quản lý của GCP (biến thể định dạng của 'Cloud Dataproc') | `cloud-dataproc` | `gcp` | ✅ CÓ |
| `vue.js` | `JavaScript` | JS framework (biến thể định dạng của 'Vue.js') | `vue.js` | `javascript` | ✅ CÓ |
| `aws secrets manager` | `AWS` | Secrets Manager là dịch vụ quản lý secret của AWS (biến thể định dạng của 'AWS Secrets Manager') | `aws-secrets-manager` | `aws` | ✅ CÓ |
| `sqlalchemy` | `Python` | Python ORM (biến thể định dạng của 'SQLAlchemy') | `sqlalchemy` | `python` | ✅ CÓ |
| `webdriverio` | `JavaScript` | WebdriverIO là test framework cho JavaScript (biến thể định dạng của 'WebdriverIO') | `webdriverio` | `javascript` | ✅ CÓ |
| `Chaijs` | `JavaScript` | Chai là assertion library cho JavaScript (biến thể định dạng của 'Chai.js') | `chaijs` | `javascript` | ❌ KHÔNG |
| `Amazon_VPC` | `AWS` | VPC là dịch vụ mạng ảo của AWS (biến thể định dạng của 'Amazon VPC') | `amazon_vpc` | `aws` | ❌ KHÔNG |
| `AWS-CodeBuild` | `AWS` | CodeBuild là dịch vụ build của AWS (biến thể định dạng của 'AWS CodeBuild') | `aws-codebuild` | `aws` | ✅ CÓ |
| `DJANGO-CHANNELS` | `Django` | Channels là extension của Django (biến thể định dạng của 'Django Channels') | `django-channels` | `django` | ✅ CÓ |
| `REDUX SAGA` | `Redux` | Redux Saga là middleware của Redux (biến thể định dạng của 'Redux Saga') | `redux-saga` | `redux` | ✅ CÓ |
| `AWS-Glue` | `AWS` | Glue là dịch vụ ETL của AWS (biến thể định dạng của 'AWS Glue') | `aws-glue` | `aws` | ✅ CÓ |
| `Aws Glue` | `AWS` | Glue là dịch vụ ETL của AWS (biến thể định dạng của 'AWS Glue') | `aws-glue` | `aws` | ✅ CÓ |
| `SVELTE` | `JavaScript` | JS framework (biến thể định dạng của 'Svelte') | `svelte` | `javascript` | ✅ CÓ |
| `AWS-CODEPIPELINE` | `AWS` | CodePipeline là dịch vụ CI/CD của AWS (biến thể định dạng của 'AWS CodePipeline') | `aws-codepipeline` | `aws` | ✅ CÓ |
| `AMAZON CLOUDWATCH` | `AWS` | CloudWatch là dịch vụ monitoring của AWS (biến thể định dạng của 'Amazon CloudWatch') | `amazon-cloudwatch` | `aws` | ✅ CÓ |
| `tRUFFLE` | `Solidity` | Truffle là framework phát triển Solidity (biến thể định dạng của 'Truffle') | `truffle` | `solidity` | ✅ CÓ |
| `magento` | `PHP` | Magento là nền tảng ecommerce viết bằng PHP (biến thể định dạng của 'Magento') | `magento` | `php` | ✅ CÓ |
| `Amazon_EKS` | `AWS` | EKS là dịch vụ Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon_eks` | `aws` | ❌ KHÔNG |
| `azure-sql-database` | `Azure` | Azure SQL Database là dịch vụ database của Azure (biến thể định dạng của 'Azure SQL Database') | `azure-sql-database` | `azure` | ✅ CÓ |
| `DJANGO` | `Python` | Python framework (biến thể định dạng của 'Django') | `django` | `python` | ✅ CÓ |
| `AWS ELASTIC BEANSTALK` | `AWS` | Elastic Beanstalk là PaaS của AWS (biến thể định dạng của 'AWS Elastic Beanstalk') | `aws-elastic-beanstalk` | `aws` | ✅ CÓ |
| `celery` | `Python` | Python library (biến thể định dạng của 'Celery') | `celery` | `python` | ✅ CÓ |
| `cORE dATA` | `Swift` | Core Data là framework persistence của Apple dùng với Swift (biến thể định dạng của 'Core Data') | `core-data` | `swift` | ✅ CÓ |
| `CLOUD BUILD` | `Google Cloud Platform` | Cloud Build là dịch vụ CI/CD của GCP (biến thể định dạng của 'Cloud Build') | `cloud-build` | `gcp` | ✅ CÓ |
| `framer-motion` | `React` | Framer Motion là animation library của React (biến thể định dạng của 'Framer Motion') | `framer-motion` | `reactjs` | ✅ CÓ |
| `entity framework core` | `Entity Framework` | EF Core là thế hệ mới của EF (biến thể định dạng của 'Entity Framework Core') | `entity-framework-core` | `entity-framework` | ✅ CÓ |
| `LANGCHAIN` | `Python` | LangChain thường dùng qua Python SDK (biến thể định dạng của 'LangChain') | `langchain` | `python` | ✅ CÓ |
| `cLOUD dATAPROC` | `Google Cloud Platform` | Dataproc là dịch vụ Spark/Hadoop quản lý của GCP (biến thể định dạng của 'Cloud Dataproc') | `cloud-dataproc` | `gcp` | ✅ CÓ |
| `Cloud-SQL` | `Google Cloud Platform` | Cloud SQL là dịch vụ database của GCP (biến thể định dạng của 'Cloud SQL') | `cloud-sql` | `gcp` | ✅ CÓ |
| `pymysql` | `MySQL` | PyMySQL là driver Python cho MySQL (biến thể định dạng của 'PyMySQL') | `pymysql` | `mysql` | ✅ CÓ |
| `pYtORCH` | `Python` | Python library (biến thể định dạng của 'PyTorch') | `pytorch` | `python` | ✅ CÓ |
| `KERAS` | `TensorFlow` | Keras chạy trên TensorFlow backend (biến thể định dạng của 'Keras') | `keras` | `tensorflow` | ✅ CÓ |
| `rspec` | `Ruby` | RSpec là test framework của Ruby (biến thể định dạng của 'RSpec') | `rspec` | `ruby` | ✅ CÓ |
| `apollo client` | `GraphQL` | Apollo Client là client cho GraphQL (biến thể định dạng của 'Apollo Client') | `apollo-client` | `graphql` | ✅ CÓ |
| `Dbt` | `SQL` | dbt biên dịch transformation thành SQL (biến thể định dạng của 'dbt') | `dbt` | `sql` | ✅ CÓ |
| `cLOUD sql` | `Google Cloud Platform` | Cloud SQL là dịch vụ database của GCP (biến thể định dạng của 'Cloud SQL') | `cloud-sql` | `gcp` | ✅ CÓ |
| `gradio` | `Python` | Gradio là Python library (biến thể định dạng của 'Gradio') | `gradio` | `python` | ✅ CÓ |
| `nuxt.js` | `Vue.js` | Nuxt.js là meta-framework của Vue (biến thể định dạng của 'Nuxt.js') | `nuxt.js` | `vue.js` | ✅ CÓ |
| `COMBINE` | `Swift` | Combine là framework reactive của Apple dùng với Swift (biến thể định dạng của 'Combine') | `combine` | `swift` | ✅ CÓ |
| `SPARK-STREAMING` | `Apache Spark` | Spark Streaming là module của Spark (biến thể định dạng của 'Spark Streaming') | `spark-streaming` | `apache-spark` | ✅ CÓ |
| `XAMARIN` | `C#` | Xamarin viết bằng C# (biến thể định dạng của 'Xamarin') | `xamarin` | `c#` | ✅ CÓ |
| `gke` | `Kubernetes` | GKE là Kubernetes quản lý của GCP (biến thể định dạng của 'GKE') | `gke` | `kubernetes` | ✅ CÓ |
| `JEST` | `JavaScript` | Jest là test framework cho JavaScript (biến thể định dạng của 'Jest') | `jestjs` | `javascript` | ✅ CÓ |
| `Amazon-S3` | `AWS` | S3 là dịch vụ storage của AWS (biến thể định dạng của 'Amazon S3') | `amazon-s3` | `aws` | ✅ CÓ |
| `azure-api-management` | `Azure` | API Management là dịch vụ quản lý API của Azure (biến thể định dạng của 'Azure API Management') | `azure-api-management` | `azure` | ✅ CÓ |
| `juNIT` | `Java` | JUnit là test framework cho Java (biến thể định dạng của 'JUnit') | `junit` | `java` | ✅ CÓ |
| `azure-machine-learning` | `Azure` | Azure ML là dịch vụ ML của Azure (biến thể định dạng của 'Azure Machine Learning') | `azure-machine-learning` | `azure` | ✅ CÓ |
| `aws-fargate` | `AWS` | Fargate là dịch vụ serverless container của AWS (biến thể định dạng của 'AWS Fargate') | `aws-fargate` | `aws` | ✅ CÓ |
| `eLASTICSEARCH` | `Java` | Elasticsearch viết bằng Java (biến thể định dạng của 'Elasticsearch') | `elasticsearch` | `java` | ✅ CÓ |
| `SAP-FICO` | `SAP` | FICO là module tài chính của SAP (biến thể định dạng của 'SAP FICO') | `sap-fico` | `sap` | ✅ CÓ |
| `Sqlalchemy` | `Python` | Python ORM (biến thể định dạng của 'SQLAlchemy') | `sqlalchemy` | `python` | ✅ CÓ |
| `AWS CODEBUILD` | `AWS` | CodeBuild là dịch vụ build của AWS (biến thể định dạng của 'AWS CodeBuild') | `aws-codebuild` | `aws` | ✅ CÓ |
| `istio` | `Kubernetes` | Istio là service mesh chạy trên Kubernetes (biến thể định dạng của 'Istio') | `istio` | `kubernetes` | ✅ CÓ |
| `aws lambda` | `AWS` | Lambda là dịch vụ serverless của AWS (biến thể định dạng của 'AWS Lambda') | `aws-lambda` | `aws` | ✅ CÓ |
| `Freertos` | `Embedded C` | FreeRTOS thường viết bằng Embedded C (biến thể định dạng của 'FreeRTOS') | `freertos` | `embedded-c` | ✅ CÓ |
| `AMAZON CLOUDFRONT` | `AWS` | CloudFront là dịch vụ CDN của AWS (biến thể định dạng của 'Amazon CloudFront') | `amazon-cloudfront` | `aws` | ✅ CÓ |
| `Cloud-Run` | `Google Cloud Platform` | Cloud Run là dịch vụ serverless container của GCP (biến thể định dạng của 'Cloud Run') | `cloud-run` | `gcp` | ✅ CÓ |
| `AWS_Elastic_Beanstalk` | `AWS` | Elastic Beanstalk là PaaS của AWS (biến thể định dạng của 'AWS Elastic Beanstalk') | `aws_elastic_beanstalk` | `aws` | ❌ KHÔNG |
| `REACT` | `JavaScript` | JS library (biến thể định dạng của 'React') | `reactjs` | `javascript` | ✅ CÓ |
| `Kotlin-Coroutines` | `Kotlin` | Coroutines là tính năng của Kotlin (biến thể định dạng của 'Kotlin Coroutines') | `kotlin-coroutines` | `kotlin` | ✅ CÓ |
| `AZURE-DATABRICKS` | `Apache Spark` | Azure Databricks chạy trên nền Spark (biến thể định dạng của 'Azure Databricks') | `azure-databricks` | `apache-spark` | ✅ CÓ |
| `AZURE-API-MANAGEMENT` | `Azure` | API Management là dịch vụ quản lý API của Azure (biến thể định dạng của 'Azure API Management') | `azure-api-management` | `azure` | ✅ CÓ |
| `Amazon-EMR` | `AWS` | EMR là dịch vụ big data của AWS (biến thể định dạng của 'Amazon EMR') | `amazon-emr` | `aws` | ✅ CÓ |
| `AWS_CodePipeline` | `AWS` | CodePipeline là dịch vụ CI/CD của AWS (biến thể định dạng của 'AWS CodePipeline') | `aws_codepipeline` | `aws` | ❌ KHÔNG |
| `CLOUD DATAFLOW` | `Google Cloud Platform` | Dataflow là dịch vụ xử lý dữ liệu của GCP (biến thể định dạng của 'Cloud Dataflow') | `cloud-dataflow` | `gcp` | ✅ CÓ |
| `sap hana` | `SAP` | HANA là database platform của SAP (biến thể định dạng của 'SAP HANA') | `sap-hana` | `sap` | ✅ CÓ |
| `pRETTIER` | `JavaScript` | Prettier là formatter cho JavaScript (biến thể định dạng của 'Prettier') | `prettier` | `javascript` | ✅ CÓ |
| `astro` | `JavaScript` | Astro là framework JavaScript (biến thể định dạng của 'Astro') | `astro` | `javascript` | ✅ CÓ |
| `qWIK` | `JavaScript` | Qwik là framework JavaScript (biến thể định dạng của 'Qwik') | `qwik` | `javascript` | ✅ CÓ |
| `AMAZON-CLOUDWATCH` | `AWS` | CloudWatch là dịch vụ monitoring của AWS (biến thể định dạng của 'Amazon CloudWatch') | `amazon-cloudwatch` | `aws` | ✅ CÓ |
| `React_Native` | `JavaScript` | React Native viết bằng JavaScript (biến thể định dạng của 'React Native') | `react_native` | `javascript` | ❌ KHÔNG |
| `redux` | `JavaScript` | State library cho JS (biến thể định dạng của 'Redux') | `redux` | `javascript` | ✅ CÓ |
| `SAP-MM` | `SAP` | MM là module quản lý vật tư của SAP (biến thể định dạng của 'SAP MM') | `sap-mm` | `sap` | ✅ CÓ |
| `Jmeter` | `Java` | JMeter viết bằng Java (biến thể định dạng của 'JMeter') | `jmeter` | `java` | ✅ CÓ |
| `PLAYWRIGHT` | `JavaScript` | Playwright là test framework cho JavaScript (biến thể định dạng của 'Playwright') | `playwright` | `javascript` | ✅ CÓ |
| `PYRAMID` | `Python` | Python framework (biến thể định dạng của 'Pyramid') | `pyramid` | `python` | ✅ CÓ |
| `TRPC` | `TypeScript` | tRPC dựa trên type-safety của TypeScript (biến thể định dạng của 'tRPC') | `trpc` | `typescript` | ✅ CÓ |
| `Stm32` | `Embedded C` | Lập trình STM32 thường dùng Embedded C (biến thể định dạng của 'STM32') | `stm32` | `embedded-c` | ✅ CÓ |
| `ASP.NET-CORE` | `C#` | ASP.NET Core viết bằng C# (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `c#` | ✅ CÓ |
| `kotlin` | `Java` | Kotlin chạy trên JVM, tương tác với Java (biến thể định dạng của 'Kotlin') | `kotlin` | `java` | ✅ CÓ |
| `Spring_Security` | `Spring` | Spring Security là module của Spring (biến thể định dạng của 'Spring Security') | `spring_security` | `spring` | ❌ KHÔNG |
| `node.js` | `JavaScript` | Node.js chạy JavaScript phía server (biến thể định dạng của 'Node.js') | `node.js` | `javascript` | ✅ CÓ |
| `cloud-dataflow` | `Google Cloud Platform` | Dataflow là dịch vụ xử lý dữ liệu của GCP (biến thể định dạng của 'Cloud Dataflow') | `cloud-dataflow` | `gcp` | ✅ CÓ |
| `fORMIK` | `React` | Formik là form library của React (biến thể định dạng của 'Formik') | `formik` | `reactjs` | ✅ CÓ |
| `react-native` | `JavaScript` | React Native viết bằng JavaScript (biến thể định dạng của 'React Native') | `react-native` | `javascript` | ✅ CÓ |
| `ASP.NET CORE` | `ASP.NET` | ASP.NET Core là thế hệ mới của ASP.NET (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `asp.net` | ✅ CÓ |
| `chakra-ui` | `React` | Chakra UI là component library cho React (biến thể định dạng của 'Chakra UI') | `chakra-ui` | `reactjs` | ✅ CÓ |
| `fastapi` | `Python` | Python framework (biến thể định dạng của 'FastAPI') | `fastapi` | `python` | ✅ CÓ |
| `AMAZON-COGNITO` | `AWS` | Cognito là dịch vụ authentication của AWS (biến thể định dạng của 'Amazon Cognito') | `amazon-cognito` | `aws` | ✅ CÓ |
| `REDSHIFT` | `AWS` | Redshift là data warehouse dịch vụ của AWS (biến thể định dạng của 'Redshift') | `redshift` | `aws` | ✅ CÓ |
| `truffle` | `Solidity` | Truffle là framework phát triển Solidity (biến thể định dạng của 'Truffle') | `truffle` | `solidity` | ✅ CÓ |
| `framer motion` | `React` | Framer Motion là animation library của React (biến thể định dạng của 'Framer Motion') | `framer-motion` | `reactjs` | ✅ CÓ |
| `nx monorepo` | `JavaScript` | Nx là monorepo tool cho hệ sinh thái JS (biến thể định dạng của 'Nx Monorepo') | `nx-monorepo` | `javascript` | ✅ CÓ |
| `Amazon-ElastiCache` | `AWS` | ElastiCache là dịch vụ cache của AWS (biến thể định dạng của 'Amazon ElastiCache') | `amazon-elasticache` | `aws` | ✅ CÓ |
| `xamarin.forms` | `Xamarin` | Xamarin.Forms là module của Xamarin (biến thể định dạng của 'Xamarin.Forms') | `xamarin.forms` | `xamarin` | ✅ CÓ |
| `EXPRESS` | `JavaScript` | Express chạy trên JavaScript (biến thể định dạng của 'Express') | `express` | `javascript` | ✅ CÓ |
| `SINON.JS` | `JavaScript` | Sinon là mocking library cho JavaScript (biến thể định dạng của 'Sinon.js') | `sinon.js` | `javascript` | ✅ CÓ |
| `ENTITY FRAMEWORK` | `C#` | EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework') | `entity-framework` | `c#` | ✅ CÓ |
| `Spark-Streaming` | `Apache Spark` | Spark Streaming là module của Spark (biến thể định dạng của 'Spark Streaming') | `spark-streaming` | `apache-spark` | ✅ CÓ |
| `Aws Codepipeline` | `AWS` | CodePipeline là dịch vụ CI/CD của AWS (biến thể định dạng của 'AWS CodePipeline') | `aws-codepipeline` | `aws` | ✅ CÓ |
| `ANGULAR` | `JavaScript` | Angular chạy trên JavaScript runtime (biến thể định dạng của 'Angular') | `angular` | `javascript` | ✅ CÓ |
| `rOOM` | `Android` | Room là thư viện persistence của Android (biến thể định dạng của 'Room') | `android-room` | `android` | ✅ CÓ |
| `redux-thunk` | `Redux` | Redux Thunk là middleware của Redux (biến thể định dạng của 'Redux Thunk') | `redux-thunk` | `redux` | ✅ CÓ |
| `KOTLIN` | `Java` | Kotlin chạy trên JVM, tương tác với Java (biến thể định dạng của 'Kotlin') | `kotlin` | `java` | ✅ CÓ |
| `Amazon_EC2` | `AWS` | EC2 là dịch vụ compute của AWS (biến thể định dạng của 'Amazon EC2') | `amazon_ec2` | `aws` | ❌ KHÔNG |
| `Django_Channels` | `Django` | Channels là extension của Django (biến thể định dạng của 'Django Channels') | `django_channels` | `django` | ❌ KHÔNG |
| `WEBDRIVERIO` | `JavaScript` | WebdriverIO là test framework cho JavaScript (biến thể định dạng của 'WebdriverIO') | `webdriverio` | `javascript` | ✅ CÓ |
| `Redux_Thunk` | `Redux` | Redux Thunk là middleware của Redux (biến thể định dạng của 'Redux Thunk') | `redux_thunk` | `redux` | ❌ KHÔNG |
| `sTYLED cOMPONENTS` | `React` | Styled Components dùng cho React (biến thể định dạng của 'Styled Components') | `styled-components` | `reactjs` | ✅ CÓ |
| `Azure-Databricks` | `Apache Spark` | Azure Databricks chạy trên nền Spark (biến thể định dạng của 'Azure Databricks') | `azure-databricks` | `apache-spark` | ✅ CÓ |
| `qwik` | `JavaScript` | Qwik là framework JavaScript (biến thể định dạng của 'Qwik') | `qwik` | `javascript` | ✅ CÓ |
| `Backbone.Js` | `JavaScript` | JS framework (biến thể định dạng của 'Backbone.js') | `backbone.js` | `javascript` | ✅ CÓ |
| `sTREAMLIT` | `Python` | Python framework (biến thể định dạng của 'Streamlit') | `streamlit` | `python` | ✅ CÓ |
| `rECOIL` | `React` | Recoil là state library của React (biến thể định dạng của 'Recoil') | `recoil` | `reactjs` | ✅ CÓ |
| `VUEX` | `Vue.js` | Vuex là state management của Vue (biến thể định dạng của 'Vuex') | `vuex` | `vue.js` | ✅ CÓ |
| `bEAUTIFULsOUP` | `Python` | Python library (biến thể định dạng của 'BeautifulSoup') | `beautifulsoup` | `python` | ✅ CÓ |
| `nEXT.JS` | `JavaScript` | Next.js chạy trên JavaScript (biến thể định dạng của 'Next.js') | `next.js` | `javascript` | ✅ CÓ |
| `React-Query` | `React` | React Query là data-fetching library của React (biến thể định dạng của 'React Query') | `react-query` | `reactjs` | ✅ CÓ |
| `Asp.Net Core` | `C#` | ASP.NET Core viết bằng C# (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `c#` | ✅ CÓ |
| `spark streaming` | `Apache Spark` | Spark Streaming là module của Spark (biến thể định dạng của 'Spark Streaming') | `spark-streaming` | `apache-spark` | ✅ CÓ |
| `cloud sql` | `Google Cloud Platform` | Cloud SQL là dịch vụ database của GCP (biến thể định dạng của 'Cloud SQL') | `cloud-sql` | `gcp` | ✅ CÓ |
| `Amazon_Route_53` | `AWS` | Route 53 là dịch vụ DNS của AWS (biến thể định dạng của 'Amazon Route 53') | `amazon_route_53` | `aws` | ❌ KHÔNG |
| `Ember.Js` | `JavaScript` | JS framework (biến thể định dạng của 'Ember.js') | `ember.js` | `javascript` | ✅ CÓ |
| `SAP-HANA` | `SAP` | HANA là database platform của SAP (biến thể định dạng của 'SAP HANA') | `sap-hana` | `sap` | ✅ CÓ |
| `sPRING mvc` | `Spring` | Spring MVC là module của Spring (biến thể định dạng của 'Spring MVC') | `spring-mvc` | `spring` | ✅ CÓ |
| `grails` | `Java` | Grails chạy trên JVM (biến thể định dạng của 'Grails') | `grails` | `java` | ✅ CÓ |
| `eNTITY fRAMEWORK` | `C#` | EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework') | `entity-framework` | `c#` | ✅ CÓ |
| `BLAZOR WEBASSEMBLY` | `Blazor` | Blazor WASM là chế độ chạy của Blazor (biến thể định dạng của 'Blazor WebAssembly') | `blazor-webassembly` | `blazor` | ✅ CÓ |
| `web3.js` | `JavaScript` | Web3.js là thư viện JavaScript (biến thể định dạng của 'Web3.js') | `web3.js` | `javascript` | ✅ CÓ |
| `GITHUB` | `Git` | GitHub là dịch vụ hosting cho Git (biến thể định dạng của 'GitHub') | `github` | `git` | ✅ CÓ |
| `KUBERNETES-HELM` | `Kubernetes` | Helm là package manager của Kubernetes (biến thể định dạng của 'Kubernetes Helm') | `kubernetes-helm` | `kubernetes` | ✅ CÓ |
| `sinon.js` | `JavaScript` | Sinon là mocking library cho JavaScript (biến thể định dạng của 'Sinon.js') | `sinon.js` | `javascript` | ✅ CÓ |
| `JUNIT` | `Java` | JUnit là test framework cho Java (biến thể định dạng của 'JUnit') | `junit` | `java` | ✅ CÓ |
| `PUB/SUB` | `Google Cloud Platform` | Pub/Sub là dịch vụ messaging của GCP (biến thể định dạng của 'Pub/Sub') | `pub/sub` | `gcp` | ❌ KHÔNG |
| `Junit` | `Java` | JUnit là test framework cho Java (biến thể định dạng của 'JUnit') | `junit` | `java` | ✅ CÓ |
| `jEST` | `JavaScript` | Jest là test framework cho JavaScript (biến thể định dạng của 'Jest') | `jestjs` | `javascript` | ✅ CÓ |
| `Tanstack Query` | `React` | TanStack Query là data-fetching library của React (biến thể định dạng của 'TanStack Query') | `tanstack-query` | `reactjs` | ✅ CÓ |
| `azure-logic-apps` | `Azure` | Logic Apps là dịch vụ workflow của Azure (biến thể định dạng của 'Azure Logic Apps') | `azure-logic-apps` | `azure` | ✅ CÓ |
| `AWS GLUE` | `AWS` | Glue là dịch vụ ETL của AWS (biến thể định dạng của 'AWS Glue') | `aws-glue` | `aws` | ✅ CÓ |
| `spring-mvc` | `Spring` | Spring MVC là module của Spring (biến thể định dạng của 'Spring MVC') | `spring-mvc` | `spring` | ✅ CÓ |
| `AZURE-SERVICE-FABRIC` | `Azure` | Service Fabric là nền tảng microservices của Azure (biến thể định dạng của 'Azure Service Fabric') | `azure-service-fabric` | `azure` | ✅ CÓ |
| `CX_ORACLE` | `Oracle Database` | cx_Oracle là driver Python cho Oracle (biến thể định dạng của 'cx_Oracle') | `cx_oracle` | `oracle-database` | ❌ KHÔNG |
| `Npm` | `Node.js` | npm là package manager mặc định của Node.js (biến thể định dạng của 'npm') | `npm` | `node.js` | ✅ CÓ |
| `SOCKET.IO` | `Node.js` | Socket.IO thường chạy trên Node.js server (biến thể định dạng của 'Socket.IO') | `socket.io` | `node.js` | ✅ CÓ |
| `GRAILS` | `Java` | Grails chạy trên JVM (biến thể định dạng của 'Grails') | `grails` | `java` | ✅ CÓ |
| `MICRONAUT` | `Java` | Micronaut là framework Java (biến thể định dạng của 'Micronaut') | `micronaut` | `java` | ✅ CÓ |
| `azure-data-lake` | `Azure` | Data Lake là dịch vụ lưu trữ big data của Azure (biến thể định dạng của 'Azure Data Lake') | `azure-data-lake` | `azure` | ✅ CÓ |
| `RSPEC` | `Ruby` | RSpec là test framework của Ruby (biến thể định dạng của 'RSpec') | `rspec` | `ruby` | ✅ CÓ |
| `Amazon_Athena` | `AWS` | Athena là dịch vụ query serverless của AWS (biến thể định dạng của 'Amazon Athena') | `amazon_athena` | `aws` | ❌ KHÔNG |
| `TERRAFORM-PROVIDER-AWS` | `Terraform` | Provider là module mở rộng của Terraform (biến thể định dạng của 'Terraform Provider AWS') | `terraform-provider-aws` | `terraform` | ✅ CÓ |
| `aZURE bLOB sTORAGE` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage') | `azure-blob-storage` | `azure` | ✅ CÓ |
| `FRAMER-MOTION` | `React` | Framer Motion là animation library của React (biến thể định dạng của 'Framer Motion') | `framer-motion` | `reactjs` | ✅ CÓ |
| `aZURE cdn` | `Azure` | Azure CDN là dịch vụ CDN của Azure (biến thể định dạng của 'Azure CDN') | `azure-cdn` | `azure` | ✅ CÓ |
| `Smart_Contract` | `Solidity` | Smart contract trên Ethereum thường viết bằng Solidity (biến thể định dạng của 'Smart Contract') | `smart_contract` | `solidity` | ❌ KHÔNG |
| `React-Native` | `JavaScript` | React Native viết bằng JavaScript (biến thể định dạng của 'React Native') | `react-native` | `javascript` | ✅ CÓ |
| `Cloud_Functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Cloud Functions') | `cloud_functions` | `gcp` | ❌ KHÔNG |
| `Azure-Kubernetes-Service` | `Azure` | AKS là dịch vụ Kubernetes quản lý của Azure (biến thể định dạng của 'Azure Kubernetes Service') | `azure-kubernetes-service` | `azure` | ✅ CÓ |
| `AIOHTTP` | `Python` | Python library (biến thể định dạng của 'aiohttp') | `aiohttp` | `python` | ✅ CÓ |
| `sVELTE` | `JavaScript` | JS framework (biến thể định dạng của 'Svelte') | `svelte` | `javascript` | ✅ CÓ |
| `SYMFONY` | `PHP` | Symfony là framework PHP (biến thể định dạng của 'Symfony') | `symfony` | `php` | ✅ CÓ |
| `azure application insights` | `Azure` | Application Insights là dịch vụ APM của Azure (biến thể định dạng của 'Azure Application Insights') | `azure-application-insights` | `azure` | ✅ CÓ |
| `kAFKA sTREAMS` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams') | `apache-kafka-streams` | `apache-kafka` | ✅ CÓ |
| `AMAZON-ATHENA` | `AWS` | Athena là dịch vụ query serverless của AWS (biến thể định dạng của 'Amazon Athena') | `amazon-athena` | `aws` | ✅ CÓ |
| `Amazon-EKS` | `Kubernetes` | EKS là Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon-eks` | `kubernetes` | ✅ CÓ |
| `sWIFTui` | `Swift` | SwiftUI là UI framework của Swift (biến thể định dạng của 'SwiftUI') | `swiftui` | `swift` | ✅ CÓ |
| `NUMPY` | `Python` | Python library (biến thể định dạng của 'NumPy') | `numpy` | `python` | ✅ CÓ |
| `pillow` | `Python` | Python library (biến thể định dạng của 'Pillow') | `python-imaging-library` | `python` | ✅ CÓ |
| `aMAZON sns` | `AWS` | SNS là dịch vụ notification của AWS (biến thể định dạng của 'Amazon SNS') | `amazon-sns` | `aws` | ✅ CÓ |
| `pUB/sUB` | `Google Cloud Platform` | Pub/Sub là dịch vụ messaging của GCP (biến thể định dạng của 'Pub/Sub') | `pub/sub` | `gcp` | ❌ KHÔNG |
| `Amazon_S3` | `AWS` | S3 là dịch vụ storage của AWS (biến thể định dạng của 'Amazon S3') | `amazon_s3` | `aws` | ❌ KHÔNG |
| `d3.JS` | `JavaScript` | D3.js là thư viện visualization của JavaScript (biến thể định dạng của 'D3.js') | `d3.js` | `javascript` | ✅ CÓ |
| `GENSIM` | `Python` | Python library (biến thể định dạng của 'Gensim') | `gensim` | `python` | ✅ CÓ |
| `ssis` | `SQL Server` | SSIS là công cụ ETL của SQL Server (biến thể định dạng của 'SSIS') | `ssis` | `sql-server` | ❌ KHÔNG |
| `react hook form` | `React` | React Hook Form là form library của React (biến thể định dạng của 'React Hook Form') | `react-hook-form` | `reactjs` | ✅ CÓ |
| `azure-synapse-analytics` | `Azure` | Synapse Analytics là data warehouse của Azure (biến thể định dạng của 'Azure Synapse Analytics') | `azure-synapse-analytics` | `azure` | ✅ CÓ |
| `cODEiGNITER` | `PHP` | CodeIgniter là framework PHP (biến thể định dạng của 'CodeIgniter') | `codeigniter` | `php` | ✅ CÓ |
| `Kubernetes-Helm` | `Kubernetes` | Helm là package manager của Kubernetes (biến thể định dạng của 'Kubernetes Helm') | `kubernetes-helm` | `kubernetes` | ✅ CÓ |
| `aPP eNGINE` | `Google Cloud Platform` | App Engine là PaaS của GCP (biến thể định dạng của 'App Engine') | `app-engine` | `gcp` | ✅ CÓ |
| `aws-iam` | `AWS` | IAM là dịch vụ quản lý quyền của AWS (biến thể định dạng của 'AWS IAM') | `aws-iam` | `aws` | ✅ CÓ |
| `react` | `JavaScript` | JS library (biến thể định dạng của 'React') | `reactjs` | `javascript` | ✅ CÓ |
| `arcORE` | `Android` | ARCore thường dùng trên nền tảng Android (biến thể định dạng của 'ARCore') | `arcore` | `android` | ✅ CÓ |
| `GITLAB` | `Git` | GitLab là dịch vụ hosting cho Git (biến thể định dạng của 'GitLab') | `gitlab` | `git` | ✅ CÓ |
| `azure app service` | `Azure` | App Service là PaaS của Azure (biến thể định dạng của 'Azure App Service') | `azure-app-service` | `azure` | ✅ CÓ |
| `FLASK` | `Python` | Python framework (biến thể định dạng của 'Flask') | `flask` | `python` | ✅ CÓ |
| `scrapy` | `Python` | Python framework (biến thể định dạng của 'Scrapy') | `scrapy` | `python` | ✅ CÓ |
| `lOGSTASH` | `Elasticsearch` | Logstash thuộc ELK stack cùng Elasticsearch (biến thể định dạng của 'Logstash') | `logstash` | `elasticsearch` | ✅ CÓ |
| `Amazon-SQS` | `AWS` | SQS là dịch vụ message queue của AWS (biến thể định dạng của 'Amazon SQS') | `sqs` | `aws` | ✅ CÓ |
| `zustand` | `React` | Zustand là state library phổ biến cho React (biến thể định dạng của 'Zustand') | `zustand` | `reactjs` | ✅ CÓ |
| `REACT QUERY` | `React` | React Query là data-fetching library của React (biến thể định dạng của 'React Query') | `react-query` | `reactjs` | ✅ CÓ |
| `cloud-dataproc` | `Apache Spark` | Dataproc chạy Spark/Hadoop quản lý (biến thể định dạng của 'Cloud Dataproc') | `cloud-dataproc` | `apache-spark` | ✅ CÓ |
| `GODOT ENGINE` | `GDScript` | Godot Engine dùng ngôn ngữ script riêng GDScript (biến thể định dạng của 'Godot Engine') | `godot` | `gdscript` | ✅ CÓ |
| `azure databricks` | `Apache Spark` | Azure Databricks chạy trên nền Spark (biến thể định dạng của 'Azure Databricks') | `azure-databricks` | `apache-spark` | ✅ CÓ |
| `cocoa-touch` | `Objective-C` | Cocoa Touch gắn với Objective-C/iOS (biến thể định dạng của 'Cocoa Touch') | `cocoa-touch` | `objective-c` | ✅ CÓ |
| `aZURE mACHINE lEARNING` | `Azure` | Azure ML là dịch vụ ML của Azure (biến thể định dạng của 'Azure Machine Learning') | `azure-machine-learning` | `azure` | ✅ CÓ |
| `TURBOREPO` | `JavaScript` | Turborepo là monorepo tool cho hệ sinh thái JS (biến thể định dạng của 'Turborepo') | `turborepo` | `javascript` | ✅ CÓ |
| `azure-databricks` | `Azure` | Azure Databricks tích hợp Spark trên Azure (biến thể định dạng của 'Azure Databricks') | `azure-databricks` | `azure` | ✅ CÓ |
| `APOLLO CLIENT` | `GraphQL` | Apollo Client là client cho GraphQL (biến thể định dạng của 'Apollo Client') | `apollo-client` | `graphql` | ✅ CÓ |
| `elementor` | `WordPress` | Elementor là page builder plugin của WordPress (biến thể định dạng của 'Elementor') | `elementor` | `wordpress` | ✅ CÓ |
| `playwright` | `JavaScript` | Playwright là test framework cho JavaScript (biến thể định dạng của 'Playwright') | `playwright` | `javascript` | ✅ CÓ |
| `socket.io` | `Node.js` | Socket.IO thường chạy trên Node.js server (biến thể định dạng của 'Socket.IO') | `socket.io` | `node.js` | ✅ CÓ |
| `NEXT.JS` | `React` | Next.js là meta-framework của React (biến thể định dạng của 'Next.js') | `next.js` | `reactjs` | ✅ CÓ |
| `cOCOA tOUCH` | `Objective-C` | Cocoa Touch gắn với Objective-C/iOS (biến thể định dạng của 'Cocoa Touch') | `cocoa-touch` | `objective-c` | ✅ CÓ |
| `aZURE dATABRICKS` | `Azure` | Azure Databricks tích hợp Spark trên Azure (biến thể định dạng của 'Azure Databricks') | `azure-databricks` | `azure` | ✅ CÓ |
| `enzyme` | `React` | Enzyme là test utility cho React (biến thể định dạng của 'Enzyme') | `enzyme` | `reactjs` | ✅ CÓ |
| `passport.js` | `Node.js` | Passport là middleware auth của Node.js (biến thể định dạng của 'Passport.js') | `passport.js` | `node.js` | ✅ CÓ |
| `tRANSFORMERS` | `Python` | Hugging Face Transformers là Python library (biến thể định dạng của 'Transformers') | `transformers` | `python` | ✅ CÓ |
| `CHAKRA UI` | `React` | Chakra UI là component library cho React (biến thể định dạng của 'Chakra UI') | `chakra-ui` | `reactjs` | ✅ CÓ |
| `esp32` | `Embedded C` | Lập trình ESP32 thường dùng Embedded C (biến thể định dạng của 'ESP32') | `esp32` | `embedded-c` | ✅ CÓ |
| `vuex` | `Vue.js` | Vuex là state management của Vue (biến thể định dạng của 'Vuex') | `vuex` | `vue.js` | ✅ CÓ |
| `CLOUD COMPOSER` | `Airflow` | Cloud Composer là Airflow quản lý trên GCP (biến thể định dạng của 'Cloud Composer') | `cloud-composer` | `airflow` | ✅ CÓ |
| `styled-components` | `React` | Styled Components dùng cho React (biến thể định dạng của 'Styled Components') | `styled-components` | `reactjs` | ✅ CÓ |
| `react native` | `React` | React Native dựa trên React (biến thể định dạng của 'React Native') | `react-native` | `reactjs` | ✅ CÓ |
| `hARDHAT` | `Solidity` | Hardhat là framework phát triển Solidity (biến thể định dạng của 'Hardhat') | `hardhat` | `solidity` | ✅ CÓ |
| `CLOUD-FUNCTIONS` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `codeigniter` | `PHP` | CodeIgniter là framework PHP (biến thể định dạng của 'CodeIgniter') | `codeigniter` | `php` | ✅ CÓ |
| `azure-kubernetes-service` | `Azure` | AKS là dịch vụ Kubernetes quản lý của Azure (biến thể định dạng của 'Azure Kubernetes Service') | `azure-kubernetes-service` | `azure` | ✅ CÓ |
| `aws-codebuild` | `AWS` | CodeBuild là dịch vụ build của AWS (biến thể định dạng của 'AWS CodeBuild') | `aws-codebuild` | `aws` | ✅ CÓ |
| `aws gLUE` | `AWS` | Glue là dịch vụ ETL của AWS (biến thể định dạng của 'AWS Glue') | `aws-glue` | `aws` | ✅ CÓ |
| `sap abap` | `SAP` | ABAP là ngôn ngữ lập trình của SAP (biến thể định dạng của 'SAP ABAP') | `sap-abap` | `sap` | ✅ CÓ |
| `VUE.JS` | `JavaScript` | JS framework (biến thể định dạng của 'Vue.js') | `vue.js` | `javascript` | ✅ CÓ |
| `solidjs` | `JavaScript` | SolidJS là framework JavaScript (biến thể định dạng của 'SolidJS') | `solidjs` | `javascript` | ✅ CÓ |
| `NUXT.JS` | `Vue.js` | Nuxt.js là meta-framework của Vue (biến thể định dạng của 'Nuxt.js') | `nuxt.js` | `vue.js` | ✅ CÓ |
| `azure service bus` | `Azure` | Service Bus là dịch vụ message queue của Azure (biến thể định dạng của 'Azure Service Bus') | `azure-service-bus` | `azure` | ✅ CÓ |
| `aMAZON eks` | `AWS` | EKS là dịch vụ Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon-eks` | `aws` | ✅ CÓ |
| `AMAZON-RDS` | `AWS` | RDS là dịch vụ database của AWS (biến thể định dạng của 'Amazon RDS') | `amazon-rds` | `aws` | ✅ CÓ |
| `AMAZON-EKS` | `AWS` | EKS là dịch vụ Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon-eks` | `aws` | ✅ CÓ |
| `Node.Js` | `JavaScript` | Node.js chạy JavaScript phía server (biến thể định dạng của 'Node.js') | `node.js` | `javascript` | ✅ CÓ |
| `SUPERTEST` | `Node.js` | Supertest dùng để test HTTP server Node.js (biến thể định dạng của 'Supertest') | `supertest` | `node.js` | ✅ CÓ |
| `Passportjs` | `Node.js` | Passport là middleware auth của Node.js (biến thể định dạng của 'Passport.js') | `passport.js` | `node.js` | ✅ CÓ |
| `amazon vpc` | `AWS` | VPC là dịch vụ mạng ảo của AWS (biến thể định dạng của 'Amazon VPC') | `amazon-vpc` | `aws` | ✅ CÓ |
| `CLOUD-SPANNER` | `Google Cloud Platform` | Cloud Spanner là dịch vụ database phân tán của GCP (biến thể định dạng của 'Cloud Spanner') | `cloud-spanner` | `gcp` | ✅ CÓ |
| `sap fico` | `SAP` | FICO là module tài chính của SAP (biến thể định dạng của 'SAP FICO') | `sap-fico` | `sap` | ✅ CÓ |
| `Kafka_Streams` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams') | `kafka_streams` | `apache-kafka` | ❌ KHÔNG |
| `Blazor-WebAssembly` | `Blazor` | Blazor WASM là chế độ chạy của Blazor (biến thể định dạng của 'Blazor WebAssembly') | `blazor-webassembly` | `blazor` | ✅ CÓ |
| `kubernetes helm` | `Kubernetes` | Helm là package manager của Kubernetes (biến thể định dạng của 'Kubernetes Helm') | `kubernetes-helm` | `kubernetes` | ✅ CÓ |
| `xAMARIN` | `C#` | Xamarin viết bằng C# (biến thể định dạng của 'Xamarin') | `xamarin` | `c#` | ✅ CÓ |
| `gENSIM` | `Python` | Python library (biến thể định dạng của 'Gensim') | `gensim` | `python` | ✅ CÓ |
| `rEACT hOOK fORM` | `React` | React Hook Form là form library của React (biến thể định dạng của 'React Hook Form') | `react-hook-form` | `reactjs` | ✅ CÓ |
| `rEDUX sAGA` | `Redux` | Redux Saga là middleware của Redux (biến thể định dạng của 'Redux Saga') | `redux-saga` | `redux` | ✅ CÓ |
| `aZURE nOTIFICATION hUBS` | `Azure` | Notification Hubs là dịch vụ push notification của Azure (biến thể định dạng của 'Azure Notification Hubs') | `azure-notification-hubs` | `azure` | ✅ CÓ |
| `BEAUTIFULSOUP` | `Python` | Python library (biến thể định dạng của 'BeautifulSoup') | `beautifulsoup` | `python` | ✅ CÓ |
| `azure cdn` | `Azure` | Azure CDN là dịch vụ CDN của Azure (biến thể định dạng của 'Azure CDN') | `azure-cdn` | `azure` | ✅ CÓ |
| `CLOUD BIGTABLE` | `Google Cloud Platform` | Bigtable là dịch vụ NoSQL của GCP (biến thể định dạng của 'Cloud Bigtable') | `cloud-bigtable` | `gcp` | ✅ CÓ |
| `aMAZON aURORA` | `AWS` | Aurora là dịch vụ database của AWS (biến thể định dạng của 'Amazon Aurora') | `amazon-aurora` | `aws` | ✅ CÓ |
| `Gke` | `Google Cloud Platform` | GKE là dịch vụ Kubernetes quản lý của GCP (biến thể định dạng của 'GKE') | `gke` | `gcp` | ✅ CÓ |
| `Aws Secrets Manager` | `AWS` | Secrets Manager là dịch vụ quản lý secret của AWS (biến thể định dạng của 'AWS Secrets Manager') | `aws-secrets-manager` | `aws` | ✅ CÓ |
| `Azure_Key_Vault` | `Azure` | Key Vault là dịch vụ quản lý secret của Azure (biến thể định dạng của 'Azure Key Vault') | `azure_key_vault` | `azure` | ❌ KHÔNG |
| `Amazon Vpc` | `AWS` | VPC là dịch vụ mạng ảo của AWS (biến thể định dạng của 'Amazon VPC') | `amazon-vpc` | `aws` | ✅ CÓ |
| `azure-active-directory` | `Azure` | Azure AD là dịch vụ định danh của Azure (biến thể định dạng của 'Azure Active Directory') | `azure-active-directory` | `azure` | ✅ CÓ |
| `nestjs` | `TypeScript` | NestJS viết bằng TypeScript (biến thể định dạng của 'NestJS') | `nestjs` | `typescript` | ✅ CÓ |
| `VITE` | `JavaScript` | Build tool cho JS (biến thể định dạng của 'Vite') | `vite` | `javascript` | ✅ CÓ |
| `scipy` | `Python` | Python library (biến thể định dạng của 'SciPy') | `scipy` | `python` | ✅ CÓ |
| `Azure_App_Service` | `Azure` | App Service là PaaS của Azure (biến thể định dạng của 'Azure App Service') | `azure_app_service` | `azure` | ❌ KHÔNG |
| `Cloud-Spanner` | `Google Cloud Platform` | Cloud Spanner là dịch vụ database phân tán của GCP (biến thể định dạng của 'Cloud Spanner') | `cloud-spanner` | `gcp` | ✅ CÓ |
| `fIREBASE hOSTING` | `Firebase` | Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting') | `firebase hosting` | `firebase` | ❌ KHÔNG |
| `FIRESTORE` | `Google Cloud Platform` | Firestore là dịch vụ NoSQL của GCP (biến thể định dạng của 'Firestore') | `firestore` | `gcp` | ✅ CÓ |
| `DROPWIZARD` | `Java` | Dropwizard là framework Java (biến thể định dạng của 'Dropwizard') | `dropwizard` | `java` | ✅ CÓ |
| `ethers.js` | `JavaScript` | Ethers.js là thư viện JavaScript (biến thể định dạng của 'Ethers.js') | `ethers.js` | `javascript` | ✅ CÓ |
| `MATPLOTLIB` | `Python` | Python library (biến thể định dạng của 'Matplotlib') | `matplotlib` | `python` | ✅ CÓ |
| `Cloud-Composer` | `Airflow` | Cloud Composer là Airflow quản lý trên GCP (biến thể định dạng của 'Cloud Composer') | `cloud-composer` | `airflow` | ✅ CÓ |
| `Cloud_Spanner` | `Google Cloud Platform` | Cloud Spanner là dịch vụ database phân tán của GCP (biến thể định dạng của 'Cloud Spanner') | `cloud_spanner` | `gcp` | ❌ KHÔNG |
| `Amazon_API_Gateway` | `AWS` | API Gateway là dịch vụ quản lý API của AWS (biến thể định dạng của 'Amazon API Gateway') | `amazon_api_gateway` | `aws` | ❌ KHÔNG |
| `sCIpY` | `Python` | Python library (biến thể định dạng của 'SciPy') | `scipy` | `python` | ✅ CÓ |
| `Vertex-AI` | `Google Cloud Platform` | Vertex AI là dịch vụ ML của GCP (biến thể định dạng của 'Vertex AI') | `vertex-ai` | `gcp` | ✅ CÓ |
| `drupal` | `PHP` | Drupal là CMS viết bằng PHP (biến thể định dạng của 'Drupal') | `drupal` | `php` | ✅ CÓ |
| `jest` | `JavaScript` | Jest là test framework cho JavaScript (biến thể định dạng của 'Jest') | `jestjs` | `javascript` | ✅ CÓ |
| `bIGqUERY` | `Google Cloud Platform` | BigQuery là data warehouse dịch vụ của GCP (biến thể định dạng của 'BigQuery') | `bigquery` | `gcp` | ✅ CÓ |
| `Chai.Js` | `JavaScript` | Chai là assertion library cho JavaScript (biến thể định dạng của 'Chai.js') | `chai.js` | `javascript` | ✅ CÓ |
| `AZURE-SYNAPSE-ANALYTICS` | `Azure` | Synapse Analytics là data warehouse của Azure (biến thể định dạng của 'Azure Synapse Analytics') | `azure-synapse-analytics` | `azure` | ✅ CÓ |
| `tanstack query` | `React` | TanStack Query là data-fetching library của React (biến thể định dạng của 'TanStack Query') | `tanstack-query` | `reactjs` | ✅ CÓ |
| `aMAZON ec2` | `AWS` | EC2 là dịch vụ compute của AWS (biến thể định dạng của 'Amazon EC2') | `amazon-ec2` | `aws` | ✅ CÓ |
| `XAMARIN.ANDROID` | `Xamarin` | Xamarin.Android là module của Xamarin (biến thể định dạng của 'Xamarin.Android') | `xamarin.android` | `xamarin` | ✅ CÓ |
| `nESTjs` | `Node.js` | NestJS chạy trên Node.js (biến thể định dạng của 'NestJS') | `nestjs` | `node.js` | ✅ CÓ |
| `cloud-run` | `Google Cloud Platform` | Cloud Run là dịch vụ serverless container của GCP (biến thể định dạng của 'Cloud Run') | `cloud-run` | `gcp` | ✅ CÓ |
| `GRADIO` | `Python` | Gradio là Python library (biến thể định dạng của 'Gradio') | `gradio` | `python` | ✅ CÓ |
| `symfony` | `PHP` | Symfony là framework PHP (biến thể định dạng của 'Symfony') | `symfony` | `php` | ✅ CÓ |
| `rEACT nATIVE` | `React` | React Native dựa trên React (biến thể định dạng của 'React Native') | `react-native` | `reactjs` | ✅ CÓ |
| `Firebase-Hosting` | `Firebase` | Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting') | `firebase-hosting` | `firebase` | ❌ KHÔNG |
| `Azure_Blob_Storage` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage') | `azure_blob_storage` | `azure` | ❌ KHÔNG |
| `Spring-Boot` | `Java` | Spring Boot chạy trên Java (biến thể định dạng của 'Spring Boot') | `spring-boot` | `java` | ✅ CÓ |
| `amazon elasticache` | `AWS` | ElastiCache là dịch vụ cache của AWS (biến thể định dạng của 'Amazon ElastiCache') | `amazon-elasticache` | `aws` | ✅ CÓ |
| `Azure-Logic-Apps` | `Azure` | Logic Apps là dịch vụ workflow của Azure (biến thể định dạng của 'Azure Logic Apps') | `azure-logic-apps` | `azure` | ✅ CÓ |
| `ISTIO` | `Kubernetes` | Istio là service mesh chạy trên Kubernetes (biến thể định dạng của 'Istio') | `istio` | `kubernetes` | ✅ CÓ |
| `CLOUDFORMATION` | `AWS` | CloudFormation là IaC dịch vụ của AWS (biến thể định dạng của 'CloudFormation') | `cloudformation` | `aws` | ✅ CÓ |
| `Azure Devops` | `Azure` | Azure DevOps là bộ công cụ CI/CD của Azure (biến thể định dạng của 'Azure DevOps') | `azure-devops` | `azure` | ✅ CÓ |
| `AWS-KMS` | `AWS` | KMS là dịch vụ quản lý key mã hóa của AWS (biến thể định dạng của 'AWS KMS') | `aws-kms` | `aws` | ✅ CÓ |
| `webxr` | `JavaScript` | WebXR là API JavaScript cho AR/VR trên web (biến thể định dạng của 'WebXR') | `webxr` | `javascript` | ✅ CÓ |
| `ARDUINO` | `C++` | Arduino sketch dựa trên C++ (biến thể định dạng của 'Arduino') | `arduino` | `c++` | ✅ CÓ |
| `flask` | `Python` | Python framework (biến thể định dạng của 'Flask') | `flask` | `python` | ✅ CÓ |
| `AWS-SECRETS-MANAGER` | `AWS` | Secrets Manager là dịch vụ quản lý secret của AWS (biến thể định dạng của 'AWS Secrets Manager') | `aws-secrets-manager` | `aws` | ✅ CÓ |
| `STREAMLIT` | `Python` | Python framework (biến thể định dạng của 'Streamlit') | `streamlit` | `python` | ✅ CÓ |
| `tORNADO wEB` | `Python` | Python framework (biến thể định dạng của 'Tornado Web') | `tornado` | `python` | ✅ CÓ |
| `databricks` | `Apache Spark` | Databricks là nền tảng quản lý Spark (biến thể định dạng của 'Databricks') | `databricks` | `apache-spark` | ✅ CÓ |
| `Mqtt` | `IoT` | MQTT là giao thức truyền thông phổ biến trong IoT (biến thể định dạng của 'MQTT') | `mqtt` | `iot` | ✅ CÓ |
| `APOLLO-SERVER` | `Node.js` | Apollo Server chạy trên Node.js (biến thể định dạng của 'Apollo Server') | `apollo-server` | `node.js` | ✅ CÓ |
| `xgbOOST` | `Python` | Python library phổ biến qua API Python (biến thể định dạng của 'XGBoost') | `xgboost` | `python` | ✅ CÓ |
| `GOOGLE-DATA-STUDIO` | `Google Cloud Platform` | Data Studio tích hợp hệ sinh thái GCP (biến thể định dạng của 'Google Data Studio') | `google-data-studio` | `gcp` | ✅ CÓ |
| `Azure-Functions` | `Azure` | Azure Functions là dịch vụ serverless của Azure (biến thể định dạng của 'Azure Functions') | `azure-functions` | `azure` | ✅ CÓ |
| `sOCKET.io` | `Node.js` | Socket.IO thường chạy trên Node.js server (biến thể định dạng của 'Socket.IO') | `socket.io` | `node.js` | ✅ CÓ |
| `pandas` | `Python` | Python library (biến thể định dạng của 'Pandas') | `pandas` | `python` | ✅ CÓ |
| `Rspec` | `Ruby` | RSpec là test framework của Ruby (biến thể định dạng của 'RSpec') | `rspec` | `ruby` | ✅ CÓ |
| `Amazon-CloudFront` | `AWS` | CloudFront là dịch vụ CDN của AWS (biến thể định dạng của 'Amazon CloudFront') | `amazon-cloudfront` | `aws` | ✅ CÓ |
| `argocd` | `Kubernetes` | ArgoCD là công cụ GitOps triển khai lên Kubernetes (biến thể định dạng của 'ArgoCD') | `argocd` | `kubernetes` | ✅ CÓ |
| `maven` | `Java` | Maven là build tool cho Java (biến thể định dạng của 'Maven') | `maven` | `java` | ✅ CÓ |
| `kubernetes` | `Docker` | K8s thường điều phối container Docker (biến thể định dạng của 'Kubernetes') | `kubernetes` | `docker` | ✅ CÓ |
| `vERTEX ai` | `Google Cloud Platform` | Vertex AI là dịch vụ ML của GCP (biến thể định dạng của 'Vertex AI') | `vertex-ai` | `gcp` | ✅ CÓ |
| `Azure_Data_Factory` | `Azure` | Data Factory là dịch vụ ETL của Azure (biến thể định dạng của 'Azure Data Factory') | `azure_data_factory` | `azure` | ❌ KHÔNG |
| `jmeter` | `Java` | JMeter viết bằng Java (biến thể định dạng của 'JMeter') | `jmeter` | `java` | ✅ CÓ |
| `Azure_DNS` | `Azure` | Azure DNS là dịch vụ DNS của Azure (biến thể định dạng của 'Azure DNS') | `azure_dns` | `azure` | ❌ KHÔNG |
| `Azure-CDN` | `Azure` | Azure CDN là dịch vụ CDN của Azure (biến thể định dạng của 'Azure CDN') | `azure-cdn` | `azure` | ✅ CÓ |
| `AZURE-APP-SERVICE` | `Azure` | App Service là PaaS của Azure (biến thể định dạng của 'Azure App Service') | `azure-app-service` | `azure` | ✅ CÓ |
| `Spring-Security` | `Spring` | Spring Security là module của Spring (biến thể định dạng của 'Spring Security') | `spring-security` | `spring` | ✅ CÓ |
| `KIBANA` | `Elasticsearch` | Kibana dùng để visualize dữ liệu Elasticsearch (biến thể định dạng của 'Kibana') | `kibana` | `elasticsearch` | ✅ CÓ |
| `AZURE SERVICE BUS` | `Azure` | Service Bus là dịch vụ message queue của Azure (biến thể định dạng của 'Azure Service Bus') | `azure-service-bus` | `azure` | ✅ CÓ |
| `SWIFTUI` | `Swift` | SwiftUI là UI framework của Swift (biến thể định dạng của 'SwiftUI') | `swiftui` | `swift` | ✅ CÓ |
| `NPM` | `Node.js` | npm là package manager mặc định của Node.js (biến thể định dạng của 'npm') | `npm` | `node.js` | ✅ CÓ |
| `react-hook-form` | `React` | React Hook Form là form library của React (biến thể định dạng của 'React Hook Form') | `react-hook-form` | `reactjs` | ✅ CÓ |
| `rsPEC` | `Ruby` | RSpec là test framework của Ruby (biến thể định dạng của 'RSpec') | `rspec` | `ruby` | ✅ CÓ |
| `SEQUELIZE.JS` | `Node.js` | Sequelize là ORM cho Node.js (biến thể định dạng của 'Sequelize.js') | `sequelize.js` | `node.js` | ✅ CÓ |
| `typescript` | `JavaScript` | TypeScript biên dịch ra JavaScript (biến thể định dạng của 'TypeScript') | `typescript` | `javascript` | ✅ CÓ |
| `React-Hook-Form` | `React` | React Hook Form là form library của React (biến thể định dạng của 'React Hook Form') | `react-hook-form` | `reactjs` | ✅ CÓ |
| `CLOUD IAM` | `Google Cloud Platform` | Cloud IAM là dịch vụ quản lý quyền của GCP (biến thể định dạng của 'Cloud IAM') | `cloud-iam` | `gcp` | ✅ CÓ |
| `Salesforce-Apex` | `Salesforce` | Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex') | `apex` | `salesforce` | ❌ KHÔNG |
| `Azure_Logic_Apps` | `Azure` | Logic Apps là dịch vụ workflow của Azure (biến thể định dạng của 'Azure Logic Apps') | `azure_logic_apps` | `azure` | ❌ KHÔNG |
| `Bigquery` | `Google Cloud Platform` | BigQuery là data warehouse dịch vụ của GCP (biến thể định dạng của 'BigQuery') | `bigquery` | `gcp` | ✅ CÓ |
| `LOGSTASH` | `Elasticsearch` | Logstash thuộc ELK stack cùng Elasticsearch (biến thể định dạng của 'Logstash') | `logstash` | `elasticsearch` | ✅ CÓ |
| `Nuxtjs` | `Vue.js` | Nuxt.js là meta-framework của Vue (biến thể định dạng của 'Nuxt.js') | `nuxt.js` | `vue.js` | ✅ CÓ |
| `amazon-ec2` | `AWS` | EC2 là dịch vụ compute của AWS (biến thể định dạng của 'Amazon EC2') | `amazon-ec2` | `aws` | ✅ CÓ |
| `Framer_Motion` | `React` | Framer Motion là animation library của React (biến thể định dạng của 'Framer Motion') | `framer_motion` | `reactjs` | ❌ KHÔNG |
| `amazon athena` | `AWS` | Athena là dịch vụ query serverless của AWS (biến thể định dạng của 'Amazon Athena') | `amazon-athena` | `aws` | ✅ CÓ |
| `OKHTTP` | `Java` | OkHttp là HTTP client cho Java/Android (biến thể định dạng của 'OkHttp') | `okhttp` | `java` | ✅ CÓ |
| `sEQUELIZE.JS` | `Node.js` | Sequelize là ORM cho Node.js (biến thể định dạng của 'Sequelize.js') | `sequelize.js` | `node.js` | ✅ CÓ |
| `CLOUD DATAPROC` | `Google Cloud Platform` | Dataproc là dịch vụ Spark/Hadoop quản lý của GCP (biến thể định dạng của 'Cloud Dataproc') | `cloud-dataproc` | `gcp` | ✅ CÓ |
| `NX MONOREPO` | `JavaScript` | Nx là monorepo tool cho hệ sinh thái JS (biến thể định dạng của 'Nx Monorepo') | `nx-monorepo` | `javascript` | ✅ CÓ |
| `sPRING sECURITY` | `Spring` | Spring Security là module của Spring (biến thể định dạng của 'Spring Security') | `spring-security` | `spring` | ✅ CÓ |
| `winforms` | `C#` | WinForms là UI framework của .NET/C# (biến thể định dạng của 'WinForms') | `winforms` | `c#` | ✅ CÓ |
| `AZURE KUBERNETES SERVICE` | `Azure` | AKS là dịch vụ Kubernetes quản lý của Azure (biến thể định dạng của 'Azure Kubernetes Service') | `azure-kubernetes-service` | `azure` | ✅ CÓ |
| `amazon-s3` | `AWS` | S3 là dịch vụ storage của AWS (biến thể định dạng của 'Amazon S3') | `amazon-s3` | `aws` | ✅ CÓ |
| `Azure-Cognitive-Services` | `Azure` | Cognitive Services là dịch vụ AI của Azure (biến thể định dạng của 'Azure Cognitive Services') | `azure-cognitive-services` | `azure` | ✅ CÓ |
| `gITlAB` | `Git` | GitLab là dịch vụ hosting cho Git (biến thể định dạng của 'GitLab') | `gitlab` | `git` | ✅ CÓ |
| `arcore` | `Android` | ARCore thường dùng trên nền tảng Android (biến thể định dạng của 'ARCore') | `arcore` | `android` | ✅ CÓ |
| `K6` | `JavaScript` | k6 dùng script JavaScript để load test (biến thể định dạng của 'k6') | `k6` | `javascript` | ✅ CÓ |
| `spark-streaming` | `Apache Spark` | Spark Streaming là module của Spark (biến thể định dạng của 'Spark Streaming') | `spark-streaming` | `apache-spark` | ✅ CÓ |
| `Nestjs` | `Node.js` | NestJS chạy trên Node.js (biến thể định dạng của 'NestJS') | `nestjs` | `node.js` | ✅ CÓ |
| `amazon api gateway` | `AWS` | API Gateway là dịch vụ quản lý API của AWS (biến thể định dạng của 'Amazon API Gateway') | `amazon-api-gateway` | `aws` | ✅ CÓ |
| `xgboost` | `Python` | Python library phổ biến qua API Python (biến thể định dạng của 'XGBoost') | `xgboost` | `python` | ✅ CÓ |
| `smart-contract` | `Solidity` | Smart contract trên Ethereum thường viết bằng Solidity (biến thể định dạng của 'Smart Contract') | `smart-contracts` | `solidity` | ✅ CÓ |
| `AWS_Lambda` | `AWS` | Lambda là dịch vụ serverless của AWS (biến thể định dạng của 'AWS Lambda') | `aws_lambda` | `aws` | ❌ KHÔNG |
| `sqlaLCHEMY` | `Python` | Python ORM (biến thể định dạng của 'SQLAlchemy') | `sqlalchemy` | `python` | ✅ CÓ |
| `kibana` | `Elasticsearch` | Kibana dùng để visualize dữ liệu Elasticsearch (biến thể định dạng của 'Kibana') | `kibana` | `elasticsearch` | ✅ CÓ |
| `Entity_Framework` | `C#` | EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework') | `entity_framework` | `c#` | ❌ KHÔNG |
| `AWS SECRETS MANAGER` | `AWS` | Secrets Manager là dịch vụ quản lý secret của AWS (biến thể định dạng của 'AWS Secrets Manager') | `aws-secrets-manager` | `aws` | ✅ CÓ |
| `aZURE sql dATABASE` | `Azure` | Azure SQL Database là dịch vụ database của Azure (biến thể định dạng của 'Azure SQL Database') | `azure-sql-database` | `azure` | ✅ CÓ |
| `DRUPAL` | `PHP` | Drupal là CMS viết bằng PHP (biến thể định dạng của 'Drupal') | `drupal` | `php` | ✅ CÓ |
| `Nodejs` | `JavaScript` | Node.js chạy JavaScript phía server (biến thể định dạng của 'Node.js') | `node.js` | `javascript` | ✅ CÓ |
| `SPRING SECURITY` | `Spring` | Spring Security là module của Spring (biến thể định dạng của 'Spring Security') | `spring-security` | `spring` | ✅ CÓ |
| `Amazon Ec2` | `AWS` | EC2 là dịch vụ compute của AWS (biến thể định dạng của 'Amazon EC2') | `amazon-ec2` | `aws` | ✅ CÓ |
| `Pytorch` | `Python` | Python library (biến thể định dạng của 'PyTorch') | `pytorch` | `python` | ✅ CÓ |
| `azure-blob-storage` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage') | `azure-blob-storage` | `azure` | ✅ CÓ |
| `AZURE-COGNITIVE-SERVICES` | `Azure` | Cognitive Services là dịch vụ AI của Azure (biến thể định dạng của 'Azure Cognitive Services') | `azure-cognitive-services` | `azure` | ✅ CÓ |
| `pymongo` | `MongoDB` | PyMongo là driver Python cho MongoDB (biến thể định dạng của 'PyMongo') | `pymongo` | `mongodb` | ✅ CÓ |
| `aZURE sYNAPSE aNALYTICS` | `Azure` | Synapse Analytics là data warehouse của Azure (biến thể định dạng của 'Azure Synapse Analytics') | `azure-synapse-analytics` | `azure` | ✅ CÓ |
| `cloud-functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `SQLALCHEMY` | `Python` | Python ORM (biến thể định dạng của 'SQLAlchemy') | `sqlalchemy` | `python` | ✅ CÓ |
| `Cloud-Monitoring` | `Google Cloud Platform` | Cloud Monitoring là dịch vụ monitoring của GCP (biến thể định dạng của 'Cloud Monitoring') | `cloud-monitoring` | `gcp` | ✅ CÓ |
| `eslint` | `JavaScript` | ESLint là linter cho JavaScript (biến thể định dạng của 'ESLint') | `eslint` | `javascript` | ✅ CÓ |
| `yarn` | `Node.js` | Yarn là package manager của Node.js (biến thể định dạng của 'Yarn') | `yarn` | `node.js` | ✅ CÓ |
| `firebase-hosting` | `Firebase` | Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting') | `firebase-hosting` | `firebase` | ❌ KHÔNG |
| `fRAMER mOTION` | `React` | Framer Motion là animation library của React (biến thể định dạng của 'Framer Motion') | `framer-motion` | `reactjs` | ✅ CÓ |
| `WEB3.JS` | `JavaScript` | Web3.js là thư viện JavaScript (biến thể định dạng của 'Web3.js') | `web3.js` | `javascript` | ✅ CÓ |
| `AMAZON EMR` | `AWS` | EMR là dịch vụ big data của AWS (biến thể định dạng của 'Amazon EMR') | `amazon-emr` | `aws` | ✅ CÓ |
| `REACT-NATIVE` | `React` | React Native dựa trên React (biến thể định dạng của 'React Native') | `react-native` | `reactjs` | ✅ CÓ |
| `Docker_Compose` | `Docker` | Docker Compose là tính năng của Docker (biến thể định dạng của 'Docker Compose') | `docker_compose` | `docker` | ❌ KHÔNG |
| `Aws Kms` | `AWS` | KMS là dịch vụ quản lý key mã hóa của AWS (biến thể định dạng của 'AWS KMS') | `aws-kms` | `aws` | ✅ CÓ |
| `core data` | `Swift` | Core Data là framework persistence của Apple dùng với Swift (biến thể định dạng của 'Core Data') | `core-data` | `swift` | ✅ CÓ |
| `firestore` | `Google Cloud Platform` | Firestore là dịch vụ NoSQL của GCP (biến thể định dạng của 'Firestore') | `firestore` | `gcp` | ✅ CÓ |
| `Django_REST_Framework` | `Django` | DRF là extension của Django (biến thể định dạng của 'Django REST Framework') | `django_rest_framework` | `django` | ❌ KHÔNG |
| `logstash` | `Elasticsearch` | Logstash thuộc ELK stack cùng Elasticsearch (biến thể định dạng của 'Logstash') | `logstash` | `elasticsearch` | ✅ CÓ |
| `PSYCOPG2` | `PostgreSQL` | psycopg2 là driver Python cho PostgreSQL (biến thể định dạng của 'psycopg2') | `psycopg2` | `postgresql` | ✅ CÓ |
| `aZURE dEVoPS` | `Azure` | Azure DevOps là bộ công cụ CI/CD của Azure (biến thể định dạng của 'Azure DevOps') | `azure-devops` | `azure` | ✅ CÓ |
| `room` | `Android` | Room là thư viện persistence của Android (biến thể định dạng của 'Room') | `android-room` | `android` | ✅ CÓ |
| `rEACT` | `JavaScript` | JS library (biến thể định dạng của 'React') | `reactjs` | `javascript` | ✅ CÓ |
| `cassandra` | `Java` | Cassandra viết bằng Java (biến thể định dạng của 'Cassandra') | `cassandra` | `java` | ✅ CÓ |
| `Winforms` | `C#` | WinForms là UI framework của .NET/C# (biến thể định dạng của 'WinForms') | `winforms` | `c#` | ✅ CÓ |
| `xamarin.ios` | `Xamarin` | Xamarin.iOS là module của Xamarin (biến thể định dạng của 'Xamarin.iOS') | `xamarin.ios` | `xamarin` | ✅ CÓ |
| `kubernetes-helm` | `Kubernetes` | Helm là package manager của Kubernetes (biến thể định dạng của 'Kubernetes Helm') | `kubernetes-helm` | `kubernetes` | ✅ CÓ |
| `Azure_Functions` | `Azure` | Azure Functions là dịch vụ serverless của Azure (biến thể định dạng của 'Azure Functions') | `azure_functions` | `azure` | ❌ KHÔNG |
| `xAMARIN.aNDROID` | `Xamarin` | Xamarin.Android là module của Xamarin (biến thể định dạng của 'Xamarin.Android') | `xamarin.android` | `xamarin` | ✅ CÓ |
| `compute engine` | `Google Cloud Platform` | Compute Engine là dịch vụ compute của GCP (biến thể định dạng của 'Compute Engine') | `compute-engine` | `gcp` | ✅ CÓ |
| `recoil` | `React` | Recoil là state library của React (biến thể định dạng của 'Recoil') | `recoil` | `reactjs` | ✅ CÓ |
| `APOLLO-CLIENT` | `GraphQL` | Apollo Client là client cho GraphQL (biến thể định dạng của 'Apollo Client') | `apollo-client` | `graphql` | ✅ CÓ |
| `AMAZON-CLOUDFRONT` | `AWS` | CloudFront là dịch vụ CDN của AWS (biến thể định dạng của 'Amazon CloudFront') | `amazon-cloudfront` | `aws` | ✅ CÓ |
| `Azure Cosmos Db` | `Azure` | Cosmos DB là dịch vụ NoSQL của Azure (biến thể định dạng của 'Azure Cosmos DB') | `azure-cosmos-db` | `azure` | ✅ CÓ |
| `Amazon Ecs` | `AWS` | ECS là dịch vụ container orchestration của AWS (biến thể định dạng của 'Amazon ECS') | `amazon-ecs` | `aws` | ✅ CÓ |
| `React_Query` | `React` | React Query là data-fetching library của React (biến thể định dạng của 'React Query') | `react_query` | `reactjs` | ❌ KHÔNG |
| `Arcore` | `Android` | ARCore thường dùng trên nền tảng Android (biến thể định dạng của 'ARCore') | `arcore` | `android` | ✅ CÓ |
| `KUBERNETES` | `Docker` | K8s thường điều phối container Docker (biến thể định dạng của 'Kubernetes') | `kubernetes` | `docker` | ✅ CÓ |
| `Terraform-Provider-AWS` | `Terraform` | Provider là module mở rộng của Terraform (biến thể định dạng của 'Terraform Provider AWS') | `terraform-provider-aws` | `terraform` | ✅ CÓ |
| `kUBERNETES hELM` | `Kubernetes` | Helm là package manager của Kubernetes (biến thể định dạng của 'Kubernetes Helm') | `kubernetes-helm` | `kubernetes` | ✅ CÓ |
| `Emberjs` | `JavaScript` | JS framework (biến thể định dạng của 'Ember.js') | `ember.js` | `javascript` | ✅ CÓ |
| `Ruby_on_Rails` | `Ruby` | Rails là framework của Ruby (biến thể định dạng của 'Ruby on Rails') | `ruby_on_rails` | `ruby` | ❌ KHÔNG |
| `AZURE BLOB STORAGE` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage') | `azure-blob-storage` | `azure` | ✅ CÓ |
| `azure-functions` | `Azure` | Azure Functions là dịch vụ serverless của Azure (biến thể định dạng của 'Azure Functions') | `azure-functions` | `azure` | ✅ CÓ |
| `viewmodel` | `Android` | ViewModel là thành phần kiến trúc của Android (biến thể định dạng của 'ViewModel') | `viewmodel` | `android` | ✅ CÓ |
| `cLOUD iam` | `Google Cloud Platform` | Cloud IAM là dịch vụ quản lý quyền của GCP (biến thể định dạng của 'Cloud IAM') | `cloud-iam` | `gcp` | ✅ CÓ |
| `fREErtos` | `Embedded C` | FreeRTOS thường viết bằng Embedded C (biến thể định dạng của 'FreeRTOS') | `freertos` | `embedded-c` | ✅ CÓ |
| `cloudformation` | `AWS` | CloudFormation là IaC dịch vụ của AWS (biến thể định dạng của 'CloudFormation') | `cloudformation` | `aws` | ✅ CÓ |
| `azure-dns` | `Azure` | Azure DNS là dịch vụ DNS của Azure (biến thể định dạng của 'Azure DNS') | `azure-dns` | `azure` | ✅ CÓ |
| `xAMARIN.fORMS` | `Xamarin` | Xamarin.Forms là module của Xamarin (biến thể định dạng của 'Xamarin.Forms') | `xamarin.forms` | `xamarin` | ✅ CÓ |
| `ASP.NET-MVC` | `ASP.NET` | ASP.NET MVC là module của ASP.NET (biến thể định dạng của 'ASP.NET MVC') | `asp.net-mvc` | `asp.net` | ✅ CÓ |
| `AWS LAMBDA` | `AWS` | Lambda là dịch vụ serverless của AWS (biến thể định dạng của 'AWS Lambda') | `aws-lambda` | `aws` | ✅ CÓ |
| `Chakra_UI` | `React` | Chakra UI là component library cho React (biến thể định dạng của 'Chakra UI') | `chakra_ui` | `reactjs` | ❌ KHÔNG |
| `eXPRESS` | `Node.js` | Express chạy trên Node.js (biến thể định dạng của 'Express') | `express` | `node.js` | ✅ CÓ |
| `oKhTTP` | `Java` | OkHttp là HTTP client cho Java/Android (biến thể định dạng của 'OkHttp') | `okhttp` | `java` | ✅ CÓ |
| `LIGHTGBM` | `Python` | Python library phổ biến qua API Python (biến thể định dạng của 'LightGBM') | `lightgbm` | `python` | ✅ CÓ |
| `cx_oracle` | `Oracle Database` | cx_Oracle là driver Python cho Oracle (biến thể định dạng của 'cx_Oracle') | `cx_oracle` | `oracle-database` | ❌ KHÔNG |
| `entity framework` | `C#` | EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework') | `entity-framework` | `c#` | ✅ CÓ |
| `swiftui` | `Swift` | SwiftUI là UI framework của Swift (biến thể định dạng của 'SwiftUI') | `swiftui` | `swift` | ✅ CÓ |
| `FORMIK` | `React` | Formik là form library của React (biến thể định dạng của 'Formik') | `formik` | `reactjs` | ✅ CÓ |
| `spring mvc` | `Spring` | Spring MVC là module của Spring (biến thể định dạng của 'Spring MVC') | `spring-mvc` | `spring` | ✅ CÓ |
| `aws-glue` | `AWS` | Glue là dịch vụ ETL của AWS (biến thể định dạng của 'AWS Glue') | `aws-glue` | `aws` | ✅ CÓ |
| `SCRAPY` | `Python` | Python framework (biến thể định dạng của 'Scrapy') | `scrapy` | `python` | ✅ CÓ |
| `Apollo_Server` | `Node.js` | Apollo Server chạy trên Node.js (biến thể định dạng của 'Apollo Server') | `apollo_server` | `node.js` | ❌ KHÔNG |
| `vITEST` | `JavaScript` | Vitest là test framework cho JavaScript/Vite (biến thể định dạng của 'Vitest') | `vitest` | `javascript` | ✅ CÓ |
| `Esp32` | `Embedded C` | Lập trình ESP32 thường dùng Embedded C (biến thể định dạng của 'ESP32') | `esp32` | `embedded-c` | ✅ CÓ |
| `YARN` | `Node.js` | Yarn là package manager của Node.js (biến thể định dạng của 'Yarn') | `yarn` | `node.js` | ✅ CÓ |
| `Amazon Eks` | `Kubernetes` | EKS là Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon-eks` | `kubernetes` | ✅ CÓ |
| `kafka-streams` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams') | `apache-kafka-streams` | `apache-kafka` | ✅ CÓ |
| `quarkus` | `Java` | Quarkus là framework Java (biến thể định dạng của 'Quarkus') | `quarkus` | `java` | ✅ CÓ |
| `WEBXR` | `JavaScript` | WebXR là API JavaScript cho AR/VR trên web (biến thể định dạng của 'WebXR') | `webxr` | `javascript` | ✅ CÓ |
| `django rest framework` | `Django` | DRF là extension của Django (biến thể định dạng của 'Django REST Framework') | `django-rest-framework` | `django` | ✅ CÓ |
| `Entity-Framework` | `C#` | EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework') | `entity-framework` | `c#` | ✅ CÓ |
| `PYTORCH` | `Python` | Python library (biến thể định dạng của 'PyTorch') | `pytorch` | `python` | ✅ CÓ |
| `express` | `Node.js` | Express chạy trên Node.js (biến thể định dạng của 'Express') | `express` | `node.js` | ✅ CÓ |
| `Azure_Machine_Learning` | `Azure` | Azure ML là dịch vụ ML của Azure (biến thể định dạng của 'Azure Machine Learning') | `azure_machine_learning` | `azure` | ❌ KHÔNG |
| `sUPERTEST` | `Node.js` | Supertest dùng để test HTTP server Node.js (biến thể định dạng của 'Supertest') | `supertest` | `node.js` | ✅ CÓ |
| `Nltk` | `Python` | Python library (biến thể định dạng của 'NLTK') | `nltk` | `python` | ✅ CÓ |
| `django-channels` | `Django` | Channels là extension của Django (biến thể định dạng của 'Django Channels') | `django-channels` | `django` | ✅ CÓ |
| `remix` | `React` | Remix là meta-framework của React (biến thể định dạng của 'Remix') | `remix` | `reactjs` | ✅ CÓ |
| `SAP_ABAP` | `SAP` | ABAP là ngôn ngữ lập trình của SAP (biến thể định dạng của 'SAP ABAP') | `sap_abap` | `sap` | ❌ KHÔNG |
| `CLOUD STORAGE` | `Google Cloud Platform` | Cloud Storage là dịch vụ lưu trữ của GCP (biến thể định dạng của 'Cloud Storage') | `cloud-storage` | `gcp` | ✅ CÓ |
| `TESTCONTAINERS` | `Docker` | Testcontainers chạy test bằng container Docker (biến thể định dạng của 'Testcontainers') | `testcontainers` | `docker` | ✅ CÓ |
| `DJANGO-REST-FRAMEWORK` | `Django` | DRF là extension của Django (biến thể định dạng của 'Django REST Framework') | `django-rest-framework` | `django` | ✅ CÓ |
| `Sinon.Js` | `JavaScript` | Sinon là mocking library cho JavaScript (biến thể định dạng của 'Sinon.js') | `sinon.js` | `javascript` | ✅ CÓ |
| `github` | `Git` | GitHub là dịch vụ hosting cho Git (biến thể định dạng của 'GitHub') | `github` | `git` | ✅ CÓ |
| `fIRESTORE` | `Google Cloud Platform` | Firestore là dịch vụ NoSQL của GCP (biến thể định dạng của 'Firestore') | `firestore` | `gcp` | ✅ CÓ |
| `Argocd` | `Kubernetes` | ArgoCD là công cụ GitOps triển khai lên Kubernetes (biến thể định dạng của 'ArgoCD') | `argocd` | `kubernetes` | ✅ CÓ |
| `xamarin.android` | `Xamarin` | Xamarin.Android là module của Xamarin (biến thể định dạng của 'Xamarin.Android') | `xamarin.android` | `xamarin` | ✅ CÓ |
| `AZURE-CDN` | `Azure` | Azure CDN là dịch vụ CDN của Azure (biến thể định dạng của 'Azure CDN') | `azure-cdn` | `azure` | ✅ CÓ |
| `rASPBERRY pI` | `Linux` | Raspberry Pi thường chạy hệ điều hành Linux (biến thể định dạng của 'Raspberry Pi') | `raspberry-pi` | `linux` | ✅ CÓ |
| `KAFKA-STREAMS` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams') | `apache-kafka-streams` | `apache-kafka` | ✅ CÓ |
| `amazon sns` | `AWS` | SNS là dịch vụ notification của AWS (biến thể định dạng của 'Amazon SNS') | `amazon-sns` | `aws` | ✅ CÓ |
| `Cloud_Build` | `Google Cloud Platform` | Cloud Build là dịch vụ CI/CD của GCP (biến thể định dạng của 'Cloud Build') | `cloud_build` | `gcp` | ❌ KHÔNG |
| `Azure_Data_Lake` | `Azure` | Data Lake là dịch vụ lưu trữ big data của Azure (biến thể định dạng của 'Azure Data Lake') | `azure_data_lake` | `azure` | ❌ KHÔNG |
| `RUBY-ON-RAILS` | `Ruby` | Rails là framework của Ruby (biến thể định dạng của 'Ruby on Rails') | `ruby-on-rails` | `ruby` | ✅ CÓ |
| `KUBECTL` | `Kubernetes` | kubectl là CLI điều khiển Kubernetes (biến thể định dạng của 'Kubectl') | `kubectl` | `kubernetes` | ✅ CÓ |
| `AWS-STEP-FUNCTIONS` | `AWS` | Step Functions là dịch vụ workflow của AWS (biến thể định dạng của 'AWS Step Functions') | `aws-step-functions` | `aws` | ✅ CÓ |
| `AZURE-MONITOR` | `Azure` | Azure Monitor là dịch vụ monitoring của Azure (biến thể định dạng của 'Azure Monitor') | `azure-monitor` | `azure` | ✅ CÓ |
| `azure-virtual-machines` | `Azure` | VM là dịch vụ compute của Azure (biến thể định dạng của 'Azure Virtual Machines') | `azure-virtual-machines` | `azure` | ✅ CÓ |
| `AZURE FUNCTIONS` | `Azure` | Azure Functions là dịch vụ serverless của Azure (biến thể định dạng của 'Azure Functions') | `azure-functions` | `azure` | ✅ CÓ |
| `AMAZON-SQS` | `AWS` | SQS là dịch vụ message queue của AWS (biến thể định dạng của 'Amazon SQS') | `sqs` | `aws` | ✅ CÓ |
| `SALESFORCE APEX` | `Salesforce` | Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex') | `apex` | `salesforce` | ❌ KHÔNG |
| `azure-service-fabric` | `Azure` | Service Fabric là nền tảng microservices của Azure (biến thể định dạng của 'Azure Service Fabric') | `azure-service-fabric` | `azure` | ✅ CÓ |
| `PREACT` | `React` | Preact là bản thay thế nhẹ của React (biến thể định dạng của 'Preact') | `preact` | `reactjs` | ✅ CÓ |
| `ktor` | `Kotlin` | Ktor là framework web viết bằng Kotlin (biến thể định dạng của 'Ktor') | `ktor` | `kotlin` | ✅ CÓ |
| `rEMIX` | `React` | Remix là meta-framework của React (biến thể định dạng của 'Remix') | `remix` | `reactjs` | ✅ CÓ |
| `AWS_Fargate` | `AWS` | Fargate là dịch vụ serverless container của AWS (biến thể định dạng của 'AWS Fargate') | `aws_fargate` | `aws` | ❌ KHÔNG |
| `aMAZON rOUTE 53` | `AWS` | Route 53 là dịch vụ DNS của AWS (biến thể định dạng của 'Amazon Route 53') | `amazon-route-53` | `aws` | ✅ CÓ |
| `aMAZON ecs` | `AWS` | ECS là dịch vụ container orchestration của AWS (biến thể định dạng của 'Amazon ECS') | `amazon-ecs` | `aws` | ✅ CÓ |
| `amazon-elasticache` | `AWS` | ElastiCache là dịch vụ cache của AWS (biến thể định dạng của 'Amazon ElastiCache') | `amazon-elasticache` | `aws` | ✅ CÓ |
| `bOTTLE` | `Python` | Python framework (biến thể định dạng của 'Bottle') | `bottle` | `python` | ✅ CÓ |
| `vercel` | `Next.js` | Vercel là nền tảng deploy chính thức của Next.js (biến thể định dạng của 'Vercel') | `vercel` | `next.js` | ✅ CÓ |
| `prisma` | `Node.js` | Prisma là ORM phổ biến cho Node.js/TypeScript (biến thể định dạng của 'Prisma') | `prisma` | `node.js` | ✅ CÓ |
| `wEB3.JS` | `JavaScript` | Web3.js là thư viện JavaScript (biến thể định dạng của 'Web3.js') | `web3.js` | `javascript` | ✅ CÓ |
| `cloud-spanner` | `Google Cloud Platform` | Cloud Spanner là dịch vụ database phân tán của GCP (biến thể định dạng của 'Cloud Spanner') | `cloud-spanner` | `gcp` | ✅ CÓ |
| `Cloud_Dataproc` | `Apache Spark` | Dataproc chạy Spark/Hadoop quản lý (biến thể định dạng của 'Cloud Dataproc') | `cloud_dataproc` | `apache-spark` | ❌ KHÔNG |
| `entity-framework` | `C#` | EF là ORM cho .NET/C# (biến thể định dạng của 'Entity Framework') | `entity-framework` | `c#` | ✅ CÓ |
| `mOCKITO` | `Java` | Mockito là mocking framework cho Java (biến thể định dạng của 'Mockito') | `mockito` | `java` | ✅ CÓ |
| `Scikit learn` | `Python` | Python library (biến thể định dạng của 'Scikit-learn') | `scikit-learn` | `python` | ✅ CÓ |
| `backbone.js` | `JavaScript` | JS framework (biến thể định dạng của 'Backbone.js') | `backbone.js` | `javascript` | ✅ CÓ |
| `kubectl` | `Kubernetes` | kubectl là CLI điều khiển Kubernetes (biến thể định dạng của 'Kubectl') | `kubectl` | `kubernetes` | ✅ CÓ |
| `SOLIDJS` | `JavaScript` | SolidJS là framework JavaScript (biến thể định dạng của 'SolidJS') | `solidjs` | `javascript` | ✅ CÓ |
| `Amazon_Kinesis` | `AWS` | Kinesis là dịch vụ streaming của AWS (biến thể định dạng của 'Amazon Kinesis') | `amazon_kinesis` | `aws` | ❌ KHÔNG |
| `app-engine` | `Google Cloud Platform` | App Engine là PaaS của GCP (biến thể định dạng của 'App Engine') | `app-engine` | `gcp` | ✅ CÓ |
| `aZURE sERVICE bUS` | `Azure` | Service Bus là dịch vụ message queue của Azure (biến thể định dạng của 'Azure Service Bus') | `azure-service-bus` | `azure` | ✅ CÓ |
| `vUE.JS` | `JavaScript` | JS framework (biến thể định dạng của 'Vue.js') | `vue.js` | `javascript` | ✅ CÓ |
| `blazor-webassembly` | `Blazor` | Blazor WASM là chế độ chạy của Blazor (biến thể định dạng của 'Blazor WebAssembly') | `blazor-webassembly` | `blazor` | ✅ CÓ |
| `lightgbm` | `Python` | Python library phổ biến qua API Python (biến thể định dạng của 'LightGBM') | `lightgbm` | `python` | ✅ CÓ |
| `styled components` | `React` | Styled Components dùng cho React (biến thể định dạng của 'Styled Components') | `styled-components` | `reactjs` | ✅ CÓ |
| `NODE.JS` | `JavaScript` | Node.js chạy JavaScript phía server (biến thể định dạng của 'Node.js') | `node.js` | `javascript` | ✅ CÓ |
| `vIEWmODEL` | `Android` | ViewModel là thành phần kiến trúc của Android (biến thể định dạng của 'ViewModel') | `viewmodel` | `android` | ✅ CÓ |
| `Tornado_Web` | `Python` | Python framework (biến thể định dạng của 'Tornado Web') | `tornado_web` | `python` | ❌ KHÔNG |
| `retrofit` | `Java` | Retrofit là HTTP client cho Java/Android (biến thể định dạng của 'Retrofit') | `retrofit` | `java` | ✅ CÓ |
| `Azure_Monitor` | `Azure` | Azure Monitor là dịch vụ monitoring của Azure (biến thể định dạng của 'Azure Monitor') | `azure_monitor` | `azure` | ❌ KHÔNG |
| `CODEIGNITER` | `PHP` | CodeIgniter là framework PHP (biến thể định dạng của 'CodeIgniter') | `codeigniter` | `php` | ✅ CÓ |
| `FREERTOS` | `Embedded C` | FreeRTOS thường viết bằng Embedded C (biến thể định dạng của 'FreeRTOS') | `freertos` | `embedded-c` | ✅ CÓ |
| `pYtEST` | `Python` | Python test framework (biến thể định dạng của 'PyTest') | `pytest` | `python` | ✅ CÓ |
| `jax` | `Python` | Python library (biến thể định dạng của 'JAX') | `jax` | `python` | ✅ CÓ |
| `amazon-eks` | `Kubernetes` | EKS là Kubernetes quản lý của AWS (biến thể định dạng của 'Amazon EKS') | `amazon-eks` | `kubernetes` | ✅ CÓ |
| `spring-boot` | `Java` | Spring Boot chạy trên Java (biến thể định dạng của 'Spring Boot') | `spring-boot` | `java` | ✅ CÓ |
| `aws iam` | `AWS` | IAM là dịch vụ quản lý quyền của AWS (biến thể định dạng của 'AWS IAM') | `aws-iam` | `aws` | ✅ CÓ |
| `asp.net-mvc` | `ASP.NET` | ASP.NET MVC là module của ASP.NET (biến thể định dạng của 'ASP.NET MVC') | `asp.net-mvc` | `asp.net` | ✅ CÓ |
| `PRISMA` | `Node.js` | Prisma là ORM phổ biến cho Node.js/TypeScript (biến thể định dạng của 'Prisma') | `prisma` | `node.js` | ✅ CÓ |
| `Lightgbm` | `Python` | Python library phổ biến qua API Python (biến thể định dạng của 'LightGBM') | `lightgbm` | `python` | ✅ CÓ |
| `JETPACK COMPOSE` | `Android` | Jetpack Compose là UI toolkit của Android (biến thể định dạng của 'Jetpack Compose') | `android-jetpack-compose` | `android` | ✅ CÓ |
| `tURBOREPO` | `JavaScript` | Turborepo là monorepo tool cho hệ sinh thái JS (biến thể định dạng của 'Turborepo') | `turborepo` | `javascript` | ✅ CÓ |
| `hibernate` | `Java` | Hibernate là ORM cho Java (biến thể định dạng của 'Hibernate') | `hibernate` | `java` | ✅ CÓ |
| `WOOCOMMERCE` | `WordPress` | WooCommerce là plugin ecommerce của WordPress (biến thể định dạng của 'WooCommerce') | `woocommerce` | `wordpress` | ✅ CÓ |
| `transformers` | `Python` | Hugging Face Transformers là Python library (biến thể định dạng của 'Transformers') | `transformers` | `python` | ✅ CÓ |
| `SPARK STREAMING` | `Apache Spark` | Spark Streaming là module của Spark (biến thể định dạng của 'Spark Streaming') | `spark-streaming` | `apache-spark` | ✅ CÓ |
| `VERTEX AI` | `Google Cloud Platform` | Vertex AI là dịch vụ ML của GCP (biến thể định dạng của 'Vertex AI') | `vertex-ai` | `gcp` | ✅ CÓ |
| `cloud dataflow` | `Google Cloud Platform` | Dataflow là dịch vụ xử lý dữ liệu của GCP (biến thể định dạng của 'Cloud Dataflow') | `cloud-dataflow` | `gcp` | ✅ CÓ |
| `SPRING-SECURITY` | `Spring` | Spring Security là module của Spring (biến thể định dạng của 'Spring Security') | `spring-security` | `spring` | ✅ CÓ |
| `CLOUD-COMPOSER` | `Airflow` | Cloud Composer là Airflow quản lý trên GCP (biến thể định dạng của 'Cloud Composer') | `cloud-composer` | `airflow` | ✅ CÓ |
| `azure synapse analytics` | `Azure` | Synapse Analytics là data warehouse của Azure (biến thể định dạng của 'Azure Synapse Analytics') | `azure-synapse-analytics` | `azure` | ✅ CÓ |
| `azure-data-factory` | `Azure` | Data Factory là dịch vụ ETL của Azure (biến thể định dạng của 'Azure Data Factory') | `azure-data-factory` | `azure` | ✅ CÓ |
| `gitlab` | `Git` | GitLab là dịch vụ hosting cho Git (biến thể định dạng của 'GitLab') | `gitlab` | `git` | ✅ CÓ |
| `AWS-GLUE` | `AWS` | Glue là dịch vụ ETL của AWS (biến thể định dạng của 'AWS Glue') | `aws-glue` | `aws` | ✅ CÓ |
| `Sinonjs` | `JavaScript` | Sinon là mocking library cho JavaScript (biến thể định dạng của 'Sinon.js') | `sinonjs` | `javascript` | ❌ KHÔNG |
| `amazon-vpc` | `AWS` | VPC là dịch vụ mạng ảo của AWS (biến thể định dạng của 'Amazon VPC') | `amazon-vpc` | `aws` | ✅ CÓ |
| `stm32` | `Embedded C` | Lập trình STM32 thường dùng Embedded C (biến thể định dạng của 'STM32') | `stm32` | `embedded-c` | ✅ CÓ |
| `REACT-HOOK-FORM` | `React` | React Hook Form là form library của React (biến thể định dạng của 'React Hook Form') | `react-hook-form` | `reactjs` | ✅ CÓ |
| `asp.net cORE` | `C#` | ASP.NET Core viết bằng C# (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `c#` | ✅ CÓ |
| `freertos` | `Embedded C` | FreeRTOS thường viết bằng Embedded C (biến thể định dạng của 'FreeRTOS') | `freertos` | `embedded-c` | ✅ CÓ |
| `AZURE DEVOPS` | `Azure` | Azure DevOps là bộ công cụ CI/CD của Azure (biến thể định dạng của 'Azure DevOps') | `azure-devops` | `azure` | ✅ CÓ |
| `AZURE MONITOR` | `Azure` | Azure Monitor là dịch vụ monitoring của Azure (biến thể định dạng của 'Azure Monitor') | `azure-monitor` | `azure` | ✅ CÓ |
| `mATERIAL ui` | `React` | Material UI là component library cho React (biến thể định dạng của 'Material UI') | `material-ui` | `reactjs` | ✅ CÓ |
| `KAFKA STREAMS` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams') | `apache-kafka-streams` | `apache-kafka` | ✅ CÓ |
| `asp.net core` | `C#` | ASP.NET Core viết bằng C# (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `c#` | ✅ CÓ |
| `junit` | `Java` | JUnit là test framework cho Java (biến thể định dạng của 'JUnit') | `junit` | `java` | ✅ CÓ |
| `SPRING BOOT` | `Java` | Spring Boot chạy trên Java (biến thể định dạng của 'Spring Boot') | `spring-boot` | `java` | ✅ CÓ |
| `Azure_Databricks` | `Apache Spark` | Azure Databricks chạy trên nền Spark (biến thể định dạng của 'Azure Databricks') | `azure_databricks` | `apache-spark` | ❌ KHÔNG |
| `Compute_Engine` | `Google Cloud Platform` | Compute Engine là dịch vụ compute của GCP (biến thể định dạng của 'Compute Engine') | `compute_engine` | `gcp` | ❌ KHÔNG |
| `vUEX` | `Vue.js` | Vuex là state management của Vue (biến thể định dạng của 'Vuex') | `vuex` | `vue.js` | ✅ CÓ |
| `sequelize.js` | `Node.js` | Sequelize là ORM cho Node.js (biến thể định dạng của 'Sequelize.js') | `sequelize.js` | `node.js` | ✅ CÓ |
| `SALESFORCE-APEX` | `Salesforce` | Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex') | `apex` | `salesforce` | ❌ KHÔNG |
| `ASPNET Core` | `ASP.NET` | ASP.NET Core là thế hệ mới của ASP.NET (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `asp.net` | ✅ CÓ |
| `Aws Codebuild` | `AWS` | CodeBuild là dịch vụ build của AWS (biến thể định dạng của 'AWS CodeBuild') | `aws-codebuild` | `aws` | ✅ CÓ |
| `ENTITY-FRAMEWORK-CORE` | `Entity Framework` | EF Core là thế hệ mới của EF (biến thể định dạng của 'Entity Framework Core') | `entity-framework-core` | `entity-framework` | ✅ CÓ |
| `aws fargate` | `AWS` | Fargate là dịch vụ serverless container của AWS (biến thể định dạng của 'AWS Fargate') | `aws-fargate` | `aws` | ✅ CÓ |
| `spring boot` | `Java` | Spring Boot chạy trên Java (biến thể định dạng của 'Spring Boot') | `spring-boot` | `java` | ✅ CÓ |
| `sINON.JS` | `JavaScript` | Sinon là mocking library cho JavaScript (biến thể định dạng của 'Sinon.js') | `sinon.js` | `javascript` | ✅ CÓ |
| `cloud composer` | `Google Cloud Platform` | Cloud Composer là dịch vụ Airflow quản lý của GCP (biến thể định dạng của 'Cloud Composer') | `cloud-composer` | `gcp` | ✅ CÓ |
| `NESTJS` | `Node.js` | NestJS chạy trên Node.js (biến thể định dạng của 'NestJS') | `nestjs` | `node.js` | ✅ CÓ |
| `REDUX` | `JavaScript` | State library cho JS (biến thể định dạng của 'Redux') | `redux` | `javascript` | ✅ CÓ |
| `kUBECTL` | `Kubernetes` | kubectl là CLI điều khiển Kubernetes (biến thể định dạng của 'Kubectl') | `kubectl` | `kubernetes` | ✅ CÓ |
| `Amazon-Route-53` | `AWS` | Route 53 là dịch vụ DNS của AWS (biến thể định dạng của 'Amazon Route 53') | `amazon-route-53` | `aws` | ✅ CÓ |
| `XamarinForms` | `Xamarin` | Xamarin.Forms là module của Xamarin (biến thể định dạng của 'Xamarin.Forms') | `xamarinforms` | `xamarin` | ❌ KHÔNG |
| `PILLOW` | `Python` | Python library (biến thể định dạng của 'Pillow') | `python-imaging-library` | `python` | ✅ CÓ |
| `Azure-Blob-Storage` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage') | `azure-blob-storage` | `azure` | ✅ CÓ |
| `bottle` | `Python` | Python framework (biến thể định dạng của 'Bottle') | `bottle` | `python` | ✅ CÓ |
| `Spring_Boot` | `Java` | Spring Boot chạy trên Java (biến thể định dạng của 'Spring Boot') | `spring_boot` | `java` | ❌ KHÔNG |
| `BIGQUERY` | `Google Cloud Platform` | BigQuery là data warehouse dịch vụ của GCP (biến thể định dạng của 'BigQuery') | `bigquery` | `gcp` | ✅ CÓ |
| `GODOT-ENGINE` | `GDScript` | Godot Engine dùng ngôn ngữ script riêng GDScript (biến thể định dạng của 'Godot Engine') | `godot` | `gdscript` | ✅ CÓ |
| `aws fARGATE` | `AWS` | Fargate là dịch vụ serverless container của AWS (biến thể định dạng của 'AWS Fargate') | `aws-fargate` | `aws` | ✅ CÓ |
| `linq` | `C#` | LINQ là tính năng ngôn ngữ của C#/.NET (biến thể định dạng của 'LINQ') | `linq` | `c#` | ✅ CÓ |
| `AMAZON S3` | `AWS` | S3 là dịch vụ storage của AWS (biến thể định dạng của 'Amazon S3') | `amazon-s3` | `aws` | ✅ CÓ |
| `Kotlin_Coroutines` | `Kotlin` | Coroutines là tính năng của Kotlin (biến thể định dạng của 'Kotlin Coroutines') | `kotlin_coroutines` | `kotlin` | ❌ KHÔNG |
| `laravel` | `PHP` | Laravel là framework PHP (biến thể định dạng của 'Laravel') | `laravel` | `php` | ✅ CÓ |
| `rEACT rOUTER` | `React` | React Router là routing library của React (biến thể định dạng của 'React Router') | `react-router` | `reactjs` | ✅ CÓ |
| `spacy` | `Python` | Python library (biến thể định dạng của 'spaCy') | `spacy` | `python` | ✅ CÓ |
| `lANGcHAIN` | `Python` | LangChain thường dùng qua Python SDK (biến thể định dạng của 'LangChain') | `langchain` | `python` | ✅ CÓ |
| `docker-compose` | `Docker` | Docker Compose là tính năng của Docker (biến thể định dạng của 'Docker Compose') | `docker-compose` | `docker` | ✅ CÓ |
| `dJANGO` | `Python` | Python framework (biến thể định dạng của 'Django') | `django` | `python` | ✅ CÓ |
| `SCIKIT-LEARN` | `Python` | Python library (biến thể định dạng của 'Scikit-learn') | `scikit-learn` | `python` | ✅ CÓ |
| `azure blob storage` | `Azure` | Blob Storage là dịch vụ lưu trữ của Azure (biến thể định dạng của 'Azure Blob Storage') | `azure-blob-storage` | `azure` | ✅ CÓ |
| `CLOUD-RUN` | `Google Cloud Platform` | Cloud Run là dịch vụ serverless container của GCP (biến thể định dạng của 'Cloud Run') | `cloud-run` | `gcp` | ✅ CÓ |
| `terraform-provider-aws` | `Terraform` | Provider là module mở rộng của Terraform (biến thể định dạng của 'Terraform Provider AWS') | `terraform-provider-aws` | `terraform` | ✅ CÓ |
| `PYMONGO` | `MongoDB` | PyMongo là driver Python cho MongoDB (biến thể định dạng của 'PyMongo') | `pymongo` | `mongodb` | ✅ CÓ |
| `azure-cognitive-services` | `Azure` | Cognitive Services là dịch vụ AI của Azure (biến thể định dạng của 'Azure Cognitive Services') | `azure-cognitive-services` | `azure` | ✅ CÓ |
| `salesforce-apex` | `Salesforce` | Apex là ngôn ngữ lập trình của Salesforce (biến thể định dạng của 'Salesforce Apex') | `apex` | `salesforce` | ❌ KHÔNG |
| `sOLIDjs` | `JavaScript` | SolidJS là framework JavaScript (biến thể định dạng của 'SolidJS') | `solidjs` | `javascript` | ✅ CÓ |
| `aZURE vIRTUAL mACHINES` | `Azure` | VM là dịch vụ compute của Azure (biến thể định dạng của 'Azure Virtual Machines') | `azure-virtual-machines` | `azure` | ✅ CÓ |
| `ASTRO` | `JavaScript` | Astro là framework JavaScript (biến thể định dạng của 'Astro') | `astro` | `javascript` | ✅ CÓ |
| `CLOUD MONITORING` | `Google Cloud Platform` | Cloud Monitoring là dịch vụ monitoring của GCP (biến thể định dạng của 'Cloud Monitoring') | `cloud-monitoring` | `gcp` | ✅ CÓ |
| `Azure-Data-Factory` | `Azure` | Data Factory là dịch vụ ETL của Azure (biến thể định dạng của 'Azure Data Factory') | `azure-data-factory` | `azure` | ✅ CÓ |
| `eNTITY fRAMEWORK cORE` | `Entity Framework` | EF Core là thế hệ mới của EF (biến thể định dạng của 'Entity Framework Core') | `entity-framework-core` | `entity-framework` | ✅ CÓ |
| `aSTRO` | `JavaScript` | Astro là framework JavaScript (biến thể định dạng của 'Astro') | `astro` | `javascript` | ✅ CÓ |
| `LOOKER` | `SQL` | Looker dùng LookML dựa trên SQL (biến thể định dạng của 'Looker') | `looker` | `sql` | ✅ CÓ |
| `CLOUD-STORAGE` | `Google Cloud Platform` | Cloud Storage là dịch vụ lưu trữ của GCP (biến thể định dạng của 'Cloud Storage') | `cloud-storage` | `gcp` | ✅ CÓ |
| `cLOUD fUNCTIONS` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `amazon-athena` | `AWS` | Athena là dịch vụ query serverless của AWS (biến thể định dạng của 'Amazon Athena') | `amazon-athena` | `aws` | ✅ CÓ |
| `flutter` | `Dart` | Flutter viết bằng Dart (biến thể định dạng của 'Flutter') | `flutter` | `dart` | ✅ CÓ |
| `Azure Sql Database` | `Azure` | Azure SQL Database là dịch vụ database của Azure (biến thể định dạng của 'Azure SQL Database') | `azure-sql-database` | `azure` | ✅ CÓ |
| `AMAZON-VPC` | `AWS` | VPC là dịch vụ mạng ảo của AWS (biến thể định dạng của 'Amazon VPC') | `amazon-vpc` | `aws` | ✅ CÓ |
| `arduino` | `C++` | Arduino sketch dựa trên C++ (biến thể định dạng của 'Arduino') | `arduino` | `c++` | ✅ CÓ |
| `EMBER.JS` | `JavaScript` | JS framework (biến thể định dạng của 'Ember.js') | `ember.js` | `javascript` | ✅ CÓ |
| `wINfORMS` | `C#` | WinForms là UI framework của .NET/C# (biến thể định dạng của 'WinForms') | `winforms` | `c#` | ✅ CÓ |
| `Ssrs` | `SQL Server` | SSRS là công cụ reporting của SQL Server (biến thể định dạng của 'SSRS') | `reporting-services` | `sql-server` | ❌ KHÔNG |
| `apollo-client` | `GraphQL` | Apollo Client là client cho GraphQL (biến thể định dạng của 'Apollo Client') | `apollo-client` | `graphql` | ✅ CÓ |
| `azure service fabric` | `Azure` | Service Fabric là nền tảng microservices của Azure (biến thể định dạng của 'Azure Service Fabric') | `azure-service-fabric` | `azure` | ✅ CÓ |
| `QUARKUS` | `Java` | Quarkus là framework Java (biến thể định dạng của 'Quarkus') | `quarkus` | `java` | ✅ CÓ |
| `Azure Dns` | `Azure` | Azure DNS là dịch vụ DNS của Azure (biến thể định dạng của 'Azure DNS') | `azure-dns` | `azure` | ✅ CÓ |
| `AMAZON-S3` | `AWS` | S3 là dịch vụ storage của AWS (biến thể định dạng của 'Amazon S3') | `amazon-s3` | `aws` | ✅ CÓ |
| `raspberry-pi` | `Linux` | Raspberry Pi thường chạy hệ điều hành Linux (biến thể định dạng của 'Raspberry Pi') | `raspberry-pi` | `linux` | ✅ CÓ |
| `woocommerce` | `WordPress` | WooCommerce là plugin ecommerce của WordPress (biến thể định dạng của 'WooCommerce') | `woocommerce` | `wordpress` | ✅ CÓ |
| `amazon-sagemaker` | `AWS` | SageMaker là dịch vụ ML của AWS (biến thể định dạng của 'Amazon SageMaker') | `amazon-sagemaker` | `aws` | ✅ CÓ |
| `Pymongo` | `MongoDB` | PyMongo là driver Python cho MongoDB (biến thể định dạng của 'PyMongo') | `pymongo` | `mongodb` | ✅ CÓ |
| `jETPACK cOMPOSE` | `Android` | Jetpack Compose là UI toolkit của Android (biến thể định dạng của 'Jetpack Compose') | `android-jetpack-compose` | `android` | ✅ CÓ |
| `Amazon_RDS` | `AWS` | RDS là dịch vụ database của AWS (biến thể định dạng của 'Amazon RDS') | `amazon_rds` | `aws` | ❌ KHÔNG |
| `beautifulsoup` | `Python` | Python library (biến thể định dạng của 'BeautifulSoup') | `beautifulsoup` | `python` | ✅ CÓ |
| `svelte` | `JavaScript` | JS framework (biến thể định dạng của 'Svelte') | `svelte` | `javascript` | ✅ CÓ |
| `Amazon_ECS` | `AWS` | ECS là dịch vụ container orchestration của AWS (biến thể định dạng của 'Amazon ECS') | `amazon_ecs` | `aws` | ❌ KHÔNG |
| `d3.js` | `JavaScript` | D3.js là thư viện visualization của JavaScript (biến thể định dạng của 'D3.js') | `d3.js` | `javascript` | ✅ CÓ |
| `Docker-Compose` | `Docker` | Docker Compose là tính năng của Docker (biến thể định dạng của 'Docker Compose') | `docker-compose` | `docker` | ✅ CÓ |
| `Cloud_Bigtable` | `Google Cloud Platform` | Bigtable là dịch vụ NoSQL của GCP (biến thể định dạng của 'Cloud Bigtable') | `cloud_bigtable` | `gcp` | ❌ KHÔNG |
| `godot-engine` | `GDScript` | Godot Engine dùng ngôn ngữ script riêng GDScript (biến thể định dạng của 'Godot Engine') | `godot` | `gdscript` | ✅ CÓ |
| `ENZYME` | `React` | Enzyme là test utility cho React (biến thể định dạng của 'Enzyme') | `enzyme` | `reactjs` | ✅ CÓ |
| `Aws Lambda` | `AWS` | Lambda là dịch vụ serverless của AWS (biến thể định dạng của 'AWS Lambda') | `aws-lambda` | `aws` | ✅ CÓ |
| `TENSORFLOW` | `Python` | Python library (biến thể định dạng của 'TensorFlow') | `tensorflow` | `python` | ✅ CÓ |
| `trpc` | `TypeScript` | tRPC dựa trên type-safety của TypeScript (biến thể định dạng của 'tRPC') | `trpc` | `typescript` | ✅ CÓ |
| `AMAZON-ROUTE-53` | `AWS` | Route 53 là dịch vụ DNS của AWS (biến thể định dạng của 'Amazon Route 53') | `amazon-route-53` | `aws` | ✅ CÓ |
| `Material Ui` | `React` | Material UI là component library cho React (biến thể định dạng của 'Material UI') | `material-ui` | `reactjs` | ✅ CÓ |
| `ASP.NET_Core` | `ASP.NET` | ASP.NET Core là thế hệ mới của ASP.NET (biến thể định dạng của 'ASP.NET Core') | `asp.net_core` | `asp.net` | ❌ KHÔNG |
| `ANGULAR MATERIAL` | `Angular` | Angular Material là component library của Angular (biến thể định dạng của 'Angular Material') | `angular-material` | `angular` | ✅ CÓ |
| `AZURE-KEY-VAULT` | `Azure` | Key Vault là dịch vụ quản lý secret của Azure (biến thể định dạng của 'Azure Key Vault') | `azure-key-vault` | `azure` | ✅ CÓ |
| `Okhttp` | `Java` | OkHttp là HTTP client cho Java/Android (biến thể định dạng của 'OkHttp') | `okhttp` | `java` | ✅ CÓ |
| `arkIT` | `Swift` | ARKit thường dùng qua Swift trên iOS (biến thể định dạng của 'ARKit') | `arkit` | `swift` | ✅ CÓ |
| `Woocommerce` | `WordPress` | WooCommerce là plugin ecommerce của WordPress (biến thể định dạng của 'WooCommerce') | `woocommerce` | `wordpress` | ✅ CÓ |
| `Kafka-Streams` | `Apache Kafka` | Kafka Streams là thư viện xử lý stream của Kafka (biến thể định dạng của 'Kafka Streams') | `apache-kafka-streams` | `apache-kafka` | ✅ CÓ |
| `Ruby On Rails` | `Ruby` | Rails là framework của Ruby (biến thể định dạng của 'Ruby on Rails') | `ruby-on-rails` | `ruby` | ✅ CÓ |
| `Angular_Material` | `Angular` | Angular Material là component library của Angular (biến thể định dạng của 'Angular Material') | `angular_material` | `angular` | ❌ KHÔNG |
| `xAMARIN.Ios` | `Xamarin` | Xamarin.iOS là module của Xamarin (biến thể định dạng của 'Xamarin.iOS') | `xamarin.ios` | `xamarin` | ✅ CÓ |
| `amazon-cloudfront` | `AWS` | CloudFront là dịch vụ CDN của AWS (biến thể định dạng của 'Amazon CloudFront') | `amazon-cloudfront` | `aws` | ✅ CÓ |
| `langchain` | `Python` | LangChain thường dùng qua Python SDK (biến thể định dạng của 'LangChain') | `langchain` | `python` | ✅ CÓ |
| `bLAZOR` | `C#` | Blazor viết bằng C# (biến thể định dạng của 'Blazor') | `blazor` | `c#` | ✅ CÓ |
| `sTORYBOOK` | `JavaScript` | Storybook là công cụ dựng UI component cho JavaScript (biến thể định dạng của 'Storybook') | `storybook` | `javascript` | ✅ CÓ |
| `compute-engine` | `Google Cloud Platform` | Compute Engine là dịch vụ compute của GCP (biến thể định dạng của 'Compute Engine') | `compute-engine` | `gcp` | ✅ CÓ |
| `cocoa touch` | `Objective-C` | Cocoa Touch gắn với Objective-C/iOS (biến thể định dạng của 'Cocoa Touch') | `cocoa-touch` | `objective-c` | ✅ CÓ |
| `Cloud-Functions` | `Google Cloud Platform` | Cloud Functions là dịch vụ serverless của GCP (biến thể định dạng của 'Cloud Functions') | `google-cloud-functions` | `gcp` | ✅ CÓ |
| `FIREBASE HOSTING` | `Firebase` | Firebase Hosting là dịch vụ của Firebase (biến thể định dạng của 'Firebase Hosting') | `firebase hosting` | `firebase` | ❌ KHÔNG |
| `azure dns` | `Azure` | Azure DNS là dịch vụ DNS của Azure (biến thể định dạng của 'Azure DNS') | `azure-dns` | `azure` | ✅ CÓ |
| `Trpc` | `TypeScript` | tRPC dựa trên type-safety của TypeScript (biến thể định dạng của 'tRPC') | `trpc` | `typescript` | ✅ CÓ |
| `app engine` | `Google Cloud Platform` | App Engine là PaaS của GCP (biến thể định dạng của 'App Engine') | `app-engine` | `gcp` | ✅ CÓ |
| `DOCKER COMPOSE` | `Docker` | Docker Compose là tính năng của Docker (biến thể định dạng của 'Docker Compose') | `docker-compose` | `docker` | ✅ CÓ |
| `cloud-composer` | `Airflow` | Cloud Composer là Airflow quản lý trên GCP (biến thể định dạng của 'Cloud Composer') | `cloud-composer` | `airflow` | ✅ CÓ |
| `react router` | `React` | React Router là routing library của React (biến thể định dạng của 'React Router') | `react-router` | `reactjs` | ✅ CÓ |
| `MAGENTO` | `PHP` | Magento là nền tảng ecommerce viết bằng PHP (biến thể định dạng của 'Magento') | `magento` | `php` | ✅ CÓ |
| `ruby on rails` | `Ruby` | Rails là framework của Ruby (biến thể định dạng của 'Ruby on Rails') | `ruby-on-rails` | `ruby` | ✅ CÓ |
| `vertex-ai` | `Google Cloud Platform` | Vertex AI là dịch vụ ML của GCP (biến thể định dạng của 'Vertex AI') | `vertex-ai` | `gcp` | ✅ CÓ |
| `Azure-App-Service` | `Azure` | App Service là PaaS của Azure (biến thể định dạng của 'Azure App Service') | `azure-app-service` | `azure` | ✅ CÓ |
| `Amazon-EC2` | `AWS` | EC2 là dịch vụ compute của AWS (biến thể định dạng của 'Amazon EC2') | `amazon-ec2` | `aws` | ✅ CÓ |
| `TRANSFORMERS` | `Python` | Hugging Face Transformers là Python library (biến thể định dạng của 'Transformers') | `transformers` | `python` | ✅ CÓ |
| `asp.net mvc` | `ASP.NET` | ASP.NET MVC là module của ASP.NET (biến thể định dạng của 'ASP.NET MVC') | `asp.net-mvc` | `asp.net` | ✅ CÓ |
| `aZURE sERVICE fABRIC` | `Azure` | Service Fabric là nền tảng microservices của Azure (biến thể định dạng của 'Azure Service Fabric') | `azure-service-fabric` | `azure` | ✅ CÓ |
| `redux toolkit` | `Redux` | Redux Toolkit là bộ công cụ chính thức của Redux (biến thể định dạng của 'Redux Toolkit') | `redux-toolkit` | `redux` | ✅ CÓ |
| `JOTAI` | `React` | Jotai là state library của React (biến thể định dạng của 'Jotai') | `jotai` | `reactjs` | ✅ CÓ |
| `jINJA2` | `Python` | Python template engine (biến thể định dạng của 'Jinja2') | `jinja2` | `python` | ✅ CÓ |
| `Pymysql` | `MySQL` | PyMySQL là driver Python cho MySQL (biến thể định dạng của 'PyMySQL') | `pymysql` | `mysql` | ✅ CÓ |
| `COMPUTE-ENGINE` | `Google Cloud Platform` | Compute Engine là dịch vụ compute của GCP (biến thể định dạng của 'Compute Engine') | `compute-engine` | `gcp` | ✅ CÓ |
| `ASP.NET-Core` | `ASP.NET` | ASP.NET Core là thế hệ mới của ASP.NET (biến thể định dạng của 'ASP.NET Core') | `asp.net-core` | `asp.net` | ✅ CÓ |
| `Arkit` | `Swift` | ARKit thường dùng qua Swift trên iOS (biến thể định dạng của 'ARKit') | `arkit` | `swift` | ✅ CÓ |
| `dropwizard` | `Java` | Dropwizard là framework Java (biến thể định dạng của 'Dropwizard') | `dropwizard` | `java` | ✅ CÓ |
| `SAP_HANA` | `SAP` | HANA là database platform của SAP (biến thể định dạng của 'SAP HANA') | `sap_hana` | `sap` | ❌ KHÔNG |
| `AMAZON KINESIS` | `AWS` | Kinesis là dịch vụ streaming của AWS (biến thể định dạng của 'Amazon Kinesis') | `amazon-kinesis` | `aws` | ✅ CÓ |

</details>

## Kết luận

| | Kết quả |
| --- | --- |
| Độ phủ skill_data.json (Phần A, 1000 case) | **921/1000 = 92.1%** |
| Độ phủ skill_implies.json (Phần B, 1000 case) | **920/1000 = 92.0%** |

Độ phủ tổng 92.1% của Phần A che giấu 1 khác biệt lớn
giữa 2 loại kỹ năng — tách theo A.1 để không kết luận nhầm:

| Nhóm | Case | Tìm thấy | Độ phủ |
| --- | --- | --- | --- |
| Công nghệ chung (ngôn ngữ, framework, DB, tool, khái niệm...) | 521 | 514 | **98.7%** |
| Tên dịch vụ cloud CỤ THỂ (Amazon EC2, Azure Cosmos DB, Cloud Run...) | 96 | 71 | **74.0%** |

Với **công nghệ chung** — loại kỹ năng chiếm đa số trên CV/JD thật —
skill_data.json đạt độ phủ cao
(98.7%); phần lớn MISS (xem A.3) rơi vào
công nghệ quá mới hoặc tên gọi hiếm gặp mà nguồn dữ liệu gốc (Stack Overflow
tags, xem `app/data/crawl_so_tags.py`) chưa kịp cập nhật. Ngược lại, độ phủ
gần như **bằng 0** với **tên dịch vụ cloud cụ thể** — đây KHÔNG phải lỗ hổng
bất ngờ mà là hệ quả tất yếu của nguồn dữ liệu: Stack Overflow tag hóa theo
NỀN TẢNG chung (`aws`, `azure`, `gcp` đều đã có trong skill_data.json), không
tag riêng từng SKU dịch vụ (`amazon-ec2`, `azure-cosmosdb`...). Hệ quả thực tế
cho D2: nếu JD ghi cụ thể "Amazon EC2" thay vì "AWS", CV chỉ ghi "AWS" chung
chung sẽ KHÔNG được Layer 1 nhận diện khớp — phải rơi xuống Layer 3 (fuzzy)
hoặc bị tính là thiếu, dù về bản chất ứng viên có kỹ năng liên quan.

skill_implies.json có độ phủ thấp hơn skill_data.json — đúng như kỳ vọng, vì
đây là quan hệ **kéo theo giữa 2 skill** (tổ hợp) thay vì **định danh 1 skill**
(đơn), nên không gian cần phủ lớn hơn nhiều bậc; các MISS ở B.2 (ví dụ
`cx_Oracle` → `Oracle Database`, `Pub/Sub` → `Google Cloud Platform`, `Salesforce Apex` → `Salesforce`, `Salesforce Lightning` → `Salesforce`, `SSRS` → `SQL Server`...) là ứng
viên trực tiếp để bổ sung vào `skill_implies.json` qua các script
`app/data/add_*_skills.py`, vì thiếu quan hệ kéo theo ở Layer 2 khiến JD phải
liệt kê tường minh cả framework lẫn ngôn ngữ nền thì CV mới được chấm đủ điểm
D2 — nếu JD chỉ ghi "Prisma" mà CV chỉ ghi "Node.js" (không ghi "Prisma"), hệ
thống matched đúng; nhưng chiều ngược lại (JD ghi "Node.js", CV chỉ ghi
"Prisma") sẽ MISS nếu quan hệ kéo theo chưa có trong file.

**Hạn chế của thực nghiệm này:** corpus của cả 2 phần do người viết tổng hợp
từ tri thức miền cá nhân, không phải khảo sát tần suất xuất hiện thực tế trên
CV/JD của hệ thống (ngoài phạm vi thu thập được của đồ án) — độ phủ đo được ở
đây là ước lượng có căn cứ domain, không phải số liệu production. Nếu có log
`evaluate_all_skills()` thực tế, cách đo chính xác hơn là thống kê trực tiếp
tỷ lệ `matched_layer="missing"` trên yêu cầu JD thật.

---
*Tái tạo báo cáo này: `python scripts/d2_kb_coverage_experiment.py`*
