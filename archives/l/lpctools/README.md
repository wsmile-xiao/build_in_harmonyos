# lpctools

NXP LPC 系列微控制器的 **ISP（In-System Programming）烧录工具集**。

## 三个可执行文件

| 程序 | 作用 |
|---|---|
| `lpcprog` | 串口 ISP 烧录器。命令：`dump` / `flash` / `id` / `blank` / `go` |
| `lpcisp` | 另一条 LPC 产品线的烧录器，device 是**位置参数** |
| `lpc_binary_check` | 读取待烧录镜像，检查向量表与 user code |

## 用法

```
lpcprog -d <dev_name> -c <command> [options] [dump/prog file name]
```

| 选项 | 作用 |
|---|---|
| `-d \| --device=dev_path` | 主机串口线 |
| `-c \| --command=cmd` | dump / flash / id / blank / go |
| `-p \| --parts=file` | 型号描述表，默认 `/etc/lpctools_parts.def` 或 `./lpctools_parts.def` |
| `-b \| --baudrate=N` | 波特率，默认 B115200 |
| `-f \| --freq=N` | 目标振荡器频率 |
| `-t \| --trace` | 打开串口通信 trace |
| `-n \| --no-user-code` | 不为异常向量 7 计算有效 user code |

`lpcisp` 的命令行语义不同——**device 是位置参数，不认 `-c`**：

```
lpcisp [options] device [-s | --synchronize]
lpcisp [options] device command [command arguments]
```

## 快速验证（不需要 LPC 板子）

```
$ lpcprog -h | head -2
---------------- LPC ISP Prog tool --------------------------------
Usage: ./lpcprog -d <dev_name> -c <command> [options] [dump/prog file name]

$ lpcprog -d /dev/null -c id
serial_read: end of file !!!!
Error reading read-part-id acknowledge.
Unable to connect to target, consider hard reset of target or link
$ echo $?
255
```

把串口指向 `/dev/null`，握手立刻 EOF，「连不上目标」这条真实失败路径就能
稳定复现——上面正是本包消费者测试的断言依据（30 条，零硬件）。

## 注意

- `lpcprog -h` 退出码是 **0**，而 `lpc_binary_check -h` 是 **255**——同一工具集内两处不一致。
- 用法行里嵌的是 `argv[0]`（完整调用路径），不是字面量 `./lpcprog`。脚本里匹配
  用法行时不要写死路径前缀。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 1.07 | `lpctools/1.07` | 已适配（aarch64） |

## 授权

GPL-2.0-or-later。
