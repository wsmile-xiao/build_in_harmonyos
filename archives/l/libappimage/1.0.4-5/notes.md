# libappimage 1.0.4-5 — 适配记录

**日期**: 2026-09-26
**状态**: ✅ 适配完成（conan create + test_package + ctest 100% 通过）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libappimage |
| 版本 | 1.0.4-5（commit 7acfb43e150e，tag v1.0.4-5） |
| 构建系统 | cmake（+ vendored squashfuse 走 autotools） |
| 源码 | https://github.com/AppImage/libappimage/archive/refs/tags/v1.0.4-5.tar.gz |
| SHA256 | 2c4e18860a790c5959da6eb064cbd07f165fe6a9b15989491a3a3f176d06af31 |
| 作用 | AppImage 管理/桌面集成库（libappimage.so、libappimage_shared.a、libappimage_hashlib.a） |

## 二、依赖设计

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | librsvg 强制精确版本；pkg_check_modules 用组件 .pc（glib-2.0/gobject-2.0/gio-2.0 等） |
| cairo-gobject | 1.18.4.3 | 仓库惯例 cairo 提供者（合并构建，libcairo + libcairo-gobject） |
| zlib | 1.3.1.1 | OHOS -fPIC 重建版（cnb 的 1.3.1/1.3.1.2 非 PIC，链 .so 会 relocation 报错） |
| librsvg | 2.62.3.1 | AppImage 缩略图后端（cairo/rsvg 图标渲染） |
| libarchive | 3.8.7 | payload 读写 |
| boost | 1.90.0.2 | Boost::filesystem（USE_SYSTEM_BOOST=ON） |
| xz | 5.6.2 | liblzma（与 libarchive/libtiff 一致）；xz recipe 无 pkg_config_name → generate() 手写 liblzma.pc |
| gtest | 1.17.0.2 | 替代 tarball 中未打包的 gtest 子模块（find_package(GTest)） |
| libfuse | 2.9.9（tool） | squashfuse configure 链接检查；静态库，运行时仅 dlopen |
| automake/autoconf/libtool | tool | vendored squashfuse 的 autotools 构建 |
| desktop-file-utils | 0.28（tool） | BUILD_TESTING 需要 desktop-file-validate |

## 三、适配过程与坑位

1. **vendoring**：xdg-utils-cxx v1.0.1 与 squashfuse 1f98030 在 Conan 制品仓均无包，
   两者源码进 conandata.yml（多 source get()），build() 中先行构建：
   - xdg-utils-cxx：独立 cmake 构建安装到 `<build_folder>/prefix`，
     dependencies.cmake 增加 `XDGUTILS_PREFIX` 逃生舱（list INSERT CMAKE_PREFIX_PATH），
     等价于上游 ExternalProject 的行为；
   - squashfuse：套用 appimage 项目自带的 squashfuse.patch + squashfuse_dlopen.patch
     （先 patch 再 dlopen patch，后者依赖前者对 Makefile.am/ll.c 的改动），
     `typedef off_t sqfs_off_t` → `int64_t`（off_t 在 OHOS aarch64 默认 32 位），
     `--disable-demo --disable-high-level --disable-shared --with-fuse=<libfuse pkg>`，
     产物 libsquashfuse.a/libsquashfuse_ll.a/libfuseprivate.a 静态合入 libappimage.so。
2. **CMake 4.x**：`cmake_minimum_required(VERSION 3.0-3.4)` 8 处统一提升到 3.5
   （补丁 0001）；xdg-utils-cxx 的 3.0 用 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 绕过。
3. **gtest 子模块缺失**：release tarball 的 `lib/gtest/` 为空 → 补丁 0004 改为
   `find_package(GTest REQUIRED)` + INTERFACE IMPORTED 别名（gtest→GTest::gtest）；
   gtest 1.17 要求 C++17，`set(CMAKE_CXX_STANDARD 17)` 仅置于 BUILD_TESTING 块内，
   库本体保持 C++11。
4. **libarchive 包名**：CMakeDeps 生成 `libarchive` 配置，上游的 `LibArchive` 找不到
   → 补丁 0002 改为 `(libarchive libarchive libarchive)`。
5. **cairo 提供者**：仓库惯例是 cairo-gobject/1.18.4.3（合并构建），
   pkg-config 模块名为 `cairo-gobject` → 补丁 0005 改
   `import_pkgconfig_target(... PKGCONFIG_TARGET cairo-gobject)`，
   target 名仍为 libcairo，对下游透明；同时避免与纯 cairo/1.18.4.2 双份 libcairo 冲突。
6. **xz 无 pkg_config_name**：PkgConfigDeps 不生成 liblzma.pc，而上游
   `pkg_check_modules(liblzma REQUIRED)` 必需 → generate() 手写 liblzma.pc 到
   generators_folder（CMakeToolchain 已把该目录挂上 PKG_CONFIG_PATH）。
   squashfuse.pc 同理手写，指向源树 .libs（静态合入 libappimage.so，消费者无需链接）。
