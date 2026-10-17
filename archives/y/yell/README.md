# yell

**命令行 PC 喇叭蜂鸣器**（ehaupt / critical.ch，1.1 / 2002；FreeBSD port `audio/yell`）

yell 是一个极小的 C 语言 CLI：向 `/dev/speaker` 写入一段 ASCII 音符串，
在 PC 喇叭上播放一小段旋律。作者用它远程"喊话" sysop，也用作任务完成
通知（`make buildworld && yell`）。整个上游只有 4 个文件（Makefile /
yell.c / yell.h / README），零外部依赖，唯一系统要求是 libc。

## 用法

```bash
yell   # 在 PC 喇叭上播放内置旋律（t208a+b~a+a-~f+f~e-d）
```

无任何命令行参数；退出码恒为 0（含 speaker 设备打不开的情形——
`play()` 对 `open()` 结果有 `if (handle >= 0)` 守卫，优雅降级）。

> **OHOS 平台说明**：OHOS 无 PC speaker 硬件（无 `/dev/speaker` 设备），
> yell 在本平台运行时是「安全空操作」——可编译、可安装、退出码 0，
> 但不发声。作为极简 C CLI 的移植样例与 shell 通知占位保留。

## 移植要点

- 唯一源码修改：`#include <dev/speaker/speaker.h>`（FreeBSD 内核头，其
  声明未被使用）替换为 `<unistd.h>`（补 `write`/`close` 显式声明）。
- 上游 Makefile 的 install 目标（硬编码 `/usr/local/bin` + setuid 4110）
  不适用，配方改为等价单次 `clang -O3` 调用 + `package()` 手工打包。

## 许可证

BSD-2-Clause（FreeBSD port 记录；tarball 内无许可证文件，版本目录
`licenses/LICENSE` 内有归属说明与标准文本）。
