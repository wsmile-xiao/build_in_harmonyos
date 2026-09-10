# 测试报告 — cloud-utils-ec2metadata 0.34

## 验证摘要

| 项目 | 结果 |
|------|------|
| conan create（G2 干净构建 + test_package） | ✅ PASS |
| W3 本地 CI 模拟（L0/L1/L2/L4/L5） | ✅ PASS（1/1, 100%） |
| OHOS 专项测试（test_ohos_ec2metadata.py） | ✅ PASS（4 项断言） |
| SHA-256 校验（官方 tarball） | ✅ 0e2d6bb9c738d7016bb8af6780bef74dee263a02963e9c01a6b8331e7cafdf8d |

## OHOS 专项测试执行记录

```text
[help] rc=1            # 上游 usage() 设计行为（写 stderr、exit 1），断言输出文本
[instance-id] rc=0 → i-ohos-test-001
[ami-id] rc=0        → ami-ohos-0.34
[wmm-help] rc=0
OHOS TEST PASSED (rc=0)
```

测试内容：ec2metadata env-shebang 解析；本地 socketserver mock（代理 + IMDS）路由
IMDSv2 token PUT 与 meta-data GET 的完整功能路径；write-mime-multipart 冒烟。

## 上游测试双口径台账（R02 逐入口复核）

### 上游测试枚举（source_declared_total = 7）

test/ 下 7 个独立上游测试脚本（run-all 为运行器、tox 为静态检查，均非独立用例）：

| # | 脚本 | 独立用例 | 声明/注册项 -> 构建条件 -> 目标 -> 注册 -> 执行 |
|---|------|---------|------|
| 1 | test-growpart | ✅ | bash 脚本（无 CMake/Meson 注册，Makefile 无 test 目标）-> 需 root + sfdisk/mkfs.ext4/losetup -> 未实例化 |
| 2 | test-growpart-fsimage | ✅ | 同上 -> 需 sfdisk -> 未实例化 |
| 3 | test-growpart-fsimage-middle | ✅ | 同上 -> 需 sfdisk/sgdisk -> 未实例化 |
| 4 | test-growpart-lvm | ✅ | 同上 -> 需 root + lvm2/sfdisk -> 未实例化（上游 CI 亦 SKIP） |
| 5 | test-growpart-overprovision | ✅ | 同上 -> 需 sfdisk -> 未实例化 |
| 6 | test-growpart-start-matches-size | ✅ | 同上 -> 需 sfdisk/sgdisk -> 未实例化 |
| 7 | test-mic | ✅ | 同上 -> 需 root + sfdisk/mkfs.ext4/mount-image-callback -> 未实例化 |

### 逐入口最小纳入/运行尝试（R02，实际命令与首错）

TMPDIR/TMP/TEMP 均指向可写目录 `/storage/Users/currentUser/tmp/r02logs/upstream/`（/tmp 只读）；cwd 均为上游源码 test/ 目录；shebang `#!/bin/bash` 缺失用显式 `bash ./test/<t>` 执行：

| 脚本 | 实际命令 | cwd | 退出码 | 首条错误 | 绝对日志（SHA-256） |
|------|---------|-----|--------|---------|------|
| test-growpart | `bash ./test/test-growpart` | `<src>/test` | 1 | `sorry, must be root`（NEED_ROOT） | `/storage/Users/currentUser/tmp/r02logs/upstream/test-growpart.out` `c9b068fbc62d24185eb82c6922e293658debc9d2e7369ddacd0dca7d83bcff46` |
| test-growpart-fsimage | `bash ./test/test-growpart-fsimage` | `<src>/test` | 1 | `sfdisk: command not found` | `/storage/Users/currentUser/tmp/r02logs/upstream/test-growpart-fsimage.out` `b9894f7a3bf7fe46b3b312d4d6c91f6d789575d0faf1b71817bf9af1a33fa5e5` |
| test-growpart-fsimage-middle | `bash ./test/test-growpart-fsimage-middle` | `<src>/test` | 1 | `sfdisk: command not found` | `/storage/Users/currentUser/tmp/r02logs/upstream/test-growpart-fsimage-middle.out` `b6e6b27dc2ca35dda9fc1dba44b49dd406902c864a1c1be66e0601f1c7da4fad` |
| test-growpart-lvm | `bash ./test/test-growpart-lvm` | `<src>/test` | 1 | `sorry, must be root`（NEED_ROOT） | `/storage/Users/currentUser/tmp/r02logs/upstream/test-growpart-lvm.out` `c9b068fbc62d24185eb82c6922e293658debc9d2e7369ddacd0dca7d83bcff46` |
| test-growpart-overprovision | `bash ./test/test-growpart-overprovision` | `<src>/test` | 1 | `sfdisk: command not found` | `/storage/Users/currentUser/tmp/r02logs/upstream/test-growpart-overprovision.out` `292538e5bf41e19c597e5997205fc4c53d7694cb3af8714dbef0a82c70414bad` |
| test-growpart-start-matches-size | `bash ./test/test-growpart-start-matches-size` | `<src>/test` | 1 | `sfdisk: command not found` | `/storage/Users/currentUser/tmp/r02logs/upstream/test-growpart-start-matches-size.out` `c4671058b9fd3b494a236799ac898f367b27ce082d3953624e019c54e2a083a1` |
| test-mic | `bash ./test/test-mic` | `<src>/test` | 1 | `sorry, must be root`（NEED_ROOT） | `/storage/Users/currentUser/tmp/r02logs/upstream/test-mic.out` `c9b068fbc62d24185eb82c6922e293658debc9d2e7369ddacd0dca7d83bcff46` |
| run-all（运行器） | `bash test/run-all` | `<src>` | 0 | 3 SKIP(not root) + 4 因 /bin/bash 解释器缺失标 FAIL；`run-all.out` `fbfb62a6552a636bcd4cfc7ccb2e1d827c8464860221355e2a730d3125cdc331` | `/storage/Users/currentUser/tmp/r02logs/upstream/run-all.out` |

