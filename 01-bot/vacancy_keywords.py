# -*- coding: utf-8 -*-
"""
IT-роль ключевые слова для фильтрации вакансий.
Используется в vacancy_filter.py.

Портировано из it-vacancies-base/02-filter/keywords.py.
"""

import re

# ============================================================
# Все ключевые слова (~900 элементов)
# Скопировано из корневого it_role_keywords.py
# ============================================================

IT_ROLE_KEYWORDS = [
    # ============================================================
    # ЯЗЫКИ ПРОГРАММИРОВАНИЯ
    # ============================================================
    "python", "питон", "пайтон",
    "java", "джава",
    "javascript", "java script", "js", "ecmascript",
    "typescript", "ts",
    "go", "golang", "голанг",
    "rust", "раст",
    "c++", "cpp", "си++", "си плюс плюс", "плюсы",
    "c#", "csharp", "c sharp", "си шарп",
    ".net", "dotnet", "dot net", "дотнет",
    "php", "пхп",
    "ruby", "руби",
    "swift", "свифт",
    "kotlin", "котлин",
    "scala", "скала",
    "perl", "перл",
    "dart", "дарт",
    "elixir", "эликсир",
    "erlang", "эрланг",
    "haskell", "хаскель", "хаскел",
    "clojure", "кложур",
    "lua", "луа",
    "objective-c", "objective c", "objc",
    "groovy", "гроови",
    "julia", "джулия",
    "matlab", "матлаб",
    "fortran", "фортран",
    "cobol", "кобол",
    "delphi", "делфи", "делфи",
    "pascal", "паскаль",
    "abap", "абап",
    "apex",
    "f#", "fsharp",
    "ocaml",
    "lisp", "лисп",
    "scheme",
    "r language", " r,", "язык r",
    "vba",
    "assembly", "asm", "ассемблер",
    "solidity", "солидити",
    "vyper",

    # ============================================================
    # SQL И БД-ЯЗЫКИ
    # ============================================================
    "sql", "скуль", "эс ку эль",
    "pl/sql", "plsql",
    "t-sql", "tsql", "transact-sql",
    "noSQL", "nosql",
    "hql",

    # ============================================================
    # СКРИПТЫ И ШЕЛЛЫ
    # ============================================================
    "bash", "баш",
    "shell", "шелл",
    "powershell", "пауэршелл",
    "zsh", "ksh",

    # ============================================================
    # FRONTEND ФРЕЙМВОРКИ И БИБЛИОТЕКИ
    # ============================================================
    "react", "react.js", "reactjs", "реакт",
    "vue", "vue.js", "vuejs", "вью",
    "angular", "angular.js", "angularjs", "ангуляр",
    "svelte", "sveltekit", "свелт",
    "next.js", "nextjs", "next js", "некст",
    "nuxt", "nuxt.js", "nuxtjs", "накст",
    "gatsby",
    "ember.js", "ember",
    "backbone",
    "remix",
    "solid.js", "solidjs",
    "qwik",
    "preact",
    "alpine.js",
    "lit", "litelement",
    "jquery",
    "redux", "redux-toolkit", "rtk",
    "mobx",
    "vuex", "pinia",
    "rxjs",
    "zustand", "recoil", "jotai",
    "tanstack", "react-query", "react query",
    "webpack", "vite", "rollup", "parcel", "esbuild", "turbopack",
    "babel",
    "sass", "scss", "less", "stylus",
    "tailwind", "tailwindcss", "tailwind css",
    "bootstrap", "бутстрап",
    "material-ui", "material ui", "mui",
    "ant design", "antd",
    "chakra ui", "chakra-ui",
    "shadcn",
    "styled-components", "styled components",
    "emotion",
    "three.js", "threejs",
    "d3.js", "d3js",
    "chart.js", "chartjs",
    "html", "html5",
    "css", "css3",
    "web components", "webcomponents",
    "webassembly", "wasm",
    "pwa",
    "spa", "ssr", "ssg", "isr",
    "электрон", "electron",
    "tauri",

    # ============================================================
    # BACKEND ФРЕЙМВОРКИ
    # ============================================================
    "node.js", "nodejs", "node js", "нода", "нод",
    "express", "express.js",
    "nestjs", "nest.js", "nest js",
    "fastify",
    "koa", "koa.js",
    "hapi",
    "deno", "bun",
    "django", "джанго",
    "flask", "фласк",
    "fastapi", "фастапи",
    "pyramid",
    "tornado",
    "aiohttp",
    "starlette",
    "litestar",
    "spring", "spring boot", "spring framework", "спринг",
    "hibernate", "хибернейт",
    "micronaut",
    "quarkus",
    "vert.x", "vertx",
    "play framework",
    "akka", "акка",
    "laravel", "ларавель",
    "symfony", "симфони",
    "codeigniter",
    "yii", "yii2",
    "zend",
    "phalcon",
    "ruby on rails", "rails", "ror",
    "sinatra",
    "asp.net", "asp net", "asp.net core", "aspnet",
    "gin", "echo", "fiber", "beego", "chi",
    "actix", "actix-web",
    "rocket",
    "axum",
    "ktor", "ктор",
    "phoenix",
    "rust web",

    # ============================================================
    # MOBILE
    # ============================================================
    "ios", "айос",
    "android", "андроид",
    "swiftui",
    "uikit",
    "react native", "react-native", "reactnative", "реакт нэйтив",
    "flutter", "флаттер",
    "xamarin", "ксамарин",
    "ionic",
    "cordova", "phonegap",
    "kmm", "kotlin multiplatform", "kmp",
    "jetpack compose", "compose multiplatform",
    "arkit", "arcore",
    "mobile developer", "мобильный разработчик",
    "ios developer", "android developer",
    "ios-разработчик", "android-разработчик",

    # ============================================================
    # БАЗЫ ДАННЫХ
    # ============================================================
    "postgresql", "postgres", "постгрес", "постгря",
    "mysql", "майсиквел", "майэскюэль",
    "mariadb",
    "sqlite",
    "oracle", "oracle db", "оракл",
    "ms sql", "mssql", "sql server",
    "mongodb", "mongo", "монго",
    "dynamodb",
    "cassandra", "кассандра",
    "scylla", "scylladb",
    "redis", "редис",
    "memcached",
    "elasticsearch", "elastic", "эластик",
    "opensearch",
    "neo4j",
    "arangodb",
    "couchdb", "couchbase",
    "influxdb", "timescaledb", "questdb",
    "clickhouse", "кликхаус",
    "vertica",
    "snowflake",
    "bigquery",
    "redshift",
    "databricks",
    "greenplum",
    "teradata",
    "tarantool", "тарантул",
    "firestore",
    "firebase",
    "supabase",
    "cockroachdb",
    "tidb",
    "duckdb",
    "vector database", "vector db", "векторная бд",
    "pinecone", "weaviate", "milvus", "chroma", "qdrant", "faiss",
    "dba", "database administrator", "администратор бд",
    "администратор баз данных", "администратор базы данных",

    # ============================================================
    # DEVOPS / INFRASTRUCTURE / CLOUD
    # ============================================================
    "docker", "докер",
    "kubernetes", "k8s", "k3s", "кубер", "кубернетес",
    "helm", "хельм",
    "openshift",
    "rancher",
    "podman",
    "containerd",
    "lxc", "lxd",
    "terraform", "терраформ",
    "opentofu",
    "pulumi",
    "ansible", "ансибл",
    "puppet", "паппет",
    "chef", "шеф",
    "salt", "saltstack",
    "vagrant",
    "packer",
    "jenkins", "дженкинс",
    "gitlab ci", "gitlab-ci",
    "github actions",
    "circleci", "circle ci",
    "travis ci", "travisci",
    "teamcity",
    "bamboo",
    "drone ci", "droneci",
    "argo", "argocd", "argo cd",
    "flux",
    "spinnaker",
    "tekton",
    "prometheus", "прометеус",
    "grafana", "графана",
    "datadog", "дататог",
    "new relic", "newrelic",
    "zabbix", "заббикс",
    "nagios",
    "splunk", "сплунк",
    "elk", "elk stack",
    "kibana", "logstash", "fluentd", "fluent bit", "fluentbit", "vector log",
    "jaeger", "zipkin", "tempo",
    "opentelemetry", "otel",
    "istio", "linkerd", "consul",
    "vault", "хашикорп",
    "hashicorp",
    "nginx", "энджинкс",
    "apache", "apache http",
    "haproxy",
    "traefik",
    "envoy",
    "varnish",
    "rabbitmq", "кролик",
    "kafka", "кафка",
    "pulsar", "apache pulsar",
    "nats",
    "activemq",
    "zeromq", "0mq",
    "aws", "amazon web services",
    "azure", "майкрософт ажур",
    "gcp", "google cloud", "google cloud platform",
    "alibaba cloud",
    "yandex cloud", "яндекс облако", "yc",
    "vk cloud", "vk cloud solutions",
    "selectel", "селектел",
    "mail.ru cloud", "vk",
    "sber cloud", "sbercloud", "сбер клауд",
    "cloud.ru",
    "cloudflare", "клаудфлэр",
    "digitalocean", "digital ocean",
    "hetzner",
    "ovh",
    "linode",
    "heroku",
    "vercel",
    "netlify",
    "render.com",
    "fly.io",
    "lambda", "aws lambda",
    "ec2", "s3", "rds", "ecs", "eks", "fargate",
    "cloudfront", "route 53", "route53", "iam", "vpc",
    "elastic beanstalk", "cloudformation",
    "gke", "aks", "app engine", "cloud functions",
    "cloud run", "cloud sql",
    "gitops", "ci/cd", "cicd", "ci cd",
    "infrastructure as code", "iac", "инфраструктура как код",
    "configuration management",
    "observability", "наблюдаемость",
    "monitoring", "мониторинг",
    "slo", "sli", "sla",
    "load balancer", "балансировщик",
    "service mesh", "сервис меш",
    "api gateway", "api гейтвей",
    "serverless", "серверлесс",

    # ============================================================
    # BIG DATA / DATA ENGINEERING
    # ============================================================
    "spark", "apache spark", "спарк", "pyspark",
    "hadoop", "хадуп",
    "hdfs",
    "hive",
    "pig",
    "presto", "trino",
    "flink", "apache flink",
    "beam", "apache beam",
    "airflow", "эирфлоу",
    "dagster",
    "prefect",
    "luigi",
    "dbt", "dbt core",
    "fivetran", "stitch", "talend", "informatica", "pentaho", "nifi",
    "etl", "elt", "етл", "етл-разработчик",
    "data warehouse", "dwh", "хранилище данных",
    "data lake", "data lakehouse", "lakehouse",
    "data mart", "витрина данных",
    "data mesh",
    "data engineer", "data engineering", "дата инженер", "дата-инженер",
    "инженер данных",
    "data pipeline", "пайплайн данных",
    "streaming", "стриминг",
    "batch processing",

    # ============================================================
    # ML / AI / DATA SCIENCE
    # ============================================================
    "machine learning", "машинное обучение", "мо",
    "ml", "ml-engineer", "ml engineer", "ml-инженер",
    "deep learning", "глубокое обучение", "dl",
    "neural network", "нейросеть", "нейронные сети", "нейронка",
    "ai", "artificial intelligence", "ии", "искусственный интеллект",
    "llm", "large language model", "большие языковые модели",
    "nlp", "natural language processing", "обработка естественного языка",
    "computer vision", "cv", "компьютерное зрение",
    "opencv",
    "ocr",
    "mlops", "млопс",
    "tensorflow", "tf",
    "pytorch", "пайторч",
    "keras",
    "scikit-learn", "sklearn",
    "xgboost", "catboost", "lightgbm",
    "pandas", "пандас",
    "numpy", "нампай",
    "scipy",
    "matplotlib", "seaborn", "plotly", "bokeh",
    "jupyter", "jupyter notebook",
    "hugging face", "huggingface",
    "transformers",
    "langchain", "лангчейн",
    "llamaindex",
    "openai", "опенаи",
    "gpt", "chatgpt", "claude", "gemini", "anthropic",
    "bert", "берт",
    "yolo",
    "stable diffusion",
    "gan", "rnn", "cnn", "lstm", "transformer",
    "reinforcement learning", "rl", "обучение с подкреплением",
    "generative ai", "gen ai", "генеративный ии",
    "prompt engineering", "промпт-инжиниринг", "промт-инжиниринг",
    "rag", "retrieval augmented generation",
    "embeddings", "эмбеддинги",
    "fine-tuning", "файн-тюнинг", "дообучение",
    "mlflow", "kubeflow", "sagemaker", "vertex ai", "azure ml",
    "data science", "дата сайнс", "data scientist",
    "дата сайентист", "дата-сайентист",
    "data analyst", "аналитик данных", "дата-аналитик", "дата аналитик",
    "ai engineer", "ai-инженер",
    "research engineer", "ml researcher",
    "ml researcher", "research scientist",
    "statistical analysis", "статистический анализ",
    "a/b testing", "ab testing", "а/б тестирование",
    "time series", "временные ряды", "forecasting", "прогнозирование",
    "recommender system", "рекомендательные системы",
    "ranking", "ранжирование",

    # ============================================================
    # АНАЛИТИКА И BI
    # ============================================================
    "аналитик", "analyst",
    "system analyst", "системный аналитик", "системные аналитики",
    "business analyst", "бизнес-аналитик", "бизнес аналитик", "ба",
    "product analyst", "продуктовый аналитик",
    "web analyst", "веб-аналитик", "веб аналитик",
    "marketing analyst", "маркетинговый аналитик",
    "bi", "bi developer", "bi-разработчик",
    "bi analyst", "bi-аналитик",
    "tableau", "таблио",
    "power bi", "powerbi",
    "qlik", "qlikview", "qlik sense",
    "looker", "looker studio",
    "datalens", "yandex datalens",
    "superset", "metabase", "redash",
    "google analytics", "ga4", "google data studio",
    "metabase",
    "yandex metrica", "яндекс.метрика", "яндекс метрика",
    "amplitude",
    "mixpanel",
    "appmetrica", "appsflyer",

    # ============================================================
    # QA / ТЕСТИРОВАНИЕ
    # ============================================================
    "qa", "qa engineer", "qa-инженер", "qa инженер",
    "тестировщик", "тестирование", "tester",
    "test automation", "автоматизация тестирования",
    "manual testing", "ручное тестирование", "мануальный тестировщик",
    "automation qa", "qa automation",
    "автотесты", "автотестирование",
    "sdet",
    "selenium",
    "cypress",
    "playwright",
    "puppeteer",
    "webdriver",
    "appium",
    "jmeter",
    "gatling",
    "locust",
    "k6",
    "postman",
    "rest assured", "rest-assured",
    "soapui",
    "junit", "testng", "pytest", "unittest",
    "mocha", "chai", "jest", "jasmine", "vitest",
    "karma",
    "cucumber", "gherkin", "behat",
    "robot framework",
    "allure", "testrail", "qase",
    "performance testing", "нагрузочное тестирование",
    "stress testing", "стресс-тестирование",
    "security testing", "тестирование безопасности",
    "regression testing", "регрессионное тестирование",
    "smoke testing", "смоук-тестирование",
    "e2e", "end-to-end", "энд ту энд",
    "unit test", "юнит-тест", "юнит тест",
    "integration test", "интеграционное тестирование",
    "ui test", "api test",

    # ============================================================
    # БЕЗОПАСНОСТЬ
    # ============================================================
    "security engineer", "инженер по безопасности",
    "информационная безопасность", "иб",
    "кибербезопасность", "cybersecurity",
    "infosec", "инфобез",
    "appsec", "application security",
    "devsecops",
    "penetration testing", "пентест", "пентестер", "pentester", "pentest",
    "ethical hacking", "этичный хакинг",
    "red team", "blue team", "purple team",
    "soc", "security operations center",
    "siem",
    "qradar", "arcsight",
    "ids", "ips", "waf", "firewall", "фаервол",
    "vulnerability assessment", "vulnerability management",
    "vapt",
    "owasp",
    "iso 27001",
    "gdpr", "gdpr compliance",
    "pci dss",
    "152-фз", "пдн",
    "compliance",
    "threat intelligence", "ti",
    "threat hunting",
    "incident response", "ир",
    "forensics", "форензика",
    "malware analysis", "анализ вредоносного по",
    "reverse engineering", "реверс-инжиниринг", "реверсинг",
    "cryptography", "криптография",
    "oauth", "oauth2", "oidc", "openid connect",
    "saml", "sso", "jwt",
    "pki",
    "cve", "cvss",
    "burp", "burp suite",
    "metasploit",
    "nmap",
    "wireshark",
    "kali",
    "soar",
    "edr", "xdr", "ndr",
    "dlp",
    "ддос", "ddos",
    "криптограф", "криптографический",

    # ============================================================
    # GAMEDEV
    # ============================================================
    "game developer", "геймдев", "геймдев-разработчик",
    "игровой разработчик", "разработчик игр",
    "unity", "юнити",
    "unreal", "unreal engine", "ue4", "ue5", "анриал",
    "godot", "годот",
    "cryengine",
    "construct",
    "gamedev",
    "blueprints",
    "glsl", "hlsl", "metal shading language",
    "shader", "шейдер", "шейдеры",
    "gameplay programmer", "геймплей-программист",
    "engine programmer",
    "graphics programmer", "графический программист",
    "vfx artist", "вфх артист",
    "technical artist", "тех-артист", "технический художник",
    "animation programmer",

    # ============================================================
    # EMBEDDED / HARDWARE / IOT
    # ============================================================
    "embedded", "embedded developer", "embedded engineer",
    "встраиваемые системы", "встраиваемый",
    "прошивки", "прошивка", "разработчик прошивок",
    "firmware",
    "микроконтроллер", "микроконтроллеры", "microcontroller", "mcu",
    "плис", "fpga",
    "vhdl", "verilog", "systemverilog",
    "arduino", "ардуино",
    "raspberry pi", "распбери",
    "stm32", "esp32", "esp8266",
    "plc", "плк",
    "scada", "скада",
    "robotics", "робототехника", "робот",
    "iot", "интернет вещей",
    "industrial iot", "iiot", "промышленный интернет вещей",
    "автоматизация технологических процессов",
    "automation engineer",
    "кип", "кипиа",
    "схемотехник", "схемотехника",
    "electrical engineer", "инженер-электрик",
    "hardware engineer", "хардварный инженер", "инженер по железу",
    "hardware design",
    "asic",
    "soc", "system on chip",
    "dsp",
    "rtos", "freertos", "zephyr",
    "bare metal",
    "bsp", "board support package",
    "can bus", "can-шина",
    "modbus",
    "i2c", "spi", "uart",

    # ============================================================
    # BLOCKCHAIN / WEB3
    # ============================================================
    "blockchain", "блокчейн",
    "web3", "веб3",
    "smart contract", "смарт-контракт", "смарт контракт",
    "ethereum", "эфириум", "eth",
    "bitcoin", "биткоин", "btc",
    "polygon", "matic",
    "solana", "near protocol", "ton", "tron",
    "defi", "дефи",
    "nft", "нфт",
    "dao",
    "dapp", "децентрализованные приложения",
    "hardhat",
    "truffle",
    "foundry",
    "ethers.js", "web3.js",
    "metamask",
    "ledger",
    "hyperledger", "fabric", "corda", "quorum",
    "ipfs",
    "layer 2", "l2",

    # ============================================================
    # DESIGN (PRODUCT / UX / UI)
    # ============================================================
    "ux", "ui", "ux/ui", "ui/ux",
    "ux designer", "ui designer",
    "ux-дизайнер", "ui-дизайнер",
    "дизайнер интерфейсов",
    "продуктовый дизайнер", "product designer",
    "web designer", "веб-дизайнер",
    "motion designer", "моушн-дизайнер", "моушен дизайнер",
    "interaction designer",
    "дизайн-исследователь", "ux researcher", "юкс-ресерчер",
    "figma", "фигма",
    "sketch",
    "adobe xd",
    "framer",
    "protopie", "principle",
    "design system", "дизайн-система",

    # ============================================================
    # МЕНЕДЖМЕНТ И ЛИДЕРСТВО (IT-ориентированные)
    # ============================================================
    "product manager", "продакт-менеджер", "продакт менеджер", "продакт",
    "project manager", "проджект-менеджер", "проджект менеджер", "пм",
    "product owner", "продакт оунер", "продукт оунер", "пo",
    "scrum master", "скрам мастер", "скрам-мастер",
    "agile coach", "аджайл коуч",
    "delivery manager", "delivery lead",
    "release manager",
    "engineering manager", "ем", "инженер-менеджер",
    "head of engineering", "head of development",
    "head of qa", "head of data",
    "cto", "технический директор",
    "vp of engineering",
    "dev lead", "tech lead", "тех лид", "тех-лид", "техлид",
    "team lead", "тимлид", "тим-лид", "тим лид",
    "lead developer", "ведущий разработчик",
    "principal engineer", "principal developer",
    "staff engineer", "staff developer",
    "ic", "individual contributor",

    # ============================================================
    # АРХИТЕКТУРА
    # ============================================================
    "architect", "архитектор",
    "software architect", "архитектор по",
    "архитектор программного обеспечения",
    "system architect", "системный архитектор",
    "solution architect", "solutions architect",
    "архитектор решений",
    "enterprise architect", "корпоративный архитектор",
    "data architect", "архитектор данных",
    "cloud architect", "облачный архитектор",
    "security architect", "архитектор безопасности",
    "integration architect", "архитектор интеграций",
    "domain-driven design", "ddd", "доменно-ориентированный",

    # ============================================================
    # ОБЩИЕ РОЛИ
    # ============================================================
    "developer", "разработчик", "разработчики",
    "программист", "programmer", "coder",
    "software engineer", "инженер-программист",
    "software developer",
    "engineer", "инженер",
    "специалист",
    "fullstack", "full-stack", "full stack",
    "фуллстек", "фул стек", "фулстек",
    "frontend", "front-end", "front end",
    "фронтенд", "фронт", "фронтендер",
    "backend", "back-end", "back end",
    "бэкенд", "бэк", "бекенд", "бэкендер",
    "frontend developer", "frontend-developer", "frontend разработчик",
    "backend developer", "backend разработчик",
    "web developer", "веб-разработчик", "веб разработчик",
    "вебмастер",
    "devops", "девопс", "девопс-инженер", "devops engineer",
    "sre", "site reliability engineer", "инженер sre",
    "platform engineer", "platform engineering",
    "platform-инженер",
    "cloud engineer", "облачный инженер",
    "infrastructure engineer", "инфраструктурный инженер",
    "sysadmin", "system administrator",
    "системный администратор", "сисадмин",
    "network engineer", "сетевой инженер", "инженер по сетям",
    "network administrator",
    "support engineer", "инженер поддержки", "инженер сопровождения",
    "техническая поддержка", "техподдержка",
    "l1", "l2", "l3", "1 линия", "2 линия", "3 линия",
    "helpdesk", "хелпдеск",
    "технический специалист",
    "release engineer", "build engineer",
    "qa lead", "qa automation",
    "automation engineer",
    "ml engineer", "machine learning engineer",
    "инженер машинного обучения",
    "mlops engineer", "mlops-инженер",
    "llm engineer", "llm-инженер",
    "data engineer",
    "big data engineer", "инженер big data",
    "etl developer", "etl-разработчик",
    "ios engineer", "android engineer",
    "robotics engineer",
    "computer vision engineer", "cv engineer",
    "voice engineer",
    "speech engineer",
    "search engineer", "поисковый инженер",
    "ranking engineer",
    "recommender engineer",
    "growth engineer",
    "research engineer",

    # ============================================================
    # СЕНЬОРИТИ И УРОВНИ
    # ============================================================
    "junior", "junior+", "джуниор", "джун",
    "middle", "middle+", "мидл", "миддл",
    "senior", "senior+", "сеньор", "синьор", "сеньёр",
    "lead", "лид",
    "principal",
    "staff",
    "head",
    "intern", "trainee", "стажер", "стажёр", "стажировка", "стажерская",
    "начинающий разработчик",

    # ============================================================
    # 1С / SAP / ENTERPRISE
    # ============================================================
    "1с", "1c",
    "1с-разработчик", "1c-разработчик",
    "1с-программист", "1c-программист",
    "программист 1с", "программист 1c",
    "разработчик 1с", "разработчик 1c",
    "консультант 1с", "консультант 1c",
    "1с битрикс", "1c битрикс",
    "франчайзи 1с",
    "sap", "сап",
    "sap abap", "sap consultant", "sap-консультант",
    "sap basis", "sap fi", "sap mm", "sap sd", "sap pp",
    "sap hana",
    "ax", "axapta", "аксапта",
    "navision", "nav",
    "ms dynamics", "dynamics 365", "dynamics ax",
    "erp", "ерп",
    "scm", "ecm", "mdm", "мдм",
    "salesforce",
    "sharepoint",
    "битрикс", "bitrix", "bitrix24", "битрикс24",
    "modx", "drupal", "joomla",
    "magento", "opencart", "shopify", "woocommerce",
    "wordpress", "вордпресс",
    "low-code", "лоу-код", "low code",
    "no-code", "нокод", "нокодер", "no code",
    "1с-предприятие", "1c-предприятие",
    "1с erp", "1с зуп", "1с бухгалтерия", "1с унф", "1с документооборот",

    # ============================================================
    # МЕТОДОЛОГИИ И ПРАКТИКИ
    # ============================================================
    "agile", "аджайл",
    "scrum", "скрам",
    "kanban", "канбан",
    "waterfall",
    "lean",
    "xp", "extreme programming",
    "tdd", "test-driven development",
    "bdd", "behavior-driven development",
    "ddd", "domain-driven design",
    "oop", "ооп", "объектно-ориентированное программирование",
    "functional programming", "функциональное программирование", "фп",
    "design patterns", "паттерны проектирования", "шаблоны проектирования",
    "solid", "dry", "kiss", "yagni",
    "microservices", "микросервисы", "микросервисная архитектура",
    "monolith", "монолит",
    "event-driven", "event driven",
    "cqrs",
    "event sourcing",
    "domain", "bounded context",
    "saga pattern",

    # ============================================================
    # ПРОТОКОЛЫ И ФОРМАТЫ
    # ============================================================
    "api",
    "rest", "rest api", "restful",
    "graphql",
    "grpc",
    "soap",
    "websocket", "websockets", "вебсокеты",
    "mqtt",
    "amqp",
    "http", "https",
    "tcp/ip", "tcp", "udp",
    "tls", "ssl",
    "json", "xml", "yaml", "toml",
    "protobuf", "protocol buffers",
    "swagger",
    "openapi",
    "asyncapi",

    # ============================================================
    # ОПЕРАЦИОННЫЕ СИСТЕМЫ
    # ============================================================
    "linux", "линукс",
    "unix", "юникс",
    "windows server",
    "macos", "mac os",
    "freebsd",
    "debian", "ubuntu", "centos", "rhel", "fedora", "alpine",
    "astra linux", "астра линукс",
    "alt linux", "альт линукс",
    "red os",

    # ============================================================
    # GIT / СИСТЕМЫ КОНТРОЛЯ ВЕРСИЙ
    # ============================================================
    "git", "гит",
    "github",
    "gitlab",
    "bitbucket",
    "gitflow",
    "trunk-based development",
    "subversion", "svn",
    "mercurial",

    # ============================================================
    # АРХИТЕКТУРНЫЕ И СИСТЕМНЫЕ КОНЦЕПЦИИ
    # ============================================================
    "system design",
    "software architecture", "архитектура по",
    "code review", "ревью кода", "код-ревью",
    "code quality", "качество кода",
    "performance optimization", "оптимизация производительности",
    "рефакторинг", "refactoring",
    "legacy", "легаси",
    "computer science", "компьютерные науки", "сс",
    "algorithms", "алгоритмы",
    "data structures", "структуры данных",
    "distributed systems", "распределенные системы",
    "распределённые системы",
    "high load", "highload", "хайлоад",
    "высоконагруженные системы",
    "fault tolerance", "отказоустойчивость",
    "scalability", "масштабируемость",
    "real-time", "реальное время", "реалтайм",
    "cap theorem",

    # ============================================================
    # ПРОЧИЕ ИНСТРУМЕНТЫ И ТЕХНОЛОГИИ
    # ============================================================
    "jira", "джира",
    "confluence", "конфлюенс",
    "trello",
    "notion",
    "asana",
    "youtrack",
    "tracker", "яндекс трекер",
    "active directory", "ad",
    "ldap",
    "exchange",
    "kerberos",

    # ============================================================
    # СПЕЦИАЛИЗИРОВАННЫЕ НАПРАВЛЕНИЯ
    # ============================================================
    "fintech", "финтех",
    "edtech", "эдтех",
    "healthtech", "медтех",
    "adtech",
    "proptech",
    "agritech",
    "biotech",
    "lawtech", "legaltech",
    "high-tech", "хайтек",

    # ============================================================
    # СПЕЦИФИЧНЫЕ РУССКОЯЗЫЧНЫЕ ТЕРМИНЫ
    # ============================================================
    "айтишник", "айти", "ит-специалист", "it-специалист",
    "разраб",
    "кодер",
    "айти компания", "ит компания",
    "ит вакансия", "it вакансия",

    # ============================================================
    # ХЕШТЕГИ
    # ============================================================
    "#разработчик", "#developer", "#dev",
    "#python", "#java", "#javascript", "#typescript",
    "#golang", "#rust", "#kotlin", "#swift", "#php", "#ruby",
    "#cpp", "#csharp", "#dotnet",
    "#backend", "#frontend", "#fullstack",
    "#devops", "#sre", "#cloud",
    "#qa", "#qaengineer", "#тестировщик", "#testing",
    "#аналитик", "#analyst", "#dataanalyst", "#dataengineer",
    "#datascience", "#datascientist", "#ml", "#ai",
    "#mobile", "#ios", "#android", "#flutter", "#reactnative",
    "#react", "#vue", "#angular", "#nodejs",
    "#docker", "#kubernetes", "#k8s",
    "#aws", "#azure", "#gcp",
    "#sql", "#nosql", "#postgres", "#mongodb",
    "#linux", "#unix",
    "#git", "#github", "#gitlab",
    "#agile", "#scrum",
    "#1с", "#1c",
    "#it", "#ит", "#itjob", "#itjobs", "#itвакансия",
    "#геймдев", "#gamedev",
    "#блокчейн", "#blockchain", "#web3",
    "#ux", "#ui", "#uxui", "#design",
    "#cybersecurity", "#infosec", "#security",
    "#embedded", "#iot",
    "#mlops", "#llm", "#nlp", "#computervision",
    "#productmanager", "#projectmanager",
    "#scrummaster", "#productowner",
    "#techlead", "#teamlead", "#тимлид",
    "#senior", "#middle", "#junior",
    "#стажировка", "#intern",
    "#hr", "#ittech",
]

