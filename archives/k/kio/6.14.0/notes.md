# kio 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake (Conan 2.x recipe, `conan create`)
- 编译日期: 2026-09-13
- 编译器: OHOS SDK clang (profile `ci/conan/profiles/ohos-aarch64`, os=OHOS, aarch64)
- 状态: built
- 源码: 官方归档 https://download.kde.org/stable/frameworks/6.14/kio-6.14.0.tar.xz
  (sha256 `9b03746fd008504a96f569f37ad8ff902cc71495e7e123daa3c6de79ff2acc45`)

## 编译步骤

1. `conan create archives/k/kio/6.14.0 -pr:h=ci/conan/profiles/ohos-aarch64
   -pr:b=ci/conan/profiles/ohos-aarch64 --build=kio/*`（权威 CI
   `ci/conan/build_and_test.sh` 自动执行）。
2. `source()` 从官方 URL 下载并解包；`build()` 在 `os=OHOS` 时应用
   conandata.yml 声明的 15 个补丁（含新增 0015）后配置构建。
3. `generate()` 注入：`CMAKE_CXX_STANDARD=20`、`BUILD_TESTING=OFF`、
   `KF_IGNORE_PLATFORM_CHECK=TRUE`、`USE_DBUS=OFF`、`WITH_X11=OFF`、
   `WITH_WAYLAND=OFF`、`BUILD_DESIGNERPLUGIN=OFF`；手工注入
   `ECM_MODULE_PATH`（CMakeDeps 生成的 ECMConfig.cmake 不传播该变量）；
   生成 `conan_cmakedeps_paths.cmake`（qtbase `cmake_find_mode=none`，
   CMakeDeps 不会把 qtbase 的 lib/cmake 加进 CMAKE_PREFIX_PATH）；
   将 libxml2/2.15.3 的 lib 目录注入 LD_LIBRARY_PATH（OHOS lld 链接期需要
   libxml2.so.16）。
4. seed recipe 原含 `package()` 末尾 patchelf DT_NEEDED 改写步骤（把 KF6
   依赖的绝对 conan-cache 路径改为相对文件名，因 KF6 库无 SONAME）；本 run
   已删除该步骤（机理与证据见问题表 #10 与偏离说明 1——原地改写使 .codesign
   签名失效，产物不可加载），DT_NEEDED/SONAME 修复前移到链接期（0015）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KDE 平台探测把 OHOS 当未知平台拒绝配置 | 上游平台白名单无 OHOS | `KF_IGNORE_PLATFORM_CHECK=TRUE` |
