# sgc 3.6.0 适配笔记

## 编译环境

- 构建系统: meson (上游 `meson.build` + `meson_options.txt`, `cpp_std=c++17`)
- 编译日期: 2026-09-19
- 编译器: clang / clang++
- 状态: built
- 包名说明: 本配方命名为 `sgc`，打包的上游源码为 libsigc++ 3.6.0
  (https://github.com/libsigcplusplus/libsigcplusplus, tag 3.6.0)，
  许可证 LGPL-2.1-or-later。产物库名为 `libsigc-3.0`，pkg-config 名为
  `sigc++-3.0`，头文件根为 `include/sigc++-3.0` 与 `lib/sigc++-3.0/include`
  (生成的 `sigc++config.h` 所在目录)。

## 编译步骤

1. `get()` 获取上游 release tarball `libsigc++-3.6.0.tar.xz` 并解压
   (URL 使用字面 `++`，不用 `%2B%2B` 编码，避免 file:// 预下载缓存文件名失配)。
2. `MesonToolchain` 写入工程选项:
   `default_library=static/shared` (跟随 `shared` 选项),
   `wrap_mode=nofallback`, `benchmark=false`。
3. 在生成的 `conan_meson_native.ini` 的 `[binaries]` 段按绝对路径 pin `ar`
   (候选链: conf 编译器配置 -> 编译器同目录 -> OHOS SDK native llvm ->
   `/data/service/hnp/bin/llvm-ar` -> PATH)。
4. `Meson.configure()` + `Meson.build()`。
5. `Meson.test()` 在 build 阶段运行上游全部测试
   (上游 `build-tests` 选项默认开启，共 40 个测试可执行文件)。
6. `Meson.install()` 安装，随后 `test_package` 以 CMake 消费者视角链接验证。

## 上游测试审计

- 上游测试位置: 源码 `tests/*.cc`，通过 `tests/meson.build` 的 `test_programs`
  列表注册为 40 个 `meson test` 用例
  (test_accum_iter, test_accumulated, test_bind, test_bind_as_slot,
  test_bind_ref, test_bind_refptr, test_bind_return, test_compose,
  test_connection, test_copy_invalid_slot, test_cpp11_lambda, test_custom,
  test_disconnect, test_disconnect_during_emit, test_exception_catch,
  test_hide, test_limit_reference, test_member_method_trait, test_mem_fun,
  test_ptr_fun, test_retype, test_retype_return, test_rvalue_ref,
  test_scoped_connection, test_signal, test_signal_move, test_size, test_slot,
  test_slot_disconnect, test_slot_move, test_trackable 等，详见
  `test_package/MANIFEST.yml` 全清单)。
- `tests/benchmark.cc` 需要 boost 且不属于 `meson test` 门禁，配方以
  `benchmark=false` 关闭，属于上游支持的 opt-in 选项，非跳过测试。
- test_package 消费者测试覆盖 signal/slot/emit、connection 断开、bind 偏应用、
  trackable 自动断开 4 组契约，映射上游 test_signal / test_bind / test_trackable。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 3.6.0 release tarball 无预生成 `configure` 脚本 | 上游 3.x 主力构建系统为 Meson，源码含 `configure.ac` 但 release 包不再保证 autotools 可直接构建 | 配方采用 `conan.tools.meson.Meson`，manifest 记 `build.system: meson` |
| 2 | CI 上 `meson test` 报 `Unknown linker(s): [['llvm-ar']]` | worker 的 Meson PATH 未必含 llvm-ar，profile buildenv 只追加 `/data/service/hnp/bin`，部分 worker 该目录缺 llvm-ar | 复用 E481 模式: `_find_llvm_ar()` 按候选链解析绝对路径并写入 native 文件 `[binaries] ar` |
| 3 | `%2B%2B` 编码 URL 在 source() 报 FileNotFoundError | conan 对 file:// 路径做 percent-decode，缓存文件名与解码后文件名不一致 | conandata 统一使用字面 `++` 的官方 release URL |

## 源码修改

无补丁。libsigc++ 3.6.0 在 HarmonyOS PC (aarch64) 原生构建，无需源码修改。

## 依赖版本

- 无外部运行时依赖 (纯 C++17 标准库)。
- 构建工具: meson (Conan MesonToolchain), ninja, clang 15, pkg-config。

## 验证结果

```bash
# 上游官方测试 (meson test, 40 个用例) 在 build() 末尾执行
# test_package 消费者测试 (CMake, 链接 sigc++::sigc++ 并运行 5 组断言)
# 具体执行数/通过数以 HarmonyOS aarch64 真机预检日志为准
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 配方，build() 内运行 meson.test() |
| conandata.yml | 上游 tarball URL + SHA256 |
| test_package/test_package.cc | 实际调用 sigc++ API 的消费者测试 (R34) |
| test_package/MANIFEST.yml | 40 个上游用例清单 + 消费者测试声明 |
| manifest.yaml | 版本级清单，build.system=meson |

## 注意事项

- R26 不适用: sgc 不是系统同名库，默认 static (`default_options.shared=False`)。
- R32: sgc 为纯标准 C++，无平台分支，无需 `os in ("Linux", "OHOS")` 守卫。
- R34 落点: test_package.cc 实际调用 `sigc::signal/slot/connection/bind/trackable` API。
- R36 落点: sgc 无外部依赖。
