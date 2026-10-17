# recoverdm

按扇区从**有坏道的磁盘 / CD / DVD / 磁盘镜像**里尽量把数据抠出来的纯命令行工具，
附带一个把多轮不同读取结果**按坏块表合并**成一份最完整镜像的伙伴程序 `mergebad`。

- 上游主页：<https://www.vanheusden.com/recoverdm>（作者 Folkert van Heusden，2003-2004）
- 许可：GPL-2.0-or-later（`license.txt` 指向上级 GPL 声明）
- 分发源：Debian 官方 pool 的 pristine upstream orig tarball
  `recoverdm_0.20.orig.tar.gz`（Debian 未做任何重打包/改动，15 个文件全为上游原样）

## 它做什么

| 程序 | 作用 |
|---|---|
| `recoverdm -t <type> -i <in> -o <out>` | 逐扇区读取；普通文件用 `-t 1`(FILE)，软盘/CD/DVD/硬盘按 IDE/SCSI 用 `-t 10..19`；坏道多次重试（`-n` 重试次数、`-r` RAW 重试、`-s` 转速），读不出的扇区可写进 `-l <sectorsfile>` 坏块清单 |
| `mergebad -i <mapfile> <image> [-i ...] -o <out> [-l <outmap>]` | 拿同一介质**多次**读取出的多份镜像 + 各自的坏块清单，逐区间挑一份"该处没坏"的数据写入输出；所有镜像在同一处都坏时才按多数表决"猜"字节 |

典型用法就是：`recoverdm` 对同一张坏盘多跑几次（每次坏道分布不同）→ `mergebad`
把这几份合并成一份坏道最少的镜像 → 再对镜像做文件系统级修复。

## HarmonyOS PC 适配要点

见版本目录 `0.20/notes.md`。一句话总结：上游是**裸 Makefile**（无 configure、
`install` 目标把文件 `cp` 到烧死的 `/usr/local/bin`），且 Makefile 从不给 `CC` 赋值
⇒ GNU make 用内建默认 `cc`，OHOS 上没有这个别名，需在 make 命令行覆盖 `CC`
（配方零补丁）；上游 `CFLAGS` 用裸 `=` 且内含 `-DVERSION` ⇒ **不能**顺手覆写 `CFLAGS`。

## 已打包产物

```
bin/recoverdm
bin/mergebad
licenses/license.txt
```

上游 `recoverdm.1` 手册页在 0.20 的 orig tarball 里是 **0 字节空文件**，故不安装手册页。
