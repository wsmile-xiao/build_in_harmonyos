# pm-utils

Intel 平台的电源管理小工具集。两个独立的可执行文件，都不依赖库、没有公开头文件。

## pm-pmu

读 `/sys/devices/system/cpu/intel_pstate/` 下的运行状态，并做挂起前后的能耗记账。

```
$ pm-pmu --help
usage: pm-pmu --suspend | --check
```

**只接受长选项**——`-h` 不被接受（退出码 1），只有 `--help` 返回 0。

## pm-reset-swap

擦除交换分区头部残留的 swap signature。

```
$ pm-reset-swap <device node>
```

**参数一律当设备节点**，`-h` 不会被当成帮助。

## 快速验证

```
$ pm-reset-swap /nonexistent
Could not open "/nonexistent": No such file or directory
$ echo $?
1

$ pm-reset-swap /dev/null
Could not check "/dev/null" for swap signature: No error information
$ echo $?
2

$ pm-reset-swap /dev/zero          # 读出来全是零，恰好像合法签名
$ echo $?
0
```

三档退出码就是上面这三条路径，零特权、零硬件。

## 在 OHOS PC 上的行为

两个工具的工作目标 `/sys/devices/system/cpu/intel_pstate/` 是 **Intel P-state
专用节点**，OHOS PC 上并不存在。所以在这里：

```
$ pm-pmu --suspend ; echo $?
1
$ pm-pmu --check ; echo $?
1
```

`--suspend` / `--check` 退出码 1 且**不打印用法行**——是「执行失败」而不是
「参数没解析对」。`pm-reset-swap` 不依赖那个路径，功能完全可用。

以上正是本包消费者测试（22 条断言）的依据。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 1.4.1 | `pm-utils/1.4.1` | 已适配（aarch64） |

## 授权

GPL-2.0-or-later。
