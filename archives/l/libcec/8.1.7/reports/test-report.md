# libcec 8.1.7 测试报告

## 上游测试枚举台账（R51/R52 双口径）

**统计口径**：官方 tag `libcec-8.1.7`（sha256 e4ac4d1d…）解压后全目录枚举。

| 项目 | 结果 |
|---|---|
| source_declared_total（上游声明的独立测试用例） | 0 |
| configured_executable_total（当前 OHOS 配置实例化用例） | 0 |
| executed_passed_total | 0 |
| 失败数 / 未运行数 | 0 / 0 |

### 逐项台账

| 入口 | 类型 | 独立上游用例？ | 是否运行 | 说明 |
|---|---|---|---|---|
| 根 CMakeLists.txt / src/libcec/CMakeLists.txt | 构建目标 | 否 | — | 无 enable_testing/add_test/make check 目标（grep 全树无 ctest 注册） |
| src/rust/tests/{layout,safe_api,smoke}.rs | 绑定测试源 | 否 | 未运行 | 属可选 Rust 绑定（ENABLE_RUST_LIB=OFF 默认关闭）；需 cargo，设备无 Rust 工具链；不进入 C++ 核心库构建图，按 R47 绑定类包不计入 C++ 用例 |
| src/rust/examples、src/nodejs/example | 样例 | 否 | 未运行 | 示例非测试，且两绑定默认 OFF |
| src/dotnet（gitmodule 空目录） | 绑定 | 否 | — | 子模块未随 tarball 展开，且 .NET 绑定默认 OFF |
| windows/test.py | 打包脚本 | 否 | — | Windows 打包辅助脚本，非测试用例 |
| pyCecClient | 演示客户端 | 否 | — | Python 演示程序，非测试 |

**结论**：上游 C++ 核心库在 8.1.7 官方 tag 中未声明任何独立可执行测试用例，
全量通过率口径为 0/0（无独立上游用例可运行，非失败）。上游测试入口缺失不阻塞交付；
测试验证由下方消费者用例 + 鸿蒙专项测试承担。

## test_package 消费者用例（L1，conan create 内执行）

| 用例 | 命令 | 调用公开 API | 结果 |
|---|---|---|---|
| test_libcec | ./test_libcec | libcec_clear_configuration / libcec_initialise / libcec_get_lib_info / libcec_destroy | PASS（lib info: , features: P8_USB, DRM） |
| test_libcec_ohos | ./test_libcec_ohos | 版本宏断言 + libcec_initialise + libcec_detect_adapters | PASS（detect_adapters rc=0，无适配器优雅返回） |

## W3 本地 CI（conan create + L0/L1/L2/L4/L5）

- L0（配方静态检查）：pass
- L1（test_package 执行）：pass
- L2（CLI smoke）：cec-client --help / cec-client-8.1.7 --help / cecc-client --help / cecc-client-8.1.7 --help 全 OK；pyCecClient 非阻塞失败
- L4（patch 清理）：pass（无补丁）
- L5（产物）：pass（bin/ 含 CLI）
- `.ci-result.json` exit_code=0，log_sha256=97dfffe3d79559115419e591c0bc2cb5e79bdaee9fddc2886c2b9994235707d7

## 消费者可用性验证（硬门禁）

消费者用例 `test.c` 仅使用安装导出公开头 `<libcec/cecc.h>` 与公开 C API，模拟业务
上层组件：初始化配置 → libcec_initialise 创建实例 → libcec_get_lib_info 读取可观察
结果（features: P8_USB, DRM）→ libcec_destroy 销毁。真机编译链接运行 PASS。

## 环境

- 设备：HarmonyOS aarch64（HongMeng Kernel 1.12.0）
- 工具链：clang 15.0.4，conan 2.29.1（OHOS 适配版）
- profile：ci/conan/profiles/ohos-aarch64
