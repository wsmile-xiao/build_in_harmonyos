# members

`members` 是 `groups(1)` 的补集：`groups` 列出某用户所属的组，`members` 列出某个
**组**的成员。给定组名，向 stdout 输出以空格分隔的成员名。

## 功能概述

- `members <group>`（等价 `-a`）：主组成员 + 附属组成员，同一行。
- `-p, --primary`：只输出主组成员（`pw_gid` 等于该组 gid 的用户，来自 `getpwent` 枚举）。
- `-s, --secondary`：只输出附属组成员（`getgrnam` 的 `gr_mem`）。
- `-t, --two-lines`：始终输出两行，第一行主组成员、第二行附属组成员。
- `-h, --help`：输出选项说明。
- 退出码：组存在为 0，组不存在为 1（错误信息写 stderr）。

上游是 Debian 原生包（作者 Jim Lynch，`debian/source/format` 为 `3.0 (native)`）：
单文件 `members.cc`（约 11 KB）+ 裸 Makefile + man 页，只依赖 libc / C++ 标准库。

## OHOS 适配

- **构建系统**：裸 GNU Makefile。配方只在 make 命令行覆盖 `CXX`（取自 Conan conf），
  上游 `CPPFLAGS ?= -g -Wno-deprecated` 保持默认。
- **无补丁**：NDK clang++ / musl 下 `members.cc` 原样编译通过（`getopt_long`、
  `getgrnam`、`getpwent` 均为 musl 现成接口）。
- **安装布局**：不调用 `make install`（上游写死 `$(DESTDIR)/usr/bin/members`），改在
  `package()` 落 `bin/members`、`share/man/man1/members.1`、`licenses/copyright`。
- **运行时行为**：读取运行环境的组/用户数据库（`/etc/group`、`/etc/passwd` 或平台等价物）；
  上游 `display_primaries` 会多调一次 `getpwent`，因此主组成员枚举会跳过数据库中的第一条
  用户记录（上游既有行为，未改动）。

## 依赖关系

无第三方依赖，仅 libc 与 C++ 标准库。

## 许可证

GPL-2.0-or-later（源码头部声明 "version 2 ... or any later version"）。
