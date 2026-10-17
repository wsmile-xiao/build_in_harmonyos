# ktuberling 26.04.0 — 适配笔记（ohos-aarch64）

## 概要
ktuberling（土豆先生拼图游戏，KDE Games）26.04.0 在鸿蒙 PC（aarch64-linux-ohos）上通过 conan 完成
交叉编译与运行时冒烟验证。上游无测试套件（N=0），采用消费者 `--version` 冒烟（kfourinline 26.04.0 模式）。

- 包引用：`ktuberling/26.04.0#ac85ac7ff848ec611be07dde2b5bb368:efcf7d24850971715d7b0c04b13f5f8080bf46b5`
- 工具链：clang 15 / cppstd=17 / libc++ / OHOS 6.0 / armv8（`ohos-aarch64` profile）
- 结果：conan create 全绿（1/1 冒烟断言通过，QT_QPA_PLATFORM=offscreen）

## 关键适配决策

| # | 问题 | 决策 | 依据 |
|---|------|------|------|
| 1 | kio 版本：制品仓只有 6.14.0 / 6.26.0，6.26 与 libkdegames 锁定的 KF6 6.18 精确闭包冲突 | 消费者 override=True 将 kio 内部 requires 抬到 6.18.0 闭包 | kfourinline 26.04.0 先例；KF6 同大版本次版本前向兼容；conan graph info 验证 |
| 2 | kdoctools：发布版仅 6.19.0，与 karchive 6.18 pin 冲突，且不属于已发布 KF6 闭包 | 从 REQUIRED find_package 移除 DocTools；doc/ 与 kdoctools_install(po) 上游已有 KF6DocTools_FOUND 守卫 | kfourinline 26.04.0 同款 patch 模式 |
| 3 | Qt6 PrintSupport 缺失：ohpcd qtbase 硬编码 FEATURE_printsupport=OFF，无 Qt6PrintSupportConfig.cmake | 移除 find_package/link 中的 PrintSupport；打印路径用 `__has_include(<QPrintDialog>)` 守卫 | conducteo 5.0.2 / algobox 1.1.1 先例；仅丢失直接打印，"另存为图片"（QtGui QPagedPaintDevice）不受影响 |
| 4 | 上游无测试 | test_package 运行 `ktuberling --version` 冒烟断言 | kfourinline 26.04.0 test_package 模式 |

## 踩坑记录

1. **不要强制 `-o "*:shared=True"`**：制品仓 knotifications/6.18.0 发布的是静态包（shared=False）。
   强制全局 shared 会让 kjobwidgets 等全部依赖 package_id 失配 → 强制重建 → kjobwidgets 已发布配方
   硬编码 BUILD_TESTING=ON，其 ctest（kuiserver2jobtrackertest）在本地设备上因测试环境缺
   libKF6Notifications.so 解析路径而失败。让各包使用各自默认选项后，全部二进制直接命中制品仓缓存。

2. **QT_NO_PRINTER 不可用**：ohpcd qtbase 的 qconfig 并未定义 QT_NO_PRINTER（虽然 printsupport=OFF），
   feature 宏守卫不生效 → `fatal error: 'QPrintDialog' file not found`。改用
   `__has_include(<QPrintDialog>)`（构建期真实探测）。

3. **moc 与 __has_include**：只在 .cpp 里守卫 filePrint 实现不够——头文件里的槽声明会让 moc 生成
   `qt_static_metacall` 引用，链接期 `undefined symbol: TopLevel::filePrint()`。头文件声明必须
   同样用 `__has_include(<QPrintDialog>)` 守卫，moc 会正确展开该预处理指令。

## 依赖闭包（关键节点）
- KF6 6.18.0 closure：karchive/kconfig/kcoreaddons/kcrash/ki18n/kwidgetsaddons/kiconthemes/kcompletion/kio(6.14.0 recipe+6.18 requires)/kjobwidgets/knewstuff/kxmlgui/…
- libkdegames/26.04.0、ecm/6.26.0（tool_requires）
- qtbase/qtmultimedia/qtsvg/qtdeclarative 6.11.1（含 qtbase-sql-dbus）

