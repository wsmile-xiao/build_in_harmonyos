# qbootctl

[qbootctl](https://github.com/linux-msm/qbootctl) 是 Qualcomm A/B 启动槽管理命令行工具（bootctrl HAL 的 Linux 移植），纯 C 实现，Meson 构建。

## 功能

- 查询当前/活跃启动槽（`-c`/`-a`）
- 查询槽位是否可启动/成功（`-b`/`-n`）
- 查询槽位后缀（`-x`）
- 切换活跃槽（`-s`）、标记启动成功（`-m`）、标记不可启动（`-u`）——**需要 root 与真实 A/B 设备**

## 平台接口边界（OpenHarmony 适配要点）

qbootctl 运行期依赖以下 Linux 平台接口，鸿蒙 PC 均已由 OHOS SDK sysroot 提供：

| 接口 | 用途 | OHOS 可用性 |
|------|------|-------------|
| `linux/bsg.h` + `scsi/scsi_bsg_ufs.h` | UFS BSG ioctl（`SG_IO`） | ✅ sysroot 提供 |
| `/dev/disk/by-partlabel` | 定位 GPT 分区 | 运行时设备相关 |
| `/proc/cmdline` | 读取 `slot_suffix` 当前槽 | ✅ |
| GPT 读写（`lseek64`/`BLKSSZGET`） | 读写 GPT 头与分区属性 | 运行时设备相关 |
| `geteuid()` | root 检查 | ✅ |

## 无损测试方案

上游无自动化测试；真实槽位操作（`-s/-m/-u/-i`）被赛事安全边界禁止。本归档通过补丁
`patches/0001-meson.build.patch` + `patches/0002-qbootctl.c.patch` 提供：

- 测试专用构建 `qbootctl-test`（`QBOOTCTL_TESTING` 编译宏）：mock backend 整体包入
  `#ifdef QBOOTCTL_TESTING`，仅独立测试目标编译，使用**纯内存 backend**（不访问任何
  设备），可安全测试查询（`-c/-a/-b/-n/-x`、dump）、写状态转换、参数解析、非法槽位拒绝；
- **生产 `qbootctl` 不定义测试宏**：不含任何 mock 代码、无运行时开关（无 getenv），
  语义与上游完全一致（非 root 下 `-h/--help` 同样被拒）；
- `qbootctl-test` 作为包内测试辅助产物位于 `test/`，不进入 `bin/`、不暴露于
  `cpp_info.bindirs`，仅供 test_package 消费。

## 使用示例

```bash
qbootctl -h            # 生产二进制（非 root 被拒，与上游一致）
qbootctl -c            # 真实设备查询（需 root + A/B 设备）
# 测试专用构建（QBOOTCTL_TESTING 宏，纯内存 mock，无设备、无 root）：
qbootctl-test -c       # 查询当前槽（_a）
qbootctl-test -s b     # 内存写状态转换
qbootctl-test -n c     # 非法槽位拒绝（exit 1）
```

## 参考

- [上游仓库](https://github.com/linux-msm/qbootctl)
- [postmarketOS A/B Slots 说明](https://wiki.postmarketos.org/wiki/Android_AB_Slots)
