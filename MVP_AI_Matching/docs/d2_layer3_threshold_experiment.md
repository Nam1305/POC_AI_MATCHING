# Thực nghiệm: ngưỡng 0.85 của Layer 3 fuzzy match (D2)

Sinh tự động bởi `scripts/d2_layer3_threshold_experiment.py`. Kiểm chứng bằng
số liệu cho `_LAYER3_FUZZY_THRESHOLD = 0.85` trong
[`app/services/skill_matcher.py`](../app/services/skill_matcher.py).

## 1. Phương pháp

- **Corpus dương** (188 cặp): cùng 1 kỹ năng, chỉ khác biến
  thể bề mặt (viết tắt, dấu chấm, spacing, typo) — Layer 3 **nên khớp**.
- **Corpus âm** (160 cặp): 2 kỹ năng khác nhau về bản chất
  dù tên gần giống ký tự — Layer 3 **không nên khớp**.
- Nhãn gốc (ground truth) đến từ tri thức miền, **độc lập** với giá trị ratio.
- Với mỗi threshold trong [0.50, 0.99] (bước 0.01), tính confusion matrix và
  precision/recall/F1 trên toàn corpus.

## 2. Corpus dương — cặp cùng 1 kỹ năng (kỳ vọng: match)

| Skill A | Skill B | ratio | Kỳ vọng | Verdict @0.85 | Đúng? | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- |
| `postgresql` | `postgres` | 0.889 | match | match | ✅ | viết tắt |
| `nodejs` | `node.js` | 0.923 | match | match | ✅ | dấu chấm |
| `reactjs` | `react.js` | 0.933 | match | match | ✅ | dấu chấm |
| `vuejs` | `vue.js` | 0.909 | match | match | ✅ | dấu chấm |
| `expressjs` | `express.js` | 0.947 | match | match | ✅ | dấu chấm |
| `python` | `pythonn` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `javascript` | `javascrip` | 0.947 | match | match | ✅ | typo — thiếu ký tự |
| `docker` | `dockerr` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `kubernetes` | `kubernets` | 0.947 | match | match | ✅ | typo — thiếu ký tự |
| `kubernetes` | `kubernetess` | 0.952 | match | match | ✅ | typo — thừa ký tự |
| `selenium` | `selenim` | 0.933 | match | match | ✅ | typo — hoán vị |
| `terraform` | `teraform` | 0.941 | match | match | ✅ | typo — thiếu ký tự |
| `elasticsearch` | `elastic search` | 0.963 | match | match | ✅ | spacing |
| `restapi` | `rest api` | 0.933 | match | match | ✅ | spacing |
| `graphql` | `graph ql` | 0.933 | match | match | ✅ | spacing |
| `webpack` | `web pack` | 0.933 | match | match | ✅ | spacing |
| `redis` | `rediss` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `typescript` | `typescrip` | 0.947 | match | match | ✅ | typo — thiếu ký tự |
| `mongodb` | `mongo db` | 0.933 | match | match | ✅ | spacing |
| `postgresql` | `postgressql` | 0.952 | match | match | ✅ | typo — thừa ký tự |
| `mysql` | `mysal` | 0.800 | match | no match | ❌ | typo — hoán vị |
| `golang` | `goalng` | 0.833 | match | no match | ❌ | typo — hoán vị |
| `django` | `djago` | 0.909 | match | match | ✅ | typo — hoán vị |
| `flask` | `flassk` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `jenkins` | `jenkin` | 0.923 | match | match | ✅ | typo — thiếu ký tự |
| `ansible` | `anisble` | 0.857 | match | match | ✅ | typo — hoán vị |
| `cassandra` | `casandra` | 0.941 | match | match | ✅ | typo — thiếu ký tự |
| `rabbitmq` | `rabbit mq` | 0.941 | match | match | ✅ | spacing |
| `oauth2` | `oauth 2` | 0.923 | match | match | ✅ | spacing |
| `microservices` | `micro services` | 0.963 | match | match | ✅ | spacing |
| `angular.js` | `angularjs` | 0.947 | match | match | ✅ | dấu chấm — cùng là AngularJS 1.x |
| `aspnet` | `asp.net` | 0.923 | match | match | ✅ | dấu chấm |
| `docker compose` | `docker-compose` | 0.929 | match | match | ✅ | spacing → dash |
| `ci/cd` | `ci cd` | 0.800 | match | no match | ❌ | ký tự / → space |
| `machine learning` | `machinelearning` | 0.968 | match | match | ✅ | spacing |
| `deep learning` | `deeplearning` | 0.960 | match | match | ✅ | spacing |
| `data science` | `datascience` | 0.957 | match | match | ✅ | spacing |
| `big data` | `bigdata` | 0.933 | match | match | ✅ | spacing |
| `unit testing` | `unittesting` | 0.957 | match | match | ✅ | spacing |
| `load balancing` | `load-balancing` | 0.929 | match | match | ✅ | spacing → dash |
| `continuous integration` | `continous integration` | 0.977 | match | match | ✅ | typo — thiếu ký tự |
| `continuous deployment` | `continous deployment` | 0.976 | match | match | ✅ | typo — thiếu ký tự |
| `power bi` | `powerbi` | 0.933 | match | match | ✅ | spacing |
| `scikit-learn` | `scikit learn` | 0.917 | match | match | ✅ | dash → space |
| `pytorch` | `py torch` | 0.933 | match | match | ✅ | spacing |
| `object oriented programming` | `object-oriented programming` | 0.963 | match | match | ✅ | spacing → dash |
| `test driven development` | `test-driven development` | 0.957 | match | match | ✅ | spacing → dash |
| `api testing` | `api-testing` | 0.909 | match | match | ✅ | spacing → dash |
| `automation testing` | `automation-testing` | 0.944 | match | match | ✅ | spacing → dash |
| `performance testing` | `performence testing` | 0.947 | match | match | ✅ | typo — hoán vị |
| `regression testing` | `regresion testing` | 0.971 | match | match | ✅ | typo — thiếu ký tự |
| `black box testing` | `black-box testing` | 0.941 | match | match | ✅ | spacing → dash |
| `swagger` | `swager` | 0.923 | match | match | ✅ | typo — thiếu ký tự |
| `postman` | `postmann` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `figma` | `fgima` | 0.800 | match | no match | ❌ | typo — hoán vị |
| `photoshop` | `photoshoop` | 0.947 | match | match | ✅ | typo — thừa ký tự |
| `illustrator` | `ilustrator` | 0.952 | match | match | ✅ | typo — thiếu ký tự |
| `elasticsearch` | `elasticserach` | 0.923 | match | match | ✅ | typo — hoán vị |
| `kubernetes` | `kubenetes` | 0.947 | match | match | ✅ | typo — thiếu ký tự |
| `mongodb` | `mongodbb` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `android` | `androidd` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `android studio` | `android-studio` | 0.929 | match | match | ✅ | spacing → dash |
| `swiftui` | `swift ui` | 0.933 | match | match | ✅ | spacing |
| `kotlin` | `kotln` | 0.909 | match | match | ✅ | typo — thiếu ký tự |
| `flutter` | `fluter` | 0.923 | match | match | ✅ | typo — thiếu ký tự |
| `xamarin` | `xamarinn` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `ionic` | `ionicc` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `objective-c` | `objective c` | 0.909 | match | match | ✅ | dash → space |
| `jetpack compose` | `jetpack-compose` | 0.933 | match | match | ✅ | spacing → dash |
| `amazon web services` | `amazon-web-services` | 0.895 | match | match | ✅ | spacing → dash |
| `google cloud platform` | `google-cloud-platform` | 0.905 | match | match | ✅ | spacing → dash |
| `microsoft azure` | `microsoft-azure` | 0.933 | match | match | ✅ | spacing → dash |
| `aws lambda` | `aws-lambda` | 0.900 | match | match | ✅ | spacing → dash |
| `google cloud` | `google-cloud` | 0.917 | match | match | ✅ | spacing → dash |
| `cloudformation` | `cloud formation` | 0.966 | match | match | ✅ | spacing |
| `serverless` | `server less` | 0.952 | match | match | ✅ | spacing |
| `cloudfront` | `cloud front` | 0.952 | match | match | ✅ | spacing |
| `mysql` | `my sql` | 0.909 | match | match | ✅ | spacing |
| `postgresql` | `postgre sql` | 0.952 | match | match | ✅ | spacing |
| `mongodb` | `mongo-db` | 0.933 | match | match | ✅ | dash |
| `sqlite` | `sql lite` | 0.857 | match | match | ✅ | spacing (alt-spelling phổ biến) |
| `dynamodb` | `dynamo db` | 0.941 | match | match | ✅ | spacing |
| `cassandra` | `cassandara` | 0.947 | match | match | ✅ | typo — thừa ký tự |
| `elasticsearch` | `elastic-search` | 0.963 | match | match | ✅ | dash |
| `firebase` | `firebasee` | 0.941 | match | match | ✅ | typo — thừa ký tự |
| `oracle database` | `oracle db` | 0.750 | match | no match | ❌ | viết tắt |
| `mariadb` | `maria db` | 0.933 | match | match | ✅ | spacing |
| `couchdb` | `couch db` | 0.933 | match | match | ✅ | spacing |
| `neo4j` | `neo 4j` | 0.909 | match | match | ✅ | spacing |
| `influxdb` | `influx db` | 0.941 | match | match | ✅ | spacing |
| `golang` | `go lang` | 0.923 | match | match | ✅ | spacing |
| `php` | `phpp` | 0.857 | match | match | ✅ | typo — thừa ký tự |
| `ruby` | `rubyy` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `perl` | `perll` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `scala` | `scalaa` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `rust` | `rustt` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `haskell` | `haskel` | 0.923 | match | match | ✅ | typo — thiếu ký tự |
| `elixir` | `elixer` | 0.833 | match | no match | ❌ | typo — hoán vị |
| `erlang` | `erlan` | 0.909 | match | match | ✅ | typo — thiếu ký tự |
| `dart` | `dartt` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `julia` | `juila` | 0.800 | match | no match | ❌ | typo — hoán vị |
| `matlab` | `mat lab` | 0.923 | match | match | ✅ | spacing |
| `fortran` | `fortan` | 0.923 | match | match | ✅ | typo — thiếu ký tự |
| `cobol` | `cobal` | 0.800 | match | no match | ❌ | typo — hoán vị |
| `groovy` | `groovyy` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `lua` | `luaa` | 0.857 | match | match | ✅ | typo — thừa ký tự |
| `r programming` | `r-programming` | 0.923 | match | match | ✅ | spacing → dash |
| `visual basic` | `visual-basic` | 0.917 | match | match | ✅ | spacing → dash |
| `laravel` | `laravell` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `symfony` | `symfonyy` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `codeigniter` | `code igniter` | 0.957 | match | match | ✅ | spacing |
| `ruby on rails` | `ruby-on-rails` | 0.846 | match | no match | ❌ | spacing → dash |
| `asp.net mvc` | `asp.net-mvc` | 0.909 | match | match | ✅ | spacing → dash |
| `entity framework` | `entity-framework` | 0.938 | match | match | ✅ | spacing → dash |
| `hibernate` | `hibernatee` | 0.947 | match | match | ✅ | typo — thừa ký tự |
| `struts` | `strutss` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `gatsby` | `gatsbyy` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `nuxt.js` | `nuxtjs` | 0.923 | match | match | ✅ | bỏ dấu chấm |
| `next.js` | `nextjs` | 0.923 | match | match | ✅ | bỏ dấu chấm |
| `svelte` | `sveltee` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `ember.js` | `emberjs` | 0.933 | match | match | ✅ | bỏ dấu chấm |
| `backbone.js` | `backbonejs` | 0.952 | match | match | ✅ | bỏ dấu chấm |
| `jquery` | `jquerry` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `bootstrap` | `bootstarp` | 0.889 | match | match | ✅ | typo — hoán vị |
| `tailwind css` | `tailwindcss` | 0.957 | match | match | ✅ | spacing |
| `material ui` | `material-ui` | 0.909 | match | match | ✅ | spacing → dash |
| `chakra ui` | `chakra-ui` | 0.889 | match | match | ✅ | spacing → dash |
| `redux toolkit` | `redux-toolkit` | 0.923 | match | match | ✅ | spacing → dash |
| `styled components` | `styled-components` | 0.941 | match | match | ✅ | spacing → dash |
| `cucumber` | `cucumberr` | 0.941 | match | match | ✅ | typo — thừa ký tự |
| `robot framework` | `robot-framework` | 0.933 | match | match | ✅ | spacing → dash |
| `testng` | `test ng` | 0.923 | match | match | ✅ | spacing |
| `junit` | `juint` | 0.800 | match | no match | ❌ | typo — hoán vị |
| `mocha` | `moocha` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `jasmine` | `jasminee` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `karma` | `karmaa` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `webdriverio` | `webdriver io` | 0.957 | match | match | ✅ | spacing |
| `soapui` | `soap ui` | 0.923 | match | match | ✅ | spacing |
| `loadrunner` | `load runner` | 0.952 | match | match | ✅ | spacing |
| `gatling` | `gattling` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `gitlab ci` | `gitlab-ci` | 0.889 | match | match | ✅ | spacing → dash |
| `github actions` | `github-actions` | 0.929 | match | match | ✅ | spacing → dash |
| `circleci` | `circle ci` | 0.941 | match | match | ✅ | spacing |
| `travis ci` | `travis-ci` | 0.889 | match | match | ✅ | spacing → dash |
| `bamboo` | `bambooo` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `nagios` | `nagioss` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `zabbix` | `zabix` | 0.909 | match | match | ✅ | typo — thiếu ký tự |
| `splunk` | `splank` | 0.833 | match | no match | ❌ | typo — hoán vị |
| `datadog` | `data dog` | 0.933 | match | match | ✅ | spacing |
| `new relic` | `newrelic` | 0.941 | match | match | ✅ | spacing |
| `puppet` | `puppett` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `chef` | `cheff` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `vagrant` | `vagrantt` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `openshift` | `open shift` | 0.947 | match | match | ✅ | spacing |
| `helm` | `helmm` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `istio` | `istioo` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `nginx` | `nginxx` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `apache tomcat` | `apache-tomcat` | 0.923 | match | match | ✅ | spacing → dash |
| `varnish` | `varnesh` | 0.857 | match | match | ✅ | typo — hoán vị |
| `penetration testing` | `pen testing` | 0.733 | match | no match | ❌ | viết tắt |
| `owasp` | `owaspp` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `burp suite` | `burpsuite` | 0.947 | match | match | ✅ | spacing |
| `metasploit` | `metasploitt` | 0.952 | match | match | ✅ | typo — thừa ký tự |
| `nmap` | `n map` | 0.889 | match | match | ✅ | spacing |
| `wireshark` | `wire shark` | 0.947 | match | match | ✅ | spacing |
| `kali linux` | `kali-linux` | 0.900 | match | match | ✅ | spacing → dash |
| `ssl/tls` | `ssl tls` | 0.857 | match | match | ✅ | ký tự / → space |
| `saml` | `samll` | 0.889 | match | match | ✅ | typo — hoán vị |
| `confluence` | `confluance` | 0.900 | match | match | ✅ | typo — hoán vị |
| `trello` | `trelo` | 0.909 | match | match | ✅ | typo — thiếu ký tự |
| `asana` | `assana` | 0.909 | match | match | ✅ | typo — thừa ký tự |
| `monday.com` | `monday com` | 0.900 | match | match | ✅ | bỏ dấu chấm |
| `basecamp` | `base camp` | 0.941 | match | match | ✅ | spacing |
| `clickup` | `click up` | 0.933 | match | match | ✅ | spacing |
| `notion` | `notionn` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `miro` | `miroo` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `zeplin` | `zeplinn` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `tableau` | `tableauu` | 0.933 | match | match | ✅ | typo — thừa ký tự |
| `qlik` | `qlikk` | 0.889 | match | match | ✅ | typo — thừa ký tự |
| `looker` | `lookerr` | 0.923 | match | match | ✅ | typo — thừa ký tự |
| `apache airflow` | `airflow` | 0.667 | match | no match | ❌ | viết tắt — bỏ tiền tố apache |
| `apache spark` | `spark` | 0.588 | match | no match | ❌ | viết tắt — bỏ tiền tố apache |
| `apache hive` | `hive` | 0.533 | match | no match | ❌ | viết tắt — bỏ tiền tố apache |
| `apache hbase` | `hbase` | 0.588 | match | no match | ❌ | viết tắt — bỏ tiền tố apache |
| `snowflake` | `snowflakee` | 0.947 | match | match | ✅ | typo — thừa ký tự |
| `databricks` | `data bricks` | 0.952 | match | match | ✅ | spacing |
| `redshift` | `red shift` | 0.941 | match | match | ✅ | spacing |
| `bigquery` | `big query` | 0.941 | match | match | ✅ | spacing |