| 2 | `find_package(KF6Auth)` 被跳过 / Unix 代码路径缺位 | OHOS 下 `CMAKE_SYSTEM_NAME=OHOS`，CMake `UNIX` 为假 | 0001/0003后半/0014：UNIX 门改写为 `NOT WIN32 [AND NOT ANDROID]` |
| 3 | KAuth 头文件找不到（`<KAuth/Action>`） | 发布的 kauth 包安装小写大小写敏感头文件 | 0004/0007/0008/0009：改为 `<kauth/action.h>` 等小写形式 |
| 4 | QSslError/QSslCertificate 相关源码无法编译 | 发布的 qtbase Qt6Network 未编 SSL | 0003前半/0010/0011/0012/0013：裁剪 KSSL 类与 ftp/http worker，showSslDetails 降级为 no-op |
| 5 | `std::ranges::copy_if/all_of` 编译失败 | ohos-aarch64 profile 钉 cppstd=17，工具链 CMAKE_CXX_STANDARD 被 KF 的 project() 后置 set 压回 17（karchive 6.26.0 同型实证） | 0005/0006：值等价的 C++17 迭代器改写 |
| 6 | find_package(Qt6DBus) 不可消费 | qtbase/6.11.1 `FEATURE_dbus=OFF`（E323），且 kio 的 DBus 面（kiod/kssld/kpasswdserver）需要它 | recipe `USE_DBUS=OFF`，走上游 `HAVE_QTDBUS` 守卫排除 |
| 7 | KF6 依赖 DT_NEEDED 记录绝对 conan-cache 路径 | KF6 库无 SONAME，GNU ld 按输入路径记录 | 0015 链接期 `-Wl,-soname` 使项目内 NEEDED 变裸文件名；外部依赖绝对路径保留（设备 conan-cache 路径有效）。seed 的 `package()` patchelf `--replace-needed` 方案因原地改写签名失效被否决（见 #10） |
| 8 | lld 链接期无法加载 libxml2.so.16 | Worker 环境无系统 libxml2.so.16 | 依赖 libxml2/2.15.3 并注入 LD_LIBRARY_PATH |
| 9 | 首轮权威 CI L5 soname 门报 11 错：产物缺 DT_SONAME，且 KIOWidgets/KIOGui/KIOFileWidgets 的 DT_NEEDED 为构建树相对路径（`../../bin/libKF6KIOCore.so`），运行期不可解析 | OHOS CMake 平台不落实 VERSION/SOVERSION（上游 ecm_setup_version(SOVERSION 6) 被平台层忽略）→ 库无 SONAME → 链接器把依赖库的完整输入路径记入 DT_NEEDED（外部依赖=绝对 conan-cache 路径，项目内依赖=构建树相对路径） | 0015：为四个 KIO 库加 `LINK_OPTIONS "-Wl,-soname,libKF6*.so"`（构建期修复，产物获得 DT_SONAME，项目内 NEEDED 变为可解析的裸文件名） |
| 10 | seed recipe 的 package() patchelf 步骤在本设备不可用：原地改写后的 .so 加载报 `Permission denied`（判别实验证实：改写使 .codesign 签名失效被加载器拒绝，与 xattr 标签无关——改写产物、未改写产物、重签产物的 `security.isolate`/`hmdfs.perm`/selinux 标签完全相同，仅重签后 dlopen 由 EACCES 变 OK；r1 可载、r2 不可载同向） | 已发布包 .so 自带 .codesign 签名；原地改写字节后签名失配，加载器报 Permission denied（E517/E077 面）；且该步骤依赖 PATH 上的 readelf（CI worker 无 → 静默跳过 → 假通过），一旦在有 readelf 的 worker 上运行反而会产出全部不可加载的库 | 删除 package() 的 patchelf 步骤，DT_NEEDED 修复前移到链接期（0015）；无法前移时须按 E077 四步 remove-section→改写→重签→chmod（本轮未采用） |

## 偏离说明（相对缓存 seed recipe 的最小必要修改）

缓存 seed 的 conanfile.py / conandata.yml / patches 0001–0014 逐字保留，仅两处
必要偏离（证据见上表 #9/#10 与运行日志）：

1. **删除 package() 末尾的 patchelf DT_NEEDED 改写块**。该块在本设备上不可能
   成功：原地改写使发布包 .so 自带的 .codesign 签名失配，加载器拒绝映射报
   Permission denied（实证：r1 未改写产物 `dlopen` OK，r2 改写产物 EACCES；
   将改写产物按字节复制到新文件同样被拒——无效签名随字节一起复制；判别实验
   进一步证实与 xattr 标签无关：改写产物经 E077 四步 remove-section→重签→
   chmod 后，xattr 三项标签原样在场而 dlopen 恢复 OK，未重签的仅 remove-section
   负对照仍被拒）。在 CI worker（PATH 无 readelf）上它是静默 no-op；一旦换到
   有 readelf 的 worker 反而会产出整体不可加载的包——属于必须拆除的隐患。
