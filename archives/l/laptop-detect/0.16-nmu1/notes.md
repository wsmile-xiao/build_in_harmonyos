# laptop-detect 0.16-nmu1 适配笔记

## 上游与产物

- 上游：Debian-native 包（gitlab.com/debiants/laptop-detect，Debian 维护者
  仓库即上游），发行版本 0.16+nmu1。changelog 明示：0.16+nmu1 为
  Reproducible Builds 团队 NMU，"No source change upload to rebuild on
  buildd"——内容与 0.16 完全一致。sha256 db6f7bca... 与 .dsc PGP 记录核对
  一致（.dsc sha256 同值实测）。
- 内容：单个 POSIX sh 脚本（laptop-detect.in，构建时 sed 替换 @VERSION@
  生成）+ 手册页 laptop-detect.1 + README + debian/ 目录，共 10 文件
  （tar.xz 仅 6.1KB）。arch=all，无编译。
- 用途：系统底盘类型检测器——判定"当前是否运行在笔记本（或同类便携
  设备）上"，供安装器等调用。exit 0=笔记本、1=非笔记本、2=选项类
  （-h/-V/-D/未知选项）。
- 许可证：BSD-3-Clause（全文在 debian/copyright；上游无独立 LICENSE
  文件，配方把 copyright 原样分发到 licenses/）。
- Debian 安装布局：usr/bin/laptop-detect + usr/share/man/man1/
  laptop-detect.1。Recommends: dmidecode（可选探测通道）。

## 探测链矩阵（脚本内置逻辑，上游原样）

1. /proc/pmu 存在 → Mac 路径（grep Battery 计数）
2. dmidecode 可用且 /dev/mem 可读 → chassis-type 字符串匹配
   Notebook/Portable/Laptop/Hand Held
3. /sys/devices/virtual/dmi/id/chassis_type ∈ {8,9,10,11}（便携/笔记本/
   记事本/手持）
