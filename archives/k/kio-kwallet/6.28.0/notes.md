# 适配笔记 — kio-kwallet 6.28.0 (HarmonyOS PC / OpenHarmony)

## 任务类型
派发名 kio-kwallet/6.28.0：KDE Frameworks 6 KWallet（kwallet）API-only 库向
OpenHarmony / HarmonyOS PC (aarch64) 的 conan 适配升级。仓库已有 kwallet/6.18.0
基线（为 libkgapi 构建），本条目按派发名交付 6.28.0，保持相同的 KF6::Wallet
API-only 范围（不含 kwalletd 守护进程，kio 链条只需要 API 库）。

## 依赖拓扑结论（W0 只读分析）
- 上游 6.28.0 的依赖链（src/CMakeLists.txt + KFDEP_VERSION）：ECM、Qt6 Core/GUI/
  Widgets（Windows 才有 Concurrent）、KF6Config、KF6Notifications、KF6I18n、
  KF6WindowSystem、KF6Colorscheme（API 库本体仅 Core/GUI/Widgets + Config +
  WindowSystem 直链）。
- API-only 范围内 kwallettest（唯一测试目标）依赖 Qt6 Test + Widgets。
- ohpcd 现有包：qtbase-sql-dbus/6.11.1（含 Widgets/Test，可满足）、
  kconfig/6.26.0（cmake_find_mode=none，头文件+工具）。KF6I18n/Notifications/
  WindowSystem/Colorscheme 仅被未纳入范围的部件使用，recipe 以
  KF6_WALLET_BUILD_KWALLETD/BUILD_TOOLS etc. 全部关闭后不触达。
- KF_DEP_VERSION / ECM 版本协商被补丁 0001 对齐到 6.26.0（ohpcd 基线），
  其余依赖按 6.28 源码声明接受。

## 版本 pin 理由
- kconfig pin 6.26.0：ohpcd 当前仅发布 6.26.0；KF_DEP_VERSION 补丁让
  find_package(KF6Config 6.26) 通过。
- ecm pin 6.26.0（tool_requires）：ECM 的 KDEPimVersion/KF 版本协商逻辑在
  find_package(ECM 6.26) 时同样需要对齐，6.26.0 与 kconfig 同代。
- qtbase pin 6.11.1：仓库基线（6.18.0 kwallet 配方同源），向上兼容 6.28 源码
  所需的 API。

## E018：symlink 域隔离与 copy-instead-of-link 方案
- 本机实测：conan 的 python 进程树整体被禁 symlink(2)——os.symlink 直接
  EPERM；make 阶段 `cmake -E cmake_symlink_library` 报 "Permission denied"。
  交互 bash 域不受限（`ln -s` 可用），即沙箱按进程域授予 symlink 权限。
- 关键陷阱：仅把 VERSION 属性置空串仍会生成尾部点号产物
  `libKF6Wallet.so.`（cmake 拼接 `<soname>.<version>`，空 version 也拼），
  随后创建 `libKF6Wallet.so.` -> `libKF6Wallet.so.6` 的 symlink 依旧触发
  E018。**必须整行删除 VERSION/SOVERSION 两个属性**（补丁 0002）。
- 保上游 DT_SONAME：configure() 注入
  `CMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,libKF6Wallet.so.6`（仅 shared）。
- package() 在签名前物化 soname 名：`cp libKF6Wallet.so -> libKF6Wallet.so.6`
  （_materialize_soname_copy），两份 ELF 都走 OHOS 签名。消费者
  test_package 的运行时链接收集 glob `lib*.so*` 同时覆盖两个文件。

## 上游测试真相（如实记录）
- kwallettest 是 `add_executable` + `ecm_mark_as_test()`，**没有 add_test()**
  → `ctest -N` 注册数为 0，"No tests were found" 是上游本态，非适配缺失。
- recipe 的 R51 三步法：`ctest -N` 盘点（0 如实记录）+ 硬断言
  bin/kwallettest 已构建 + 直接执行并强制退出码。
- **终态（v2 配方，daemon 栈真实执行）**：3/3 全部通过，无跳过，见下文
  「对话 #4」。早期 API-only 口径（2 passed / 1 skipped，DISPLAY 平台守卫）
  已被 daemon 栈方案取代，作为历史记录保留于对话 #1–#3 与 git 历史。

## DISPLAY 守卫（Qt offscreen 陷阱）
- 本机无显示服务但环境残留 DISPLAY 时，kwallettest 的 QApplication 路径
  SIGSEGV。