2. **新增 patch 0015 + conandata 声明**：为 KF6KIOCore/KIOGui/KIOWidgets/
   KIOFileWidgets 加 `-Wl,-soname,libKF6*.so`。机制：OHOS 平台层忽略
   VERSION/SOVERSION，无 SONAME 使链接器记录路径形态的 DT_NEEDED；构建期
   显式 soname 后，项目内 NEEDED 变为裸文件名（可经 LD_LIBRARY_PATH 解析），
   库自身也获得 DT_SONAME。外部 KF6 依赖的绝对路径 NEEDED 仍在（设备上
   conan-cache 路径有效，与本仓 KF6 全家族一致），由知识条目记录。

依据 implement-policy「优先诊断根因，允许最小必要修改并在报告中说明偏离理由」。

## 源码修改（14 个补丁的机理分类）

平台探测守卫（OHOS 非 CMake UNIX，按 Unix-like 构建）：

- `0001-CMakeLists.txt.patch`：KF6Auth 的 `if (UNIX AND NOT ANDROID)` →
  `if (NOT WIN32 AND NOT ANDROID)`，保证 OHOS 上仍 find_package(KF6Auth)。
- `0003-src-core-CMakeLists.txt.patch`（后半）：`kioglobal_p_unix.cpp` 的
  `if (UNIX)` → `if (NOT WIN32)`，Unix 全局实现进入 KIOCore。
- `0014-src-kioworkers-file-CMakeLists.txt.patch`：file worker 链接
  Qt6::Network + KF6::AuthCore 的 `if(UNIX)` → `if(NOT WIN32 AND NOT ANDROID)`。

无 SSL 裁剪（发布 qtbase 的 Qt6Network 未编 SSL）：

- `0003-src-core-CMakeLists.txt.patch`（前半）：从 KIOCore 源列表注释掉
  `ksslcertificatemanager.cpp` / `ksslerroruidata.cpp`（依赖 QSslError API）。
- `0010-src-widgets-CMakeLists.txt.patch`：从 KIOWidgets 注释掉
  `ksslcertificatebox.cpp` / `ksslinfodialog.cpp` / `sslui.cpp`。
- `0011-src-widgets-ksslinfodialog.h.patch`：头文件签名中
  `QSslError::SslError` → `int`（配合 0010 的实现裁剪保持自洽）。
- `0012-src-widgets-widgetsaskuseractionhandler.cpp.patch`：
  `showSslDetails()` 降级为 no-op（原实现需要 QSslCertificate/KSslInfoDialog）。
- `0013-src-kioworkers-CMakeLists.txt.patch`：禁用 ftp / http worker 子目录
  （需要 SSL API）；`0002-src-CMakeLists.txt.patch` 为对应的说明性注释。

KAuth 大小写（发布包小写头文件）：

- `0004-src-core-slavebase.cpp.patch`：`<KAuth/Action>` → `<kauth/action.h>`。
- `0007-src-kioworkers-file-file_unix.cpp.patch`：`<KAuth/Action>` /
  `<KAuth/ExecuteJob>` → 小写。
- `0008/0009`：file KAuth helper 的 `<KAuth/HelperSupport>` /
  `<KAuth/ActionReply>` → 小写。

C++20 ranges → C++17 迭代器（profile cppstd=17）：

- `0005-src-filewidgets-kfilefiltercombo.cpp.patch`：
  `std::ranges::copy_if` → `std::copy_if(begin, end, ...)`。
- `0006-src-gui-systemd-systemdprocessrunner.cpp.patch`：
  `std::ranges::all_of` → `std::all_of(begin, end, ...)`。

平台行为修复（2026-09-15 真因修复轮，仅两枚，均不改测试 oracle）：