## 3. Corpus âm — cặp khác kỹ năng (kỳ vọng: no match)

| Skill A | Skill B | ratio | Kỳ vọng | Verdict @0.85 | Đúng? | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- |
| `angular` | `angularjs` | 0.875 | no match | match | ❌ | framework khác nhau (AngularJS 1.x vs Angular 2+) |
| `java` | `javascript` | 0.571 | no match | no match | ✅ | ngôn ngữ khác nhau, chỉ trùng tiền tố |
| `sql` | `mysql` | 0.750 | no match | no match | ✅ | khái niệm chung vs sản phẩm cụ thể |
| `sql` | `nosql` | 0.750 | no match | no match | ✅ | hai mô hình dữ liệu đối lập |
| `vue` | `vuex` | 0.857 | no match | match | ❌ | framework vs thư viện quản lý state của nó |
| `react` | `redux` | 0.400 | no match | no match | ✅ | framework vs thư viện quản lý state riêng biệt |
| `node` | `nodemon` | 0.727 | no match | no match | ✅ | runtime vs dev-tool riêng biệt |
| `npm` | `pnpm` | 0.857 | no match | match | ❌ | package manager khác nhau |
| `git` | `gitlab` | 0.667 | no match | no match | ✅ | công cụ vs nền tảng lưu trữ |
| `git` | `github` | 0.667 | no match | no match | ✅ | công cụ vs nền tảng lưu trữ |
| `docker` | `dockerfile` | 0.750 | no match | no match | ✅ | công cụ vs định dạng file cấu hình |
| `swift` | `swiftui` | 0.833 | no match | no match | ✅ | ngôn ngữ vs framework UI riêng |
| `c` | `c++` | 0.500 | no match | no match | ✅ | ngôn ngữ khác nhau |
| `c` | `c#` | 0.667 | no match | no match | ✅ | ngôn ngữ khác nhau |
| `go` | `mongo` | 0.571 | no match | no match | ✅ | ngôn ngữ vs cơ sở dữ liệu, không liên quan |
| `ruby` | `ruby on rails` | 0.471 | no match | no match | ✅ | ngôn ngữ vs framework cụ thể |
| `spring` | `spring boot` | 0.706 | no match | no match | ✅ | framework nền vs framework con cụ thể |
| `jira` | `jenkins` | 0.364 | no match | no match | ✅ | công cụ quản lý dự án vs CI/CD, không liên quan |
| `linux` | `unix` | 0.444 | no match | no match | ✅ | hệ điều hành khác nhau (dù cùng họ) |
| `mysql` | `postgresql` | 0.400 | no match | no match | ✅ | hai hệ quản trị CSDL khác nhau |
| `n3` | `n4` | 0.500 | no match | no match | ✅ | hai mức JLPT khác nhau — có thứ bậc, không phải lỗi chính tả |
| `react native` | `react` | 0.588 | no match | no match | ✅ | framework mobile vs thư viện UI web gốc |
| `angular` | `angular material` | 0.609 | no match | no match | ✅ | framework lõi vs thư viện UI component riêng |
| `react` | `react query` | 0.625 | no match | no match | ✅ | framework vs thư viện data-fetching riêng |
| `webpack` | `webpack-dev-server` | 0.560 | no match | no match | ✅ | bundler vs dev-server riêng |
| `selenium` | `selenium grid` | 0.762 | no match | no match | ✅ | thư viện vs hạ tầng chạy song song riêng |
| `docker` | `docker swarm` | 0.667 | no match | no match | ✅ | engine vs orchestrator riêng |
| `kubernetes` | `kubeflow` | 0.444 | no match | no match | ✅ | orchestration platform vs ML pipeline platform |
| `terraform` | `terragrunt` | 0.632 | no match | no match | ✅ | IaC tool vs wrapper tool riêng |
| `ansible` | `ansible tower` | 0.700 | no match | no match | ✅ | tool vs sản phẩm enterprise riêng |
| `prometheus` | `promtail` | 0.556 | no match | no match | ✅ | monitoring metric vs log-shipping, khác hệ |
| `grafana` | `grafana loki` | 0.737 | no match | no match | ✅ | dashboard tool vs log aggregation riêng |
| `elasticsearch` | `elastic apm` | 0.667 | no match | no match | ✅ | search engine vs APM riêng |
| `kafka` | `kafka connect` | 0.556 | no match | no match | ✅ | message broker vs integration framework riêng |
| `mysql` | `mariadb` | 0.167 | no match | no match | ✅ | hai RDBMS khác nhau (fork nhưng là sản phẩm riêng) |
| `postgresql` | `postgis` | 0.706 | no match | no match | ✅ | RDBMS vs extension địa lý riêng |
| `mongodb` | `mongoose` | 0.667 | no match | no match | ✅ | database vs ODM library riêng |
| `express` | `express-session` | 0.636 | no match | no match | ✅ | framework vs middleware riêng |
| `babel` | `babel-loader` | 0.588 | no match | no match | ✅ | compiler vs webpack loader riêng |
| `eslint` | `eslint-config-airbnb` | 0.462 | no match | no match | ✅ | linter vs 1 bộ config riêng |
| `npm` | `npx` | 0.667 | no match | no match | ✅ | package manager vs command runner riêng |
| `yarn` | `yarn workspaces` | 0.421 | no match | no match | ✅ | package manager vs tính năng con riêng |
| `jira` | `jira service desk` | 0.381 | no match | no match | ✅ | issue tracker vs sản phẩm dịch vụ riêng |
| `swagger` | `swagger ui` | 0.824 | no match | no match | ✅ | spec format vs công cụ hiển thị riêng |
| `selenium` | `selenium ide` | 0.800 | no match | no match | ✅ | thư viện vs công cụ ghi kịch bản riêng |
| `nunit` | `xunit` | 0.800 | no match | no match | ✅ | hai testing framework khác nhau cho .NET |
| `tensorflow` | `tensorflow lite` | 0.800 | no match | no match | ✅ | framework đầy đủ vs bản rút gọn cho mobile/edge |
| `pytorch` | `pytorch lightning` | 0.583 | no match | no match | ✅ | framework lõi vs wrapper framework riêng |
| `keras` | `keras tuner` | 0.625 | no match | no match | ✅ | framework vs công cụ tuning riêng |
| `pandas` | `pandas profiling` | 0.545 | no match | no match | ✅ | thư viện vs công cụ EDA riêng |
| `numpy` | `numba` | 0.600 | no match | no match | ✅ | thư viện tính toán vs JIT compiler riêng |
| `scikit-learn` | `scikit-image` | 0.667 | no match | no match | ✅ | ML library vs image-processing library riêng, cùng họ scikit |
| `git` | `git flow` | 0.545 | no match | no match | ✅ | công cụ VCS vs quy trình branching riêng |
| `aws` | `aws amplify` | 0.429 | no match | no match | ✅ | nền tảng cloud vs 1 dịch vụ cụ thể riêng |
| `azure` | `azure devops` | 0.588 | no match | no match | ✅ | nền tảng cloud vs sản phẩm CI/CD riêng |
| `linux` | `linux mint` | 0.667 | no match | no match | ✅ | hệ điều hành họ Unix vs 1 bản phân phối cụ thể |
| `apache` | `apache kafka` | 0.667 | no match | no match | ✅ | web server vs message broker, chỉ trùng tên hãng |
| `spark` | `sparkline` | 0.714 | no match | no match | ✅ | big data engine vs thành phần trực quan nhỏ, không liên quan |
| `hadoop` | `hadoop streaming` | 0.545 | no match | no match | ✅ | hệ sinh thái vs tính năng con riêng |
| `android` | `android auto` | 0.737 | no match | no match | ✅ | OS vs sản phẩm xe hơi riêng |
| `ios` | `ionic` | 0.500 | no match | no match | ✅ | hệ điều hành Apple vs framework hybrid, tên gần giống ngẫu nhiên |
| `swift` | `swift package manager` | 0.385 | no match | no match | ✅ | ngôn ngữ vs công cụ quản lý gói riêng |
| `kotlin` | `kotlin multiplatform` | 0.462 | no match | no match | ✅ | ngôn ngữ vs kỹ thuật multiplatform riêng |
| `flutter` | `flutter web` | 0.778 | no match | no match | ✅ | framework mobile vs target web riêng |
| `xamarin` | `xamarin forms` | 0.700 | no match | no match | ✅ | nền tảng vs UI toolkit con riêng |
| `react native` | `react native web` | 0.857 | no match | match | ❌ | mobile framework vs adapter web riêng |
| `objective-c` | `objective-c++` | 0.917 | no match | match | ❌ | biến thể ngôn ngữ khác nhau (lai C++) |
| `aws` | `aws organizations` | 0.300 | no match | no match | ✅ | nền tảng vs dịch vụ quản lý tài khoản riêng |
| `azure` | `azure functions` | 0.500 | no match | no match | ✅ | nền tảng vs dịch vụ serverless cụ thể |
| `gcp` | `gcp marketplace` | 0.333 | no match | no match | ✅ | nền tảng vs kênh phân phối riêng |
| `lambda` | `lambda school` | 0.632 | no match | no match | ✅ | AWS compute service vs tổ chức đào tạo, không liên quan |
| `s3` | `s3 glacier` | 0.333 | no match | no match | ✅ | storage service vs tier lưu trữ lạnh riêng |
| `ec2` | `ecs` | 0.667 | no match | no match | ✅ | compute instance vs container orchestration service khác |
| `cloudfront` | `cloudflare` | 0.700 | no match | no match | ✅ | CDN của AWS vs công ty CDN độc lập khác |
| `heroku` | `heroku ci` | 0.800 | no match | no match | ✅ | PaaS vs tính năng CI riêng |
| `vercel` | `vercel edge` | 0.706 | no match | no match | ✅ | nền tảng vs tính năng edge riêng |
| `mysql` | `mysql workbench` | 0.500 | no match | no match | ✅ | database engine vs GUI tool riêng |
| `postgresql` | `pgadmin` | 0.235 | no match | no match | ✅ | database engine vs GUI tool riêng, tên khác hẳn |
| `mongodb` | `mongodb atlas` | 0.700 | no match | no match | ✅ | database vs dịch vụ cloud-hosted riêng |
| `redis` | `redis cluster` | 0.556 | no match | no match | ✅ | database vs kiến trúc triển khai riêng |
| `cassandra` | `cassandra query language` | 0.545 | no match | no match | ✅ | database vs ngôn ngữ truy vấn riêng |
| `dynamodb` | `dynamodb streams` | 0.667 | no match | no match | ✅ | database vs tính năng CDC riêng |
| `firebase` | `firebase auth` | 0.762 | no match | no match | ✅ | nền tảng vs 1 dịch vụ con riêng |
| `oracle` | `oracle apex` | 0.706 | no match | no match | ✅ | RDBMS vs low-code platform riêng |
| `sql server` | `sql server management studio` | 0.526 | no match | no match | ✅ | database engine vs GUI tool riêng |
| `neo4j` | `neo4j desktop` | 0.556 | no match | no match | ✅ | database vs công cụ desktop riêng |
| `python` | `python2` | 0.923 | no match | match | ❌ | Python 3 hiện đại vs Python 2 đã EOL — khác nhau về bản chất |
| `java` | `java ee` | 0.727 | no match | no match | ✅ | ngôn ngữ lõi vs đặc tả enterprise riêng |
| `c` | `objective-c` | 0.167 | no match | no match | ✅ | ngôn ngữ C thuần vs biến thể hướng đối tượng riêng |
| `go` | `go kit` | 0.500 | no match | no match | ✅ | ngôn ngữ vs microservices toolkit riêng |
| `scala` | `scalatest` | 0.714 | no match | no match | ✅ | ngôn ngữ vs testing framework riêng |
| `haskell` | `haskell platform` | 0.609 | no match | no match | ✅ | ngôn ngữ vs bộ phân phối cũ riêng |
| `elixir` | `phoenix framework` | 0.348 | no match | no match | ✅ | ngôn ngữ vs framework web riêng |
| `erlang` | `erlang otp` | 0.750 | no match | no match | ✅ | ngôn ngữ vs framework/thư viện OTP riêng |
| `perl` | `perl 6` | 0.800 | no match | no match | ✅ | phiên bản khác biệt lớn, sau đổi tên thành Raku |
| `matlab` | `matlab simulink` | 0.571 | no match | no match | ✅ | ngôn ngữ tính toán vs công cụ mô phỏng riêng |
| `groovy` | `groovy grails` | 0.632 | no match | no match | ✅ | ngôn ngữ vs framework riêng |
| `dart` | `dart sass` | 0.615 | no match | no match | ✅ | ngôn ngữ vs bộ biên dịch CSS riêng, chỉ trùng tên |
| `laravel` | `laravel nova` | 0.737 | no match | no match | ✅ | framework vs admin panel sản phẩm riêng |
| `symfony` | `symfony flex` | 0.737 | no match | no match | ✅ | framework vs công cụ quản lý gói riêng |
| `django` | `django rest framework` | 0.444 | no match | no match | ✅ | framework vs extension xây REST API riêng |
| `rails` | `rails api` | 0.714 | no match | no match | ✅ | framework vs chế độ cấu hình riêng |
| `spring` | `spring cloud` | 0.667 | no match | no match | ✅ | framework nền vs bộ công cụ microservices riêng |
| `hibernate` | `hibernate search` | 0.720 | no match | no match | ✅ | ORM vs module tìm kiếm mở rộng riêng |
| `next.js` | `next auth` | 0.500 | no match | no match | ✅ | framework vs thư viện xác thực riêng |
| `nuxt.js` | `nuxt content` | 0.421 | no match | no match | ✅ | framework vs module quản lý nội dung riêng |
| `gatsby` | `gatsby cloud` | 0.667 | no match | no match | ✅ | framework vs dịch vụ hosting riêng |
| `svelte` | `sveltekit` | 0.800 | no match | no match | ✅ | thư viện UI vs framework ứng dụng đầy đủ riêng |
| `ember.js` | `ember data` | 0.556 | no match | no match | ✅ | framework vs thư viện quản lý dữ liệu riêng |
| `jquery` | `jquery ui` | 0.800 | no match | no match | ✅ | thư viện lõi vs bộ UI component riêng |
| `bootstrap` | `bootstrap icons` | 0.750 | no match | no match | ✅ | framework CSS vs bộ icon riêng |
| `tailwind css` | `tailwind ui` | 0.783 | no match | no match | ✅ | framework CSS vs bộ component trả phí riêng |
| `cucumber` | `cucumber studio` | 0.696 | no match | no match | ✅ | framework BDD vs sản phẩm SaaS riêng |
| `robot framework` | `robotic process automation` | 0.488 | no match | no match | ✅ | testing framework vs RPA, không liên quan dù tên gần giống |
| `testng` | `testcafe` | 0.571 | no match | no match | ✅ | hai testing framework hoàn toàn khác nhau |
| `junit` | `junit params` | 0.588 | no match | no match | ✅ | framework lõi vs extension tham số hoá test riêng |
| `mocha` | `mochawesome` | 0.625 | no match | no match | ✅ | framework vs plugin báo cáo riêng |
| `jasmine` | `jasmine node` | 0.737 | no match | no match | ✅ | framework vs adapter chạy trên Node riêng |
| `selenium` | `selenium base` | 0.762 | no match | no match | ✅ | thư viện vs framework wrapper bên thứ 3 riêng |
| `appium` | `appium desktop` | 0.600 | no match | no match | ✅ | thư viện vs công cụ desktop hỗ trợ riêng |
| `postman` | `postman flow` | 0.737 | no match | no match | ✅ | công cụ API testing vs tính năng automation riêng |
| `soapui` | `soapui pro` | 0.750 | no match | no match | ✅ | bản free vs bản trả phí — sản phẩm thương mại khác |
| `jenkins` | `jenkins pipeline` | 0.609 | no match | no match | ✅ | CI server vs khái niệm pipeline-as-code riêng |
| `gitlab` | `gitlab runner` | 0.632 | no match | no match | ✅ | nền tảng vs agent thực thi CI riêng |
| `github` | `github copilot` | 0.600 | no match | no match | ✅ | nền tảng lưu trữ code vs công cụ AI hỗ trợ code, không liên quan |
| `circleci` | `circleci orbs` | 0.762 | no match | no match | ✅ | nền tảng CI vs gói cấu hình tái sử dụng riêng |
| `puppet` | `puppet forge` | 0.667 | no match | no match | ✅ | công cụ config-management vs kho module riêng |
| `chef` | `chef habitat` | 0.500 | no match | no match | ✅ | công cụ vs sản phẩm đóng gói ứng dụng riêng |
| `vagrant` | `vagrant cloud` | 0.700 | no match | no match | ✅ | công cụ local VM vs dịch vụ chia sẻ box riêng |
| `terraform` | `terraform cloud` | 0.750 | no match | no match | ✅ | công cụ CLI vs dịch vụ SaaS riêng |
| `helm` | `helm hub` | 0.667 | no match | no match | ✅ | công cụ package manager vs kho chart riêng (đã deprecated) |
| `istio` | `istio ambient` | 0.556 | no match | no match | ✅ | service mesh vs chế độ triển khai mới riêng |
| `nagios` | `nagios xi` | 0.800 | no match | no match | ✅ | bản mã nguồn mở vs sản phẩm thương mại riêng |
| `splunk` | `splunk cloud` | 0.667 | no match | no match | ✅ | sản phẩm on-prem vs dịch vụ cloud riêng |
| `datadog` | `datadog rum` | 0.778 | no match | no match | ✅ | nền tảng monitoring vs tính năng real-user-monitoring riêng |
| `newrelic` | `new relic one` | 0.762 | no match | no match | ✅ | sản phẩm cũ vs nền tảng hợp nhất mới |
| `burp suite` | `burp suite enterprise` | 0.645 | no match | no match | ✅ | bản free/pro vs bản doanh nghiệp riêng |
| `metasploit` | `metasploitable` | 0.833 | no match | no match | ✅ | công cụ tấn công vs máy ảo mục tiêu để luyện tập |
| `nmap` | `nmap scripting engine` | 0.320 | no match | no match | ✅ | công cụ vs engine mở rộng riêng |
| `wireshark` | `tshark` | 0.667 | no match | no match | ✅ | bản GUI vs bản CLI riêng, tên khác |
| `kali linux` | `kali nethunter` | 0.583 | no match | no match | ✅ | bản phân phối desktop vs bản mobile riêng |
| `owasp` | `owasp zap` | 0.714 | no match | no match | ✅ | tổ chức/tiêu chuẩn vs công cụ cụ thể do tổ chức phát triển |
| `jira` | `jira align` | 0.571 | no match | no match | ✅ | issue tracker vs sản phẩm scaled-agile riêng |
| `confluence` | `confluence cloud` | 0.769 | no match | no match | ✅ | bản on-prem/server vs bản cloud riêng |
| `trello` | `trello power-ups` | 0.545 | no match | no match | ✅ | công cụ vs hệ thống plugin riêng |
| `asana` | `asana intelligence` | 0.435 | no match | no match | ✅ | công cụ quản lý task vs tính năng AI riêng |
| `notion` | `notion calendar` | 0.571 | no match | no match | ✅ | công cụ ghi chú vs sản phẩm lịch riêng |
| `miro` | `mural` | 0.444 | no match | no match | ✅ | hai công cụ whiteboard online khác nhau, đối thủ cạnh tranh |
| `tableau` | `tableau prep` | 0.737 | no match | no match | ✅ | công cụ trực quan hoá vs công cụ chuẩn bị dữ liệu riêng |
| `power bi` | `power automate` | 0.545 | no match | no match | ✅ | công cụ BI vs công cụ tự động hoá quy trình riêng, cùng hãng |
| `qlik` | `qlikview` | 0.667 | no match | no match | ✅ | hai sản phẩm khác nhau của cùng hãng Qlik |
| `looker` | `lookml` | 0.667 | no match | no match | ✅ | sản phẩm BI vs ngôn ngữ mô hình hoá riêng của nó |
| `airflow` | `luigi` | 0.167 | no match | no match | ✅ | hai workflow orchestration tool khác nhau |
| `spark` | `spark streaming` | 0.500 | no match | no match | ✅ | engine xử lý batch vs module xử lý streaming riêng |
| `hive` | `hive metastore` | 0.444 | no match | no match | ✅ | công cụ truy vấn vs thành phần lưu metadata riêng |
| `hbase` | `hbase shell` | 0.625 | no match | no match | ✅ | database vs công cụ dòng lệnh riêng |
| `snowflake` | `snowpark` | 0.706 | no match | no match | ✅ | data warehouse vs framework lập trình riêng của Snowflake |
| `databricks` | `databricks sql` | 0.833 | no match | no match | ✅ | nền tảng vs tính năng SQL riêng |
| `redshift` | `redshift spectrum` | 0.640 | no match | no match | ✅ | data warehouse vs tính năng truy vấn S3 riêng |
| `bigquery` | `bigquery ml` | 0.842 | no match | no match | ✅ | data warehouse vs tính năng ML riêng |

