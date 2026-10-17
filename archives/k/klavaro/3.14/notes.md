# klavaro 3.14 适配笔记

## 基本信息
- 软件: klavaro（GTK3 触摸打字教学工具，GUI 应用）
- 版本: 3.14（上游 2022-11 发布）
- 构建系统: autotools（tarball 自带 configure，无 automake 环境下直接 patch 生成文件）
- 上游: https://klavaro.sourceforge.io/ / https://downloads.sourceforge.net/project/klavaro/klavaro-3.14.tar.bz2
- sha256: 87187e49d301c510e6964098cdb612126bf030d2a875fd799eadcad3eae56dab（实测 2026-09-09 下载核对一致）
- 产物: bin/klavaro 可执行文件（R38：软件级 commands.json 已建）+ data 资源（glade/键盘布局/课文）

## 上游核验（2026-09-09 实证）
- configure.ac 依赖清单：gtkdatabox>=1.0.0（PKG_CHECK_MODULES+AC_CHECK_LIB）、gtk+-3.0>=3.12、gdk-3.0>=3.12、pango>=1.32.4、cairo>=1.12、curl（AC_CHECK_HEADERS+AC_CHECK_LIB）、gmodule-2.0、libm、gettext/libintl、intltool（IT_PROG_INTLTOOL）
- 测试套件 N=0 实证：configure.ac 无 AM_TESTS；src/Makefile.am 无 TESTS/check_PROGRAMS；`make check` 实跑所有子目录 "Nothing to be done for 'check'"——上游无自动化测试

## 依赖模型（gtkdatabox/goffice 先例 + 本包首次全 conan GTK 链）
- gtk/3.24.43（conan 直依赖）：PkgConfigDeps 生成 gtk+-3.0.pc；gdk-3.0.pc 由配方 _copy_gdk_pc() 从包内 re-expose（PkgConfigDeps 只产聚合 pc）
- gtkdatabox/1.0.0（conan）：上游硬依赖，制品仓已发布
- curl/8.15.0（conan）：上游 AC_CHECK_* 只探测不进链接线（系统 curl 假设）
- intltool/0.51.0（tool_requires）：IT_PROG_INTLTOOL
- fontconfig/2.18.1.1 + expat/2.8.2.1（override）：cairo/1.18.4 pin 2.18.1.1/2.8.2.1，gtkdatabox pin 2.18.1/2.8.2 —— 顶层 override 对齐 cairo 分支（两版本 OHOS binary 均已发布，R36 图对齐）
- libintl：glib 包携带 proxy-libintl（libintl.so.8，g_libintl_* 符号），0003 补丁加 -lintl

## 补丁清单
| # | 补丁 | 类型 | 说明 |
|---|------|------|------|
| 0001 | configure-bypass-xml-parser-check | backport | XML::Parser perl 模块检测绕过：intltool -x（XML 合并）需要该 XS 模块，OHOS 应用沙箱内 musl loader 对用户区 .so 的 dlopen 报 Permission denied（实测 perl -MXML::Parser 永远失败，非路径问题）。appdata.xml 改走配方内 perl shim |
| 0002 | config.sub-accept-linux-ohos | portability | 标准 OHOS 三元组支持 |
| 0003 | src-Makefile.in-link-curl-intl | bugfix | klavaro_LDADD 追加 -lcurl -lintl：上游 AC_CHECK_LIB 探测后不进链接线（系统路径假设）；OHOS conan 库需显式 -l。LIBS env/make-args 注入会污染 configure conftest（曾致 conftest 运行失败），改补丁最稳 |

