# abiword-plugin-pdb 3.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游完整 configure.ac 被替换为 minimal 版，仅构建 pdb 插件）
- 编译日期: 2026-08-13
- 编译器: clang/clang++（OHOS SDK，conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64 / OHOS / armv8)

## 源码与方案
- 源码: GNOME GitLab `World/AbiWord` release-3.0.8 tarball（11.4MB，git archive 无 configure）
  - url: https://gitlab.gnome.org/World/AbiWord/-/archive/release-3.0.8/AbiWord-release-3.0.8.tar.gz
  - sha256: 7c490e46f0a6143f84d5c7e3fed246f34486ad70cd55f162c792827607cd7e9a
- minimal 方案: 只构建 pdb（PalmDoc）导入/导出插件模块
  - 插件源码自包含: `plugins/pdb/xp/ie_imp_PalmDoc.cpp/.h` + `ie_exp_PalmDoc.cpp/.h` + `ie_impexp_PalmDoc.cpp/.h`
  - AbiWord 运行时 API（IE_Imp/IE_Exp/PD_Document/XAP_Module/UT_GrowBuf/UT_UCS4_mbtowc）与
    libgsf GsfInput/GsfOutput API 由自写 compat/ shim 提供（libgsf 与 AbiWord 核心未发布到 OHOS 制品仓）
  - 产出: `libabiword-plugin-pdb.so`，安装到 `lib/abiword-3.0/plugins/`
- 参考: sibling abiword-plugin-clarisworks 3.0.8 同款 minimal 方案；pdb 插件额外需要
  **GsfOutput** shim（导出方向，`gsf_output_write/seek/tell` + 可增长内存缓冲区）

## 编译步骤
1. `init-build` 下载解压源码（orig 目录保持 pristine，复用已缓存 abiword-3.0.8.tar.gz）
2. 修改 configure.ac（替换为 minimal 版）与 Makefile.am（仅构建插件 + 端到端测试）
3. 编写 compat/ shim（18 文件 = clarisworks 基线 + GsfOutput/IE_Exp/ut_mbtowc/ut_path/
   xap_EncodingManager 扩展）与 tests/test_pdb_plugin.cpp
4. `refresh-patch --auto` 生成补丁（仅 2 个修改文件；compat/tests 走 export_sources）
5. conanfile.py:
   - `source()`: 下载 + apply_conandata_patches（export sources 自动 merge 进 source 目录）
   - `build()`: `autoreconf -fi` → `_drop_umask_077(configure)` → `autotools.configure()`
     → `make -j1` → `make check -j1`
   - `package()`: `autotools.install()`
6. 手动编译全绿: configure → make -j1 → make install DESTDIR（插件落位
   lib/abiword-3.0/plugins/）→ **make check: 1/1 PASS（39/39 断言）**
7. conan create 全绿（见验证结果）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | toybox `patch --dry-run` 真实应用 new-file 补丁 | 鸿蒙默认 /usr/bin/patch 为 toybox 0.8.12，其 dry-run 对 new-file 补丁真实创建文件，污染 pristine orig 目录（E258 草稿） | compat/ 与 tests/ 不再生成补丁，改为 conanfile.py `export_sources()` 传递；补丁只保留 2 个修改文件（Makefile.am、configure.ac） |
| 2 | config.status 创建临时目录失败 | E114: HMDFS 上 `umask 077 && mktemp -d` 生成的 0700 临时目录不可写（setgid） | conanfile.py `_drop_umask_077()` 运行时从生成的 configure 中删除 `umask 077`，已有正式条目 E114 |
| 3 | make 并行 jobserver FIFO EPERM | E074: 鸿蒙 SELinux 禁止创建 FIFO，make -j>1 卡住/报错 | 全部 `make` 调用带 `-j1`，已有正式条目 E074 |
| 4 | 上游 configure.ac 需要 gtk3/cairo/libgsf/wv/libxslt/boost 全链路 | HarmonyOS PC 无这些依赖 | 替换为 minimal configure.ac，只构建 pdb 插件 + compat shim |
| 5 | git archive 无 configure 脚本 | 上游 tarball 为 git archive 快照 | build() 中 `autoreconf -fi` 从 minimal configure.ac 生成 |
| 6 | 环境 automake 硬编码绝对路径 | 安装的 automake/aclocal/libtoolize 指向不存在的 autoconf/autom4te/sed | conanfile.py `_prepare_autotools_env()` 将 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 指到 PATH 实际位置 |
| 7 | `xxx_UT_DEBUGMSG` 未声明 | 上游 ie_exp_PalmDoc.cpp 使用永久禁用的 `xxx_UT_DEBUGMSG` 调试宏，clarisworks 版 ut_debugmsg.h 未提供 | compat/ut_debugmsg.h 增加 `#define xxx_UT_DEBUGMSG(M)` |
| 8 | `UT_ASSERT` 未声明 | 上游 ie_impexp_PalmDoc.cpp 通过 ie_imp.h 传递使用 UT_ASSERT（真实 ie_imp.h include ut_assert.h） | compat/ie_imp.h 增加 `#include "ut_assert.h"` |
| 9 | `gsf_off_t` 重复/缺失定义 | GsfOutput shim 独立于 GsfInput，两 header 各自 typedef `gsf_off_t` | 移到 compat/glib.h 统一 typedef（带 GSF_OFF_T_DEFINED 守卫），两个 gsf header 复用 |
| 10 | libtoolize 把 aux 文件放到上级目录 | autoreconf 首次运行环境不完整（SED/AUTOCONF 未设），libtoolize 探测包根目录失败 | 先设 SED/AUTOCONF/AUTOM4TE/AUTOHEADER 再运行 autoreconf -fi（manual 构建与 conan 构建均验证） |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-Makefile.am.patch | 替换完整 Makefile.am 为 minimal 版：构建 libabiword-plugin-pdb.la（-module -avoid-version）+ 端到端测试 test_pdb_plugin |
| patches/0002-configure.ac.patch | 替换完整 configure.ac 为 minimal 版：AC_INIT(abiword-plugin-pdb) + AM_INIT_AUTOMAKE + LT_INIT(disable-static) + AC_CONFIG_FILES([Makefile]) |