- `0016-src-gui-kprocessrunner.cpp.patch`：根因链——`CommandLauncherJob` 对
  不存在/不可执行命令走 `/bin/sh -c`（sh 退出码 127 → `slotProcessExited` →
  `emitDelayedError` → deleteLater，路径健全），但 `fromExecutable` 直 exec
  的可执行文件在 OHOS 上被安全策略拒绝执行（用户可写存储上的系统二进制拷贝
  exec 报 EACCES，raw 探针实证：拷贝 toybox 到 FUSE 目录 exec rc=126，同目录
  自编译二进制可执行）时 QProcess 发 `errorOccurred(FailedToStart)` 且**永不
  发 finished()**，`slotProcessExited` 不运行 → KProcessRunner/KProcess 永久
  泄漏（实测 instanceCount=2 残留并污染后续子测）。修复：`slotProcessError`
  对 FailedToStart 走与 127 相同的 `emitDelayedError`（延迟发 error +
  deleteLater）。平台中立、能力探测式（对正常路径零影响）。
- `0017-src-urifilters-shorturi-kshorturifilter.cpp.patch`：根因链——
  本构环境 ksycoca 无协议注册项（KF6 协议注册链 = kf6/kio 目录下 worker
  插件 JSON 元数据，http/https worker 因 qtbase 无 SSL 未编入）→
  `isKnownProtocol("https")` 恒 false → 短 URL 分支把默认 scheme
  "https://" 再拼一层 "://" 产出畸形 URI `https:////host`（合法形态应为
  先判 URL 本身：`QUrl("https://gg:www.kde.org")` 因端口非数字 invalid，
  上游正是靠这条 Error 路径交棒 kurisearchfilter 完成 gg: 关键词搜索）。
  修复：scheme 串已含 "://" 时不再追加。注册表健全的系统行为不变。

## 依赖版本

- qtbase/6.11.1（Qt6Core/Gui/Widgets/Network/Concurrent；无 DBus、无 SSL、
  无 UiPlugin）
- KF6 6.14.0：karchive kconfig kcoreaddons ki18n kservice solid kcrash
  kbookmarks kcolorscheme kcompletion kguiaddons kiconthemes kitemviews
  kjobwidgets kwidgetsaddons kwindowsystem kauth
- libxml2/2.15.3（lld 链接期 libxml2.so.16）
- ecm/6.20.0（tool_requires）

## 验证结果

- 权威 CI（r3，9c0915b7de）：`ci/conan/build_and_test.sh`
  （CI_PACKAGES=archives/k/kio/6.14.0，profile ohos-aarch64）
  **PASS**（Success 1/1）。L0=pass；L1=pass（test_package 执行 + L1e 破坏性
  负测试确认真实依赖）；L2=skip（ktelnetservice6/ktrash6 无头环境无法
  --version，非阻塞）；L4=warn（补丁含 strcpy/sprintf 关键词，上游代码语境，
  非阻塞）；L5=fail（soname 门残 7 错：6 错为外部 KF6 依赖的绝对
  conan-cache DT_NEEDED（家族性，源自其他包，设备上可解析）；1 错为本包
  自有产物 libkuriikwsfiltereng_private.so 缺 DT_SONAME（patch 0015 仅覆盖
  4 个主库，属本配方残余而非家族性）；另 KF6KIO Targets.cmake 保留
  IMPORTED_NO_SONAME TRUE（平台模块不感知链接旗标）；见 notes 问题 #9/#10
  与知识草稿，非阻塞）。包目录 `.conan2/p/b/kiod1567cf5ce34e/p`。
- 权威 CI（r4，2026-09-15，含新增补丁 0016/0017）：`ci/conan/build_and_test.sh`
  （CI_PACKAGES=archives/k/kio/6.14.0，profile ohos-aarch64）
  **PASS**（Success 1/1）。门禁结论与 r3 完全一致（L0=pass、L1=pass、
  L2=skip、L4=warn、L5=fail 非阻塞 soname 残余，逐项同 r3）。E415 原地改写
  核验通过：全仓 63408 个跟踪文件 pre/post sha256 逐一相同，conandata.yml 由
  CI 自还原。包/构建目录 `.conan2/p/b/kio1d34425d296ee`。
