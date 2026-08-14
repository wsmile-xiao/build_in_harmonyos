# E321 — Linux A/B 启动槽/GPT 管理工具在 OpenHarmony 上的平台接口边界与无损消费者测试

## 错误特征（symptom）

适配 qbootctl 类 A/B 启动槽管理 CLI 时，在非 root、无真实 A/B 设备的
OpenHarmony PC 环境（CI / test_package / 赛事真机）下：

```
This program must be run as root!
No slots found, is this an A/B device?
Failed to open bootdev dir (No such file or directory)
Unable to open '/dev/bsg/ufs-bsg0'
```

- 编译本身通常通过（OHOS sysroot 已提供 `linux/bsg.h`、`scsi/scsi_bsg_ufs.h`）；
- 但运行期任何命令都被 root 检查或设备路径拦截，无法验证 CLI 纯逻辑；
- 上游无自动化测试（无 tests/、无 meson test()、无 CI 脚本）。

## 触发条件

- 构建系统: meson（qbootctl）；其他 GPT/UFS 工具类似
- 阶段: runtime / testing / installation
- 上游: linux-msm/qbootctl 0.2.2（纯 C，15 个文件，无测试）

## 根因分析

生产 backend 与真实设备访问强耦合、且无注入点：

1. `qbootctl.c` 在 `main()` 入口 `geteuid() != 0` 即拒绝运行；
2. `bootctrl_impl.c` 硬编码 `/dev/disk/by-partlabel`、`/proc/cmdline`；
3. `ufs-bsg.c` 硬编码 `/dev/bsg/ufs-bsg0` 并做 SG_IO ioctl；
4. `gpt-utils.c` 对真实块设备做 lseek64/read/write/BLKSSZGET。

因此无设备环境下既无法测试只读查询（-c/-a/-b/-n/-x），也无法测试参数解析。

## 解决方案（rec_approach: injectable-backend-env-gate）

最小补丁（archives/q/qbootctl/0.2.2/patches/0001-meson.build.patch + 0002-qbootctl.c.patch）：

1. **编译期宏隔离**：mock backend 整体包入 `#ifdef QBOOTCTL_TESTING`，仅 meson
   独立测试目标 `qbootctl-test`（`-DQBOOTCTL_TESTING`）编译；生产目标 `qbootctl`
   不定义宏，不含任何 mock 代码、无运行时开关（无 getenv）；
2. **生产语义与上游一致**：生产 main() 保持上游原样——`geteuid() != 0` 最先检查，
   `-h`/`--help` 非 root 同样被拒（exit 1）；
3. **测试专用构建**：`QBOOTCTL_TESTING` 下 `impl = &mock_bootctl`（编译期绑定，
   无环境变量开关），跳过 root 检查；mock 状态跨进程镜像到当前目录普通文件
   `.qbootctl-mock.state`（仅测试构建），test_package 用临时目录运行。

### 最终包内容（qbootctl-test 不进 bin/）

- `bin/qbootctl`（生产，真实 backend，无 mock 代码、无运行时开关）+
  `licenses/LICENSE`；
- `test/qbootctl-test`（QBOOTCTL_TESTING 宏测试专用构建）仅作为包内测试辅助
  产物提供给 test_package，不进入 bin/、不暴露于 `cpp_info.bindirs`（仓库规则
  未明确允许测试专用二进制进入正式 bin/，故移出；Conan 2 中 test_package 无法
  访问被测包源码，无法在 test_package 内重新构建，必须以包内测试目录形式提供）。

### 修复前后命令与退出码

| 命令 | 修复前（生产无 mock 能力） | 修复后 |
|------|--------|--------|
| `qbootctl -h`（非 root） | "must be run as root!" exit 1 | 同左（生产语义不变） |
| `qbootctl-test -c` | 无测试专用构建，无法测试 | `Current slot: _a` exit 0 |
| `qbootctl-test -a` | 同上 | `Active slot: _a` exit 0 |
| `qbootctl-test -b a` | 同上 | `SLOT _a: is marked bootable` exit 0 |
| `qbootctl-test -n a` | 同上 | `SLOT _a: is marked successful` exit 0 |
| `qbootctl-test -x` | 同上 | `_a` exit 0 |
| `qbootctl-test`（dump） | 同上 | 槽位信息 exit 0 |
| `qbootctl-test -s b` | 同上 | 内存写状态转换 exit 0；随后 `-a` 显示 `_b` |
| `qbootctl-test -n c` | 同上 | `Expected slot not 'c'` exit 1（非法槽位拒绝） |
| `QBOOTCTL_BACKEND=mock qbootctl -c` | 生产忽略该环境变量 exit 1 | 同左（无运行时开关） |

### 禁止做法

- ❌ 执行 `qbootctl -s/-m/-u/-i`（真实槽位切换/GPT 写入/UFS BSG，即使 mock 也禁止等价调用）；
- ❌ sudo/root 运行 qbootctl 测试；
- ❌ 测试 backend 触碰 /dev、/sys、/proc、真实块设备、loop/mount/losetup。

## 测试覆盖与未覆盖边界

- **使用 mock（测试专用构建 qbootctl-test）**：-h/--help、-c/-a/-b/-n/-x、无参数
  dump、非法槽位拒绝（-n c）、写状态转换（-s→-a、-u→-b、-m→-n）、临时目录隔离
  （仅 .qbootctl-mock.state 出现且为 6 整数、无设备路径）、许可证安装；
- **生产二进制验证**：strings 无 QBOOTCTL_BACKEND/mock 符号、非 root 全拒绝、
  忽略 QBOOTCTL_BACKEND 环境变量；
- **未在真机执行**（安全边界禁止，无真实硬件操作）：真实槽位切换、GPT 头/属性写入、
  UFS boot LUN 切换、真实 /dev/disk/by-partlabel 枚举、真实 /proc/cmdline 解析。

## 查重差异（与已有 E-entry）

- knowledge 全库 grep：`qbootctl|bootctrl|A/B slot|boot slot|bsg.h|by-partlabel|
  GPT partition|gpt-utils|ufs-bsg` 均无命中；321 条 E-entry 无覆盖；
- E051（setreuid SIGSYS）、E171（euidaccess）、E220（权限/工具链运行期探测）、
  E244（mock 错误契约）仅部分相关，均未覆盖「硬件依赖 CLI 的平台接口边界 +
  可注入 backend 无损测试」这一组合主题。

## 复用范围

可供其他 GPT/A-B/UFS 工具（abootimg、gpt-fdisk、ufs-tools、bootctrl HAL 消费者）
复用：编译期宏隔离的独立测试目标模式、生产无运行时开关保证、mock 查询/写状态
转换测试范式、非法参数拒绝测试、临时目录隔离校验、test_package MANIFEST 统计口径。

## 验证

```bash
python3 test_package/test_qbootctl.py <qbootctl-bin> <qbootctl-test-bin> <pkg-dir>
# RESULT: passed=30 failed=0 total=30 (exit 0)；1 case + 30 assertions
```

## 关联条目

- 相关: E051, E171, E220, E244
- 原则: P004, P014, P016
