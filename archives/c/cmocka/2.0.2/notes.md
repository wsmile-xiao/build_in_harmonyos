# cmocka 2.0.2 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-30
- 本地验证编译器: MinGW GCC 8.1.0
- 本地验证工具: CMake 3.30.5-msvc23 + Ninja 1.12.1
- OHOS 真机验证: clang 15 / armv8 / OHOS 6.0
- 状态: built

## 编译步骤
Conan recipe 使用官方源码包：

```text
https://cmocka.org/files/2.0/cmocka-2.0.2.tar.xz
sha256: 39f92f366bdf3f1a02af4da75b4a5c52df6c9f7e736c7d65de13283f9f0ef416
```

构建选项：

- `BUILD_SHARED_LIBS=OFF`
- `WITH_EXAMPLES=ON`
- `UNIT_TESTING=ON`
- `PICKY_DEVELOPER=OFF`

`test_package` 编译并运行一个最小 cmocka 测试程序，验证：

- `find_package(cmocka REQUIRED)`
- 下游 `find_package(cmocka 1.1.0 REQUIRED)` 可接受 `cmocka/2.0.2`
- `cmocka::cmocka` target
- `cmocka_run_group_tests()` 可执行通过

本地 Conan 构建已通过。首次本地包引用：

```text
cmocka/2.0.2#6c239f72bceb60ead7f52276e9e73cd5:fe9a9f6787718522ad3eff6bfbcf54867de112b0#fb0c3ab564dd7cbc14d101905f161074
```

`test_package` 运行结果为 2 个用例全部通过。

追加 `cmake_config_version_compat=AnyNewerVersion` 后，本地已重新执行
`py_compile`、`conan export` 和 `git diff --check`。该兼容性元数据用于让
下游 `find_package(cmocka 1.1.0 REQUIRED)` 可接受 `cmocka/2.0.2`。

OHOS 真机 Conan 构建已通过，run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-cmocka-cmocka-2.0.2-newport-r2-conan-r1-20260730-185344-13742
```

包引用：

```text
cmocka/2.0.2#6c239f72bceb60ead7f52276e9e73cd5:21b17f8b2bc0e9511e276e3d57a23893067cefe5#e3e944abe74a10f5bd2f8f6b889683da
```

真机结果：`L0=pass`，`L1=pass`，`L2=skip(no bin/ dir)`，`L4=pass(no patches)`，
`L5=pass(lib/ has content)`，`L1e=pass`。`test_package` 运行 2/2 PASS。

下游 `nss-wrapper` 上游测试依赖验证已在新端口真机完成，run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-nss-wrapper-cmocka-upstream-r2-upstream-cmocka-r2-20260730-193826-36790
```

该轮先构建当前 `cmocka/2.0.2`，`test_package` 2/2 PASS，包引用：

```text
cmocka/2.0.2#7650239be635a24ee3440183b21882ee:21b17f8b2bc0e9511e276e3d57a23893067cefe5#2ba5dbae8ea25b7cc6449305ba18a04a
```

随后启用 `nss-wrapper` 的 `with_upstream_tests=True` 并添加
`cmocka/2.0.2` 测试依赖。CMake 已生成 `cmocka::cmocka` target，
`nss-wrapper` configure 和 generate 均完成，证明 `cmocka/2.0.2` 已能
满足其上游 `find_package(cmocka 1.1.0 REQUIRED)`。

在 `nss-wrapper` 继续补齐测试侧 NSS_STATUS fallback 和 shadow API 能力检测后，
新端口真机最终 upstream CTest 通过，run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-nss-wrapper-upstream-r4-rerun1-20260730-204550-6012
```

最终该轮先构建当前 `cmocka/2.0.2`，包引用：

```text
cmocka/2.0.2#7650239be635a24ee3440183b21882ee:21b17f8b2bc0e9511e276e3d57a23893067cefe5#8f803c886fde1137015abd219a2a9df2
```

随后 `nss-wrapper` 上游 CTest 9/9 registered PASS。原始 `test_shadow`
入口未注册，原因是 OHOS sysroot 有 `shadow.h`，但缺少
`setspent/getspent/endspent/getspnam`。

`cmocka` 自身官方 upstream CTest 已在新端口真机完成，run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-cmocka-upstream-tests-r1-settings-r2-20260730-223653-60221
```