- 消费者冒烟（test_package）：链接 libKF6KIOCore，执行 KIO::UDSEntry
  写读回环 + KProtocolInfo 协议注册表查询：**PASS**
  （`PASS: KIO UDSEntry roundtrip OK`）。
- 上游测试门禁（第一轮实测，证据 testgate-run.log / testgate-run-iter1.log）：
  1. BUILD_TESTING=ON 在本 profile 可配置（Qt6 Test/Network/Xml/Concurrent
     组件均在发布 qtbase 中）；
  2. 套件编译阻塞 1 处：autotests/kfilewidgettest.cpp 使用 C++20 独有的
     括号聚合初始化 `LocationTestItem(true, "folder1")`（P0960），profile
     钉 cppstd=17 无法编译——需改上游测试源码才能构建；
  3. 将该文件排除出构建（仅实验，不入候选）后套件可全量编译，ctest
     实测 **17 通过 / 42 失败（59 项，29%）**：失败集中于 KSycoca/DBus
     会话（kprotocolinfo/kurifilter/desktopexecparser/knewfilemenu 系）、
     trash 守护进程（testtrash 超时）、会话服务（commandlauncherjob
     scope/service）、GUI 会话前置（kfilewidgets 系）等无头 OHOS CI 不具备
     的桌面环境；3 项超时（testtrash/jobtest/jobremotetest）。

## 上游测试环境补充实验（2026-09-13，用户授权 AUTHORIZED_ENV_RETRY）

第一轮"无桌面环境"结论被推翻大半：逐项排查后，真正的阻塞是 5 个可指名的
设备/构建层问题 + 少量真实平台限制。全部实验在
`tmp/oh-device-porting-v2/kio-6.14.0/` 与 conan 缓存 scratch（b/kio16310a48b9232）
内进行，**工程候选零改动，权威 CI 未重跑（无工程输入变化）**。

环境修复层（按根因）：

| # | 根因 | 证据 | 对策（仅实验树） |
|---|------|------|------------------|
| E1 | ssh 域对文件系统 AF_UNIX `bind()`/`mkfifo` 全域 EPERM；抽象命名空间 socket 与 TCP loopback 可用（python/clang 探针实证） | tmp/probe_sock.sh、probe_ldpreload.sh 输出 | KIO patch：connectionbackend.cpp 以原生 fd 做抽象 bind/listen/connect，再 `QLocalServer::listen(fd)`/`QLocalSocket::setSocketDescriptor` 移交 Qt |
| E2 | OHOS Qt 构建把 `PlatformSupportsAbstractNamespace` 编译为 false → `AbstractNamespaceOption` 降级 WorldAccess → chmod/rename socket 文件 → `EOPNOTSUPP(95)` | qlocalserver_unix.cpp L31-44 + listdirtest 失败串 `Unknown error 95` | 同 E1（绕开 Qt 选项机制） |
| E3 | /storage FUSE 把所有文件属主显示为挂载属主(20001006:1006)，进程真实 uid=20020085 → Qt `checkXdgRuntimeDir` 永不通过 → RuntimeLocation 返回空 → worker 启动落在 `/` 报 Permission denied | testgate-run.log listdirtest QWARN + qstandardpaths_unix.cpp 源码 | XDG_RUNTIME_DIR 每轮首建（Qt mkdir(0700) 成功即通过检查） |
| E4 | ECM 把 `QT_PLUGIN_PATH=$BUILD/bin` 烘焙进 CTestTestfile 的 ENVIRONMENT 属性，覆盖外部 env → offscreen 平台插件找不到 | run3 前 widget 簇 0.04-0.08s 秒败、无任何 QTest 输出 | sed CTestTestfile 指向 qtbase 包 plugins（49 处） |
| E5 | conan KF6 包大量相对路径 DT_NEEDED（`../../bin/`、`../../../bin/`），musl 按进程 CWD 解析 → CWD=$BUILD 时不可解析 → 加载即死 | direct 运行输出 `Error loading shared library ../../bin/libKF6IconThemes.so` | 在相对路径落点建 symlink farm（b/bin、kio16310a48b9232/bin）；qtsvg 包 lib 追加进 LD_LIBRARY_PATH |
| E6 | jobtest/jobremotetest 硬编码 `/tmp`（只读 fs）→ qFatal | run2 log `QFATAL ... couldn't create /tmp/jobtest/` | 实验树改 `QStandardPaths::TempLocation`（上游源码未动） |

