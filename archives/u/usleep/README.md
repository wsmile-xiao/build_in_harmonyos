# usleep

## 是什么

usleep 是 usleep(3) 的命令行封装（Arch AUR 包 `usleep` 的上游源码）：

```
usleep <微秒数>
```

睡眠指定的微秒数后以 0 退出，常用于 shell 脚本里做亚秒级延时。

## 行为（usleep.c 全部逻辑）

| 输入 | 行为 |
|------|------|
| 无参数 | 立即以 0 退出 |
| `usleep N` | `atoi(N)` 赋给 `unsigned int` 后调用 `usleep()`，退出码恒为 0 |
| 非数字（如 `abc`） | `atoi()` 得 0，立即退出 |
| 多余参数 | 忽略 |
| 负数 | 回绕为极大的无符号值（`-1` ≈ 71 分钟），属上游既有行为 |

## OHOS 适配

- 单文件 C，只用 `<stdlib.h>` 与 `<unistd.h>`；musl 在默认特性集下声明 `usleep()`，
  **无需源码 patch**。
- 上游 Makefile 写死 `CC = gcc`：配方在 make 命令行用 Conan conf
  （`tools.build:compiler_executables`）的编译器覆盖（R33），保留上游 `-Wall -Wextra -O2`。
- 上游 `make install` 以 `PREFIX=/usr/bin` 为目标，配方 `package()` 直接 copy 到 `bin/`。
- 上游无 release/tag：版本 `20160311.094456` 是 master 头提交 `4f880a7a` 的 committer 时间戳，
  `conandata.yml` 用官方 `archive/<sha>.tar.gz` 固定该提交。
- 上游无测试套件；适配后补全 test_package（A1-A3 产物检查 + F1-F6 功能检查，共 9 项）。

## 依赖关系

- 编译依赖：无（上游 PKGBUILD 的 git 仅用于 AUR 拉取源码，Conan 走 tarball 不需要）
- 运行依赖：无（仅 libc）

## 参考资料

- 上游仓库：https://github.com/cpeuvrel/usleep-aur
- 源码归档：`archive/4f880a7a4cd4e0064f10ddc84dda1716c0b99803.tar.gz`（SHA256 86d1c4f7...）
