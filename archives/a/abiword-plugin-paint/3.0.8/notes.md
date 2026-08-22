# abiword-plugin-paint 3.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游完整 configure.ac 被替换为 minimal 版，仅构建 paint 插件）
- 编译日期: 2026-08-13
- 编译器: clang/clang++（OHOS SDK，conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64 / OHOS / armv8)

## 源码与方案
- 源码: GNOME GitLab `World/AbiWord` release-3.0.8 tarball（git archive 无 configure）
  - url: https://gitlab.gnome.org/World/AbiWord/-/archive/release-3.0.8/AbiWord-release-3.0.8.tar.gz
  - sha256: 7c490e46f0a6143f84d5c7e3fed246f34486ad70cd55f162c792827607cd7e9a
- minimal 方案: 只构建 paint 插件（在外部程序中就地编辑图片、另存为 BMP 的图像编辑插件）
  - 插件源码自包含: `plugins/paint/xp/AbiGeneric.{cpp,h}` + `AbiPaint.{cpp,h}` + `plugins/paint/unix/ut_UnixProcess.cpp`
  - AbiWord 运行时 API（XAP_App/XAP_Frame/XAP_Prefs/EV_EditMethod/EV_Menu_Action/XAP_Menu_Factory/
    FV_View/IE_ImpGraphic/UT_* 等）由自写 compat/ shim 提供（AbiWord 核心未发布到 OHOS 制品仓）
  - 产出: `libabiword-plugin-paint.so`，安装到 `lib/abiword-3.0/plugins/`
- 参考: sibling abiword-plugin-clarisworks 同款 minimal 方案（compat shim + export_sources + 修改文件补丁）

## 编译步骤
1. `init-build` 下载解压源码（orig 目录保持 pristine）
2. 修改 configure.ac（替换为 minimal 版）与 Makefile.am（仅构建插件 + 端到端测试）
3. 编写 compat/ shim（35 个头文件 + abiword_shim.cpp）与 tests/test_paint_plugin.cpp
4. `autoreconf -fi` → configure → `make -j1` → `make install DESTDIR` → `make check -j1`
5. `refresh-patch --auto` 生成补丁（仅 2 个修改文件；compat/tests 走 export_sources）
6. conanfile.py:
   - `source()`: 下载 + apply_conandata_patches（export sources 自动 merge 进 source 目录）
   - `build()`: `autoreconf -fi` → `_drop_umask_077(configure)` → `autotools.configure()`
     → `make -j1` → `make check -j1`
   - `package()`: `autotools.install()`
7. conan create 全绿: make check PASS（1 个端到端测试，内部 23 项断言）+ test_package PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | toybox `patch --dry-run` 真实应用 new-file 补丁 | 鸿蒙默认 /usr/bin/patch 为 toybox，其 dry-run 对 new-file 补丁真实创建文件，污染 pristine orig 目录 | compat/ 与 tests/ 不再生成补丁，改为 conanfile.py `export_sources()` 传递；补丁只保留 2 个修改文件（Makefile.am、configure.ac）。知识条目 E258 草稿 |
| 2 | config.status 创建临时目录失败 | E114: HMDFS 上 `umask 077 && mktemp -d` 生成的 0700 临时目录不可写（setgid） | conanfile.py `_drop_umask_077()` 运行时从生成的 configure 中删除 `umask 077`（clarisworks 同款方案），已有正式条目 E114 |
| 3 | make 并行 jobserver FIFO EPERM | E074: 鸿蒙 SELinux 禁止创建 FIFO，make -j>1 卡住/报错 | 全部 `make` 调用带 `-j1`，已有正式条目 E074 |
| 4 | 上游 configure.ac 需要 gtk3/cairo/libgsf/wv/libxslt/boost 全链路 | HarmonyOS PC 无这些依赖 | 替换为 minimal configure.ac，只构建 paint 插件 + compat shim |
| 5 | git archive 无 configure 脚本 | 上游 tarball 为 git archive 快照 | build() 中 `autoreconf -fi` 从 minimal configure.ac 生成 |
| 6 | 环境 automake 硬编码绝对路径 | 安装的 automake/aclocal/libtoolize 指向不存在的 autoconf/autom4te | conanfile.py `_prepare_autotools_env()` 将 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 指到 PATH 实际位置 |
| 7 | conan create 链接失败: `.lo` is not a valid libtool object | explore 阶段在 compat/ 目录内执行过 make，残留 libtool 构建产物（.lo/.o/.dirstamp）；export_sources 把构建产物当源码发布进 recipe | 归档前清理 compat/、tests/ 下全部构建产物（find ... -delete），只保留源文件 |
| 8 | compat/xap_Frame.h 使用 XAP_Dialog_MessageBox::tAnswer 报 incomplete type | 头文件仅前置声明类，枚举需要完整类型 | compat/xap_Frame.h 改为 include "xap_Dlg_MessageBox.h" |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-Makefile.am.patch | 替换完整 Makefile.am 为 minimal 版：构建 libabiword-plugin-paint.la（-module -avoid-version）+ 端到端测试 test_paint_plugin |
| patches/0002-configure.ac.patch | 替换完整 configure.ac 为 minimal 版：AC_INIT(abiword-plugin-paint) + AM_INIT_AUTOMAKE + LT_INIT(disable-static) + AC_CONFIG_FILES([Makefile]) |

非补丁源码（conanfile.py export_sources 传递）:
- compat/（35 个 .h + abiword_shim.cpp）: AbiWord 运行时 shim（XAP_App/XAP_Frame/XAP_Prefs/EV_EditMethod/EV_Menu_*/XAP_Menu_Factory/FV_View/IE_ImpGraphic/UT_* 等）
- tests/test_paint_plugin.cpp: 端到端插件测试（dlopen→register→prefs scheme→菜单/EditMethod 校验→unregister，R34）

## 依赖版本
- 无 conan 依赖（dependency-free）：AbiWord 核心 API 由 compat shim 提供
- 编译工具链: OHOS SDK clang/clang++ 15、autoconf 2.72、automake 1.17、libtool
- 运行时: dlopen（test_package 用 -ldl）

## 验证结果
```bash
# conan create（clean source，全绿）
conan create archives/a/abiword-plugin-paint/3.0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → make check: PASS: test_paint_plugin（内部 23 项断言全过）
# → test_package: PASS: abiword-plugin-paint module loaded, registered and unregistered

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
| compat/ | AbiWord 运行时 shim（35 .h + abiword_shim.cpp） |
| tests/test_paint_plugin.cpp | 端到端插件测试 |
| test_package/ | conan 消费测试（dlopen 插件 ABI） |

## 注意事项
- **禁止为新增源码（compat/tests）生成 new-file 补丁**：toybox patch --dry-run 会真实应用，
  污染 orig 目录导致补丁管线损坏（E258）。新增文件一律走 export_sources。
- **归档前必须清理 compat/ tests/ 下的 libtool 构建产物**（.lo/.o/.dirstamp/.Plo/.Po），
  否则 export_sources 把构建产物当源码发布，conan create 链接时报 `.lo is not a valid libtool object`。
- 知识条目: E114（umask 077 / HMDFS）、E074（make -j1 FIFO）、E258 草稿（toybox dry-run）
- make 必须 -j1（E074）；configure 生成后必须去除 umask 077（E114）
- 系统 channel 已用 `@ohpcd/stable` 构建验证
---

**编译结束**: 2026-08-13 12:22
**最终状态**: built
