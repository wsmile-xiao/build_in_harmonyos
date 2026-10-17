# E429 草稿 — HarmonyOS PC: /proc/diskstats 仅 root 可读，监控工具需代码级优雅降级

## 可复现症状与稳定错误签名

- `Can't open /proc/diskstats: Permission denied`（topline 启动即 die）
- 稳定签名：`fopen("/proc/diskstats")` 返回 EACCES；普通用户 shell 直读同报错。

## 根因与最小复现

- HarmonyOS PC 虚拟化环境将磁盘统计以 `/proc/diskstats → /sys/block/diskstats`
  符号链接暴露，目标仅 root 可读；`/proc/stat`、`/proc/meminfo` 普通用户可读。
- 最小复现：`head -c 100 /proc/diskstats` → Permission denied；
  `head -c 60 /proc/stat` → 正常输出。
- 触发实例：topline 0.6 消费者测试（conan create G2，2026-09-19，HarmonyOS PC 真机）。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 直接 fopen（上游原逻辑） | EACCES → die() → 工具无法启动 |
| 知识库 E031 的 sudo-run | CI/conan 包环境无 sudo，不可用 |
| 代码级优雅降级（采纳） | fopen 失败即 stderr 告警 + 短路磁盘采样；CPU 维度正常输出，消费者测试 106 字节监控输出验证通过 |

## 最终方案、输入输出与真实验证

- 输入：`ds = fopen("/proc/diskstats", "re")` 失败（ds==NULL）。
- 处理：`init_disks()` 告警不退出；`do_disks()` 首行 `if (!ds) return;`。
- 输出：进程正常启动，监控输出仅含 CPU 统计（磁盘列省略），stderr 有明确降级提示。
- 真实验证：topline 0.6 消费者测试在真机通过（captured 106 bytes of monitor output），
  conan-verify G0-G4/L2/L4/L5 全绿（archives/t/topline/0.6/reports/conan-verify-report.md）。

## 适用范围、反例、解除条件与风险

- 适用：磁盘统计为辅助功能的监控工具（topline、htop、nmon、dstat 等）。
- 反例：磁盘统计为核心功能的工具（iostat 本体）不可降级了事，逐设备
  `/sys/block/<dev>/stat` 同样受限时按无法适配处理，不静默删功能。
- 解除条件：平台未来放开 /sys/block/diskstats 读权限后，降级路径自动失效
  （正常读取路径不受补丁影响）。
- 风险：降级后用户可能不知磁盘列缺失，必须 stderr 告警（补丁已带）。

## 知识库查重与新增价值

- grep index.tsv：命中 E031（htop，/proc 整体受限，方案 sudo-run）、E303
  （受限进程文件系统探测）；无 diskstats 专属条目。
- 新增价值：E031 的 sudo-run 在 CI/包环境不可用；本条给出 CI 可用的代码级降级
  方案 + 平台精确边界（/proc/stat 可读、仅 diskstats 受限），并给出核心功能不可
  降级的反例边界。