工具链/设备级根本限制（证据充分，非环境可补）：

- **kfilewidgettest.cpp 无法编译**：设备 clang 15.0.4 不支持 P0960（括号聚合
  初始化，clang 16+ 才实现）。最小探针 `Agg a(true,"x")` 在 `-std=c++20` 下
  仍报 no matching constructor；恢复该测试目标后 8 errors 与语言标准无关。
- **kdirmodeltest 需要 mkfifo**：设备无任何对本域可写的 fifo-capable 文件
  系统（/tmp 只读、/data/local/tmp 拒绝、/data/storage/el2 tmpfs 对本域
  Permission denied、/storage FUSE mkfifo EPERM）→ QFATAL named pipe。
- **http/ftp 面**：qtbase 无 SSL（上游依赖事实），http/ftp worker 未编入，
  mimetypefinderjobtest 的 http/ftp 子测、kprotocolinfotest 的 http 协议
  断言不可满足（修依赖 qtbase 重编，超出本 run 范围）。
- **dataprotocoltest iso8859-7 子测**：Qt 文本编解码缺 ISO-8859-7（qtbase
  无 ICU），期望 UTF-8 字节串得到 Latin-1 直通。
- **kfileitemtest 权限断言**：FUSE 强制 setgid+0751 形态权限（1513 vs 0700），
  无真实权限语义的可写文件系统。

实测结果（ctest 官方计数）：

| 轮次 | 套件 | 通过 | 失败 | 说明 |
|------|------|------|------|------|
| 基线（第一轮） | 59 | 17 | 42（含 3 超时） | 无环境补充 |
| run3（E1-E6 全部生效） | 59 | **23** | 36（含 1 超时：kiocore-jobtest 120.03s） | 新增通过：listdirtest、mkpathjobtest、threadtest、deletejobtest、batchrenamejobtest 等；基线 3 项超时消除 2 项（testtrash、jobremotetest），kiocore-jobtest 未消除（run3/run4/run6 一致 Timeout 120s，归残余清单） |
| run6（60 项含 kfilewidgettest） | 60 | 23 | 37 + 1 Not Run | kfilewidgettest 因 P0960 无法构建；设备存储在会话末段降级（.conan2 文件短暂性 ENOENT），widget 簇末段数字可信度受限 |

直接运行补充证据（非 ctest 计数）：testtrash 从 120s 超时变为真实执行，
**54/57 子测通过**，仅 root 属主文件语义 3 项失败（需 root chown，环境不可补）；
commandlauncherjob_forkingtest 大部分子测通过，残留"带空格可执行路径"与
错误进程回收计数两类行为性失败；kurifiltertest 可执行但 URI 归一断言在
设备路径形态下不满足。

逐簇终局分类：环境已修复（worker 启动簇；超时簇仅消除 testtrash、
jobremotetest 两项）；环境已补仍失败（KSycoca/应用数据簇、commandlauncher
残留子测、krecentdocumenttest、kurifilter 断言簇）；残余未消除
（kiocore-jobtest 持续 Timeout 120.03s，run3/run4/run6 一致复现，归因未定，
随残余清单交付）；根本不可行（P0960 工具链、mkfifo、SSL/http、ICU
编解码、FUSE 权限语义、root 属主）。完整证据链与可复用环境脚本见
`tmp/oh-device-porting-v2/kio-6.14.0/`（kioenv.sh、sockshim.c、
connectionbackend.cpp patch、logs/testgate-run*.log）。

  结论（更新）：上游套件在本设备**真实可运行**，NOT_RUN 不再成立；
  建议按"上游测试 PARTIAL_PASS（23/59 基线套件 + 平台限制清单）"推进，
  剩余失败均已逐条归因（见上表与分类），其中可修部分依赖 qtbase 重编
  （SSL/ICU）、root 权限与设备工具链升级（clang 16+），均超出本 run 范围。

