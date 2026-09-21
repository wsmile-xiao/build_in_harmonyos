# raul 2.0.0 适配笔记

## 编译环境
- 构建系统: meson（上游 2.0.0 为纯头文件库：无库目标，仅 install_headers + pkg.generate）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，sysroot aarch64-linux-ohos）
- 目标平台: HarmonyOS PC (aarch64)，conan profile ohos-aarch64-device
- 状态: built

## 上游测试清点（R51 申报表）
| 项 | 值 |
|---|---|
| test/ 源文件 | 10 个 .cpp + test/headers/test_headers.cpp |
| meson test 注册数（meson test --list） | 11（10 单元测试 + test_headers 头文件自包含检查） |
| 实际执行 | 10（socket_test 平台 skip，见问题 1） |
| 通过 | 10/10 执行用例（100%） |
| 跳过 | 1（socket_test：OHOS 拒绝 AF_UNIX bind） |
| 依赖 | 无（各测试为自包含 assert/main 可执行文件，仅链接 pthread） |
| 数据/工具测试 | autoship/REUSE 为上游可选元数据检查，工具不在环境内时 meson 自动不注册 |

## 编译步骤
1. `init-build` 下载官方源码 `raul-2.0.0.tar.xz`（sha256 a6788d4f93bbb51618381112797776fa8bcbfe9b11bfc64021bb076770eb6e44）
2. `lang-preflight` → detected=cpp（meson.build project('raul', ['cpp'])，源码主体 100% C++）
3. 修改 .work/test/socket_test.cpp（补丁 0001），`refresh-patch --auto` 生成补丁
4. `conan-verify --profile ohos-aarch64-device`：G0–G4 + L2/L4/L5
5. `finish`：W2 结构 + R36 依赖 + W3 本地 CI（含 conan create 与 test_package）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | socket_test 断言 `unix_server_sock.bind("unix:///tmp/raul_test_sock")` 失败（Signal 6 core dumped） | OHOS 安全策略拒绝 AF_UNIX bind：/tmp 只读（EROFS=30）且可写目录同样 EPERM=1（python AF_UNIX 探针实证：$TMPDIR/cwd/data-local-tmp 全部失败；TCP 回环 bind 正常）。上游测试为 Linux 语义，OHOS 上不可执行 | 补丁 0001：bind 因平台策略失败（EPERM/EROFS/EACCES）时按 meson 约定以退出码 77 跳过（meson 记为 SKIP），其余断言与用例不变；非平台原因的 bind 失败仍返回 1 报错 |
| 2 | 初版补丁改 TMPDIR 后仍失败 | 误判根因为 /tmp 只读；实测可写目录亦 EPERM，AF_UNIX 整体被平台禁止 | 回退 TMPDIR 改动，改为平台能力探测 + meson skip（问题 1 的最终方案） |
| 3 | conan-init 构建系统探测误判为 autotools | 生成阶段未识别 meson.build，回退默认模板 | 按 `templates/conanfile-meson.py.tmpl` 与 c-list 3.1.0 先例手写 Meson 配方（tool_requires meson/1.11.0 + MesonToolchain） |
| 4 | （预防）CI worker PATH 不含 llvm-ar/llvm-ranlib，Meson 链接器探测可能失败 | 与 c-list/account-utils 同款环境差异 | generate() 从 `tools.build:compiler_executables` 推导同目录 llvm-ar/llvm-ranlib 写入 machine file [binaries] |

## 源码修改
- `patches/0001-test-socket_test.cpp.patch`：test/socket_test.cpp 在 AF_UNIX bind 因平台策略失败（EPERM/EROFS/EACCES）时打印原因并 `return 77`（meson SKIP）；非平台原因仍 `return 1`（失败）。新增 `#include <cerrno>`；+15/-1 行；无平台宏，通用可移植语义

## 依赖版本
- 无第三方库依赖（requires 为空；仅系统 pthread/threads）
- 构建工具：meson/1.11.0（tool_requires，制品仓 OHOS aarch64 二进制）

## 验证结果
```bash
# AF_UNIX 能力探针（python3，设备原生）
BIND_FAIL <TMPDIR>/probe.sock -> [Errno 1] Operation not permitted
BIND_FAIL ./probe.sock         -> [Errno 1] Operation not permitted
TCP_BIND_OK ('127.0.0.1', 51463)

# 上游 meson test（设备原生，与 conan create 同路径）
# 补丁前：socket_test FAIL（SIGABRT）；补丁后：Ok 10 + Skipped 1（socket_test exit 77）
raul/2.0.0: HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "executed": 10, "passed": 10, "failed": 0, "skipped": 1}

# 消费者测试（test_package/test_raul.cpp）
raul consumer test PASSED: 40 assertions
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| include/raul-2/raul/*.hpp | ~100 KB | 12 个公共头文件（上游 install_headers 布局） |
| lib/pkgconfig/raul-2.pc | ~300 B | 上游 pkg-config（filebase raul-2） |

## 注意事项
- 纯头文件库：消费方 `#include <raul/Array.hpp>`（include 根为 `<prefix>/include/raul-2`，与上游 pkg-config Cflags 一致）
- 上游 Meson 无库目标，`default_library`/`shared` 选项不适用，配方不提供 shared 选项
- socket_test 在 OHOS 记为 SKIP 而非 PASS/FAIL：平台能力缺失（AF_UNIX 被禁），如实登记于 MANIFEST.yml 与本文件

## 对话记录

### 对话 #1 — 适配与验证（2026-09-20/21）

- 初版补丁把 socket_test 临时路径改为 TMPDIR，conan create 中仍失败；python AF_UNIX
  探针定位为平台安全策略（可写目录 EPERM=1、/tmp EROFS=30，TCP 回环正常），改为
  平台能力探测 + meson skip（exit 77）后：10 项通过、1 项 SKIP。
- conan-verify G0–G4 PASS；W3 本地 CI 全门禁 PASS（L0/L1/L1e/L5）；消费者测试 40/40。
- finish 的 G0 clean-verify 因工具按 autotools 探测 configure 而失败（非阻塞；本包为
  Meson，conan-verify 的 G2 conan create 已实证构建与测试成功）。

**编译结束**: 2026-09-20
---

**编译结束**: 2026-09-21 00:18
**最终状态**: built
