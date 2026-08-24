# astra-toolbox 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools (build/linux: configure.ac + Makefile.in + autogen.sh)
- 编译日期: 2026-08-22
- 编译器: clang 15 / clang++ 15 (aarch64-unknown-linux-gnu, OHOS 6.0)
- 状态: built (OHOS armv8, conan create 通过)

## 编译步骤
1. `get` 下载 `https://github.com/astra-toolbox/astra-toolbox/archive/refs/tags/v2.3.0.tar.gz` (sha256 `f47371b8...c2198`)
2. `apply_conandata_patches` 应用 `patches/0001-config.sub-ohos.patch` (build/linux/config.sub.dist 识别 `linux-ohos`)
3. `build_requirements`: `automake/1.18` + `libtool/2.5.4` (SDK 已提供 autoconf 2.72/m4/perl)
4. `_prepare_build_env` 设置 `TMPDIR`/`CONFIG_SHELL`/`ACLOCAL_PATH`，注入 mktemp-wrapper 规避 HMDFS `mktemp -d` 权限问题
5. `build/linux/autogen.sh` (aclocal + autoconf + libtoolize) 生成 `configure`
6. `Autotools.configure(build_script_folder=build/linux)` 参数 `--build/--host=aarch64-unknown-linux-gnu --with-cuda=no --disable-shared --enable-static`
7. `Autotools.make(-j1)` 编译约 80 个 `src/*.cpp` 为 `libastra`
8. `Autotools.install` + 手工补齐 `include/astra/*.h/*.inl` 与 `libastra.pc` 到 package

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 初始 `conandata.yml` 用 `sources: "2.3.0": {url,sha256}` 导致 `get() got unexpected keyword argument '2.3.0'` | conandata 版本键需解包 | `source()` 中 `self.conan_data["sources"][self.version]` 解包后 `get()` |
| 2 | `patch --dry-run` `Hunk 1 FAILED 115` | rebase 后补丁上下文过期/制表符冗余 | 用 `diff -U3` 从干净 a/b 树重制 unified diff，4 处 `linux-ohos` 落盘，`patch -p1 --dry-run` 通过 |
| 3 | `CMake Error: Imported target includes non-existent path .../p/include` | 上游默认 `make install` 在 `--with-cuda=no` 时仅装 `lib`，头文件在 `install-headers` | `package()` 手工 `copy` `include/astra/*.h/*.inl` 与 `libastra.pc` |
| 4 | `conan create` 5~8 分钟 `make -j1` 超 300s 超时 | 单线程编译 80+ 源文件 + 大量 `-Woverride` 日志 | 后台 `nohup conan create` + 轮询 `astra-conan.log`，最终 `Built target astra_toolbox_smoke` / `smoke PASS` |

## 源码修改
- `patches/0001-config.sub-ohos.patch` (portability): 在 `build/linux/config.sub.dist` 两处匹配分支添加 `linux-ohos`，使 `--host/--build=aarch64-unknown-linux-gnu` 在 OHOS 上可识别 (4 行变更，`patch -p1 --dry-run` 通过)。

## 依赖版本
- 运行时: 无 (零依赖)
- 构建时: `automake/1.18`, `libtool/2.5.4` (tool_requires); SDK: `autoconf 2.72`, `clang 15.0.4`, `cmake 4.1.2`, `make 4.4.1`

## 验证结果
```bash
conan create archives/a/astra-toolbox/2.3.0 --version=2.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# Package: astra-toolbox/2.3.0#683e1aa...:4b97726...#84889f2...
# lib: libastra.a (16 MB), headers: 118 .h + 10 .inl under include/astra/, pkgconfig: libastra.pc
# test_package: ./astra_toolbox_smoke
# astra-toolbox version=203 (2.3.0)
# smoke PASS
conan list "astra-toolbox/2.3.0:*"  # -> 4b977264... (shared=False, OHOS armv8 Release)
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libastra.a | ~16 MB | 静态库 |
| include/astra/*.h (118) + *.inl (10) | - | 公共头 |
| lib/pkgconfig/libastra.pc | <1 KB | pkg-config |

## 注意事项
- OHOS 默认无 CUDA/MATLAB/Python，`--with-cuda=no` 是关键；需 CUDA 时另起版本。
- 本配方为 `autotools` + `build/linux` 子目录构建 (`build_script_folder=build/linux`)，`autogen.sh` 需在 `conanbuild` 环境下执行。
- `make -j1` 约 5~8 分钟属正常，前台 300s 会超时，重跑请用后台轮询。
