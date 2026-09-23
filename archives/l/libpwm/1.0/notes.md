# libpwm 1.0-rc2 — HarmonyOS PC 适配说明

## 概况

libpwm 让用户态程序驱动 Linux PWM 设备：透明支持字符设备 ABI（/dev/pwmchipN）
与 sysfs ABI（/sys/class/pwm），提供打开芯片、取 PWM 线、round/get/set 波形的 API，
并附带 pwmset、pwmround、pwmtestperf 三个示例程序。

- 上游：https://git.kernel.org/pub/scm/linux/kernel/git/ukleinek/libpwm.git
- 构建：autotools，**tarball 自带 configure（autoconf 2.72）与 Makefile.in**
- 依赖：无（仅 libc）
- 许可证：LGPL-2.1-only

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 自带 configure | 直接 `./configure && make`，不需要 autoreconf/aclocal/automake（与 libirman 同型） |
| 2 | E011：configure 的 umask 077 | HMDFS 为 setgid 挂载，config.status 自建的 0700 临时目录不可用 → `build()` 就地把 `umask 077` 改为 `022`（icoutils/libirman 先例） |
| 3 | E007：config.guess | 显式 `--build/--host=aarch64-unknown-linux-ohos`，configure 不做猜测 |
| 4 | 无 PWM 设备 | 沙箱既无 /dev/pwmchipN 也无 /sys/class/pwm → 上游三个示例程序执行并报告找不到芯片（环境限制，如实申报），消费者测试只覆盖打开失败路径 |

## 测试

### 上游（build() 内执行，真机）

`pwmround`、`pwmset`、`pwmtestperf` 三个示例程序真机执行，输出记入
`upstream-programs.log`；无 PWM 芯片时它们按设计报告失败原因，不驱动硬件。

### 消费者测试（test_package，CMake）

`test_package/test_libpwm.c` 共 4 条断言，全部是沙箱中确定的行为：

- `pwm_chip_open_by_number(0)` 返回 NULL 且 `errno` 非 0
- 不存在的芯片号返回 NULL
- 越界的芯片号（4294967295）返回 NULL

> 上游 API 不做 NULL 检查（`pwm_chip_close()`/`pwm_chip_num_pwms()` 直接解引用句柄），
> 因此消费者测试不构造伪句柄，避免测出未定义行为。

## 已知限制

- 波形 round/get/set 等真正驱动硬件的路径无法在无 PWM 芯片的环境验证。
- 未修改上游源码与测试（无 `patches/`）。
