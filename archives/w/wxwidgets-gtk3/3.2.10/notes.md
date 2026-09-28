# wxwidgets-gtk3 3.2.10 适配笔记

## 定位

- 为 codeblocks 25.03（wxWidgets GUI IDE）补齐的前置 GUI 库包
- 与 wxwidgets base 变体同源（wxWidgets 3.2.10），不同包名区分变体
- 设备验证: 10.62.210.132:8022 (OHOS 6.0 aarch64)

## 关键事实（W0 依赖核查）

- 制品仓 gtk/3.24.43 为 broadway-only 构建（x11/wayland 后端禁用）
- wx 3.2.10 源码分析结论：
  - `build/cmake/toolkit.cmake:124` 仅当 `WXGTK AND wxHAVE_GDK_X11` 才
    `find_package(X11 REQUIRED)`；`wxHAVE_GDK_X11` 由 FindGTK3.cmake 对
    gdk/gdk.h 做 `check_symbol_exists(GDK_WINDOWING_X11)` 得出——broadway
    下为 false，不触发 X11 依赖
  - src/gtk/ 中 gdk_x11_*/GDK_WINDOW_XID 调用均位于 GDK_WINDOWING_X11
    守卫块内（display.cpp:179、toplevel.cpp:119 等）
  - include/wx/gtk/private/wrapgdk.h 按 GDK_WINDOWING_* 条件包含后端头

## 变体配置决策

- png/jpeg builtin：libtiff/4.7.2 依赖 libjpeg-turbo/3.2.0，若 wx 声明
  libjpeg/10 则同图两个 jpeg 实现，CMakeDeps 生成物有冲突风险——改用
  wx 源码内置（src/png、src/jpeg），TIFF 直接 OFF
- zlib/1.3.1.1 sys 方式沿用 base 变体已验证可行路径；expat 最终改 builtin
  （r3：wxxml 经 CMake 内置 FindEXPAT 取变量，与 conan CMakeDeps 的小写
  expat 配置文件名接不上）
- 不引入 curl（base 变体仅因 webrequest 引入，本包 wxUSE_WEBREQUEST=OFF）

## 迭代记录

### r1（2026-09-02）

- 初版配方上传设备 conan create → 依赖图 expat 版本冲突
  （fontconfig/2.18.1.1 pin expat/2.8.2.1，配方声明 2.8.2）

### r2

- expat 改 2.8.2.1 → CMake 配置死在 toolkit.cmake:38 Unsupported platform。
  根因链：设备原版 conan 的 CMakeToolchain 不设 CMAKE_SYSTEM_NAME（generic_system
  块为空）→ CMake 走 uname 探测得到 HarmonyOS（未知平台，UNIX 不成立）；
  CI 适配版 conan 按 profile 注释映射 CMAKE_SYSTEM_NAME=HarmonyOS（同样 UNIX
  不成立）。0001 补丁的 STREQUAL "OHOS" 两种环境都命不中。
- 修法：配方 tc.cache_variables["CMAKE_SYSTEM_NAME"]="OHOS"（与 base 变体
  历史验证一致），补丁即可命中；副作用 CMAKE_CROSSCOMPILING=TRUE（host
  HarmonyOS ≠ OHOS）→ wx functions.cmake:308 给库名追加 -OHOS 后缀
  （CI worker 也是 OHOS 原生机，行为一致、确定）

### r3

- SYSTEM_NAME 修复后配置通过（GTK3 broadway 探测成功，wxHAVE_GDK_X11=false，
  未触发 find_package(X11)），编译至 81% wxcore 链接成功
  （libwx_gtk3u_core-3.2-OHOS.a）→ wxxml 挂：expat.h not found。
  根因：wxxml 用 CMake 内置 FindEXPAT 的 EXPAT_INCLUDE_DIRS 变量，
  conan expat 包 cmake_file_name 为小写 "expat"，FindEXPAT 找不到 →
  变量空。base 变体当年 GUI 关 → XRC/XML 关 → wxxml 不编译，未踩此坑
- 修法：wxUSE_EXPAT=builtin（wx 源码自带 src/expat），移除 expat 依赖

### r4

- wxxml 过。html 挂：protocol.h:90 SetTimeout override 错。
  根因：htmlpars.cpp 无条件 include wx/url.h → protocol/protocol.h；
  上游对 wxUSE_SOCKETS=OFF 未做干净（SetTimeout 覆盖 wxSocketBase 方法，
  sockets 关闭时基类继承链消失）。base 变体关 sockets 之所以能过：
  base 不编 html 库
