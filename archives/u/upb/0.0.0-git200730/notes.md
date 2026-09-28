# upb 0.0.0-git200730 OHOS 适配记录

平台任务 `contrib-11539`，`upb 0.0.0-git200730`，`taskBranch=feat/upb-0.0.0-git200730`，路径 A。

## 源码

- Debian orig：`https://deb.debian.org/debian/pool/main/u/upb/upb_0.0.0~git200730.orig.tar.xz`
- `sha256 = 1b70c6eb8176c96361382b8524028b1c69acc42b892c025dd364ab2614f68fe6`
- 快照含 checked-in 的 `generated_for_cmake/google/protobuf/descriptor.upb.{c,h}` 与 `generated_for_cmake/upb/json/parser.c`（Ragel 产物），因此核心库**不需要 protoc/ragel**。

## 构建

上游 CMakeLists 由 `tools/make_cmakelists.py` 生成，存在以下问题，故不走 CMake：

- 引用了从未定义的 `descriptor_upb_proto` 目标 → `descriptor.upb.c` 不参与编译；
- `cc_test` 被注释掉 → CMake 不构建任何测试；
- 没有任何 `install()` 规则。

配方直接用 OHOS clang 编译 21 个 C 源文件（`upb/**` 19 个 + 2 个 generated）为 `libupb.a`，
并安装头文件。无三方依赖。

## 上游测试（8 个 cc_test，实跑 2 个）

`tests/testmain.cc` 提供 `main`，各测试文件定义 `run_tests()`。本配方构建并实跑：

- `tests/pb/test_varint.c` —— 只依赖 `upb/pb/varint.int.h`，无生成头文件；
- `tests/test_table.cc` —— 只依赖 `upb/table.int.h`，无生成头文件。

其余逐条豁免（详见 `test_package/MANIFEST.yml`）：

| 测试 | 未运行原因 |
|---|---|
| test_cpp | 需 `tests/test_cpp.upbdefs.h`（protoc-gen-upb 生成） |
| test_generated_code | 需 `tests/test.upb.h`、`test_messages_proto3.upb.h` |
| pb/test_decoder | 需 `tests/pb/test_decoder.upbdefs.h` |
| pb/test_encoder | 需 `google/protobuf/descriptor.upbdefs.h` |
| json/test_json | 需 `tests/json/test.upb.h`/`test.upbdefs.h` |
| bindings/lua/test_upb.lua | 需 Lua 5.2 运行时与 upb Lua 绑定 |

生成这些头文件需要 `protoc` + `protoc-gen-upb` 插件，而 `upbc/` 需要 protobuf + abseil
与 Bazel 工具链，本环境不具备；Lua 绑定亦未构建。以上均在 MANIFEST 中声明。

## 消费者测试

`test_package/test_upb.c`：用已安装的 `upb/pb/varint.int.h` + `libupb.a` 验证
`upb_vencode64/32`、`upb_vdecode_check2_branch64`、zigzag、`upb_value_size`，共 9 项断言。

## 结果

- 真机 `conan create` 退出码 0；上游 2/2（其余 6 项逐条豁免）、消费者 9/9。
