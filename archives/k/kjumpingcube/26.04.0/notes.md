# kjumpingcube 26.04.0 notes

## Scope

KDE release-service 26.04.0 的 KJumpingCube（KXmlGui GUI 游戏，单可执行
`bin/kjumpingcube`，无库产物）。官方发布归档：
`https://download.kde.org/stable/release-service/26.04.0/src/kjumpingcube-26.04.0.tar.xz`
（SHA256 `834e1245d84b40608d06d80c34c10eeaf7fdf26d068b56335b04aa19c60ba447`，
Scout 固定并已在本机复核一致）。

## Upstream tests: NO_UPSTREAM_TESTS（EVIDENCE_COMPLETE）

上游 26.04.0 不含任何测试套件，已对照官方归档核证：

- 无 `autotests/`、无 `tests/` 目录；
- 全树 grep 无 `add_test` / `enable_testing` / `include(ECMAddTests)` /
  `ecm_add_test`（`po/` 除外，为翻译目录）；
- `src/CMakeLists.txt` 只注册 `add_executable(kjumpingcube)`。

因此按 NO_UPSTREAM_TESTS 路线：`BUILD_TESTING=OFF`，正确性由
test_package 消费者测试承担（见下）。

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列）。
- `KF_SKIP_PO_PROCESSING=ON`：跳过 `ki18n_install(po)` 的翻译目录处理
  （完整 gettext 工具链非游戏所需；libkdegames/kxmlgui 先例）。
- **KF6DocTools 缺口**：ohpcd 无 kdoctools/6.18.0（KF6 6.18.0 家族锁），
  patch 掉 `add_subdirectory(doc)` 与 `kdoctools_install(po)`，并从 KF6
  umbrella find_package 组件表移除 DocTools（手册文档不参与构建/运行）。
- **KIO 消费（kio/6.14.0 + 家族 override）**：`src/game.cpp` 真实使用
  KIO（`KIO::stat` / `KIO::file_copy`，游戏状态经 URL 保存/加载，配合
  KJobWidgets::setWindow），不能裁剪。ohpcd 无 kio/6.18.0（仅
  6.14.0/6.26.0；6.26.0 会要求 kconfigwidgets/kiconthemes 等不存在的
  6.26 族）。因此消费 kio/6.14.0，并以 `override=True` 将其全部 6.14
  依赖钉（kauth/kbookmarks/kcolorscheme/kcompletion/kconfig/kconfigwidgets/
  kcoreaddons/kcrash/kguiaddons/ki18n/kiconthemes/kjobwidgets/kservice/
  kwidgetsaddons/kwindowsystem/solid/karchive）统一升到 6.18.0，与家族
  一致：kio 已安装 configs 请求 `find_dependency(KF6* >= 6.14)`，6.18.0
  满足；KF6 大版本内 ABI 稳定（同 kxmlgui/6.18.0 消费 karchive/6.19.0
  制品的先例）。教训记录：首轮曾误判源码零 KIO 引用（grep 引号转义被
  ssh 层吞掉导致漏检 `#include <KIO/FileCopyJob>`），CI attempt2 以
  `fatal error: 'KIO/FileCopyJob' file not found` 证伪后回改。
- **Qt6::DBus**：`main.cpp` 经 KF6DBusAddons（KDBusService）需要
  Qt6::DBus；制品仓 qtbase/6.11.1 基础变体未开 FEATURE_dbus（知识 E323），
  按 E441 直接消费 `qtbase-sql-dbus/6.11.1` 变体（与已发布的
  kdbusaddons/6.18.0 配方一致），并在 `conan_cmakedeps_paths.cmake` 中把
  该变体的 `lib/cmake` 确定性地置于搜索首位，防止传递引入的 plain qtbase
  变体抢先解析 Qt6Config 导致 `Failed to find required Qt component
  'DBus'`。
- **libkdegames/26.04.0.1**：消费 SONAME 修复版（官方 26.04.0 为
  SONAME 缺陷版，禁止消费；26.04.0.1 已合入官方 main 并发布 ohpcd）。
- **karchive override**：kiconthemes/6.18.0 现行 revision 要求
  karchive/6.19.0 而 knewstuff/6.18.0 要求 6.18.0，`override=True` 钉住
  6.18.0 保持全图一致（libkdegames/26.04.0.1 同解法）。
- **ECM_MODULE_PATH / conan_cmakedeps_paths.cmake**：手工设置/生成
  （CMakeDeps 不传播 ECM_MODULE_PATH；qtbase 系 cmake_find_mode=none）。
- **DT_NEEDED 清洗与重签名（E537）**：package() 对 `bin/`、`lib/` 下的
  ELF 产物做 in-place `.dynstr` 路径形态 DT_NEEDED → basename 清洗
  （SONAME 缺失的 KF6 依赖会把 conan 缓存绝对路径写进 NEEDED），
  `llvm-objcopy --remove-section .codesign` 后 `binary-sign-tool
  -selfSign 1` 重签名；禁用 patchelf（重写 program header 后 musl 拒载）。
- **test_package 平台自愈垫片（方案 B）**：test() 开始时对依赖闭包做
  迭代路径形态 DT_NEEDED 修复（机制/根因/限制见下节专述）。

## test_package 平台 PR-check 自愈垫片（2026-09-26，方案 B）