## 上游测试环境补充实验（2026-09-15，真因修复轮收口）

本轮对残余 22 项中 7 项"行为性失败"做库内真因修复（0016/0017），并把
2026-09-14 的环境提升层（E1-E6）在新工程树（kio1d34425d296ee）上完整复刻后
复测。证据：logs/testgate-run10{,b,c}.log、clr3-iter{0,1,2}/、probes/（rawabs、
sockprobe、exec 探针）、exp-connbackend.diff。

| 轮次 | 套件 | 通过 | 失败 | 说明 |
|------|------|------|------|------|
| run7b（09-14，旧树，无 0016/0017） | 59 | 37 | 22 | 环境提升后基线 |
| run10（09-15，新树，E1-E6 未复刻） | 59 | 26 | 33 | 设备重启（09-15 09:44）后 ssh 会话域名 20001006→20020085、FUSE 属主映射不变，Qt runtime-dir 属主检查失配，叠加 E4 未复刻 → 11 项新增失败（listdirtest/jobremotetest/mkpathjobtest/threadtest/deletejobtest/deleteortrashjobtest/batchrenamejobtest/clipboardupdatertest/fileundomanagertest/pastetest/kdiroperatortest），另 2 项失败模式变化；确认为环境复刻缺失，非补丁回归 |
| run10c（09-15，新树 + E1-E6 复刻 + 0016/0017） | 59 | **37** | 22（清单与 run7b 完全一致） | 373.7s；ctest 计数持平，子测试层净增益见下 |

补丁效果的子测试级实证（直跑，环境与 ctest 一致）：

- commandlauncherjob_forking/scopetest/servicetest ×3：每二进制 9 通过/4 失败
  → **11 通过/2 失败**，单轮 31s → 0.44s（0016 生效："错误进程回收后
  instanceCount=2≠0" 两子测转通过）。残余 2 失败 = 带空格可执行路径
  waitForStarted=false，归因②类：设备安全策略拒绝执行用户可写存储上的
  系统二进制拷贝（EACCES），非库行为缺陷。
- kurifiltertest ×2：colon 69/35、space 70/34 → **92/12** 每二进制（0017
  生效 + 测试环境 PATH 补入 kservice 包 bin 修复 executables(kbuildsycoca6)
  ×2；共 +23/+22 子测）。

残余 12 子测/二进制最终归簇（kurifiltertest colon 为例，space 变体同构）：