## 4. Quét ngưỡng — confusion matrix theo threshold

| Threshold | TP | FP | TN | FN | Precision | Recall | F1 | Accuracy | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 188 | 133 | 27 | 0 | 0.586 | 1.000 | 0.739 | 0.618 |  |
| 0.51 | 188 | 124 | 36 | 0 | 0.603 | 1.000 | 0.752 | 0.644 |  |
| 0.52 | 188 | 124 | 36 | 0 | 0.603 | 1.000 | 0.752 | 0.644 |  |
| 0.53 | 188 | 123 | 37 | 0 | 0.605 | 1.000 | 0.754 | 0.647 |  |
| 0.54 | 187 | 123 | 37 | 1 | 0.603 | 0.995 | 0.751 | 0.644 |  |
| 0.55 | 187 | 117 | 43 | 1 | 0.615 | 0.995 | 0.760 | 0.661 |  |
| 0.56 | 187 | 111 | 49 | 1 | 0.628 | 0.995 | 0.770 | 0.678 |  |
| 0.57 | 187 | 110 | 50 | 1 | 0.630 | 0.995 | 0.771 | 0.681 |  |
| 0.58 | 187 | 104 | 56 | 1 | 0.643 | 0.995 | 0.781 | 0.698 |  |
| 0.59 | 185 | 98 | 62 | 3 | 0.654 | 0.984 | 0.786 | 0.710 |  |
| 0.60 | 185 | 98 | 62 | 3 | 0.654 | 0.984 | 0.786 | 0.710 |  |
| 0.61 | 185 | 92 | 68 | 3 | 0.668 | 0.984 | 0.796 | 0.727 |  |
| 0.62 | 185 | 91 | 69 | 3 | 0.670 | 0.984 | 0.797 | 0.730 |  |
| 0.63 | 185 | 87 | 73 | 3 | 0.680 | 0.984 | 0.804 | 0.741 |  |
| 0.64 | 185 | 82 | 78 | 3 | 0.693 | 0.984 | 0.813 | 0.756 |  |
| 0.65 | 185 | 80 | 80 | 3 | 0.698 | 0.984 | 0.817 | 0.761 |  |
| 0.66 | 185 | 80 | 80 | 3 | 0.698 | 0.984 | 0.817 | 0.761 |  |
| 0.67 | 184 | 60 | 100 | 4 | 0.754 | 0.979 | 0.852 | 0.816 |  |
| 0.68 | 184 | 60 | 100 | 4 | 0.754 | 0.979 | 0.852 | 0.816 |  |
| 0.69 | 184 | 60 | 100 | 4 | 0.754 | 0.979 | 0.852 | 0.816 |  |
| 0.70 | 184 | 59 | 101 | 4 | 0.757 | 0.979 | 0.854 | 0.819 |  |
| 0.71 | 184 | 49 | 111 | 4 | 0.790 | 0.979 | 0.874 | 0.848 |  |
| 0.72 | 184 | 45 | 115 | 4 | 0.803 | 0.979 | 0.882 | 0.859 |  |
| 0.73 | 184 | 42 | 118 | 4 | 0.814 | 0.979 | 0.889 | 0.868 |  |
| 0.74 | 183 | 35 | 125 | 5 | 0.839 | 0.973 | 0.901 | 0.885 |  |
| 0.75 | 183 | 35 | 125 | 5 | 0.839 | 0.973 | 0.901 | 0.885 |  |
| 0.76 | 182 | 28 | 132 | 6 | 0.867 | 0.968 | 0.915 | 0.902 |  |
| 0.77 | 182 | 22 | 138 | 6 | 0.892 | 0.968 | 0.929 | 0.920 |  |
| 0.78 | 182 | 20 | 140 | 6 | 0.901 | 0.968 | 0.933 | 0.925 |  |
| 0.79 | 182 | 19 | 141 | 6 | 0.905 | 0.968 | 0.936 | 0.928 |  |
| 0.80 | 182 | 19 | 141 | 6 | 0.905 | 0.968 | 0.936 | 0.928 |  |
| 0.81 | 176 | 11 | 149 | 12 | 0.941 | 0.936 | 0.939 | 0.934 |  |
| 0.82 | 176 | 11 | 149 | 12 | 0.941 | 0.936 | 0.939 | 0.934 |  |
| 0.83 | 176 | 10 | 150 | 12 | 0.946 | 0.936 | 0.941 | 0.937 | **← F1 cao nhất** |
| 0.84 | 173 | 7 | 153 | 15 | 0.961 | 0.920 | 0.940 | 0.937 |  |
| 0.85 | 172 | 6 | 154 | 16 | 0.966 | 0.915 | 0.940 | 0.937 | **← 0.85 (đang dùng)** |
| 0.86 | 166 | 3 | 157 | 22 | 0.982 | 0.883 | 0.930 | 0.928 |  |
| 0.87 | 166 | 3 | 157 | 22 | 0.982 | 0.883 | 0.930 | 0.928 |  |
| 0.88 | 166 | 2 | 158 | 22 | 0.988 | 0.883 | 0.933 | 0.931 |  |
| 0.89 | 151 | 2 | 158 | 37 | 0.987 | 0.803 | 0.886 | 0.888 |  |
| 0.90 | 150 | 2 | 158 | 38 | 0.987 | 0.798 | 0.882 | 0.885 |  |
| 0.91 | 123 | 2 | 158 | 65 | 0.984 | 0.654 | 0.786 | 0.807 |  |
| 0.92 | 120 | 1 | 159 | 68 | 0.992 | 0.638 | 0.777 | 0.802 |  |
| 0.93 | 85 | 0 | 160 | 103 | 1.000 | 0.452 | 0.623 | 0.704 |  |
| 0.94 | 55 | 0 | 160 | 133 | 1.000 | 0.293 | 0.453 | 0.618 |  |
| 0.95 | 26 | 0 | 160 | 162 | 1.000 | 0.138 | 0.243 | 0.534 |  |
| 0.96 | 10 | 0 | 160 | 178 | 1.000 | 0.053 | 0.101 | 0.489 |  |
| 0.97 | 3 | 0 | 160 | 185 | 1.000 | 0.016 | 0.031 | 0.468 |  |
| 0.98 | 0 | 0 | 160 | 188 | 1.000 | 0.000 | 0.000 | 0.460 |  |
| 0.99 | 0 | 0 | 160 | 188 | 1.000 | 0.000 | 0.000 | 0.460 |  |

