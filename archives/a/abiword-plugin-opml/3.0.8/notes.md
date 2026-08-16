# abiword-plugin-opml 3.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游完整 configure.ac 被替换为 minimal 版，仅构建 OPML 导入插件）
- 编译日期: 2026-08-14
- 编译器: clang/clang++ 15（OHOS SDK，conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64 / OHOS / armv8)

## 源码与方案
- 源码: AbiWord release-3.0.8 上游源码
  - gitlab.gnome.org 官方 git archive 在本机网络不可达（TCP 超时），改用 **Debian pool 权威镜像**
  - url: https://mirrors.huaweicloud.com/debian/pool/main/a/abiword/abiword_3.0.8+ds.orig.tar.xz
  - sha256: a600ed11c8e5f1ae0c0f09993664429c7da0f7b02a4484bc23fb8dea1eaa059e
  - 顶层目录同为 AbiWord-release-3.0.8，已用 clarisworks 补丁 dry-run 验证文件一致
- minimal 方案: 只构建 OPML 导入插件（`.opml` outline 导入模块）
  - 插件源码自包含: `plugins/opml/xp/ie_imp_OPML.cpp`
  - OPML 插件**不依赖 libxml2**（plugin.m4 仅引用 ${PLUGIN_CFLAGS}/${PLUGIN_LIBS}，
    XML 解析用 AbiWord 自研 IE_Imp_XML）
  - AbiWord 运行时 API 由自写 compat/ shim 提供（AbiWord 核心未发布到 OHOS 制品仓）
  - 产出: `libabiword-plugin-opml.so`，安装到 `lib/abiword-3.0/plugins/`
- 参考: abiword-plugin-clarisworks 3.0.8（同族，同 minimal 方案）

## 编译步骤
1. `init-build` 下载解压源码（orig 目录保持 pristine）
2. 修改 configure.ac（替换为 minimal 版）与 Makefile.am（仅构建插件 + 端到端测试）
3. 编写 compat/ shim（17 个文件）与 tests/test_opml_plugin.cpp
4. `refresh-patch --auto` 生成补丁（仅 2 个修改文件；compat/tests 走 export_sources）
5. conanfile.py:
   - `source()`: 下载 + apply_conandata_patches（export sources 自动 merge 进 source 目录）
   - `build()`: `autoreconf -fi` → `_drop_umask_077(configure)` → `bash ./configure` → `make -j1` → `make check -j1`
   - `package()`: `make install DESTDIR`
