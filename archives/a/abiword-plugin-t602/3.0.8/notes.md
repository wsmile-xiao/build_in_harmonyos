# abiword-plugin-t602 3.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游完整 configure.ac 被替换为 minimal 版，仅构建 t602 插件）
- 编译日期: 2026-08-14
- 编译器: clang/clang++（OHOS SDK 15，conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64 / OHOS / armv8)

## 源码与方案
- 源码: GNOME GitLab `World/AbiWord` release-3.0.8 tarball（git archive 无 configure）
  - url: https://gitlab.gnome.org/World/AbiWord/-/archive/release-3.0.8/AbiWord-release-3.0.8.tar.gz
  - sha256: 7c490e46f0a6143f84d5c7e3fed246f34486ad70cd55f162c792827607cd7e9a
- minimal 方案: 只构建 t602 导入插件（`.602`/`.t602`/`.txt` 导入模块）
  - 插件源码自包含: `plugins/t602/xp/ie_imp_T602.cpp (+.h)`
  - AbiWord 运行时 API（IE_Imp/PD_Document/XAP_Module/UT_String/GsfInput）由
    自写 compat/ shim 提供（AbiWord 核心与 libgsf 未发布到 OHOS 制品仓）
  - 产出: `libabiword-plugin-t602.so`，安装到 `lib/abiword-3.0/plugins/`
- 参考: sibling abiword-plugin-clarisworks / abiword-plugin-pdb 同款 minimal 方案

## 编译步骤
1. `init-build` 复用缓存 tarball（abiword-3.0.8.tar.gz）解压源码（orig 目录保持 pristine）
2. 修改 configure.ac（替换为 minimal 版）与 Makefile.am（仅构建插件 + 端到端测试）
3. 编写 compat/ shim（12 个头文件 + abiword_shim.cpp，含 t602 专属
   ut_string_class.h / xap_Prefs.h / xap_App.h / appendFmt / appendObject / PTO_Field）
   与 tests/test_t602_plugin.cpp
4. `refresh-patch --auto` 生成补丁（仅 2 个修改文件；compat/tests 走 export_sources）
5. conanfile.py:
   - `source()`: 下载 + apply_conandata_patches（export sources 自动 merge 进 source 目录）
   - `build()`: 预创建 install-sh → `autoreconf -fi` → `_drop_umask_077(configure)`
     → `autotools.configure()` → `make -j1` → `make check -j1`
   - `package()`: `autotools.install()`
6. conan create 全绿: make check PASS（24 项断言全过）+ test_package PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 报 `required file './ltmain.sh' not found` | libtoolize aux-dir 启发式扫 `. / .. / ../..` 找 install-sh/install.sh；OHOS 宿主 `$HOME/tmp/install.sh` 使 libtoolize 把 ltmain.sh 复制到 `../..`（$HOME/tmp）而非源码根 | build() 在 `autoreconf -fi` 前先建占位 `install-sh`，使启发式命中 `.`。知识条目 E321 草稿 |
| 2 | toybox `patch --dry-run` 真实应用 new-file 补丁 | 鸿蒙默认 /usr/bin/patch 为 toybox 0.8.12，其 dry-run 对 `--- /dev/null → +++ b/...` 补丁真实创建文件，污染 pristine orig 目录 | compat/ 与 tests/ 不生成补丁，改为 conanfile.py `export_sources()` 传递；补丁只保留 2 个修改文件（Makefile.am、configure.ac）。知识条目 E258 草稿 |
| 3 | config.status 创建临时目录失败 | E114: HMDFS 上 `umask 077 && mktemp -d` 生成的 0700 临时目录不可写（setgid） | conanfile.py `_drop_umask_077()` 运行时从生成的 configure 中删除 `umask 077`，已有正式条目 E114 |
| 4 | make 并行 jobserver FIFO EPERM | E074: 鸿蒙 SELinux 禁止创建 FIFO，make -j>1 卡住/报错 | 全部 `make` 调用带 `-j1`，已有正式条目 E074 |
| 5 | 上游 configure.ac 需要 gtk3/cairo/libgsf/wv/libxslt/boost 全链路 | HarmonyOS PC 无这些依赖 | 替换为 minimal configure.ac，只构建 t602 插件 + compat shim |
| 6 | git archive 无 configure 脚本 | 上游 tarball 为 git archive 快照 | build() 中 `autoreconf -fi` 从 minimal configure.ac 生成 |
| 7 | 环境 automake 硬编码绝对路径 | 安装的 automake/aclocal/libtoolize 指向不存在的 autoconf/autom4te/sed | conanfile.py `_prepare_autotools_env()` 将 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 指到 PATH 实际位置 |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-Makefile.am.patch | 替换完整 Makefile.am 为 minimal 版：构建 libabiword-plugin-t602.la（-module -avoid-version）+ 端到端测试 test_t602_plugin |
| patches/0002-configure.ac.patch | 替换完整 configure.ac 为 minimal 版：AC_INIT(abiword-plugin-t602) + AM_INIT_AUTOMAKE + LT_INIT(disable-static) + AC_CONFIG_FILES([Makefile]) |