## 功能损失
- 直接打印（文件→打印）：Qt PrintSupport 在 ohpcd qtbase 中不可用，按 conducteo/algobox 先例裁剪。
- 帮助手册（doc/ DocBook）：kdoctools 不在发布闭包内，KHelpClient 在线手册路径为空。
- 核心玩法（拼图、贴纸、语音、存档、导出图片、全屏）完整保留。
## 对话记录（适配过程摘要）
- 2026-09-21 开工：W0 依赖预检通过（Qt6 6.11.1 / KF6 6.18.0 closure / libkdegames 26.04.0 / ecm 6.26.0 均已发布）；kio 仅 6.14.0/6.26.0（6.26 与 libkdegames 锁定的 6.18 精确 pin 冲突），kdoctools 仅 6.19.0（与 karchive 6.18 pin 冲突）→ 采用 kfourinline 26.04.0 同款策略：kio/6.14.0 recipe + 消费者 override=True 抬到 6.18 闭包（conan graph info 验证），DocTools 从 REQUIRED 移除（上游 KF6DocTools_FOUND 守卫）
- 源码核验：官方 download.kde.org tar.xz，sha256 一致（5a6f2ad4…5150）；上游无测试套件（N=0）
- conan create 迭代 7 轮：(1) kconfig 等直接 requires 补 override=True 消除版本分裂；(2) 发现不可加 `-o "*:shared=True"`——制品仓 knotifications 发布的是静态包，强制全局 shared 使全链 package_id 失配 → kjobwidgets 被迫重建 → 其已发布配方硬编码 BUILD_TESTING=ON 且 ctest 缺 LD_LIBRARY_PATH 解析 libKF6Notifications 而失败；改用各包默认选项后全部命中制品仓缓存；(3) qtbase 硬编码 FEATURE_printsupport=OFF（无 Qt6PrintSupportConfig.cmake）→ 按 conducteo/algobox 先例裁剪 PrintSupport；(4) QT_NO_PRINTER 在该 qtbase qconfig 中未定义，feature 宏守卫失效 → 改用 `__has_include(<QPrintDialog>)`；(5) moc 生成的 qt_static_metacall 引用 filePrint 导致链接期 undefined symbol → 头文件槽声明同样用 __has_include 守卫
- 最终 conan create 全绿（1/1 冒烟断言），test_package `--version`（offscreen）通过；W3 本地 CI：L0/L1/L1e/L5 pass，L2 skip（非阻塞，test_package 内已覆盖）、L4 warn（patch 关键字误报）、pass rate 100%；finish 补齐 test-report.md / packaging / .staging-verified，状态 built
- 功能损失：仅直接打印（Qt PrintSupport 缺失）与 DocBook 手册（kdoctools 不在闭包内）；核心玩法完整
## CI 首轮失败诊断与修复（2026-09-22）

- **现象**：PR #11760 首轮 CI（worker OpenHarmonyPCDeveloper-CI-032，build #55221）死在 `[conan-build-test, cleanup]`，两步均 `zsh: can't open input file: ci/conan/<脚本>` exit 127。
- **定性**：非配方问题。git 取证：分支内 `ci/conan/build_and_test.sh`(1fe74063)/`cleanup.sh`(1160e03c)/`setup.sh`(205db8f1) blob 与 main 完全一致；分支两 commit 仅新增 `archives/k/ktuberling/` 11 文件；同构建中 `conan-setup` 步骤 ✅（该步同样从 repo 工作树读脚本），23 秒后 build-test 才打不开文件 → worker 侧 checkout 树物料化异常（HMDFS 病机，E518/E569「worker 整机病」同类特征）。单轮失败按 E569 方法论不盲改配方。
- **修复动作**：①分支从 10222eeec 变基到最新 main 48d9cee68（W1 同步，落后 108 commit 清零）；②本机执行与 CI 同构全量校验（setup.sh + build_and_test.sh CI_PACKAGES=archives/k/ktuberling/26.04.0）全绿后推送新 head；③推送后评论 /rebuild 重触发 CI（评论触发型，push 不会自动跑）。

- 2026-09-23 CI 第二轮失败（build #56248）修复：source() 下载 71.6MB tar.xz 经 download.kde.org 重定向到 ftp.kaist.ac.kr，3 次重试中断（14%/43%/60%），conan create 3600s 超时（kio/6.14.0 因消费者 override 无法命中预编译二进制需源码重建，叠加慢下载）。修复：conandata.yml URL 切换 mirror.nju.edu.cn 教育网官方 KDE 镜像（同文件 sha256 复验一致，实测 ~18.7MB/s）+ build_timeouts.txt 覆盖 10800s。本机同构 CI 复验 rc=0 全绿（L0/L1/L5 pass，L2 skip 非阻塞，L4 warn 误报）
---

**编译结束**: 2026-09-21 19:27
**最终状态**: built（2026-09-22 CI 修复轮后待复验）