| 簇 | 子测 | 根因 | 分类 |
|----|------|------|------|
| isKnownProtocol 注册表缺失 | noFiltering(http://www.kde.org)×2、shortUris 带 http:/ftp: 前缀 ×6、refOrQuery ×1、environmentVariables ×1 | http/https/ftp worker 未编入（qtbase 无 SSL）→ ksycoca 协议项缺失 → isKnownProtocol 恒 false，带 scheme 输入走不到 NetProtocol 早退而被 KAutoWebSearch 兜底为 google 搜索；协议注册链=worker 插件 JSON（非 .protocol 文件），补齐依赖 qtbase SSL 重编 | ①依赖性，超出本 run |
| passwd 语义 | localFiles(~bin)×1 | /etc/passwd 有 bin 但 home 字段为空（bin:x:2:2:::/bin/false）→ KUser 无效 home → ERROR≠LOCAL_DIR；应用 uid 20020085 无 passwd 项 | ②库行为正确（oracle 假设 Unix passwd 完整） |

三处既往结论修正：

1. **kbuildsycoca6 曾加载失败而非预热无效**：早期"预热无效"归因不成立，
   实际是该二进制当时相对路径 DT_NEEDED 无法加载；E5 symlink farm 后可正常
   运行并产出 ksycoca 缓存，预热本身有效。
2. **http 注册链是 worker 插件 JSON 而非 .protocol**：KF6 KProtocolInfo 的
   协议项由 kbuildsycoca6 从 kf6/kio 下 worker 插件 JSON 元数据构建，本构无
   http/https worker 故注册表无这些协议。
3. **IgnoreHidden 假设不成立**：kurlnavigator userHomeDir 失败与 hidden
   过滤无关；真因是 oracle 假设 `~<loginName>` 展开依赖 passwd——应用 uid
   20020085 无 passwd 项，KUser 无效 → loginName 空 → 输入退化为 "~"，库侧
   正确展开为 $HOME，期望值 QUrl::fromLocalFile(空串)=Invalid URL 恒不可满足。

其他残余归簇维持并补充本轮证据：

- kdirlistertest（ctest Timeout）：FUSE inotify 语义不完整（探针实证 create
  仅发 IN_ATTRIB 无 IN_CREATE，write/close/rename/delete 事件缺失或不确定）；
  kcoreaddons KDirWatch 仅对 IN_CREATE|IN_MOVED_TO 发 created()，kio 侧
  handleFileDirty 的未知文件父目录重列降级已存在但事件本身缺失。修复落点在
  kcoreaddons KDirWatch（stat 轮询回退）——**越界（本 run 仅
  archives/k/kio/**），归档为边界阻塞**。
- kurlnavigator：run9 直跑 13/1；本轮直跑 12/2，新增 testRelativePaths 失败
  为重启后设备 QLocalSocket 连接拒绝（会话域名变化）所致的测试内辅助 socket
  失败，非库回归（0017 不触该文件）；userHomeDir 维持②类（passwd）。
- 设备重启（09-15 09:44）引入的会话域名变化（20001006→20020085，FUSE 存储
  写入属主映射保持 20001006）使 Qt XDG_RUNTIME_DIR 属主检查必挂：实验树在
  E1 原生抽象 socket fd 方案上追加兜底（QTemporaryFile 不可用时以合成名直走
  抽象 socket，raw 探针实证抽象 bind/listen 在新域名下仍被允许）；该兜底仅在
  实验树，不入候选。

结论（最终）：新树 + 0016/0017 复测 **37/59**（22 失败清单与 run7b 完全
一致）；行为性失败子测试净减 +51（commandlauncherjob +2×3、kurifiltertest
+23/+22）；其余残余归因见上表，可修部分依赖 qtbase SSL 重编（http/https
协议注册面）与 kcoreaddons KDirWatch 的 FUSE 回退（越界，已归档）。

## 注意事项

- 本版本 `BUILD_TESTING=OFF`（门禁结论见上节）。
- 下游消费 kio 时 CMakeDeps 不参与（`cmake_find_mode=none`），消费方用
  kio 自带的 `KF6KIOConfig.cmake`，需要把 KF6 各依赖包的 lib/cmake 加入
  CMAKE_PREFIX_PATH（test_package/conanfile.py 的 generate() 是可复制样例）。
- http/ftp worker 未编入：`KIO::get("http://...")` 等作业在该构建无 worker
  可用；SSL 相关 UI（KSslInfoDialog）不可用。
- `KProtocolInfo` 依赖 KSycoca 缓存；沙箱首次查询可能返回空表属预期。
- 外部 KF6 依赖的 DT_NEEDED 为绝对 conan-cache 路径（构建机上有效）；这是
  本仓 KF6 家族共同状态，待各依赖库自身补 soname 后逐级消除。

---
**编译结束**: 2026-09-15（含 0016/0017 真因修复轮与 CI r4 重跑）
**最终状态**: built
