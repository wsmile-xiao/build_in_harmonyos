# libsigc++ 2.10.8 适配笔记

## 编译环境
- 构建系统: meson + ninja
- 编译日期: 2026-07-12
- 编译器: clang/clang++ (aarch64-linux-ohos, libc++, C++17)
- 状态: built

## 编译步骤

```bash
meson setup build --prefix=<pkg> \
  -Ddefault_library=shared -Dmaintainer-mode=false \
  -Dbuild-documentation=false -Dvalidation=false -Dbuild-pdf=false \
  -Dbuild-examples=false -Dbenchmark=false -Dwrap_mode=nodownload
meson compile -C build
meson test -C build      # 上游 32 个测试程序
meson install -C build
```

由 `conanfile.py` 的 `MesonToolchain` / `Meson` 驱动，配置选项在 `generate()` 中以
`tc.project_options` 声明，未裸用任何 shell 环境变量（R33）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tarball 无 `configure` | 2.10.8 的官方 tarball 由 `meson dist` 生成，仅含 `configure.ac`/`Makefile.am`，autotools 路线需 `autogen.sh` + mm-common + autoconf-archive | 直接走 meson 构建，不引入 autotools 引导依赖 |
| 2 | meson 探测归档器失败风险 | Conan 的 `MesonToolchain` 只把 `tools.build:compiler_executables` 的 `c`/`cpp` 写进 native file，meson 按裸名 `llvm-ar` 探测；鸿蒙 worker 的 clang 工具链在 `/data/service/hnp/bin`，`conan create` 时不在 PATH 上 | `generate()` 中从 C++ 编译器路径推导 `llvm-ar`/`llvm-ranlib` 全路径并注入 `conan_meson_native.ini` 的 `[binaries]`（与 pixman/cairo/bstring 同一模式，不污染 PATH） |
| 3 | docs/reference 可能联网拉 mm-common | `docs/reference/meson.build` 用 `dependency('mm-common-libstdc++', required: false)` 探测，源码树内有 `subprojects/mm-common.wrap`，默认 wrap 模式允许回退下载 | `-Dwrap_mode=nodownload`；同时 `-Dbuild-documentation=false`（worker 无 doxygen/dot/xsltproc） |
| 4 | 文档/示例引入无谓依赖 | `build-examples` 默认 true，`validation` 默认 true（需 xsltproc + DocBook DTD） | 全部关闭，只产出库、头文件与 pkg-config 文件 |
| 5 | 消费者找不到 `sigc++config.h` | 该头文件按 GNOME 惯例装到 `lib/sigc++-2.0/include`，不在 `include/` 下 | `package_info()` 的 `cpp_info.includedirs` 同时声明 `include/sigc++-2.0` 与 `lib/sigc++-2.0/include` |

## 源码修改

无。零补丁：libsigc++ 是纯 C++ 库（signal/slot 模板 + trackable），不触碰 glibc 专有接口、
procfs/sysfs、线程外的系统调用，musl + libc++ 下无需可移植性修改。

## 依赖版本

无第三方依赖。运行期仅依赖 `libc++`（工具链自带）与系统 `libc`（musl）。

## 验证结果

```bash
# 上游测试套件（tests/ 下 32 个程序，meson test）
Ok: 32   Fail: 0

# test_package 消费者测试
./test_libsigc
libsigc++ 2.10.8: all checks passed   # exit 0，11 条断言
```

产物：`lib/libsigc-2.0.so`（+ soname 软链）、`include/sigc++-2.0/sigc++/**`、
`lib/sigc++-2.0/include/sigc++config.h`、`lib/pkgconfig/sigc++-2.0.pc`、`licenses/COPYING`。

## 注意事项

- Conan 包名取 `libsigc`（归档目录 `archives/l/libsigc/`）；上游工程名与 pkg-config 名仍为
  `libsigc++` / `sigc++-2.0`，已通过 `cpp_info.set_property("pkg_config_name", "sigc++-2.0")`
  保证下游（glibmm、gtkmm 等）用 pkg-config 名可正常解析。
- 库名与系统库不同名（`libsigc-2.0.so`），按 R26 无需强制静态，默认动态由 Conan 管理依赖链。
- profile 的 `compiler.cppstd=17` 会覆盖上游默认的 `cpp_std=c++11`；2.10 分支在 C++17 下编译无告警、
  测试全通过。