7. **OHOS libc 为 musl**（非 bionic）：
   - **pthread_cancel / pthread_setcancelstate 未实现**（libc.so 导出 107 个 pthread
     符号但缺这两个）→ squashfuse configure 的 `-lfuse` 链接检查报
     `undefined symbol: pthread_cancel`。解决：build() 编译 no-op 桩
     `pthread_cancel_stub.c` → `compat/pthread_cancel_stub.a`，注入 squashfuse
     LDFLAGS、squashfuse.pc Libs 与 libappimage 的 CMAKE_SHARED_LINKER_FLAGS
     （静态合入 .so）；
   - **musl setenv/unsetenv 会 realloc environ 数组**，上游 test-xdg-basedir.cpp
     多处先缓存 `getenv()` 指针再 setenv/unsetenv 后使用 → 悬垂指针 UAF
     （glibc 不 realloc，上游 CI 通过）→ 补丁 0010 在 setenv 前 strdup；
   - 缺 `sys/cdefs.h`（`__BEGIN_DECLS` 未定义）→ 补丁 0006 为两份 light_elf.h
     增加 `#ifndef __BEGIN_DECLS` 回退块。
8. **libc++ 兼容**：libc++ 的 `std::istream` **无默认构造函数**（libstdc++ 有）→
   `PayloadIStream() = default;` 改为 `: std::istream(nullptr) {}`；
   streambuf 移动构造/赋值用了 libstdc++ 私有成员 `_M_in_beg/_M_in_cur/_M_in_end`
   → 改用标准访问器 `eback()/gptr()/egptr()`（补丁 0007）。
9. **boost 头文件变更**：新版 boost::filesystem 不再传递包含
   `boost/filesystem/fstream.hpp` → 测试文件显式 include（补丁 0008）；
   同补丁为 libappimage.c 补 `<limits.h>`（PATH_MAX 未声明）。
10. **OHOS 平台**：
    - XPM SIGKILL 未签名二进制/.so → ctest 前用 llvm-objcopy + binary-sign-tool
      对 build tree 可执行文件与 .so 做 selfSign；
    - /tmp 只读 → ctest 前 TMPDIR/HOME 指向可写目录；测试代码硬编码
      `/tmp/...` 的临时路径改为跟随 TMPDIR（补丁 0009）；
    - **测试数据 FS 截断**：/storage/Users 的 tmpfs overlay 在 conan copytree
      时偶发截断大文件（>180KB 的 AppImage 样本与 squashfs-root 目录受影响，
      源缓存副本完好）→ build() 中 `_repair_test_data()` 从 source 缓存
      （source() 捕获 `_src_cache_folder`，缺失时回退扫描 `~/.conan2/p/*/s`）
      恢复，只增不减；
    - **ctest 环境洁净**：OHOS 系统级导出 XDG_DATA_HOME 等，而上游 fixture
      只覆盖 HOME/XDG_DATA_HOME/XDG_CONFIG_HOME，thumbnail 测试用
      xdg_cache_home() 取到系统路径 → 补丁 0009 为 fixture 补齐
      XDG_CACHE_HOME 设置与恢复；ctest 不再内联覆盖 XDG_*（保持裸环境，
      env -i 验证全部通过）；
    - libappimage.pc 的 `prefix=@CMAKE_INSTALL_PREFIX@` 改写为 `${pcfiledir}/../..`，
      使随包发布的 .pc 可重定位。
11. **Conan 2 机制**：
    - build() 中 `source_folder == build_folder`（installer.py 在 build 前把缓存
      source copytree 到 build folder，`set_base_source(src)` 指向 build）→
      cmake 配置在 build 目录进行是正确行为；
    - VirtualRunEnv 仅在 `require.run=True` 时把 libdir 加入 LD_LIBRARY_PATH
      （Conan 2 默认 False）→ 全部 8 个 host requires 声明 `run=True`，
      否则 ctest 二进制报 "Error loading shared library libarchive.so.13"；
    - CMake wrapper 自动追加 `-DCMAKE_INSTALL_PREFIX=<package_folder>`，
      后出现的 -D 覆盖前者。

## 四、补丁清单
| 补丁 | 内容 |
|------|------|
| 0001 | cmake_minimum_required 3.0-3.4 → 3.5（CMake 4.x 兼容，8 个文件） |
| 0002 | libarchive find_package 名 LibArchive → libarchive |
| 0003 | dependencies.cmake 增加 XDGUTILS_PREFIX 逃生舱 |
| 0004 | gtest 子模块缺失 → find_package(GTest) + IMPORTED 别名 |
| 0005 | cairo pkg-config 模块名 cairo → cairo-gobject |
| 0006 | light_elf.h 增加 __BEGIN_DECLS/__END_DECLS 回退（OHOS 无 sys/cdefs.h） |
| 0007 | libc++ 兼容：istream 默认构造 + streambuf 移动改用标准访问器 |
| 0008 | boost 头文件变更适配（boost/filesystem/fstream.hpp 显式包含、PATH_MAX） |
| 0009 | 测试 TMPDIR 化：fixture 临时目录、XDG_CACHE_HOME 覆盖/恢复、硬编码 /tmp 路径、hardlink 提取目标路径 |
| 0010 | test-xdg-basedir.cpp 6 处 environ UAF 修复（setenv 前 strdup，musl 兼容） |

## 五、测试结果

- **上游 ctest：100% 通过（5/5）**
  - test_libappimage++：48 项全部 OK（TMPDIR 化 + 数据修复后）
  - test-xdg-basedir：8/8（补丁 0010 修复 musl environ UAF）
  - test_libappimage：全量 OK
  - test_shared：OK
  - TestDesktopIntegration：OK
- **本 recipe test_package**：编译链接 libappimage.so（cpp_info 直接链接 +
  -Wl,-rpath），运行 appimage_get_type / appimage_get_md5 /
  appimage_get_payload_offset（普通文件 + 构造的 Type-2 头），全部通过。
---

**编译结束**: 2026-09-26 20:24
**最终状态**: built