该轮使用 job-local 临时 recipe 探针，在隔离副本中将 `UNIT_TESTING=ON`
并在 `build()` 后执行 `ctest -N` 与 `ctest --output-on-failure -j1`。
确认通过后，本地 recipe 已把 `UNIT_TESTING=ON` 和 CTest 执行纳入默认
构建验证路径。新端口 heavy runner `--try-lock` 获取锁等待 0 秒，rc=0。
第一次 r1 未进入源码，失败原因是
隔离 `CONAN_HOME` 缺 OHOS settings；从已验证 job 拷贝 `settings.yml`
后 r2 通过。

包引用：

```text
cmocka/2.0.2#7ad151e1fe9753a259739192379d2496:21b17f8b2bc0e9511e276e3d57a23893067cefe5#d372edded24c836bfc87356479b26c8a
```

上游测试范围为 release 源码 `tests/` 在 `UNIT_TESTING=ON` 下注册的
CTest entries；`WITH_EXAMPLES=OFF` 保持当前包构建口径，因此 examples
不纳入本轮统计。真机 `ctest -N` 注册 80 项，完整 CTest 80/80 PASS，
通过率 100.00%。同轮 CI runner 结果：`L0=pass`，`L1=pass(upstream tests + test_package executed)`，
`L2=skip(no bin/ dir)`，`L4=pass(no patches)`，`L5=pass(lib/ has content)`，
L1e 反向验证 pass。

`WITH_EXAMPLES=ON` 观察性探针也已在新端口真机完成，run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-cmocka-examples-r1-20260730-231028-18546
```

该轮同时打开 `UNIT_TESTING=ON` 和 `WITH_EXAMPLES=ON`，CTest 注册 91 项并
91/91 PASS。相对 `tests/` 的 80 项，examples 额外增加 11 项：
`calculator_test`、`simple_test`、`assert_macro_test`、`assert_module_test`、
`set_parameters_test`、`set_errno_tests`、`output_override_test`、
`expect_check_data_example`、`expect_check_data_advanced`、`waiter_test_wrap`、
`test_uptime`。其中 mock/wrap 示例 `waiter_test_wrap` 和 `test_uptime`
均通过，说明本轮未遇到 linker `--wrap` 或 `/proc/uptime` 示例阻塞。

examples 观察探针通过后，当前 recipe 已全量纳入 examples；正式 recipe
使用 `WITH_EXAMPLES=ON`，同时执行 `tests/` 与 examples/mock 的 CTest。

中间提交版 recipe 在 `WITH_EXAMPLES=OFF` 下的新端口真机重跑也已通过，
run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-cmocka-final-recipe-r1-20260730-234535-42032
```

该轮不再使用临时 recipe 变体，而是使用本地当前 recipe：`UNIT_TESTING=ON`、
`WITH_EXAMPLES=OFF`，并在 `build()` 中执行 `ctest -N` 和完整 CTest。
heavy runner `--try-lock` 获取锁等待 1 秒，rc=0。

包引用：

```text
cmocka/2.0.2#19109ecb0b664d240d6d18dea059d63f:21b17f8b2bc0e9511e276e3d57a23893067cefe5#048efa222986327e6600f4827f398db0
```

`ctest -N` 注册 80 项，完整 CTest 80/80 PASS，`test_package`
运行 2/2 PASS。同轮 CI runner 结果：`L0=pass`，
`L1=pass(upstream tests + test_package executed)`，`L2=skip(no bin/ dir)`，
`L4=pass(no patches)`，`L5=pass(lib/ has content)`，L1e 反向验证 pass。

当前提交版 recipe 全量启用 examples 后的新端口真机最终重跑已通过，run 目录：

```text
/storage/Users/currentUser/ohos-test-runs/codex-a-cmocka-full-recipe-examples-r1-20260731-002639-5248
```

该轮使用当前 recipe：`UNIT_TESTING=ON`、`WITH_EXAMPLES=ON`，并在
`build()` 中执行 `ctest -N` 和完整 CTest。heavy runner `--try-lock`
获取锁等待 0 秒，rc=0。

包引用：

```text
cmocka/2.0.2#07881f2c819b9063a0be6ece415bb688:21b17f8b2bc0e9511e276e3d57a23893067cefe5#065f91d9f00331e7993168ce11f5b9fa
```

