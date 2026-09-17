## PR 信息
- **三方库名称**：nanomsg（不含版本号！rule1+软件名校验）
- **上游版本**：1.2
- **上游仓库地址**：https://github.com/nanomsg/nanomsg
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E532（平台识别进 UNIX 分支）/ E461（AF_UNIX bind EPERM 平台限制定性参考）

> 源码包 URL（conandata.yml）: https://github.com/nanomsg/nanomsg/archive/refs/tags/1.2.tar.gz （SHA-256 见 conandata.yml：6ef7282e833df6a364f3617692ef21e59d5c4878acea4f2d7d36e21c8858de67）

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 43 | CMakeLists.txt `add_libnanomsg_test` 宏注册的 ctest 套件（`ctest -N` 实测：传输 8 项 + 协议 6 项 + 功能 29 项；win_sec_attr 为 WIN32 专属不注册） |
| 集成测试 | 0 | 上游无独立集成测试目录 |
| 其他测试 | 0 | perf/ 下 6 个为基准工具（inproc_lat 等），非测试用例 |
| **合计** | **43** | ← rule1：合计行必填 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 43 | 不变 | 本地（HarmonyOS PC aarch64 实机）完整跑上游 ctest 套件，39 通过 |
| 集成测试 | 0 | 不变 | — |
| **鸿蒙特有测试** | 1 | 新增 | ← rule12：test_package 消费者级 OHOS 特性验证（__OHOS__ 宏探测 + inproc/tcp 回环通信 + conanrun 环境递归 libdir） |
| **合计** | **44** | +1 | |

## 上游测试用例减少原因

上游 43 项全部真实执行（无减少）。CI 离线/产物精简考虑，conanfile 的 NN_TESTS=OFF 不在 conan create 内构建测试二进制，上游测试在本地实机独立源码构建中真跑（upstream-testing.md 决策树：CI 跑不了 → 本地联网补跑 → 实测数据入正文）：

```
ctest --output-on-failure  （HarmonyOS PC aarch64 实机，LD_LIBRARY_PATH 指向 install lib）
      39/43 tests passed, 91%
```

4 项失败逐项定性（均为平台限制，非源码缺陷——独立最小复现程序 `socket(AF_UNIX, SOCK_STREAM)` + `bind()` 同样返回 `Operation not permitted (errno=1)`，证明 HarmonyOS PC 当前系统策略禁用本地 AF_UNIX socket bind；与 nng 1.8.0 归档记录的同类限制一致）：

- `ipc`：环境限制（系统 AF_UNIX bind EPERM）。报错原文：`Failed bind to "ipc://test.ipc": Operation not permitted [1] (tests/ipc.c:63)`。本地补跑尝试：直接执行同报错（见上）
- `ipc_shutdown`：环境限制（同根因）。报错原文：`Failed bind to "ipc://test-shutdown.ipc": Operation not permitted (tests/ipc_shutdown.c:94)`
- `ipc_stress`：环境限制（同根因）。报错原文：`Assertion failed: nn_bind(sock, SOCKET_ADDRESS) >= 0 (tests/ipc_stress.c:50)`
- `separation`：环境限制（同根因，测试第二段走 ipc:// 传输）。报错原文：`Failed bind to "ipc://test-separation.ipc": Operation not permitted (tests/separation.c:81)`

tcp 传输全部通过（tcp/tcp_shutdown 2 项均绿），inproc/ws 全绿。

## 上游测试用例修改说明
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在修改（逐条：文件路径+修改原因+修改内容）

## 补全测试用例说明
- [ ] **否**，上游已有测试覆盖
- [x] **是**，上游无消费者级鸿蒙验证，适配后补全（新增 test_package/test.c：nn_socket/nn_bind/nn_connect/nn_send/nn_recv 闭环——inproc pair 回环 + tcp 127.0.0.1 回环 + pubsub/reqrep socket 创建 + __OHOS__ 宏探测，12 个断言点）

## 验证结果
- 编译状态：通过（conan create 全绿，Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created）
- 上游测试用例通过率：39/43（91%）
- 新增测试用例通过率：1/1（100%）

### 编译验证
- 编译器: clang 15 (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: CMake
- 配置选项: NN_ENABLE_DOC=OFF（CI 无 asciidoctor）/ NN_TESTS=OFF（上游测试本地实机独立跑）/ NN_TOOLS=ON

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | libnanomsg.so.5.0.0 + nanocat 工具 |
| 产物存在性 | ✅ | conan create 验证（include/lib/bin 完整） |
| ELF 格式 | ✅ | aarch64-unknown-linux-ohos |
| 运行测试 | ✅ | 39/43 上游 + 1/1 消费者 |

## 补丁说明
- patches/0001-CMakeLists.txt.patch：
  1. `cmake_minimum_required` 2.8.12 → 3.5（上游 2017 年老包，新版 cmake 拒绝 <3.5 声明）
  2. 新增 HarmonyOS 平台分支（`CMAKE_SYSTEM_NAME MATCHES "HarmonyOS"` → `NN_HAVE_HARMONYOS` + `NN_HAVE_LINUX` + `set(UNIX TRUE)`，与 Android 分支同构走 POSIX 路径）——平台特有，仅加平台定义不改通用逻辑

## 依赖
- 无运行时依赖（零依赖件：仅系统 pthread，musl libc 内建；W0 检查通过）

## 补充说明
- 版本号策略：1.2 为上游正式版本号（tag 精确格式 `1.2`，无 v 前缀，commit a081f1720f57）
- 已知限制：ipc:// 传输在当前 HarmonyOS 系统策略下不可用（AF_UNIX bind EPERM，见上方逐项定性）；inproc/tcp/ws 传输正常
- 本件是 nanomsgxx 0.2（平台任务 #6652）的直接前置依赖：nanomsgxx 链接 libnanomsg（find_package(nanomsg)），本包发布后 nanomsgxx 才能继续链接
- 环境语义核验（W0b）：历史归档 manifest/notes 为空模板骨架（2026-06-05 批量导入），无历史踩坑记录可迁移；历史 patch（平台识别）与本次实做语义一致，已保留