## 关键坑（E 系列）
| 现象 | 根因 | 解决 |
|------|------|------|
| configure 卡 XML::Parser | perl XS 模块 .so 在用户目录 dlopen 被 musl loader 拒（"Permission denied" 红鲱鱼，真实原因 XS 扩展不可加载） | 0001 补丁绕过 + intltool-merge -x 的 perl shim（-d 桌面模式纯正则可用，走真 intltool-merge） |
| klavaro.appdata.xml 空/构建失败 | intltool-merge -x 需要 XML::Parser | 配方 _write_intltool_merge_shim() 写 PATH shim + configure 后把 Makefile 的 INTLTOOL_MERGE 变量重定向到 shim（configure 烤了绝对路径，PATH shim 不够）|
| perl -e 脚本后跟 -x 参数 | perl 把 -x 当自己的切割参数 | shim 里 perl -e '...' -- "$@" 加 -- 分隔符 |
| conftest "cannot run C compiled programs" | LIBS env 注入 -lcurl 后 conftest 链了 curl 但运行时无 LD_LIBRARY_PATH | 改 LDFLAGS 只放 -L；-l 由 0003 补丁进 LDADD |
| config.status "could not setup config files" | E114：HMDFS 上 mktemp -d ./confXXXX 不可写 | _patch_config_status_tmpdir() 把 ac_tmp 重定向到 tmpfs（gtkdatabox/BIRD 同款） |
| PkgConfigDeps pc 里 Libs: -L"${libdir}" 带引号 | conan 生成的 pc 用变量+引号，_pc_paths 直接提取会把引号传给 clang 致 -L"/path" 找不到库 | 提取时展开变量 + replace('"','') |
| 链接缺 g_libintl_*/curl_* | 上游不链 -lintl/-lcurl | 0003 补丁 |
| 链接缺 gdk-3.0.pc | PkgConfigDeps 只产 gtk+-3.0 聚合 pc | _copy_gdk_pc() 从 gtk 包拷贝并重写 prefix |
| test_package 运行缺 libc++_shared.so / libffi.so | OHOS SDK 运行库 + gtkdatabox（cmd-pkgs 系统栈构建）的无版本号 libffi.so | test 里 LD_LIBRARY_PATH 补 SDK aarch64-linux-ohos + /data/service/hnp/libffi.org/*/lib |
| CI #43592 链接失败 g_libintl_* undefined | glib 包 libintl.h 把 gettext 宏重定向为 g_libintl_*（#define 无条件覆盖，命令行恒等宏法不可行）；0003 补丁的裸 `-lintl` 依赖 -L 搜索顺序，CI Worker（CI-018）sysroot 的 libintl 先命中（musl 无 g_libintl_* 实现） | `_pin_intl_libpath()`：configure 后把 src/Makefile klavaro_LDADD 的 `-lintl` 重写为 glib 包 libintl.so 绝对路径（不依赖 -L 顺序，同时满足 main.o 引用与 gtk 树 --no-allow-shlib-undefined 闭包） |

## 验证结果（2026-09-09，conan create 全绿）
- G1 配方完整性: conanfile.py + conandata.yml + test_package(3 文件) + patches(3) ✓
- G2 conan create: 全绿 exit=0，0 ERROR
- test_package 探针全过:
  - [R38] bin/klavaro 存在且可执行
  - [OK] AArch64 dynamic ELF（magic + e_machine）
  - [OK] NEEDED 闭包 31 库，GTK3 栈确认链接（libgtk-3.so.0/libgdk-3.so.0/libgtkdatabox.so.1/libcurl/libcairo/libpango）
  - [OK] 运行期加载器全链解析（--version 到达 GTK init，headless "Cannot open display" 为预期）
  - [R40] 交互式打字课程 UI 需 OpenHarmony PC 显示会话（partial 标注）
- 上游测试 N=0（无套件），消费者侧 10 项断言（见 test_package/MANIFEST.yml）

## 环境备注（CI 复现要点）
- conan profile: ohos-aarch64（clang 15, OHOS 6.0, armv8）
- intltool 来自制品仓 tool_requires；msgmerge 用 SDK gettext.org（libomp.so 依赖 SDK llvm lib）
- 运行期闭包：conan 树（gtk/gtkdatabox/curl）+ OHOS SDK（libc++_shared.so）+ HNP libffi（gtkdatabox 的无版本号 libffi.so）
## 对话记录（适配过程摘要）
- 2026-09-09 任务 #2386 开工（2404_87638649 账号，worktree wt-klavaro，分支 feat/klavaro-3.14 基于最新 upstream/main 重建——旧分支 cad1bdb 为 8-20 的半成品配方，依赖当时缺失的 gtk+ 链，本版全部重写）
- 上游核验：tarball 下载+sha256 核对一致；configure.ac/Makefile.am 逐项分析；make check 实跑确认 N=0
- 依赖核验：gtk/3.24.43、gtkdatabox/1.0.0、curl/8.15.0、intltool/0.51.0 制品仓实测可用；发现 gtkdatabox(2.18.1/2.8.2) vs cairo 新 rev(2.18.1.1/2.8.2.1) 的 fontconfig/expat 精确 pin 冲突 → 顶层 override 对齐 cairo 分支（graph explain 验证无 missing binary）
- 探索编译：XML::Parser perl XS 模块在 OHOS 沙箱 dlopen 被拒（深挖：musl loader 对用户区 .so 报 Permission denied；动态库依赖、静态链接、tmpfs 放置均试过，确认环境不可用）→ 补丁绕过 + intltool-merge -x shim
- conan create 迭代 8 轮修复：引号 pc 提取 / conftest LIBS 污染 / E114 config.status tmpdir / LDADD -lcurl -lintl / INTLTOOL_MERGE Makefile 重定向 / perl -- 分隔符 / libcurl SONAME / VirtualRunEnv+SDK 路径
- conan-verify 8 门禁全 PASS；test_package 10 断言全过（ELF/AArch64/NEEDED 6 项/加载器全链）
- finish：补齐 README.md/packaging/.staging-verified/test-report.md，状态 built→published 就绪
---

**编译结束**: 2026-09-09 19:50
**最终状态**: published
