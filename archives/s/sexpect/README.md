# sexpect

sexpect 是「shell 版的 Expect」：用单个 C 语言命令行程序在 PTY 上驱动交互式程序，
不需要 Tcl/Expect 运行时。C 语言编写，零第三方依赖（libc + 线程库）。

- **上游仓库**: https://github.com/clarkwang/sexpect
- **官方源码**: https://codeload.github.com/clarkwang/sexpect/tar.gz/refs/tags/v2.4.0
  （GitHub 官方 tar 入口）
- **许可证**: GPL-3.0（随包安装 `licenses/LICENSE`）
- **分类**: 测试/自动化工具（CLI）

## 软件描述

sexpect 用 client/server 模型管理交互会话：

- `sexpect spawn [-t N] [-ttl N] ... PROG [ARGS]` — 启动会话守护进程，拥有 pty master，
  并在 `SEXPECT_SOCKFILE` 指定的位置创建 UNIX socket；被 spawn 的程序运行在 pty slave 上
- `sexpect send` — 向 pty 写入字符串（支持 `-cstring` 转义、`-cr` 回车、`-file/-fd/-env` 数据源）
- `sexpect expect [-exact|-glob|-re|-eof] PATTERN` — 等待输出匹配（含 `-timeout N`）
- `sexpect interact` — 人工接管，交互结束后可继续脚本
- `sexpect wait` — 等待并返回子进程退出码；`get`/`close`/`kill`/`set` 管理会话
- `sexpect expect_out` — 输出最近一次匹配（正则捕获组 `$expect_out(N)`）

典型用途：对交互式 CLI（ssh、ftp、数据库客户端、TUI 程序）做脚本化测试或自动化。

## OHOS 适配要点

- **PTY 层零修改**：OHOS sysroot 已提供 `posix_openpt/grantpt/unlockpt/ptsname`、
  `TIOCSCTTY`/`TIOCSWINSZ` 等接口，`pty.c`/`server.c` 原样编译运行。
- **sockfile 会合点回退（核心适配）**：HarmonyOS 对非应用进程拒绝创建 AF_UNIX
  路径名 socket（`bind(2)` 返回 `EPERM`），且 `/tmp` 只读、`/dev/shm` 不可写。
  补丁 `0001`–`0003` 在路径 bind 被拒时按 sockfile 路径的确定性哈希派生**抽象命名空间**
  套接字名，服务端与客户端同源推导；路径 socket 可用的平台（Linux）行为不变。
- **测试套件适配**：`send-null`/`send-128k` 的临时文件改用 `${TMPDIR:-/tmp}`
  （配方 `build()` 内把 `TMPDIR` 指向构建目录）；`chdir-after-logfile` 的子命令
  `ls -l /` 改为 `ls -l $tmpfile`（OHOS 沙箱拒绝列 `/`，会让 `sexpect wait`
  透传非零退出码）。断言逻辑未改。
- **上游测试**：`tests/CMakeLists.txt` 注册 27 个 CTest 用例，其中
  `spawn-nowait`、`still-open-after-exit` 由上游 `CMAKE_SYSTEM MATCHES "Linux.*"`
  守卫；HarmonyOS 上注册并运行 25 个，实测 25/25 通过。

## 依赖

无 Conan 运行时依赖；构建使用 OHOS SDK clang 与 CMake ≥ 3.17。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 2.4.0 | built | 2026-09-26 | 首适配；上游 CTest 25/25，消费者断言 10/10 |