- 修法（r5）：sockets 保持开启，修复 socklen_t 差异——
  include/wx/private/socket.h 兜底定义 WX_SOCKLEN_T/SOCKOPTLEN_T 为 int，
  OHOS getsockopt/setsockopt 要 socklen_t*（C++ 指针类型不兼容，
  socket.cpp×3 + sockunix.cpp×1 处报错）；POSIX 分支兜底改 socklen_t 并补
  include <sys/socket.h>。gethostbyname_r 系列：setup.cmake:437-460
  check_symbol_exists 运行时探测，OHOS musl 无 _r 变体自动回退
  HAVE_GETHOSTBYNAME 普通函数+互斥锁路径，无需干预

### r5

- socket 修复后全量编译打包成功（13 个 wx 库 + 5 个内置库 + wx-config/wxrc）
  → package_info 残留 expat:: 引用报错（依赖已移除）

### r6

- package_info 修正为真实库名（wx 主库带 -OHOS 后缀，内置库无后缀）。
  包构建通过 → test_package 编译挂：defs.h:62 #error "No Target!" 及
  GdkColor/GtkWidget 未知类型——消费者缺 __WXGTK__ 端口宏
- 修法（r7）：package_info.defines=["__WXGTK__"]；test 源 wx_str() 宽字符
  printf 隐患一并修为数字字段

### r7

- 全量重建 + test_package PASS：test_wxgtk3 链接全静态库集编译执行，
  4 项 API 断言全过（wxGetLibraryVersionInfo/wxColour/wxSize/wxString），
  输出 `test wxwidgets-gtk3 3.2.10: OK`
- 已知非阻塞：wxPlatformInfo 对未知 OS（OHOS）打 3 条 release 级日志断言

### finish（2026-09-03，设备端）

- conan-verify G1/G0/G2/G3 全 PASS
- W3 本地 CI 模拟 PASS（setup.sh + build_and_test.sh，.ci-result.json
  exit_code=0）。设备侧 W3 环境附注：ci profile 编译器路径按设备实测修正
  （hnp 路径设备不存在）；设备无 git，G0e 根白名单检查用等价 git shim
- W4 独立审计：PASS（P0=0/P1=0，1 个 P2 文档陈旧已修正）

### r8（2026-09-04，真机上游测试套件，R51 三步法）

上游测试清点（源码级）：tests/ 共 323 个 TEST_CASE（69 个源文件）；其中
非 GUI `test` 二进制（wxBase，`-DwxUSE_GUI=0`）注册 87 个源文件。
3.2.10 的 CMake 不支持构建 tests（仅 samples），真机以 autoconf 路径
构建运行（configure 选项镜像配方：gtk3/静态/builtin png/jpeg/expat）。

真机实测（10.62.210.132:8022，clang 15.0.4 aarch64，同一源码 tarball
sha256 校验一致 + 同一制品仓 gtk/3.24.43 broadway 依赖链）：

- 上游非 GUI 套件 `tests/test`：**295 用例全量运行，267 通过 / 28 失败**
  （断言级 1,229,604 中 1,229,496 通过，99.99%）；TEST_RC=108
- 28 个失败用例全部为平台环境差异（逐类技术原因与断言级明细见
  test-report.md）：应用沙箱拒绝枚举 `/` 与读 `/sys`、`/tmp` 只读导致
  临时文件类用例失败、musl 无 glibc locale/charset 数据（Intl/
  Translations/UILocale/NumFormatter/MBConv 组）、HMDFS inotify 事件
  语义差异（wxFileSystemWatcher）、musl strtod 精度差异（StringTestCase）；
  **无 wx 适配缺陷**
- GUI 套件 `tests/test_gui`：链接成功（见下 X11 附注）但无法运行——
  SSH 沙箱无显示访问，GTK 报 `Unable to initialize GTK+, is DISPLAY set
  properly?`（RC=255）；broadway-only gtk 无 broadwayd 运行路径

autoconf 路径环境级修复（验证工作区，不进 patches/）：
- config.sub 增加 `ohos` OS 与 `linux-ohos*` kernel-os 组合，并同步覆盖
  3rdparty/pcre、src/expat 等子目录的旧版 config.sub（上游 2021 版
  config.sub 不识别 ohos 三元组）
- toybox `mktemp -d` 创建的 0700 目录在 HMDFS 上映射为无写权限 ACL，
  autoconf config.status 由此失败（`can't create ./confXXXXXX/subs1.awk`）；
  以 mkdir 版 mktemp shim 规避（曾致 2026-05 base 变体 autotools 失败，
  本次定位根因：非 HMDFS 通用限制，是 mktemp 特定行为）
- 上游 configure 对 GTK 无条件追加 `-lX11`（unix 假设 GTK=X11），
  broadway-only 下 test_gui/test_drawing 链接失败；生成 Makefile 移除
  `-lX11` 后链接通过（与 CMake 路径 GDK_WINDOWING_X11 探测结论一致）

