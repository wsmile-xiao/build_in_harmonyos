# EXCLUDED-TESTS.md — kworkflow 0.10 未运行上游测试的逐条排除理由

排除判定基于两类证据：
(1) 设备 toybox 0.8.12 / git 2.45.2 探针（2026-09-23 实测，探针命令与输出随条目记录）；
(2) 上游源码/测试文本检索（tag 0.10，commit 2d8a04bb）。

## A. 整个测试层级

### tests/integration/**（config/device/kw_version/self_update + podman 环境）
- 排除理由：上游集成套件的容器环境由 tests/integration/podman/ 提供，需要 podman 拉起容器并在容器内跑 kw；OHOS 设备无 podman（探针 `command -v podman` 无输出），无替代容器运行时。

## B. 单测文件（tests/unit）

### fish_completion_test.sh
- 排除理由：需要 fish shell 解释 src/kw.fish（文件内直接调用 fish 执行补全断言，且无 `command -v` 守卫，缺 fish 时硬失败）；OHOS 设备无 fish（探针 `command -v fish` 无输出）。

### bash_autocomplete_test.sh
- 排除理由：测试体使用 `sort --dictionary-order`（toybox sort 探针：`Unknown option 'dictionary-order'`），且该选项出现在测试文件自身而非源码，无法通过源码补丁修复；同文件虽有 `command -v bash || exit 0` 守卫（本环境 bash 存在，守卫不生效），跑起来必失败。

### lib/signal_manager_test.sh
- 排除理由：test_default_handler 依赖 `sleep infinity`（toybox sleep 探针：`sleep: syntax error: Invalid argument 'infinity'`，toybox 仅接受数值时长）；信号断言因此必失败。

### lib/web_test.sh
- 排除理由：oneTimeSetUp 使用 `cp --recursive`（toybox cp 探针：`Unknown option 'recursive'`），setUp 阶段即失败；curl 相关路径虽有 TEST_MODE mock，但不解决 setup 失败。

### lib/dialog_ui_test.sh、lib/lore_test.sh
- 排除理由：kw 的 dialog UI 子系统调用 dialog TUI 二进制（dialog_ui_test.sh 内 52 处 dialog 引用；lore_test.sh 4 处）；OHOS 设备无 dialog（探针 `command -v dialog` 无输出）。

### lib/kw_db_test.sh、pomodoro_test.sh、report_test.sh、debug_test.sh
- 排除理由：kw 的本地数据库子系统依赖 sqlite3 CLI（kw_db_test.sh 41 处、pomodoro_test.sh 15 处、report_test.sh 3 处 sqlite3 调用；debug_test.sh 走 sqlite 记录路径）；OHOS 设备无 sqlite3（探针 `command -v sqlite3` 无输出）。

### lib/kwlib_test.sh
- 排除理由：覆盖 kwlib 全量函数，其中引用 git（31 处）/make（5 处）/tar/sqlite3，并有依赖 GNU date 字符串解析的路径（同 lib/kw_time_and_date_test.sh 条目）；非"纯脚本自足"用例集，排除后由其它精确覆盖的用例（kw_test、kw_env、kw_remote 等）承担 kwlib 间接验证。

### lib/kw_time_and_date_test.sh
- 排除理由：test_get_today_info / test_get_week_beginning_day / test_get_days_of_week / test_date_to_format / test_days_in_the_month 走 GNU date 字符串解析与日期算术（src/lib/kw_time_and_date.sh:91,125 `date --date="X - N day"`）；toybox date 探针：`date -d '2026/01/01'` → `bad date`、`date -d '2026/01/01 - 3 day'` → `bad date`（仅 `-d @epoch` 可用）。GNU date 日期算术在 OHOS 无等价物，不能靠长选项改写修复，属已知平台功能限制。