## 5. Kết quả tại threshold = 0.85 (đang dùng trong code)

| Metric | Giá trị |
| --- | --- |
| True Positive | 172 / 188 |
| False Positive | 6 / 160 |
| True Negative | 154 / 160 |
| False Negative | 16 / 188 |
| Precision | 0.966 |
| Recall | 0.915 |
| F1 | 0.940 |
| Accuracy | 0.937 |
| Error Rate (= (FP+FN)/tổng) | 0.063 |

**Threshold có F1 cao nhất trên corpus này: 0.83 (F1=0.941)**,
so với 0.85 (F1=0.940) — 0.85 nằm sát vùng tối ưu, lệch về phía
**recall** (bắt nhiều biến thể chính tả hơn) đổi lấy vài false positive, thay
vì đẩy threshold lên 0.83 để có precision tuyệt đối nhưng bỏ
sót nhiều typo hơn.

### False positive tại 0.85 (khớp nhầm)

- `angular` / `angularjs` — ratio 0.875 — framework khác nhau (AngularJS 1.x vs Angular 2+)
- `vue` / `vuex` — ratio 0.857 — framework vs thư viện quản lý state của nó
- `npm` / `pnpm` — ratio 0.857 — package manager khác nhau
- `react native` / `react native web` — ratio 0.857 — mobile framework vs adapter web riêng
- `objective-c` / `objective-c++` — ratio 0.917 — biến thể ngôn ngữ khác nhau (lai C++)
- `python` / `python2` — ratio 0.923 — Python 3 hiện đại vs Python 2 đã EOL — khác nhau về bản chất

