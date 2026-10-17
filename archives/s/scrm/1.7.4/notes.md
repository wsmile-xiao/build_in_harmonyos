# scrm 1.7.4 适配记录

官方 standalone 最新稳定版本 1.7.4，CRAN 包为另一个 R 封装，不混用版本。任务 #10445 已由 2501_91199785 领取。

## 配方与构建

新增 CMake overlay 使用已发布 cppunit/1.15.1 和 Conan CMakeDeps，避免上游 Makefile.am 写死的 /opt/local/lib。原源文件和测试断言不变。单元测试独立编译 UNITTEST、forest-debug.cc、constant_generator.cc；算法测试使用生产核心。安装 scrm、man page 和许可证。

本地源码选项只接受 SHA-256 匹配的官方 tar，默认 CI 从 conandata.yml 官方 URL 下载。导出源码已直接进入源码目录时跳过同路径 copy，避免 src and dst must have different values；该模式已有知识，不重复申报。

## 失败和修复

1. 首轮同目录 copy 失败；比较真实路径后修复。
2. 第二轮 Conan、CTest 2/2、消费者 7/7 成功，但 CMake.test(--verbose) 未展开内部结果；复用 E301 改用 CMake.ctest。
3. 第三轮所有项通过；验证器假定 OK (N tests)，真实 CompilerOutputter 为 OK (N)。保留旧事务 FAIL，用新冻结验证器执行独立事务。
4. scrm-w3-20261009T101500Z 全量通过：上游 122/122、消费者 7/7、release/postrelease 通过。

E545 草稿增加合法 verbose 被错误层静默消费、真实摘要语法、逐组注册到运行名称闭包，不仅复述 E301。

## 测试与边界

原 TESTS 为 unit_tests algorithm_tests，内部注册分别 114、8，全部保留，种子 78361 和采样次数未减少。消费者七项断言另计。源码注册和最终日志唯一名称逐项相等。

本地真机完成不代表比赛 CI、AI Review 或发布通过。制品未上传，commands.json binary=false。仅申请路径 A+B，不申报路径 C。

## 最终状态

状态 built。官方 finish 的 W3_local_ci 子步骤在 scrm-w3-20261009T114000Z 执行成功，122 项上游及 7 项消费者测试通过，事务 release/postrelease 完成。Windows 传输投影仅把 CI 文本 CRLF 规范为 LF，并补齐软件级 commands.json，未修改仓库基础设施。

submit 的旧 packaging_present 检查与 ARCHIVE-SPEC v3.0“packaging 已废弃、使用 Conan create”冲突；保留失败记录，按 R14 手动执行相同 PRE_CREATE/POST_CREATE 合同、Git 提交及平台 PR 流程，不生成无效二进制归档、不跳过构建或测试。
