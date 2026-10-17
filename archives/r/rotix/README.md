# rotix

rotix — 生成旋转混淆（ROT-x，如 ROT13）的命令行工具。给定文本、文件或标准输入，
rotix 按指定步长（rotor）旋转其中的 ASCII 字母，其余字节原样保留。

- 上游: https://github.com/shemminga/rotix
- 许可: GPL-2.0-or-later
- 本仓适配版本: 0.83（上游最后一个版本）

## 包内容

- 可执行文件: `bin/rotix`
- man 手册: `share/man/man1/rotix.1`
- 文档: `share/rotix/doc/README`
- 许可: `licenses/COPYING`

## 用法

```console
$ rotix -t 'Hello, World!'          # 默认 rotor=13，右旋
Uryyb, Jbeyq!

$ printf 'Hello\n' | rotix           # 无输入选项时读 stdin
Uryyb

$ rotix -t abc -r 3 -L               # 左旋 3
xyz

$ rotix -a -t Hello                  # 输出全部 25 种 ROT-x
ROT-01: Ifmmp
ROT-02: Jgnnq
...
ROT-13: Uryyb
...
```

主要选项：`-f <file>` 输入文件、`-o <file>` 输出文件、`-r <value>` 旋转步长
（`auto`/`-a` 为全部步长）、`-R` 右旋、`-L` 左旋、`-t <text>` 直接文本、
`-v` 版本、`-h` 帮助。

## 构建与测试

- 配方: `0.83/conanfile.py`（手写 configure + Makefile；`--i18n=0` 关闭 NLS，
  只构建 `rotix` 目标，注入 `gcc` shim 以满足 configure 的编译器探测）
- 补丁: `0.83/patches/0001-help-i18n-guard.patch`（help.c i18n 守卫，portability）
- 测试: `0.83/test_package/`（消费者测试，13 项断言，调用已安装二进制）；
  上游本身**无任何测试**（详见 `0.83/notes.md` 与 `0.83/test_package/MANIFEST.yml`）

## OHOS 适配状态

版本 `0.83` 已完成真机 shadow CI 验证（r1 一次通过）：conan create 成功、
test_package 13/13 断言 PASS、L0/L1/L4/L5 pass、exit 0。L2=skip（non-blocking）：
上游只注册短选项 `-v`/`-h`，不支持 CI 冒烟使用的 `--version`/`--help` 长选项，
属上游 CLI 惯例缺失（详见 `0.83/notes.md`）。