`ctest -N` 注册 91 项，完整 CTest 91/91 PASS，`test_package`
运行 2/2 PASS。同轮 CI runner 结果：`L0=pass`，
`L1=pass(upstream tests + test_package executed)`，`L2=skip(no bin/ dir)`，
`L4=pass(no patches)`，`L5=pass(lib/ has content)`，L1e 反向验证 pass。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 旧记录写成 autotools | 2.0.2 官方源码实际是 CMake/Meson | 元数据和 recipe 改为 CMake |
| 2 | 本机 PATH 初始无 `cmake`/`ninja` | 工具未在默认 PATH 中 | 使用 Visual Studio BuildTools 自带 CMake/Ninja，并通过已有 MinGW Conan profile 做本地验证 |
| 3 | MSVC 本地构建失败 | 沙箱禁止 MSBuild 写入用户 Temp 下的 `MSBuildTemp` | 改用 MinGW/Ninja 验证 recipe；该问题属于本地 Windows 权限限制，不是 cmocka 源码或 recipe 编译错误 |
| 4 | 直接用 PowerShell/curl 拉源码失败 | 本机 TLS/凭据链路返回 `SEC_E_NO_CREDENTIALS` | 使用 Python urllib 成功下载官方 tarball，并校验 sha256 |
| 5 | 新端口隔离 `CONAN_HOME` 首次缺 OHOS settings | 新 job 的 Conan settings 未包含 `OHOS.version` | 仅在 job-local `conan-home/settings.yml` 补入 OHOS settings 后重跑通过 |
| 6 | `test_package` CMake 初次提示未知 `HarmonyOS` 平台 | test_package 未显式映射 OHOS CMake system | 在 test_package 的 `generate()` 中同步设置 `CMAKE_SYSTEM_NAME=Linux` 和 `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 7 | `nss-wrapper` 上游测试请求 `find_package(cmocka 1.1.0 REQUIRED)` 时拒绝 2.0.2 | Conan CMakeDeps 默认版本兼容策略为 `SameMajorVersion` | 设置 `cmake_config_version_compat=AnyNewerVersion`，允许下游请求 1.1.0 时消费更新的 2.0.2 |
| 8 | 新隔离 job 首次运行 upstream tests 前 `conan create` 报 `Invalid setting 'OHOS'` | job-local `CONAN_HOME/settings.yml` 被 setup 刷成不含 OHOS 枚举的默认 settings | 从已验证的新端口 job 拷贝带 OHOS 枚举的 `settings.yml` 后重跑；这是环境准备问题，不是源码或 recipe 问题 |
| 9 | 需要判断 examples 是否纳入默认 recipe | examples 会额外构建示例程序并扩大包构建口径 | 新端口探针确认 `WITH_EXAMPLES=ON` 91/91 PASS 后，按要求将 examples 纳入默认 recipe，并用当前 recipe final rerun 再次确认 91/91 PASS |

## B 路径推进状态

当前结论分三层：

- `cmocka` 基础适配已完成：OHOS 真机 `conan create + test_package`
  通过，`test_package` 2/2 PASS。
- `nss-wrapper` 下游依赖验证已完成：`cmocka/2.0.2` 可满足
  `find_package(cmocka 1.1.0 REQUIRED)`，结合 `nss-wrapper` 侧测试源码
  能力门控后，该库上游 CTest 已在真机完成 9/9 registered PASS。
- `cmocka` 自身官方 upstream CTest 已完成：`UNIT_TESTING=ON` 下注册
  80 项，真机完整 CTest 80/80 PASS。
- examples 已全量纳入当前 recipe：`UNIT_TESTING=ON` + `WITH_EXAMPLES=ON`
  注册 91 项，当前提交版 recipe 在真机完整 CTest 91/91 PASS。

下一次继续推进建议：

1. 准备 PR/B 路径材料时，分层写明基础包 2/2、新端口自身 upstream
   CTest 80/80、当前 recipe 全量 CTest 91/91、以及 `nss-wrapper` 下游 CTest
   9/9 的不同证据。
2. 推送 PR 后观察远端 CI 和 bot review，必要时按评论补充说明 examples
   已默认启用。