**现象**（平台 buildbot PR-check，同一设备，conan home
`/storage/Users/currentUser/.cache/conan2`）：编译、打包、自有 14 条
NEEDED 清洗全部成功；test_package 冒烟 rc=127，musl 报
libKF6XmlGui.so（kxmlgui/6.18.0 缓存二进制）需要的
libKF6IconWidgets.so / libKF6IconThemes.so 加载失败，且错误打印的是
**绝对路径** `/storage/Users/currentUser/.cache/conan2/p/kicon*/p/lib/...`
——kxmlgui 的 DT_NEEDED 是构建期烙进二进制的路径形态。

**根因（两层）**：

1. 本配方自己的产物已在 package() 做 E537 清洗，但**依赖方的缓存二进制
   带着同样的病**：kxmlgui 等配方发布制品时未清洗，SONAME 缺失使其
   DT_NEEDED 烙有构建机的 conan 缓存绝对路径（实测 11 条）。这些路径
   指向的目录在本机是早期 run 留下的跨 conan home **symlink 桥**（指向
   旧默认 home `.conan2`）：SSH 交互上下文沿 symlink 能加载成功，平台
   buildbot 上下文同链路断裂（rc=127）。他人包不能改，只能在本包
   test_package 运行时自愈。
2. 被 symlink 指到的 libKF6IconWidgets.so 自身还有 `../../bin/`
   相对形态 DT_NEEDED（musl 无 `$ORIGIN`，按进程 CWD 解析）——与本包
   已修的自有二进制 `../../bin` 相对 NEEDED 同病（现有镜像手法覆盖）。

**垫片机制**（test_package/conanfile.py `test()` 开始处，纯 python、
只从 conan 解析图取源、HMDFS 真实文件）：

1. 初始扫描集合 = 自己打包的 `bin/` + `self.dependencies` 解析到的各
   依赖 `package_folder/lib/`（严禁从任何硬编码 conan home 读）。
2. 用与配方 d_val 清洗器同一模型的纯 python ELF 解析器（只读）提取
   DT_NEEDED 中含 `/` 的路径形态条目。
3. **绝对路径条目**：目标为 symlink 或缺失 → `os.makedirs(dirname)`
   后从依赖 package_folder 里按 basename 找同名文件（真实文件优先），
   `copy2` 字节级拷贝原地替换——OHOS 签名随字节走，无需重签；找不到
   源则 fail-fast 报清晰错误（ConanException）。
4. **相对路径条目**：在测试进程 CWD 下按相对层级 mkdir + 镜像拷贝
   （与自有二进制 `../../bin` 镜像同手法）。
5. 新拷入文件加入扫描集合，迭代到闭包稳定（上限 10 轮）；`self.output`
   全程打日志；目标已是真实文件时跳过（幂等）。
6. 运行环境约束遵守既有手法：运行时变量仍走命令行内联（conan 2.29
   `test()` 运行作用域会替换进程环境）；垫片只创建真实文件/目录
   （HMDFS 禁 symlink），替换 symlink 也是先删链接后放真实文件。

**已知限制**：

- 本地权威 CI 运行在 SSH/旧 conan home 上下文，symlink 桥在本地恰好
  可用——本地绿只证明垫片没改坏既有路径，**真正的验证是平台 PR
  re-run**（本次返修的验收门）。
- 垫片首次运行会把解析图内目标路径上的失效 symlink 替换为真实拷贝
  （对共享 conan 缓存目录的写副作用；方案 B 明确接受，后续运行幂等
  跳过）。
- 若某路径形态条目的 basename 在解析图依赖包内找不到真实源，test()
  fail-fast 并报出条目、来源文件与目标路径（宁可清晰失败，不做隐式
  加载尝试）。

## Products

- `bin/kjumpingcube`（KXmlGui GUI 应用）
- 桌面文件/元信息/kcfg/主题（SVGZ，gzip 兜底）/图标/日志类别等数据文件

## Verification

- 首轮权威 CI：`ci/conan/build_and_test.sh`（profile
  `ci/conan/profiles/ohos-aarch64`），本地以
  `CI_BRANCH=feat/kjumpingcube-26.04.0` 真实执行 L0n 分支门禁（吸取
  libkdegames run 教训）。结果记入 run 根目录 progress.json 与
  ci-attemptN.log。

test_package（NO_UPSTREAM_TESTS 路线的消费者验证，R34 实质消费）：

1. 无头冒烟：`bin/kjumpingcube --version`（offscreen Qt 平台 + 沙箱
   HOME/XDG），断言退出码 0 且输出版本 2.1.x——同时证明 musl 加载器经
   conan 提供的 LD_LIBRARY_PATH 显式闭包解析全部 KDEGames6/KF6/Qt6
   DT_NEEDED；
2. OHOS 断言（E537 对齐）：llvm-readelf 确认产物 DT_NEEDED 无路径形态
   （绝对缓存路径 / `../` 相对）条目；
3. libKDEGames6 出现在 DT_NEEDED 中（真实消费 libkdegames 依赖）。

- 平台 PR-check 失败返修（2026-09-26）：test_package 语义变化，验证
  影响 = FULL，attempt7 完整重跑权威 CI（ci-attempt7.log）。平台侧
  真实验证 = 平台 PR re-run（用户在 PR 页触发）；本地 attempt7 绿仅
  证明返修未破坏既有语义。