非补丁源码（conanfile.py export_sources 传递）:
- compat/（12 个 .h + abiword_shim.cpp）: AbiWord/libgsf 运行时 shim
  （相比 clarisworks 扩展: ut_string_class.h、xap_Prefs.h、xap_App.h，
  IE_Imp 增加 appendFmt/appendObject，pd_Document 增加 PTObjectType/PTO_Field，
  ut_types.h 增加 UCS_FF 等）
- tests/test_t602_plugin.cpp: 端到端插件测试（dlopen→register→sniffer→
  importFile→文本校验+PTO_Field 页码对象，24 项断言，R34）

## 依赖版本
- 无 conan 依赖（dependency-free）：AbiWord 核心与 libgsf API 由 compat shim 提供
- 编译工具链: OHOS SDK clang/clang++ 15、autoconf 2.72、automake 1.17、
  libtool 2.5.4（tool_requires automake/1.18 + libtool/2.5.4）
- 运行时: dlopen（test_package 用 -ldl）

## 验证结果
```bash
# 探索阶段（手动）
./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
make -j1 && make check -j1     # → PASS: test_t602_plugin（24 项断言全过）

# conan create（clean source，全绿）
conan create archives/a/abiword-plugin-t602/3.0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → make check: PASS: test_t602_plugin（24 项断言全过）
# → test_package: PASS: abiword-plugin-t602 module loaded, registered and unregistered (T602 Importer / 3.0.8)

# 补丁可应用性（patch_ng，新解压树）
python3 - <<'EOF'
import patch_ng
for p in ["0001-Makefile.am.patch", "0002-configure.ac.patch"]:
    ps = patch_ng.fromfile("patches/" + p); print(p, ps.apply(root=".", strip=1))
EOF
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，-j1，umask 修复，install-sh 预创建，export_sources 传 compat/tests） |
| conandata.yml | 源码 URL + sha256 + 2 个补丁声明 |
| patches/0001-Makefile.am.patch | minimal Makefile.am |
| patches/0002-configure.ac.patch | minimal configure.ac |
| compat/ | AbiWord + libgsf 运行时 shim（12 .h + abiword_shim.cpp） |
| tests/test_t602_plugin.cpp | 端到端插件测试 |
| test_package/ | conan 消费测试（dlopen 插件 ABI） |

## 注意事项
- **禁止为新增源码（compat/tests）生成 new-file 补丁**：toybox patch --dry-run 会真实应用，
  污染 orig 目录导致补丁管线损坏（E258）。新增文件一律走 export_sources。
- **autoreconf 前必须在源码根建 install-sh**：libtoolize aux-dir 启发式会被
  `$HOME/tmp/install.sh` 干扰，把 ltmain.sh 复制到 `../..`（E321 草稿）。
- 知识条目: E114（umask 077 / HMDFS）、E074（make -j1 FIFO）、E258 草稿（toybox dry-run）、
  E321 草稿（libtoolize aux-dir 启发式干扰）
- make 必须 -j1（E074）；configure 生成后必须去除 umask 077（E114）
---

**编译结束**: 2026-08-14 17:04
**最终状态**: built