- recipe 在 `_run_upstream_tests` 里 `os.environ.pop("DISPLAY", None)`。
  **不能用 conan `Environment.unset()`**：它把变量置空而不是删除，而 Qt 的
  `qEnvironmentVariableIsSet` 对 set-but-empty 返回 true，守卫被击穿
  （已用最小 envtest 包实证）。

## 本地 CI 模拟（W3）在此设备上的运行时事实（供后续包参考）
- 设备沙箱按进程域授予 exec/symlink：conan/W3 python 域可 exec
  /data/service/hnp/*、/system/bin/*（toybox 全套）与 .pi/agent/bin/*，
  不可 exec /usr/bin、$HOME/tmp、$HOME/usr/local/bin 之下"新创建"的脚本；
  且域内无 exec 转移，链式 exec 无法越界。
- 设备自带 zsh（/usr/bin/zsh，真 zsh 5.x）python 域不可达；可达的
  .pi/agent/bin/zsh 是完整 zsh 5.9，但 heredoc 临时文件硬编码 /tmp/zsh
  （无视 TMPDIR），而 /tmp 在此设备只读。
- 解法：`$HOME/.zshenv` 设 `TMPPREFIX=$HOME/tmp/zsh; export TMPPREFIX`
  （zsh 每次启动无条件 source .zshenv），heredoc 即落可写目录；toybox
  applet 经 PATH 首位的 /system/bin 正常解析。CI worker 无此文件、行为不变。
- 另外：本机清理会丢 export 的自定义变量并重写 TMPDIR/TMPPREFIX，运行
  finish 时 TMPPREFIX 依赖 .zshenv 兜底；TMPDIR 给 bash heredoc 用（置为
  $HOME 亦可写）。

## G0/归档说明
- 源码核验：kwallet-6.28.0.tar.xz sha256
  e21130c86ffa0be49065648f4e753d63d3d786fab876f511d9d09da16480f691
  （download.kde.org 官方归档，顶层目录 kwallet-6.28.0/，strip_root）。
- conan create 与 conan-verify 全绿日志见 reports/。

### 对话 #1 [2026-09-20]

- 问题：本地 CI 模拟（W3）在此设备上无法运行——CI 脚本是 zsh 专用（glob 限定符 `(N)`），而 conan 进程域可达的唯一 zsh（pi-agent 自带）heredoc 临时文件硬编码 `/tmp/zsh`（无视 TMPDIR），且 `/tmp` 只读
- 操作：定位设备沙箱的 exec 域规则（/system/bin toybox 可 exec、新创建脚本不可），用 `$HOME/.zshenv` 设 `TMPPREFIX=$HOME/tmp/zsh` 注入（zsh 每次启动无条件 source），不改 CI 脚本
- 结果（✅）：setup.sh + build_and_test.sh 在本地全部通过，CI worker 行为不变

### 对话 #2 [2026-09-20]

- 问题：cmake 阶段 `cmake_symlink_library` Permission denied（E018），置空 VERSION 仍生成尾部点号产物 `libKF6Wallet.so.` 并再次触发 symlink
- 操作：补丁 0002 整行删除 VERSION/SOVERSION；configure() 注入 `-Wl,-soname`；package() 物化 soname 副本并签名
- 结果（✅）：libKF6Wallet.so + libKF6Wallet.so.6 双文件签名，DT_SONAME 保持上游

### 对话 #3 [2026-09-20]

- 问题：W3 JC 门禁报 Junk Files——首为 2 个残留未跟踪 SKILL_FEEDBACK 文件；后为全仓模式下他人包的已跟踪状态文件（cloog/kics）
- 操作：移出无关文件；将本包工作提交到分支使 junk_check 走 incremental（等价 CI prdiff）模式
- 结果（✅）：JC/KC/L0–L5 全部通过

### 对话 #4 [2026-09-24] 上游测试 3/3 真实执行（daemon 栈）

- 问题：审查 FAIL（rule4）：上游 3 个用例只执行了 2/3——`testWallet` 被
  DISPLAY 平台守卫 QSKIP，未做真实 DBus round-trip；rule1：PR 正文
  「上游测试用例通过率」字段缺失。
- 操作（配方升级为 daemon-enabled 测试范围）：
  1. 补丁 0001 重写：BUILD_KSECRETD=ON + BUILD_KWALLETD=ON（KF_DEP_VERSION
     放宽到 6.18.0，daemon-scope KF6 组件对齐 ohpcd 已发布的 6.18.0 代；
     test_package 的 kconfig 同步对齐到 6.18.0 修复版本冲突）；
  2. conanfile 新增运行时设施：dbus/1.14.10 自建会话总线（OHOS 禁文件域
     unix socket → loopback TCP + EXTERNAL/ANONYMOUS）、ksecretd 走上游
     `--pam-login` 无头解锁协议（pipe 喂 56B PBKDF2 哈希 + unix socket 环境
     通道，绕开 KPasswordDialog GUI）、pw_shim LD_PRELOAD、runtime-wrap
     symlink 农场、qca-ossl 插件自建（Botan 双加载统一路径）；
  3. **确定性 harness**（关键经验）：整段 daemon 生命周期写成自包含 python
     脚本由 conan build() 以独立进程运行——直接在 conan build() 内 spawn 时
     ksecretd 注册 bus name 会迟滞数分钟（conan 子进程环境干扰 PAM/DBus
     握手时序），独立进程则确定；warmup pass 先跑 kwallettest 写入阶段并
     等 ksecretd 自身 5s _syncTime 落盘，再对物化后的钱包状态（3 个 seed
     文件级快照，规避 OHOS rmtree 不可靠）做正式 run，最多 3 次 attempt。
- 结果（✅）：上游 kwallettest **Totals: 3 passed, 0 failed, 0 skipped**
  （816ms，attempt 1），`testWallet` 做了真实 DBus round-trip（DISPLAY=:99 +
  QT_QPA_PLATFORM=offscreen，offscreen 插件不触 X11）；W3 本地 CI
  setup.sh + build_and_test.sh 全绿（L0/L1/L4/L5 pass，L2 skip 非阻塞：
  daemon 二进制无 --version 入口）。
- 上游 6.28 自身 race（文档化于配方 docstring）：ksecretd 仅在启动时物化
  fdo collections，kwalletd6 连接时快照 collection 列表；空状态启动会让
  上游自身的 close 后查找丢 folder（无本地补丁可复现）——warmup seeding
  即为对冲此上游行为。

## R-3（2026-09-25）：MR !11365 检视整改 —— 全量普查 + rule12 + rule6/7

- 检视判 FAIL 的四条：rule4（上游实测 N > 声明 N，少报）、rule6（最新提交晚于
  最新 AI 检视）、rule7（最新提交晚于最新 CI 结论）、rule12（鸿蒙特有测试仅纯
  断言，缺完整端到端消费者用例）。
- 整改（配方升级为全量普查执行）：
  1. **全量普查**：build/bin 实测清点 13 个测试二进制；11 个真实执行
     （standalone：blowfishtest/backendtest/testbf/testsha；daemon 栈：
     kwallettest/async/sync/path/both/many/cbc/fdo_secrets_test），kwalletwizardtest
     排除（交互式 GUI，理由文档化），kwallet-example-asynchronous 为示例非测试。
  2. **判定分型**：Qt Totals（blowfishtest）、legacy 退出码+无 Error（testbf/
     testsha）、smoke exit 0（backendtest，上游无断言恒 exit 0，如实留档）。
  3. **ENV-BLOCKED 机制**：kwalletpath 上游硬编码 /tmp/test.kwl，本机 /tmp 对
     所有进程域 EROFS（touch 实测）；测试仍执行，结果如实上报（BIN-RESULT
     kwalletpath ENV-BLOCKED + reason），不修改上游测试源码、不计入通过。
  4. **库遮蔽发现（新知识）**：glib 包自带精简版 libintl.so.8 缺
     libintl_bind_textdomain_codeset，在 LD_LIBRARY_PATH 中遮蔽 gettext 完整版
     导致 libKF6I18n.so 加载失败（Error relocating）；修复 = gettext 包 lib
     目录置于 LD_LIBRARY_PATH 最前。另：conan self.run() 会套 conanbuild env
     脚本覆盖 LD_LIBRARY_PATH，standalone 测试改用 subprocess 直跑。
- 终态结果：22/23 Qt 测试函数 passed（fdo_secrets_test 16/0、kwallettest 3/0、
  async/sync/both/many 各 3/0、cbc 4/0、blowfish 3/0；kwalletpath ENV-BLOCKED），
  legacy 3/3，`KWALLETTEST-PASS`，test_package 1/1，conan create exit 0。
- rule12：PR 正文将 daemon-stack 生命周期 harness（真实 D-Bus 会话总线 +
  ksecretd --pam-login 解锁 + kwalletd6，open→写→读→close 完整生命周期）明确
  为鸿蒙特有完整消费者用例（非纯断言）。
- rule6/7：本次提交后执行鸿蒙 PC 本机完整 CI（CI_RUN.md 流程），通过后再触发
  AI 检视与 CI 复核。
---

**编译结束**: 2026-09-20 09:49
**最终状态**: published