6. conan create 全绿: make check PASS（端到端测试 26 项断言）+ test_package PASS（dlopen）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gitlab.gnome.org 网络不可达（TCP 超时） | 本机网络限制 | 改用 Debian pool 权威镜像（huaweicloud），已验证与官方源码树一致 |
| 2 | toybox `patch --dry-run` 真实应用 new-file 补丁 | 鸿蒙默认 /usr/bin/patch 为 toybox 0.8.12，dry-run 对 `--- /dev/null` 补丁真实创建文件 | compat/ 与 tests/ 走 conanfile.py `export_sources()`，补丁只保留 2 个修改文件（E258） |
| 3 | config.status 创建临时目录失败 | E114: HMDFS 上 `umask 077 && mktemp -d` 生成的 0700 临时目录不可写 | conanfile.py `_drop_umask_077()` 运行时移除（E114 正式条目） |
| 4 | make 并行 jobserver FIFO EPERM | E074: 鸿蒙 SELinux 禁止创建 FIFO | 全部 `make` 调用带 `-j1`（E074 正式条目） |
| 5 | 上游 configure.ac 需要 gtk3/cairo/libgsf/wv/libxslt/boost 全链路 | HarmonyOS PC 无这些依赖 | 替换为 minimal configure.ac，只构建 opml 插件 + compat shim |
| 6 | git archive 无 configure 脚本 | 上游 tarball 为 git archive 快照 | build() 中 `autoreconf -fi` 生成 |
| 7 | 环境 automake 硬编码绝对路径 | 安装的 automake/aclocal/libtoolize 指向不存在的 autoconf/autom4te | conanfile.py `_prepare_autotools_env()` 将 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 指到 PATH 实际位置 |
| 8 | clang-15 作为 CXX 不自动链接 C++ 运行时 | test_package 链接阶段缺 libc++ 符号 | test_package/conanfile.py 显式 `-stdlib=libc++ -lc++`；插件模块 LDFLAGS 同样加 `-lc++` |
| 9 | OHOS loader 忽略 LD_LIBRARY_PATH | test 运行时找不到插件 .so | 测试二进制链接 `-Wl,-rpath,$(abs_builddir)/.libs` |
| 10 | 本机 conan-verify 的 G2 通过 ELF conan 入口失败 | OHOS SELinux：ELF 包装器（dev_adhoc_bin_file/hmdfs 标签）exec python3 后落入 adhoc_bin 域，clang-15 在该域无法执行（静默 exit=1） | direct `python3 -m conans.conan create`（normal_hap 域）clean build 全绿；CI（Linux worker）无此域限制。已建 ELF launcher 桥接方案验证（bash 中转），记录 E 草稿 |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-Makefile.am.patch | 替换完整 Makefile.am 为 minimal 版：构建 libabiword-plugin-opml.la（-module -avoid-version）+ 端到端测试 test_opml_plugin（check-local 运行真实 ELF 测试二进制） |
| patches/0002-configure.ac.patch | 替换完整 configure.ac 为 minimal 版：AC_INIT(abiword-plugin-opml) + AM_INIT_AUTOMAKE + LT_INIT(disable-static) + AC_CONFIG_FILES([Makefile]) |

非补丁源码（conanfile.py export_sources 传递）:
- compat/（17 文件）: AbiWord 运行时 shim（IE_Imp/PD_Document/XAP_Module/UT_GrowBuf/IE_Imp_XML/fl_AutoNum/UT_String 等）+ 自研最小 SAX XML 解析器（abiword_shim.cpp _parse_xml）
- tests/test_opml_plugin.cpp: 端到端插件测试（dlopen→register→sniffer→importFile→26 项断言）

## 依赖版本
- 无 conan 依赖（dependency-free）：AbiWord 核心与外部库 API 由 compat shim 提供
- 编译工具链: OHOS SDK clang/clang++ 15、autoconf/automake/libtool（环境预装）
- 运行时: dlopen（test_package 用 -ldl）

## 验证结果
```bash
# conan create（clean source，全绿，direct python3 入口）
python3 -m conans.conan create archives/a/abiword-plugin-opml/3.0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing \
  --user=ohpcd --channel=stable
# → make check: PASS: abiword-plugin-opml end-to-end test succeeded（26 项断言全过）
# → test_package: PASS: abiword-plugin-opml module loaded, registered and unregistered
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，-j1，umask 修复，export_sources 传 compat/tests，ELF launcher 方案） |
| conandata.yml | 源码 URL（huaweicloud 权威镜像）+ sha256 + 2 个补丁声明 |
| patches/0001-Makefile.am.patch | minimal Makefile.am |
| patches/0002-configure.ac.patch | minimal configure.ac |
| compat/ | AbiWord 运行时 shim（17 文件）+ 自研 SAX XML 解析器 |
| tests/test_opml_plugin.cpp | 端到端插件测试（26 项断言） |
| test_package/ | conan 消费测试（dlopen 插件 ABI） |

## 注意事项
- **禁止为新增源码（compat/tests）生成 new-file 补丁**：toybox patch --dry-run 会真实应用，污染 orig 目录（E258）。
  新增文件一律走 export_sources。
- 知识条目: E114（umask 077 / HMDFS）、E074（make -j1 FIFO）、E258 草稿（toybox dry-run）
- make 必须 -j1（E074）；configure 生成后必须去除 umask 077（E114）
- 本机 conan-verify 若走 ELF conan 入口会因 adhoc_bin 域限制失败，用 direct python3 -m 方式验证（与 CI 行为一致）
