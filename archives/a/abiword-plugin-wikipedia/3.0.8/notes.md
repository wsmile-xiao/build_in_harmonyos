# abiword-plugin-wikipedia 3.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游完整 configure.ac 被替换为 minimal 版，仅构建 wikipedia 插件）
- 编译日期: 2026-08-14
- 编译器: clang/clang++（OHOS SDK，conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64 / OHOS / armv8)

## 源码与方案
- 源码: GNOME GitLab `World/AbiWord` release-3.0.8 tarball（11.4MB，git archive 无 configure）
  - url: https://gitlab.gnome.org/World/AbiWord/-/archive/release-3.0.8/AbiWord-release-3.0.8.tar.gz
  - sha256: 7c490e46f0a6143f84d5c7e3fed246f34486ad70cd55f162c792827607cd7e9a
- minimal 方案: 只构建 wikipedia 插件（上下文/主菜单注册 "Wi&ki Encyclopedia" 的在线百科查询模块）
  - 插件源码自包含: `plugins/wikipedia/xp/AbiWikipedia.cpp`（单文件）
  - AbiWord 运行时 API（XAP_App/XAP_Frame/FV_View/EV_EditMethod/EV_Menu_ActionSet/
    XAP_Menu_Factory/UT_String/UT_UCS4Char/xap_Module）由自写 compat/ shim 提供
  - **wikipedia 插件无任何 libgsf 引用** → 不需要 gsf shim（与 pdb/clarisworks 差异点）
  - 产出: `libabiword-plugin-wikipedia.so`，安装到 `lib/abiword-3.0/plugins/`
- 参考: sibling abiword-plugin-pdb/clarisworks 同款 minimal 方案

## 编译步骤
1. `init-build` 复用已缓存 tarball 解压源码（orig 目录保持 pristine）
2. 修改 configure.ac（替换为 minimal 版）与 Makefile.am（仅构建插件 + 端到端测试）
3. 编写 compat/ shim（18 个头文件 + abiword_shim.cpp）与 tests/test_wikipedia_plugin.cpp
4. `track-edit add` 记录全部 21 个被改/新增文件（R6）
5. 手动 diff（orig vs work）生成 2 个修改文件补丁（Makefile.am/configure.ac）
6. conanfile.py:
   - `source()`: 下载 + apply_conandata_patches（export sources 自动 merge 进 source 目录）
   - `build()`: `autoreconf -fi` → `_drop_umask_077(configure)` → `autotools.configure()`
     → `make -j1` → `make check -j1`
   - `package()`: `autotools.install()`
7. conan-verify 全绿: G0-G4 + L2/L4/L5 PASS；conan create 内 make check PASS（1 个端到端测试，36 项断言）+ test_package PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf -fi` 报 `automake: error: required file './ltmain.sh' not found`，且 libtoolize 提示 `putting auxiliary files in '../..'` | 安装的 libtoolize 硬编码 `SED=/storage/Users/currentUser/usr/local/bin/sed`（不存在）。SED 未设置时 extract-trace/aux-dir 启发式失败，向上走目录把 ltmain.sh 放到父目录 | 在 autoreconf 前显式设 `SED=/usr/bin/sed AUTOCONF=... AUTOHEADER=... AUTOM4TE=...`（conanfile `_prepare_autotools_env()`），libtoolize 正确把辅助文件放到 `.`。新知识草稿 E324 |
| 2 | `config.status[1019]: can't create ./confW15yqA/subs1.awk: Permission denied` | E114/E129: HMDFS 上 `umask 077 && mktemp -d` 生成的 0700 临时目录不可写（setgid） | conanfile.py `_drop_umask_077()` 运行时从生成的 configure 中删除 `umask 077`（aaphoto/pdb 同款方案），已有正式条目 E129/E114 |
| 3 | make 并行 jobserver FIFO EPERM | E074: 鸿蒙 SELinux 禁止创建 FIFO，make -j>1 卡住/报错 | 全部 `make` 调用带 `-j1`，已有正式条目 E074 |
| 4 | 上游 configure.ac 需要 gtk3/cairo/libgsf/wv/libxslt/boost 全链路 | HarmonyOS PC 无这些依赖 | 替换为 minimal configure.ac，只构建 wikipedia 插件 + compat shim |
| 5 | git archive 无 configure 脚本 | 上游 tarball 为 git archive 快照 | build() 中 `autoreconf -fi` 从 minimal configure.ac 生成 |
| 6 | 插件源码 `UT_return_val_if_fail` 未直接包含 ut_assert.h | 上游靠 xap_App.h 间接引入 ut_assert.h | compat/ut_string_class.h 显式 `#include "ut_assert.h"` |
| 7 | 直接运行 test 二进制（非 make check）找不到 libabiword-plugin-wikipedia.so | 测试链接插件模块 .so，RPATH 指向未安装的 `//lib/abiword-3.0/plugins` | 由 automake 测试框架注入 LD_LIBRARY_PATH；conan create 内 make check 正常运行通过 |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-Makefile.am.patch | 替换完整 Makefile.am 为 minimal 版：构建 libabiword-plugin-wikipedia.la（-module -avoid-version）+ 端到端测试 test_wikipedia_plugin |
| patches/0002-configure.ac.patch | 替换完整 configure.ac 为 minimal 版：AC_INIT(abiword-plugin-wikipedia) + AM_INIT_AUTOMAKE + LT_INIT(disable-static) + AC_CONFIG_FILES([Makefile]) |

非补丁源码（conanfile.py export_sources 传递）:
- compat/（18 个 .h + abiword_shim.cpp）: AbiWord 运行时 shim（XAP_App/XAP_Frame/FV_View/EV_EditMethod/EV_Menu_*/XAP_Menu_Factory/UT_*）
- tests/test_wikipedia_plugin.cpp: 端到端插件测试（dlopen→register→EditMethod/菜单校验→invoke→openURL→unregister，R34）

## 依赖版本
- 无 conan 依赖（dependency-free）：AbiWord 运行时 API 由 compat shim 提供
- 编译工具链: OHOS SDK clang/clang++ 15、autoconf/automake/libtool（环境预装）
- 运行时: dlopen（test_package 用 -ldl）

## 验证结果
- make check（构建期，conan create 内）: PASS 1/1（端到端测试内部 36/36 断言）
- test_package: PASS（dlopen 插件模块 → supports_version/register/unregister）
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS，见 reports/conan-verify-report.md
- 产物: libabiword-plugin-wikipedia.so（aarch64，仅依赖 libc/libc++，导出 abi_plugin_register/unregister/supports_version）

## 交付物
| 文件 | 说明 |
|------|------|
| libabiword-plugin-wikipedia.so | dlopen 型插件模块，安装到 lib/abiword-3.0/plugins/ |

## 注意事项
- 插件为 `-module -avoid-version` 可加载模块，消费者通过 dlopen 加载，不参与链接
  （conanfile `package_info()` 只声明 libdirs，libs 留空）
- 上游无官方测试（plugins/wikipedia 无 tests 目录）；make check 的 test_wikipedia_plugin 与
  test_package 的 run_test.cpp 均为适配自研（见 test_package/MANIFEST.yml 如实声明）