# ============================================================
# Слова со спецсимволами — матчатся как substring, не через \b
# (c++, c#, .net, node.js, 1с и подобные)
# ============================================================
_SPECIAL_CHARS = set('#+./\\@')

SPECIAL_CHAR_KEYWORDS: set[str] = {
    kw for kw in IT_ROLE_KEYWORDS
    if any(c in kw for c in _SPECIAL_CHARS)
}

# ============================================================
# Общие роли — засчитываются только если есть хотя бы 1 специфический ключ
# ============================================================
GENERAL_ROLE_KEYWORDS: set[str] = {
    "engineer", "инженер", "специалист", "analyst", "аналитик",
    "architect", "архитектор", "programmer", "разработчик", "developer",
    "программист", "дизайнер", "designer", "менеджер", "manager",
    "head", "lead", "лид", "staff", "principal",
    "разработчики",  # plural
}

# ============================================================
# Специфические ключи = всё что не general и не special
# ============================================================
SPECIFIC_KEYWORDS: set[str] = {
    kw for kw in IT_ROLE_KEYWORDS
    if kw not in SPECIAL_CHAR_KEYWORDS and kw not in GENERAL_ROLE_KEYWORDS
}


# ============================================================
# Нормализация текста
# ============================================================

def normalize(text: str) -> str:
    """Lowercase + ё->е + collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().replace('ё', 'е').replace('й', 'й')).strip()


# ============================================================
# Regex-паттерны
# ============================================================

def _build_word_pattern(words: set) -> re.Pattern:
    """Паттерн с \\b для обычных слов. Исключаем слова со спецсимволами."""
    clean = sorted(
        [re.escape(w) for w in words if not any(c in w for c in _SPECIAL_CHARS)],
        key=len,
        reverse=True,
    )
    if not clean:
        return re.compile(r'(?!)')  # never matches
    return re.compile(r'\b(' + '|'.join(clean) + r')\b', re.IGNORECASE)


# Паттерн для специфических слов (без спецсимволов)
SPECIFIC_RE: re.Pattern = _build_word_pattern(SPECIFIC_KEYWORDS)

# Паттерн для общих слов (без спецсимволов)
GENERAL_RE: re.Pattern = _build_word_pattern(GENERAL_ROLE_KEYWORDS)