非补丁源码（conanfile.py export_sources 传递）:
- compat/（18 个文件）: AbiWord/libgsf 运行时 shim
  - clarisworks 基线: abiword_shim.cpp / glib.h / ut_types.h / ut_assert.h / ut_debugmsg.h /
    ut_string.h / ut_growbuf.h / ie_types.h / ie_imp.h / pd_Document.h / xap_Module.h / gsf/gsf-input.h
  - pdb 扩展: gsf/gsf-output.h（GsfOutput 可增长内存缓冲区 + write/seek/tell）/
    ie_exp.h（IE_ExpSniffer/IE_Exp 导出框架 + registerExporter）/
    ie_exp_Text.h（文本导出基类，遍历 PD_Document 文本 span 调 _writeBytes）/
    ut_mbtowc.h（UT_UCS4_mbtowc，Latin-1 → UCS4）/
    ut_path.h（UT_basename）/
    xap_EncodingManager.h（仅类名占位）
- tests/test_pdb_plugin.cpp: 端到端插件测试（dlopen→register→sniffer→import→export→round-trip，R34）

## 依赖版本
- 无 conan 依赖（dependency-free）：AbiWord 核心与 libgsf API 由 compat shim 提供
- 构建工具: tool_requires automake/1.18 + libtool/2.5.4（autoconf 套件在 /data/service/hnp/bin）
- 编译工具链: OHOS SDK clang/clang++ 15
- 运行时: dlopen（test_package 用 -ldl）

## 验证结果
```bash
# 手动编译（SKILL.md §3 Step 2）
autoreconf -fi && ./configure --prefix=$DEFAULT_PREFIX \
  --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
  && make -j1 && make install DESTDIR=$TEST_PREFIX
make check -j1
# → Testsuite summary: TOTAL 1, PASS 1, FAIL 0
# → test_pdb_plugin: PASS 39/39 断言（dlopen/register/sniffer 识别/importFile/导出 PDB 结构/round-trip）

# conan create（clean source，全绿）
conan create archives/a/abiword-plugin-pdb/3.0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → make check: PASS 1/1（39/39 断言）
# → test_package: PASS: abiword-plugin-pdb module loaded, registered and unregistered

# 补丁可应用性（patch_ng，新解压树）
python3 - <<'EOF'
import patch_ng
ps = patch_ng.fromfile("patches/0001-Makefile.am.patch"); print(ps.apply(root=".", strip=1))
ps = patch_ng.fromfile("patches/0002-configure.ac.patch"); print(ps.apply(root=".", strip=1))
EOF
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，-j1，umask 修复，export_sources 传 compat/tests） |
| conandata.yml | 源码 URL + sha256 + 2 个补丁声明 |
| patches/0001-Makefile.am.patch | minimal Makefile.am |
| patches/0002-configure.ac.patch | minimal configure.ac |
| compat/ | AbiWord + libgsf 运行时 shim（18 文件，含 GsfOutput 扩展） |
| tests/test_pdb_plugin.cpp | 端到端插件测试（39 断言，make check） |
| test_package/ | conan 消费测试（dlopen 插件 ABI，run_test.cpp） |

## 注意事项
- **禁止为新增源码（compat/tests）生成 new-file 补丁**：toybox patch --dry-run 会真实应用，
  污染 orig 目录导致补丁管线损坏（E258）。新增文件一律走 export_sources。
- 知识条目: E114（umask 077 / HMDFS）、E074（make -j1 FIFO）、E258 草稿（toybox dry-run）
- make 必须 -j1（E074）；configure 生成后必须去除 umask 077（E114）
- pdb 插件与 clarisworks 的差异点：需要 GsfOutput（导出）、IE_Exp 导出框架、ut_mbtowc、
  UT_basename、GObject ref/unref、g_ascii_strcasecmp
- 系统 channel 已用 `@ohpcd/stable` 构建验证
---

**编译结束**: 2026-08-13 11:19
**最终状态**: built
