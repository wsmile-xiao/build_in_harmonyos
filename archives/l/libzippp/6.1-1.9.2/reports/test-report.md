# libzippp 6.1-1.9.2 原生验证

HarmonyOS/aarch64，native Conan 2.29.1，clang15，Release/C++17。正式 native `conan create` RC0；全部24个原上游 assertion-active 函数在1个官方 CTest 容器执行，24/24，消费者1/1，独立鸿蒙专项1/1。不能将 CTest 容器与内部函数累加。

消费者通过安装目录的 CMakeDeps target 构建，调用真实 ZIP API；专项校验 HarmonyOS/aarch64、任务签名共享库的 dlopen/dlsym/dladdr 身份、HMDFS 投影归属语义、中文路径 ZIP 精确持久化/读回及清理。没有外设操作，不依赖其他任务的目录或进程。

唯一事务 libzippp-formal-20261005-r005：完整冻结输入、精确字节 transfer/readback、WAL/receipt 从 genesis 校验、唯一 launch、AFTER、owned_processes=0、release/postrelease PASS。完整 snapshot SHA-256：9957b1697e5df579dfec53e0a115e574396a94ebc8ae7a7393060591537e4b93。

仓内 native-conan-r005-verified-binding.json、result.json、清单和 raw-log-evidence-index.json 为结构化索引；原始 stdout/stderr 在任务外部冻结 snapshot，记录字节数和 SHA-256，不进入 PR。上游、消费者、专项共享同一真实 Conan 执行日志，不能冒充三轮独立测试。

原失败 r001（CMake.test 参数路由）、r002（签名输出权限）、r003（控制器 stdout JSON 混流）、r004（官方源码下载超时）保留真实 FAIL；均未被新 PASS 覆盖。当前 formal finish、平台 AI Review/CI、提审仍未完成，不宣称发布。