### lib/statistics_test.sh
- 排除理由：test_week_statistics / test_month_statistics 经 src/lib/statistics.sh:189 `date --date="${first} +${i} day"` 做 GNU date 日历算术，同上 toybox 必失败；test_day_statistics 等纯数据处理用例虽可运行，但文件级任一断言失败即整文件 FAIL，故整文件排除并在 README/manifest 记录"周/月统计在 OHOS 受限"。

### lib/remote_test.sh、kw_ssh_test.sh、deploy_test.sh、kernel_config_manager_test.sh、drm_plugin_test.sh
- 排除理由：模拟/依赖远端部署链路，需要 ssh/scp（remote_test.sh 25 处、kw_ssh_test.sh 25 处 ssh）、sudo（deploy_test.sh 40 处、drm_plugin_test.sh 31 处）、rsync（deploy_test.sh 18 处 rsync 同步模块到远端）；OHOS 设备无 sudo/rsync（探针 `command -v sudo`、`command -v rsync` 均无输出），且这些用例面向 x86 远端内核部署语义，非纯本机自足用例。

### build_test.sh
- 排除理由：以真实 make/NPROC 驱动内核构建流程断言（70 处 make 引用、`command -v nproc` 探测）；OHOS 设备无 make 工具链（探针 `command -v make` 无输出），无法构成有效构建环境。

### codestyle_test.sh
- 排除理由：调用 perl 跑内核 checkpatch.pl（2 处 perl 引用）；OHOS 设备无 perl（探针 `command -v perl` 无输出）。

### maintainers_test.sh
- 排除理由：oneTimeSetUp 将 samples/external/get_maintainer.pl 复制进假内核树供运行期调用（perl 解释器执行）；且 tearDown 使用 `rm --recursive --force`（toybox rm 探针：`Unknown option 'recursive'`，测试文件自身无法补丁）；双重环境缺失。

### send_patch_test.sh
- 排除理由：send-patch 链路依赖 `git send-email`（perl 实现，46 处 git 用例围绕 format-patch/send-email 断言）；OHOS 的 git 2.45.2 无 send-email 组件（perl 缺失），探针 `git send-email --help` 报 `fatal: no man viewer...` 之外的组件缺失路径。

### vm_test.sh
- 排除理由：QEMU/virsh 虚拟机管理路径需要 sudo 提权（2 处 sudo）与 vm 基础设施；OHOS 设备无 sudo/virsh。

### device_test.sh
- 排除理由：device_info 子系统按桌面发行版约定读取设备信息（含 fish 相关模板与桌面环境路径，测试内 2 处 fish 引用）；OHOS 无对应桌面设备信息栈。

