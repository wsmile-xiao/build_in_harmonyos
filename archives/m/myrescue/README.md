# myrescue

## 概述

myrescue 是一个"从已经受损的介质上抢救仍可读取的数据"的命令行工具。它与
`dd_rescue` 目标相同，但策略不同：**遇到坏块不原地死磕**，而是快速跳开坏区先把
尚未损坏的部分读完，之后再回头重试坏区，并把每个块的健康状况记录在一份与目标
文件同名的**块位图**里（`0` 未测、`1` 读取成功、`-1`/`-2`… 失败次数、`2` 读取过慢）。
因此它天然支持中断后续跑，也支持"介质时好时坏"（例如 USB 桥松动）的场合。

除主程序外还随附两个位图分析工具：

- `myrescue` — 逐块抢救本体
- `myrescue-stat` — 统计位图里各类块的占比
- `myrescue-bitmap2ppm` — 把位图画成 PPM 图像，直观看出哪些区域读不出来

## 版本

- 0.9.8（2018-12-21 发布，本目录唯一版本）

## 来源

- 主页: https://myrescue.sourceforge.net/
- 源码: https://downloads.sourceforge.net/project/myrescue/myrescue/myrescue-0.9.8/myrescue-0.9.8.tar.gz
- 许可证: GPL-2.0-or-later

## 构建依赖

- 无外部依赖（纯 C，仅 libc；`myrescue.c` 另用 Linux UAPI 头
  `<linux/usbdevice_fs.h>` 实现 USB 总线复位，OHOS native sysroot 自带该头）
- clang + GNU make（鸿蒙平台）

## 构建说明

上游 `src/Makefile` 全文只有 5 行：无 configure、**无 install 目标**、无 check/test
目标，且首行是裸赋值 `CFLAGS = -Wall`（会吞掉环境里的 CFLAGS）。因此：

- 编译器与全部编译选项必须写在 `make` **命令行**上；
- 安装由 Conan 配方的 `package()` 手工完成；
- 上游没有任何自动化测试，功能验证由 `test_package/test.sh` 的 46 条消费者断言承担
  （真实 file→file 逐块抢救 + 位图 + 两个位图分析工具的输出断言）。

零源码补丁。AArch64 上 plain `char` 默认无符号会破坏位图块状态语义，通过工具链
`-fsigned-char` 修正（详见 `0.9.8/notes.md`）。

## 用法

```bash
myrescue [<options>] <input-file> <output-file>
```

| 选项 | 说明 |
|------|------|
| `-b <块大小>` | 块大小（字节），默认 4096 |
| `-B <位图文件>` | 指定位图路径，默认 `<output-file>.bitmap` |
| `-A` | 首次出错即中止 |
| `-S` | 跳过错误（指数步进） |
| `-f <n>` | 跳过失败次数达到 n 的块 |
| `-r <重试次数>` | 每块最多读几次，默认 1 |
| `-s <起始块>` / `-e <结束块>` | 只处理该区间（结束为开区间） |
| `-G <range>` / `-F <range>` | 只在好块附近读 / 跳开好块附近的坏区 |
| `-J <n>` | 读完几块后用伪随机置换跳读（每块恰好访问一次） |
| `-T` | 让 `-A`/`-S`/`-F` 也把"读得太慢"的块当坏块 |
| `-R` | 反向拷贝 |
| `-U <dev-file>` | 每次读错后做一次 USB 总线复位 |

示例：

```bash
myrescue -b 4096 -r 3 /dev/sdb /path/safe/image.img
myrescue-stat /path/safe/image.img.bitmap
myrescue-bitmap2ppm /path/safe/image.img.bitmap 400 > map.ppm
```

## OHOS 适配要点

- `make` 命令行覆盖 `CC` 与整组 `CFLAGS`（裸 Makefile 的 `CFLAGS = -Wall` 会吞环境值）
- `-fsigned-char`：恢复块状态位图的有符号语义，否则"回头重试坏块"这一半功能静默失效
- 三枚二进制各 self-sign 一次（OHOS 不执行未签名 ELF）
- man 页：三份英文进 `share/man/man1/`，德语译文进 `share/man/de/man1/myrescue.1`
