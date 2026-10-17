# ylva

`ylva` 是一个命令行密码管理器：所有条目（标题/用户名/URL/口令/备注）存在一个 SQLite
数据库里，当前使用的数据库路径记在 `$HOME/.ylva.open_db`。整库可以用口令加密成
AES-256-CTR 密文（密钥由 PBKDF2-HMAC-SHA256 200000 轮 + 64 字节盐导出，另有
HMAC-SHA512 校验），口令可以随机生成，条目也能以终端二维码形式显示。

上游作者 Niko Rosvall，源码托管在 [nrosvall/ylva](https://github.com/nrosvall/ylva)，
MIT 许可。Debian（`ylva` 1.7-2，bookworm/trixie/forky）与 FreeBSD ports 以此 tag 为上游。

## 功能概述

- `-i <path>` 初始化数据库；`-u <path>` 切换数据库；`-p` 打印当前数据库路径
- `-a` 新增条目；`-e <id>` 编辑；`-c <id>` 复制；`-r <id>` 删除
- `-l <id>` 列出某条；`-A` 列出全部；`-t [n]` 列出最近 n 条
- `-f <term>` LIKE 检索；`-F <regex>` POSIX 正则检索；`-q <term>` 快速检索并显示口令
- `-g <len>` 生成随机口令；`--show-passwords` 在列表中显示口令；`--show-qrcode` 以二维码显示条目
- `-E` 加密当前库；`-D <path>` 解密；`--auto-encrypt` 退出前自动加密；`--force` 强制重建
- `-v` / `-h` 版本与帮助；`YLVA_DEFAULT_USERNAME`、`YLVA_COLOR` 环境变量

## 依赖关系

- 编译依赖：`openssl/3.5.8.1`（`-lcrypto`）、`sqlite3/3.49.1`（`-lsqlite3`）、
  `libqrcodegen/1.8.0`（`-lqrcodegen`），另需 `-lrt` 与 `-lm`（OHOS sysroot 中 libc/空壳档案提供）
- 运行依赖：无第三方共享库（三者均静态链入，`DT_NEEDED` 只有 `libc.so`）

## OHOS 适配要点

- **构建系统零补丁**：`src/Makefile` 写死 `CC=gcc`，`CFLAGS` 用 `?=` 且自带 `+=`，
  `LIBS` 是固定列表。GNU make 命令行赋值优先级更高，故 `build()` 直接在命令行注入
  `CC`（取自 Conan conf，R33）、`CFLAGS`、`LDFLAGS`，并原样保留上游 `LIBS`
- **`-lrt` 保留**：OHOS/musl 安装空的 `librt.a` 兼容档案，timer/clock 入口点在 libc 本身，
  上游链接行无需删改
- **qrcodegen 头文件布局**：`src/qr.c` 按 Debian `libqrcodegen-dev` 的布局包含
  `<qrcodegen/qrcodegen.h>`，而本生态 `libqrcodegen/1.8.0` 把 C 头文件平铺安装为
  `include/qrcodegen.h`。配方在 `build()` 里生成一个 build-only 转发头
  `<build>/_qrcodegen_compat/qrcodegen/qrcodegen.h`（内容一行 `#include <qrcodegen.h>`）
  复现惯例布局，上游源码保持与 tarball 逐字节一致，不产生任何 patch
- **上游内存安全缺陷修复（1 个补丁）**：`entry_new_empty()` 只 `malloc` 不初始化字段，
  查不到记录时 `entry_free()` 会对野指针 `free()`；glibc/macOS 在刚分配的零页上侥幸通过，
  OHOS 的 musl malloc 检出非法释放后以 SIGTRAP 终止（CI 实测 `ylva -l <缺失 id>` rc=-5）。
  `patches/0001-src-entry.c.patch` 在 `malloc` 后 `memset` 清零，纯 C 标准库、无平台宏（R8/PF5）
- **R26 系统同名库**：openssl/sqlite3/libqrcodegen 在本生态均为静态变体，产物
  `DT_NEEDED` 实测只有 `libc.so`，不向 OHOS `/lib` 投放同名 `.so`
- **不使用 /tmp**：状态文件在 `$HOME/.ylva.open_db`，数据库文件由 `chmod(0600)` 收权，
  不依赖可写的 `/tmp`（R10）
- **交互提示**：口令提示用 termios 关回显；stdin 不是 tty 时上游 `my_getpass()` 会直接
  返回失败（随后读取未初始化缓冲区），所以功能测试必须在真实 pty 下驱动交互流程
- **测试**：上游无任何测试套件；`test_package` 补全 29 个独立检查项
  （功能 21 + 鸿蒙特有 8）

## 参考资料

- 上游仓库：<https://github.com/nrosvall/ylva>
- 手册页：`ylva(1)`（随包安装到 `share/man/man1/`）
- Debian 包：`ylva` 1.7-2（main，bookworm/trixie/forky）
