# libsigc++ 3.0.6 适配笔记

## Scope

- Conan reference: `libsigc/3.0.6`
- Target: HarmonyOS/OHOS armv8 using the SDK Clang 15 toolchain
- Build system: Meson + Ninja
- Third-party Conan dependencies: none
- Delivery: shared library, headers, pkg-config metadata, and license

## Source

Official GNOME source tarball:
`https://download.gnome.org/sources/libsigc++/3.0/libsigc++-3.0.6.tar.xz`
(HTTP 200, 789916 bytes)

Full SHA-256: `b70edcf4611651c54a426e109b17196e1fa17da090592a5000e2d134c03ac5ce`
Archive root: `libsigc++-3.0.6/`（单一根目录）
Version evidence: `meson.build project('libsigc++', 'cpp', version: '3.0.6')`、
`configure.ac AC_INIT([libsigc++], [3.0.6], ...)`、`ChangeLog` 3.0.6 (2020-11-25)、
`NEWS` "3.0.6 (stable)"。

## Build

Meson 构建，39 个上游测试目标（tests/meson.build test_programs 列表）。

```bash
meson setup build --prefix=<pkg> \
  -Ddefault_library=shared -Dmaintainer-mode=false \
  -Dbuild-documentation=false -Dvalidation=false -Dbuild-pdf=false \
  -Dbuild-examples=false -Dbenchmark=false -Dwrap_mode=nodownload
meson compile -C build
meson test -C build      # 上游 39 个测试程序
meson install -C build
```

由 `conanfile.py` 的 `MesonToolchain` / `Meson` 驱动；OHOS 原生构建复用 2.x 线
（libsigc/2.10.8、2.12.1）的 meson 模式（E219 相关：llvm-ar/llvm-ranlib 注入）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 编译失败：`sigc::signal<int,int>` / `sigc::slot<int>` / `sigc::signal<void,const std::string&>` 报 "implicit instantiation of undefined template" | libsigc++ 3.x 的 signal/slot 模板改为函数类型语法 `signal<T_return(T_arg...)>` / `slot<T_return(T_arg...)>`；2.x 的 `signal<T_return, T_arg...>` 形态仅有前向声明（signal.h: class signal;）无定义 | test_package.cpp 改用 3.x 语法：`sigc::signal<int(int)>`、`sigc::slot<int()>`、`sigc::signal<void(const std::string&)>`（与上游 tests/test_signal.cc、test_slot.cc 用法一致） |
| 2 | conan-verify G1 配方完整性 FAIL | conanfile.py 缺少 `export_sources()` 方法与 `apply_conandata_patches` 调用 | 按仓库标准模板补齐 `export_sources()`（export_conandata_patches）与 source() 中 `apply_conandata_patches(self)` |

## 依赖版本

无第三方依赖（`sigcxx_build_dep = []`，`requirements()` 为空）。
运行期仅依赖 libc++ 与系统 libc（musl）。benchmark（需 boost）与文档
（doxygen/dot/xsltproc）均关闭。

## 验证结果

- `conan create`（含 test_package）：EXIT=0；上游 `meson test` 39/39 通过（`Ok: 39`）；
  consumer 输出 `libsigc++ 3.0.6 consumer checks passed`（12 断言）
- `conan-verify libsigc 3.0.6`：EXIT=0，G0/G1/G2/G3/G4 全 PASS，L2/L4/L5 通过
- `finish libsigc 3.0.6 published`：W2/W3/W4 通过；step6 gen_summary 为框架 bug
  （'str' object has no attribute 'append'），step8 为交付期产物（packaging/、
  .staging-verified、test-report.md），step2/step5b 因版本级 manifest/notes 补齐后恢复
- 共享库产物：libsigc-3.0.so（SONAME libsigc-3.0.so.0，meson libtool_soversion=[0,0,0]
  → libsigc-3.0.so.0.0.0），头文件 include/sigc++-3.0/，
  config 头 lib/sigc++-3.0/include/sigc++config.h，pkg-config sigc++-3.0.pc

## 注意事项

libsigc++ 3.x 与 2.x 的 ABI 不兼容（sigc++-3.0 vs sigc++-2.0），本配方为独立的
3.0.6（sigc++-3.0 ABI）包，glibmm 2.68+/gtkmm 3.x 等消费者需链接 sigc++-3.0。
---

**编译结束**: 2026-08-16 11:18
**最终状态**: built
