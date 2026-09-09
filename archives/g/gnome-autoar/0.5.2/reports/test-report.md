# gnome-autoar 0.5.2 验证报告

## 本地

- `conan create` r16：RC 0。
- 主包和消费者安装 ELF：AArch64，RUNPATH `$ORIGIN/../lib`，无 Conan cache RUNPATH。

## 目标 W3

- 设备：`10.62.150.125:8022`；事务：`w3-r001`；`launch_count=1`。
- 上游：`test-extract-unit` 22/22，TAP `1..22`，2 个有明确 crypto backend 原因的 SKIP，无失败。
- 消费者：10/10 断言，输出 `gnome-autoar 0.5.2 consumer test: OK`。
- release/postrelease：PASS，任务远端根和任务进程均清零。

权威结果：`F:\HarmonyPC\gnome-autoar-0.5.2-adapt-20260906\w3-r001\w3-r001-result.json`，SHA-256 `f52f1b7d46b5f0bb0aea75d7d701e880ac62467b390b1905f56d08efb174916a`。
