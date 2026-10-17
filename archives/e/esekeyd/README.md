# esekeyd

esekeyd — ESE Key Daemon：多媒体键盘守护进程。监听 `/dev/input/event<N>`
输入事件设备，把功能键/组合键映射为配置文件中指定的 shell 命令。
附带两个辅助工具：`keytest`（打印按键事件对应的键名）、
`learnkeys`（根据实际按键生成配置骨架）。

- 上游: https://github.com/burghardt/esekeyd（发布渠道 SourceForge；
  本仓采用与之同源的 Debian/Ubuntu orig tarball）
- 许可: GPL-2.0-or-later
- 本仓适配版本: 1.2.7（上游 2010 年最后版本，SVN-r63）

## 包内容

- 可执行文件: `bin/esekeyd`、`bin/keytest`、`bin/learnkeys`
  （上游将 esekeyd 装到 sbin，配方用 `--sbindir` 统一收进 bin）
- man 手册: `share/man/man1/{esekeyd,keytest,learnkeys}.1`
- 示例配置: `share/esekeyd/examples/`
- 许可: `licenses/COPYING`

## 用法

```console
# esekeyd <config> [input_device] [pidfile]
$ esekeyd ~/.esekeyd.conf /dev/input/event3

# 配置格式（learnkeys 可生成骨架）：
# PLAY:/usr/bin/mpc toggle
# LEFTMETA+E(press):nautilus
```

## 构建与测试

- 配方: `1.2.7/conanfile.py`（标准 autotools 流程：AutotoolsToolchain +
  configure + make -j1 + make install）
- 补丁: `1.2.7/patches/0001-makefile-vpath-and-no-parser-regen.patch`
  （移除 parser.c 生成规则 + mkparser 规则 VPATH 修复，portability）
- 测试: `1.2.7/test_package/`（消费者测试，14 项断言：三个程序的用法/
  错误路径 + 合成二进制 input_event 记录经 keytest 验证 parse() 键名映射）；
  上游本身**无任何自动化测试**（详见 `1.2.7/notes.md`）

## OHOS 适配状态

版本 `1.2.7` 已完成真机 shadow CI 验证（r5，2026-09-29）：conan create 成功、
test_package 14/14 断言 PASS、L0/L1/L4/L5 pass、L1e 破坏性反向验证确认、
exit code 0。L2=skip（non-blocking）：上游 CLI 无 `--version`/`--help`
长选项（E503 同族）。适配补丁 2 个：Makefile parser.c 生成规则/VPATH 修复、
configure config.status umask（E011/E052 HMDFS）。详见 `1.2.7/notes.md`。

## 适配提醒

esekeyd 运行时需要读取 `/dev/input/event*`（input UAPI + evdev），在
HarmonyOS PC 上实际部署时需确认设备节点与 SELinux 策略允许用户态读取；
本包验证范围限于构建、安装与非硬件路径的行为。
