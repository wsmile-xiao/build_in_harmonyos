# libmpack-lua 1.0.13 HarmonyOS 移植记录

## 源码与依赖

- 官方源码：<https://github.com/libmpack/libmpack-lua/archive/refs/tags/1.0.13.tar.gz>
- SHA-256：`436a6a3973207403d3f20082002c32e74c25d9149ff2516dc06b0b41514044bf`
- 依赖：`lua/5.1.5`、`libmpack/1.0.5`
- 目标产物：`lib/lua/5.1/mpack.so`

上游 Makefile 默认使用源码树内的 Lua 5.1.5、libmpack 1.0.5 和 Busted。Conan 中已有对应依赖，因此配方改为直接使用 Conan 依赖：将 `lmpack.c` 编译为 Lua 原生模块，并静态链接 `libmpack`；Lua 主机 API 保持由运行时解释器提供。这样既保持 `require("mpack")` 的上游行为，也避免把另一套 Lua 或测试框架打入包内。

## 测试设计

- `test.lua` 保持未修改，通过 `test/upstream_runner.c` 和 `test/upstream_runner.lua` 提供最小 Busted 兼容层执行官方测试。
- 官方套件发现并执行 23 个用例；包含 `leak_test.lua` 子测试。
- `test_package/test_lmpack.c` 是真实 Lua 5.1 consumer，会执行 `dlopen()`、`dlsym(luaopen_mpack)`、`require("mpack")`，并验证 pack/unpack、BIN 模式、MsgPack-RPC 以及 `mpack.NIL`。
- HarmonyOS 专项检查额外验证 `__OHOS__` 宏、`uname()`、模块常规文件属性和 OHOS 目标上的动态加载符号解析。

## 验证结果

- Conan OHOS armv8 交叉构建：依赖解析、模块编译、上游测试 runner 编译、consumer 编译和打包均通过；由于当前 Windows 主机不能执行 armv8 OHOS 二进制，Conan 的运行阶段按 Conan 规则跳过。
- 正确的 `conan test archives/l/libmpack-lua/1.0.13/test_package libmpack-lua/1.0.13` 通过了 test_package 编译；同样因主机不能运行 armv8 OHOS 二进制而跳过运行阶段。
- OpenHarmony SDK x86_64 目标机（HDC `127.0.0.1:5555`）：consumer `8/8` 通过，并输出 `__OHOS__` 检查结果；官方上游套件 `23/23` 通过。
- 仓库 `ci/conan/build_and_test.sh` 已在本机尝试；该脚本要求 zsh，并在 Bash 兼容尝试中因本机缺少 OHOS SQLite 运行时停止，属于本机 CI 执行环境限制，不是包构建或测试失败。
- 当前 HDC 虚拟机未提供 `binary-sign-tool`，但使用 OpenHarmony SDK 生成的目标二进制和模块可正常加载执行；配方仅在真正可运行且签名工具可用的 OHOS Conan 环境中对测试可执行文件执行自签名。

上游 `lmpack.c` 在 clang 的 `-Wconversion` 下会报告若干 `size_t` 到 `double` 的精度转换警告；这些是上游代码已有行为，本次未修改上游源码，未发现错误或测试失败。

## 规范说明

`tests/` 目录未提供独立的 `SKILL.md`，本次移植遵循仓库根目录 `SKILL.md` 以及 `docs/TEST_QUALITY_SPEC.md` 的有效规范；未修改仓库级 CI、脚本、模板或其他已有本地变更。
