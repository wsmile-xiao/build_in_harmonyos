# delay

## 是什么

delay 是一个极简的 C 命令行工具：在**标准输入与标准输出之间引入恒定延时**。
从 stdin 读到的数据先存入带时间戳的环形缓冲（dtbuf），延时到期后再写入 stdout。

典型用法（把命令 A 的输出延后 5 秒交给命令 B）：

```
command_A | delay 5s | command_B
```

## 功能概述

| 特性 | 说明 |
|------|------|
| 延时参数 | 毫秒数字，或带单位后缀：`5s`/`2m`/`1h`（秒/分/时） |
| 缓冲区 | `-b <size>`，支持 `12k`/`12m`/`12g`（KiB/MiB/GiB）；默认 1 MiB |
| 数据行为 | stdin 数据按到达时间戳排队，到点后原样写出 stdout（字节透传） |
| 终止条件 | stdout 关闭立即退出；stdin 关闭且缓冲清空后退出 |

## OHOS 适配

- 纯 C 实现、无外部依赖（仅 libc + POSIX：poll / gettimeofday / read / write），
  OHOS libc 全部提供，**无需源码 patch**。
- 上游为普通 Makefile 构建（非 autotools），in-source 构建；
  配方从 Conan conf（`tools.build:compiler_executables`）读取 CC 注入（R33），
  不依赖未定义的 shell 环境变量。
- 上游 `make install` 写死 `$(DESTDIR)/usr/bin`，配方 `package()` 直接
  copy 构建产物到 `bin/`（同 desproxy 处理方式）。
- 安装 1 个命令行工具到 `bin/`，声明为命令行工具（commands.json，R38）。
- 上游无测试套件（Makefile 无 check/test 目标）；适配后补全消费者级冒烟测试
  （test_package 4 个独立检查项：数据透传 / 空输入 / 时间单位后缀 / 缓冲区参数）。

## 依赖关系

- 编译依赖：无
- 运行依赖：无

## 参考资料

- 上游项目页：https://github.com/rom1v/delay
- Debian 打包页：https://sources.debian.org/src/delay/（上游版本 1.0）
- 源码归档：`delay-0a430a0.tar.gz`（固定 commit 0a430a0，SHA256 20f06e6a...）