### tracing/tracing_test.sh、ui/patch_hub/**
- tracing/tracing_test.sh（存在，归入 tracing/** 排除范围）——未运行：①setUp 体使用 `cp --recursive`（toybox cp 探针：`Unknown option 'recursive'`）；②其 include 的 `./tracing/tracing.sh` 位于仓库根 tracing/（由 setup.sh --enable-tracing 流程维护），本测试运行布局未纳入该目录；③所需 tests/unit/samples/tracing 未纳入 vendored 子集。
- ui/patch_hub/**（latest_patchsets_from_mailing_list / lore_mailing_lists / patch_hub_core / patchset_details_and_actions / search_string_in_lore / settings 共 6 项）：patch-hub 为独立 Rust/Lua 二进制（setup.sh 从 GitHub release 下载 x86_64 构建），OHOS aarch64 无该制品且本配方不打包 patch-hub。

## C. 已尝试的替代方案记录

- shunit2 缺失：已 vendor v2.1.8（https://github.com/kward/shunit2，tarball sha256 b2fed28ba7282e4878640395284e43f08a029a6c27632df73267c8043c71b60c）到 tests/shunit2/shunit2，命中上游 invoke_shunit 的 vendor 查找分支。
- TMPDIR：设备 /tmp 为只读 tmpfs（探针 mkdir /tmp/fp1 → `Read-only file system`），runner 将 TMPDIR 指到可写临时目录，shunit2 与各测试的临时目录均落在可写路径。
- mktemp 权限怪癖（知识：bash/5.3 构建期 drwx--S---）：运行期探针 mktemp -d 建出的目录属主可写（touch 成功）；test_package 以 `kw env --create/--use`（mktemp -d + mv + ln -sf）与 create_shared_memory_dir 两条真实路径再探，未复现构建期怪癖。
- `kw --help` 依赖 man page（上游 help 流程走 kworkflow_man）；man 需 sphinx 构建、本配方未打包，OHOS 上 `kw --help` 输出 "Couldn't find the man page for kw!" 属预期行为，usage 帮助走 `kw -h`（不受影响）。

## D. vendored 测试的机械调整（非语义改动，逐条登记）

与源码补丁同类的 GNU 长选项问题出现在两个上游测试文件自身的 setup/统计代码中
（toybox 不支持，且修的是测试文件而非源码，故单独登记）：

1. tests/unit/kw_remote_test.sh 第 798 行：`ln --symbolic ...` → `ln -sf ...`
   （toybox ln 探针：`Unknown option 'symbolic'`；不改则符号链接建不出来，被测的
   "remote 配置符号链接保持"特性无法验证——该特性对 kw env 联动有真实价值）。
2. tests/unit/explore_test.sh：`wc --lines` → `wc -l` 共 4 处
   （toybox wc 探针：`Unknown option 'lines'`；不改则全部计数断言拿到空串必失败）。
3. tests/unit/explore_test.sh 第 141/145 行：TEST_MODE 期望命令串中的
   `grep --color --line-number --recursive ... --context N` 更新为源码补丁后的
   OHOS 可移植形态 `grep --color -n -r ... -C N`（断言的是"命令构造"这一被测行为，
   期望值须与补丁后源码一致）。
4. tests/unit/lib_tests/kwio_test.sh：`wait "$!"` → `wait` 共 10 处。上游注释明确
   要求 alert_completion 的后台命令须等待结束再断言，但 `wait "$!"` 只等最后一个
   后台任务，`--alert=vs`（两个后台 touch）在 OHOS 慢存储下存在真实竞态
   （ci06 实测 "Alert's vs option didn't work."，脱离 CI 单跑即稳定通过）；
   `wait`（等待全部后台子进程）才是与测试意图一致的确定性写法。

5. tests/unit/samples/first_set_of_bytes_from_disk/{grub2_x86,rpi4,syslinux_x86}
   （3 个 32KB 磁盘首扇区二进制样本）：存储形态适配（非 GNU 长选项类调整）——
   改为单行 base64 文本存储 tests/unit/samples/first_set_of_bytes_from_disk_b64/*.b64，
   由 kw_test_runner.sh（OHOS 自研 runner）在运行上游测试前物化还原
   （逐文件 `tr -d '\n' | base64 -d`；解码数≠3 或任一解码失败即整体 FAIL）。
   原因：GitCode PR .diff 导出对二进制文件只写 "Binary files ... differ"、
   不带 GIT binary patch 数据段，buildbot 的 git apply/--3way 报
   "missing binary patch data" 无法应用（MR PR-check checkout-pr 失败根因）。
   断言语义：解码产物与原 git blob 逐位一致（双端 sha256 核对：grub2_x86=
   ff6fb5e1b998185155471185a5793a411b56844e4355369f6b1e376d38fae858、
   rpi4=7d4d4754a745b9c56eaec59c49fdb4b2a6fc02d565ae95c75577447ed5eb12ca、
   syslinux_x86=9b474446469eea3dd279946254e0ce984449843cfd57b13ffe87045d5dfeb4bd；
   设备 toybox 解码管道实测产物 sha256 与原始 blob 一致）；还原文件名与上游一致。
   diff_test.sh 两个引用用例均不依赖字节内容——test_diff_folders 只断言
   目录存在与文件名集合（"Only in ${folder_1}: get_maintainer.pl"），
   test_diff_folders_invalid_path 仅把该目录用作存在路径（断言 rc=22），
   还原后断言行为不变。改动仅涉及样本文件存储形态与自研 runner；
   tests/ 下 vendored 上游文件仍逐字节不变（上述 1-4 项除外）。
其余 vendored 文件与上游 tag 0.10 一致（除上述机械调整外逐字节一致）。

## E. 全量对账补登记（Delivery 审计发现，2026-09-23）

对账基准：上游 tag 0.10（commit 2d8a04bb）tests/ 树 `find tests -name '*_test.sh'` 共 **62** 个
= vendored 运行 **11** + 本文件登记排除 **51**（原 35 项登记覆盖 35 个文件 + 本节补登记 16 个）。
补登记项均**未运行**；其中 5 项在临时重构环境做了单次试跑取证（结论如实标注，不编造结果），
1 项实测可运行，按任务要求单独标注、不混入排除项。

### E1. 候选可运行（单次试跑实测通过）但未纳入本轮回

### tests/unit/plugins/kw_mail/to_cc_cmd_test.sh
- 未纳入本轮回：试跑（包内 src/plugins/kw_mail/to_cc_cmd.sh + vendor 测试）1/1 断言通过，
  纯 bash 处理补件 to/cc 缓存列表，无平台阻塞。未纳入原因：首轮运行集按"纯脚本自足、
  零新增 vendored 依赖"圈定时未含 kw_mail 插件域；纳管属后续工程轮（需同步 FULL CI），
  本轮为登记轮不动运行集。

### E2. 未运行（试跑失败，失败面已取证）

### tests/unit/lib/kw_config_loader_test.sh（vendored 目录名 lib_tests）
- 未运行：单次试跑 8 例 6 断言失败。首例 parse_configuration 对存在样本
  （samples/kworkflow.config）返回 22，而同一调用隔离复现 rc=0——失败点位于测试内
  多配置文件/作用域联动流程，根因未定位；不虚报通过，也不臆断根因。

### tests/unit/init_test.sh
- 未运行：单次试跑 16 例 13 断言失败；`sed: Unknown option 'in-place'` 复现 19 次——
  src/init.sh（未在主补丁范围内）大量使用 GNU sed --in-place，toybox 拒绝导致
  arch/配置模板替换链路失效。可用与主补丁同类的 `sed -i` 改写修复，但属源码补丁
  扩容（工程语义变化，须 FULL CI 复验），本登记轮不动。

### tests/unit/config_test.sh
- 未运行：单次试跑 13 例 5 断言失败。取证：测试体自身 `sed --in-place` ×8、
  `ln --symbolic` ×1 被 toybox 拒绝（`Unknown option` 探针复现），另依赖未纳入
  vendored 子集的 samples/kworkflow_x86.config 等样本（`cp: bad ...` 复现）。

### tests/unit/backup_test.sh
- 未运行：补齐 samples/configs、samples/pomodoro_data 后单次试跑 9 例 17 断言仍失败——
  样本 configs/metadata 结构与断言期望不符（`cp: bad .../configs/metadata/config-test`）、
  备份/恢复比对链路行为偏离；且 kw 备份恢复涉及 kw.db（sqlite3），设备本就无 sqlite3。

### E3. 未运行（环境缺失，未试跑）

### tests/unit/scripts/profiler_test.sh
- 未运行：其 include 的 `./scripts/profiler.sh` 位于仓库根 scripts/ 目录
  （test_package 重构布局按已运行测试依赖圈定，未含上游 scripts/），
  且所需 samples/scripts/profiler 样本未纳入 vendored 子集。

### tests/unit/plugins/kernel_install/（10 项：arch / bootloader_utils / debian / fedora /
### grub / install / rpi / systemd_boot / uninstall / utils）
- 未运行：kernel_install 插件面向目标发行版（Debian/Fedora/RPi 等）的内核安装流程，
  测试体依赖 sudo（如 debian/utils/install 三文件即 15 处 sudo）、mount、grub-mkconfig
  等需要 root 的系统操作；OHOS 设备无 sudo（探针证实），且模拟的是 x86 发行版部署语义。