### 依赖/工具可用性复查（首次跳过时 2026-09-09 查询）

| 缺失项 | 归属包 | ohpcd registry 复查 | 结论 |
|--------|--------|--------------------|------|
| sfdisk | util-linux | `conan download "util-linux/*" -r=ohpcd` → Found 0 recipes | 未发布 |
| sgdisk/gdisk | gptfdisk | `conan download "gptfdisk/*"` → Found 0 recipes | 未发布 |
| mkfs.ext4 | e2fsprogs | Found 3 recipes（1.47.0/1.47.1/1.47.4，可下载 OHOS 二进制） | 已发布，但仅提供 mkfs.ext4，不覆盖 sfdisk/sgdisk 共性缺口 |
| lvm2/pvs/vgs | lvm2 | Found 0 recipes | 未发布 |
| qemu-utils | qemu | Found 0 recipes | 未发布 |
| busybox | busybox | Found 1 recipe（1.36.1） | 已发布；上游 busybox 模式仍需 GNU sfdisk/sgdisk 链接（CI 亦 SKIP growpart-lvm） |
| root 权限 | 环境 | `id -u`=20020101 非 root；`sudo -n true` rc=1 | 无特权环境 |

### 双口径统计

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 7 | test/ 下 7 个独立上游测试脚本 |
| configured_executable_total | 0 | 上游 7 脚本均为特权+分区工具的 bash 集成测试，无 CMake/Meson/ctest 注册项，当前 OHOS 配置未实例化任何一个 |
| executed_passed_total | 0 | 上游 7 脚本均未通过（全量分母口径） |
| failed_total | 0 | 无"配置实例化后运行失败"的用例 |
| uninstantiated_total | 7 | 3 个 NEED_ROOT（test-growpart/test-growpart-lvm/test-mic，上游 run-all 对非 root 亦 SKIP）+ 4 个缺 sfdisk/sgdisk（util-linux/gptfdisk 未发布），真实外部阻塞 |

- 上游全量通过率（executed_passed/source_declared）：**0/7 = 0.0%**（7 上游因特权+分区工具缺失不可实例化，如实计入分母不计通过）
- 当前配置可执行集合通过率：OHOS 专项测试 **1/1 = 100%**（test_ohos_ec2metadata.py，4 断言，独立于上游 7 脚本计数）
- 恢复条件：①提供 root/特权环境；②util-linux（sfdisk）与 gptfdisk（sgdisk）发布到 ohpcd 或本机安装系统分区工具并提权后，可实例化并运行全部 7 个上游脚本；依赖状态非一次性结论，最终回报前将再次复查 registry

## 门禁结论

- L0：pass（commands.json R38、settings 四项、源 URL 官方、无平台宏补丁注入）
- L1：pass（test_package 实质执行被测包：L1e 负向验证确认依赖真实）
- L2：pass（7 个 bin 工具 --help 冒烟通过）
- L4：pass（补丁纯净）
- L5：pass（bin/ 产物存在）

## 产物

- conan create 输出：`reports/conan-create.log`
- W3 输出：`reports/w3-local-ci.log`
- conan-verify 报告：`reports/conan-verify-report.md`