### r9（2026-09-05，CI #40577 失败修复）

- 现象：/rebuild 后 CI #40577（worker CI-011）conan-build-test 失败——
  `$HOME/usr/local/bin/msgfmt` 运行时缺 `libintl.so.8`
  （`Error loading shared library libintl.so.8`），wx locale 的 .gmo
  全部生成失败（Error 127）→ `cmake.build()` Error 2
- 根因：wx 的 `wxBUILD_LOCALES` 默认 AUTO，靠 `find_package(Gettext
  QUIET)` 探测 msgfmt——只验证二进制存在，不验证可运行。CI-011 的
  用户前缀下有一个损坏的 msgfmt；CI-020（#37134 通过）无 msgfmt，
  AUTO 自动跳过 locale——配方构建结果依赖 worker gettext 状态，
  非确定性缺陷
- 修复：generate() 显式 `wxBUILD_LOCALES=OFF`（上游官方开关，
  build/cmake/options.cmake:19），跳过 locale 生成；wxstd 消息翻译
  目录（share/locale/*/wxstd-3.2.mo）非本包消费必需
- 版本号不递增：PR 未合并，制品仓不存在 wxwidgets-gtk3/3.2.10
  （L0j 仅在制品仓已有同版本时拦截）
- 设备端 conan create 复验通过（locale 跳过，test_package PASS）

### r10（2026-09-07，评审整改：归因证据随 PR 提交 + 模板对齐）

- Septest 二审（09-06）FAIL：28 项失败归因引用的报告不在 PR 变更内
  （reports/ 被 .gitignore 忽略），不可复核；PR 描述需按积分赛模板
  在「验证结果」小节写通过率
- 整改：
  - `reports/upstream-tests-report.md` 随 PR 提交（28 项逐条归因：
    断言行号/展开值/根因分类/可否自做依赖解决），原始日志
    `upstream-test-output.log`（857 行）与复现脚本 `upstream-test-run.sh`
    一并入库；.gitignore 加本包 reports/ 白名单（tcping/handbrake/
    lz4/rocksdb 同款先例）
  - PR 描述按「鸿蒙PC三方库积分大赛 PR 提交模板」重写（含上游/新增
    测试通过率两行）
- **r8 运行复核修正**：逐条核对失败断言发现 5 个用例
  （CopyFile/Eof/Error/FindFileNext/FileExists 宽字符）的根因是
  **测试夹具未就位**——`make -C tests all` 首次在 test_drawing 处中止，
  排在 all 末尾的 data/data-images 目标（拷贝 horse.* 到运行目录）未执
  行（证据：`wxFFile::Eof(): file is closed!`＝horse.bmp 打不开）。
  属运行脚本时序缺陷而非平台限制。脚本已修（S7c 显式构建夹具并校验）
- 待办：验证设备 sshd 离线中；恢复后重跑（预期 A 组 5 用例转通过，
  272/295=92.2%），更新报告与 PR 数字

### r11（2026-09-26，MR 7787 rule4 测试分母与 test_package 复核）

- 评审按源码测试面核验得到上游总量 `N=858`；此前 PR 只填了真机 Catch
  进程实际注册的 `N'=295`，把执行子集误写成完整上游分母，触发 rule4
  “实测 N=858 > 声明 N=295”。
- PR 正文模板行名保持标准（单元测试/集成测试/其他测试/合计），数值分
  开记录：上游分母 858（声明 N=858，实测 858）、实际运行 295、通过 267、
  失败 28、未运行 563；适配后合计 862（858 上游测试面原样保留 + 4 新增），
  N' ≥ N 不触发 rule2/3。通过率同时给出审查分母口径 267/858 和实际运行
  子集口径 267/295。未运行项不计入通过数，失败归因仍以
  `reports/upstream-tests-report.md` 和 `reports/upstream-test-output.log` 为准。
- `test_package/MANIFEST.yml` 参照 glibmm 2.66.7 先例，以
  `upstream_case_count/upstream_executed_count/upstream_passed_count/
  upstream_failed_count/upstream_not_run_count` 五字段同步该拆分。
- `test_package/CMakeLists.txt` 将 `find_package(wxwidgets-gtk3 CONFIG REQUIRED)`
  固定到 Conan CMakeDeps 导出的 config package，避免误选同名 Find 模块；
  `test_wxgtk3.cpp` 继续真实链接 `wxwidgets-gtk3::wxwidgets-gtk3` 并执行 4
  项无显示 API 断言。

---

**编译结束**: 2026-09-03 00:57
**最终状态**: built