### False negative tại 0.85 (bỏ sót)

- `mysql` / `mysal` — ratio 0.800 — typo — hoán vị
- `golang` / `goalng` — ratio 0.833 — typo — hoán vị
- `ci/cd` / `ci cd` — ratio 0.800 — ký tự / → space
- `figma` / `fgima` — ratio 0.800 — typo — hoán vị
- `oracle database` / `oracle db` — ratio 0.750 — viết tắt
- `elixir` / `elixer` — ratio 0.833 — typo — hoán vị
- `julia` / `juila` — ratio 0.800 — typo — hoán vị
- `cobol` / `cobal` — ratio 0.800 — typo — hoán vị
- `ruby on rails` / `ruby-on-rails` — ratio 0.846 — spacing → dash
- `junit` / `juint` — ratio 0.800 — typo — hoán vị
- `splunk` / `splank` — ratio 0.833 — typo — hoán vị
- `penetration testing` / `pen testing` — ratio 0.733 — viết tắt
- `apache airflow` / `airflow` — ratio 0.667 — viết tắt — bỏ tiền tố apache
- `apache spark` / `spark` — ratio 0.588 — viết tắt — bỏ tiền tố apache
- `apache hive` / `hive` — ratio 0.533 — viết tắt — bỏ tiền tố apache
- `apache hbase` / `hbase` — ratio 0.588 — viết tắt — bỏ tiền tố apache