4. /sys/class/power_supply/*/type 含 Battery 且 scope 不含 Device
   （非 Device 电池 = 笔记本电池）
5. /proc/acpi/battery 下存在目录（旧接口）
6. /proc/apm 第 6 字段 ≠ 0xff/0x80
7. 全部未命中 → exit 1

各通道均为"探测失败即静默跳过"的降级结构（`|| true`/`2>/dev/null` 守卫），
无硬依赖。

## OHOS 适配

- **纯 POSIX sh，一行补丁**。配方（abcde 先例范式）：build() 复刻
  Debian 的 sed 替换（@VERSION@ → conan 版本，锚点计数防漂移），
  package() 装 bin/laptop-detect（755）+ man1 + README +
  licenses/copyright。
- **补丁 0001（portability）**：power_supply 遍历的 ls 补 2>/dev/null
  守卫。OHOS 上 `/sys/class/power_supply` **目录存在但 EACCES 不可读**
  （真机实测 cat/ls 均 Permission denied），无守卫的 ls 向 stderr 泄漏
  错误且循环静默迭代空集；脚本其余探测均带守卫，本行属上游遗漏。
  GNU/Linux 下该目录要么缺失要么可读，补丁零行为差异。
- **版本口径**：平台任务卡 0.16-nmu1 vs Debian 0.16+nmu1（+/- 归一化）；
  conan 版本取 0.16-nmu1，包内脚本 `-V` 输出同串（版本串为信息性）。
- **调用约定**：OHOS HMDFS 禁直接 exec shebang 脚本（E046/E087，
  ncurses/freetype 同宗）→ 消费者统一 `sh laptop-detect` 调用；探针
  全部经 `sh` 执行——这正是消费者真实用法。
- **探测链在 OHOS 的预期形态**（真机实证见下）：dmidecode/modprobe 不可
  用（缺失即跳过）；/proc acpi/apm/pmu 传统节点缺失或不可读；判定实际
  依赖 sysfs（dmi chassis_type / power_supply）的暴露情况。
- 无编译、无链接、无软链；package_type=application。settings 声明完整
  四项（os/compiler/build_type/arch）：纯脚本包不消费编译设置，但 CI 的
  L0p 门禁要求 OHOS profile 四项齐全，缺 compiler/build_type 直接判
  失败；四项只进 package_id，build() 不读。
- R38 工具声明：`archives/l/laptop-detect/commands.json`（type=tool，
  versions 含 0.16-nmu1，binary=false——脚本工具经 `sh` 调用，非 ELF）。

## 上游测试口径（R51 三步法）

- **清点**：发行归档全树 0 个测试文件（无 tests/、无 autopkgtest、无
  *.t，10 文件逐一清点）。上游为 Debian-native 包，无独立测试套件。
- **等价覆盖**：消费者探针 25 断言——选项语义（exit 2 族：-V/-h/未知
  选项各自退出码+输出）、判定语义（exit ∈ {0,1}；静默是设计语义
  PRINTIT=/bin/true，诊断仅在 -v 时输出且与退出码一致）、调试模式
  （-D exit 0 + xtrace）、安装布局（bin/man/README/license 全文）、
  确定性（两次运行同退出码）。
- **实跑**：Windows Git Bash 本地 + HarmonyOS PC 真机 conan create
  消费者测试（见"真机验证记录"）。

## 真机验证记录（2026-09-26）

### 设备暴露矩阵实测（探测链逐节点）

| 探测节点 | OHOS 真机 | 脚本行为 |
|---|---|---|
| /proc/pmu | 缺失 | test -d 跳过 |
| dmidecode | 不可用（command -v 失败） | 跳过 |
| /sys/devices/virtual/dmi/id/chassis_type | **整个 dmi/id 目录缺失** | 跳过 |
| /sys/class/power_supply | **存在但 EACCES**（cat/ls 均 Permission denied） | ls 泄漏 stderr（→ 补丁 0001） |
| /proc/acpi/battery | 缺失 | 跳过 |
| /proc/apm | 缺失 | 跳过 |
| 最终判定 | rc=1（非笔记本，无电池线索） | 与设备形态一致 |

### 首轮（补丁前）

- conan create 成功（源下载 deb.debian.org 直连成功，conan 自带 CA 生效），
  探针 **24/25**：唯一失败 "plain run silent by design"——
  `ls: /sys/class/power_supply: Permission denied` 泄漏到 stderr
  （该 ls 是脚本中唯一无 2>/dev/null 守卫的探测行；GNU/Linux 上目录
  缺失或可读故不触发，OHOS"存在但不可读"首次暴露此上游遗漏）。

### 二轮（补丁后）

- conan create 成功（0001 补丁自动应用），探针 **25/25** 全绿——"plain run
  silent by design" 通过：stderr 干净、无 Permission denied 泄漏。
- conan-verify 八门禁 **Verdict PASS**（G0-G4 + L2/L4/L5，2026-09-26T19:57Z，
  详见 reports/conan-verify-report.md），R46 result.json 已上报（draft:false），
  可标记 status: published。
- 判定语义与首轮一致：rc=1（无电池线索，与设备形态一致），确定性断言通过。

### 三轮（L0 门禁修复后重跑，2026-09-26T21:07Z）

- CI 首轮（MR #12973，SHA 8cf295c926）在 L0 挂两道门禁：L0k（缺软件级
  commands.json，R38）+ L0p（settings 只有 os/arch，OHOS profile 要求四项）。
  修复：新增 `archives/l/laptop-detect/commands.json`（type=tool，
  binary=false）；conanfile settings 补齐 compiler/build_type。
- 修复后真机重跑 `python3 scripts/ohc-run.py conan-verify laptop-detect
  0.16-nmu1` → **Verdict PASS**（G0-G4 + L2/L4/L5，2026-09-26T21:07Z），
  结论行 `可标记 status: published`；conan create 消费者探针 **25/25**
  （`laptop-detect probe: 25 passed, 0 failed (rc1=1)`，rc=1 与设备形态一致）。
  settings 变更只影响 package_id（真机日志可见 compiler=clang/cppstd=17
  进入 package id），产物内容与二轮一致。

## 参考

- 上游项目: https://gitlab.com/debiants/laptop-detect
- Debian 源码包: https://packages.debian.org/source/sid/laptop-detect
- 发行归档: https://deb.debian.org/debian/pool/main/l/laptop-detect/