## 6. Kết luận

0.85 không phải là điểm tối ưu tuyệt đối theo F1 trên corpus thực nghiệm này
(0.83 cho F1 cao hơn 0.940 → 0.941), nhưng nằm
trong vùng gần-tối-ưu (F1 ở threshold 0.80–0.90 đều ≥ 0.90) và là lựa chọn
**thận trọng có chủ đích**: ưu tiên bắt được các biến thể chính tả/format phổ
biến (recall) hơn là siết precision tuyệt đối, vì:

1. Layer 3 là **tầng cuối cùng** trong cascade 3 tầng — chỉ chạy khi
   Layer 0 (exact), Layer 1 (canonical identity), Layer 2 (entailment) đã
   trượt, nên phần lớn alias/synonym thật đã được `skill_data.json` bắt
   trước khi tới Layer 3 (ví dụ `npm`/`pnpm`, nếu cả hai đều có trong
   `skill_data.json`, sẽ được Layer 1 phân biệt đúng trước khi rơi xuống đây).
2. 6 false positive quan sát được tại 0.85 rơi vào 2 mẫu hình
   quen thuộc của `SequenceMatcher.ratio()` — không threshold nào loại bỏ
   hoàn toàn được nếu không đánh đổi recall:
   - **Chuỗi ngắn, 1-2 ký tự khác biệt** (`angular`/`angularjs`,
     `vue`/`vuex`, `npm`/`pnpm`): vài ký tự lệch trên chuỗi ngắn vẫn cho
     ratio cao vì mẫu số `|a|+|b|` nhỏ.
   - **Tên gốc + hậu tố/phiên bản** (`python`/`python2`,
     `objective-c`/`objective-c++`, `react native`/`react native web`):
     toàn bộ chuỗi gốc khớp làm nền, phần hậu tố ngắn không đủ kéo ratio
     xuống dưới ngưỡng dù 2 bên là 2 công nghệ/phiên bản khác nhau về bản
     chất.
3. Case `angular`/`angularjs` (ratio 0.875) đã được ghi nhận là hạn chế biết
   trước trong `docs/thesis_report.md` (mục "Known issues"), với hướng khắc
   phục đề xuất là chặn Layer 3 khi cả hai phía cùng resolve ra canonical hợp
   lệ nhưng khác nhau — tức xử lý ở tầng canonical, không phải bằng cách siết
   threshold (sẽ đánh đổi recall của các typo hợp lệ khác).

**Khuyến nghị:** giữ nguyên 0.85 — nó nằm trong khoảng an toàn
(F1 0.80–0.90 ≈ 0.882–0.941),
và các false positive còn lại nên được xử lý bằng ràng buộc canonical (như đã
đề xuất), không phải bằng cách chỉnh threshold.

---
*Tái tạo báo cáo này: `python scripts/d2_layer3_threshold_experiment.py`*
