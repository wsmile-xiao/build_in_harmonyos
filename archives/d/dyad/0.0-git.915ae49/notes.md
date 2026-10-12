# dyad 0.0-git.915ae49 — 适配笔记

## 软件概况

- **上游**：https://github.com/rxi/dyad （rxi 的轻量级 TCP socket C 库）
- **快照**：master tip `915ae4939529b9aaaf6ebfd2f65c6cff45fc0eac`（git ls-remote
  实测 2026-10-03；上游从未发布 release tag，最后一次提交为 2016-08-28）
- **版本号口径**：`0.0-git.915ae49`，沿用仓库 git 快照惯例（同 d52 的
  `3.4.1-git20191024.ac20ebd` 形态）。库内横幅 `DYAD_VERSION "0.2.1"`（master tip 值）
- **形态**：极简 C 库，全部源码两个文件 `src/dyad.c`（1156 行）+ `src/dyad.h`（106 行）
- **许可证**：MIT
- **依赖**：零（仅 libc / POSIX socket API）

## 构建形态与配方决策

上游**没有构建系统**：仓库根只有 LICENSE / README.md / doc/ / example/ / src/，
example/build.py 只是示例编译辅助脚本，不是库的构建系统。因此：

- 包类型 `static-library`：配方直接用 profile 交叉编译器把 `src/dyad.c` 编成
  `dyad.o`，`llvm-ar rcs` 归档为 `libdyad.a`；`dyad.h` 装入 `include/`。
- 编译器与归档器从 `tools.build:compiler_executables` 字典取（R33：不从裸 shell
  变量取，CI worker 不定义 ${CC}；同 d52/abc 先例）。
- fPIC 默认开（静态库进 .so 的常规需求）。
- **零补丁**：非 Windows 路径纯 POSIX（fcntl/netdb/sys/socket/select/gettimeofday），
  musl 全兼容，源码无需任何修改。

## 源码获取（镜像预置）

- CI worker 是站点白名单网络，GitHub 直连不可达；ghfast.top 是可达的 GitHub
  镜像（**codeload 格式在 ghfast 返回 403，必须用 archive/refs/heads 格式**）。
- conandata.yml 从第一版就带镜像列表：ghfast.top 在前、官方源兜底。
- sha256 双源实测逐字节一致：
  `ca686d30025467a61318dfc34256b1623e8e87a254d96e1c82923a26ae9e1a72`
  （ghfast.top 下载与 github.com 官方 archive 下载各算一次，2026-10-03）。

## 上游测试

**上游无测试套件（0 用例）**：

- 仓库无任何构建文件（无 Makefile/CMakeLists/meson.build，tar 解包实测）；
- 无 tests/ 目录、无测试脚本、无 CI 配置（find -iname '*test*' 无输出）；
- example/ 下 6 个 .c 是交互式示例程序（echoserv/ircbot/daytime/httpserv 等），
  非断言型测试；上游 README 无测试章节。

## test_package（消费者视角，socket 回环）

`test_package/test_dyad.c` 用 **127.0.0.1 回环连接**驱动 dyad 完整消费者路径
（OHOS 沙箱内回环可用，不需要外网）：

1. `dyad_getVersion() == "0.2.1"`（master tip 横幅）
2. `dyad_listenEx(server, "127.0.0.1", 0, 16)` 绑定回环，port=0 由内核分配临时端口
3. `dyad_getPort(server)` 可观测内核分配的端口
4. server 流状态 == `DYAD_STATE_LISTENING`
5. `dyad_connect(client, "127.0.0.1", port)` 返回 0（异步）
6. client CONNECT 事件触发
7. server ACCEPT 事件触发
8. client LINE 事件收到 greeting（`\n` 已剥离）
9. server DATA 事件收到与客户端载荷逐字节一致的数据
10. `dyad_getAddress(client) == "127.0.0.1"`
11. `dyad_getPort(client)` 报告的是对端（server）端口
12. `dyad_getBytesSent(client) == strlen(payload)`
13. `dyad_getAddress(remote) == "127.0.0.1"`
14. `dyad_getBytesReceived(remote) == strlen(payload)`
15. `dyad_shutdown()` 后 `dyad_getStreamCount() == 0`（无流泄漏）

断言共 15 条，任一失败进程返回非零。test_package/conanfile.py 用 can_run 门控，
交叉编译 test_dyad.c（带 `--sysroot` + `-fuse-ld=lld -Wl,--code-sign`，OHOS ELF
执行需代码签名，同 avce00 先例）后运行。

## 本地预验证记录（2026-10-03）

- 干净环境模拟：`conan remove dyad/0.0-git.915ae49 --force` 后全链重跑
  `conan create`（含 test_package 执行），结果见回告。
- L0 门禁逐项自查（L0a-L0e 结构 / L0f patch 格式 / L0h R33 / L0i 零依赖 /
  L0m slug / L0j 版本占用）见回告。
- pr-body-lint：PR 正文过 pr_lint.py 校验（P0 清零）。

## 注意事项

- 上游自 2016 年起停更（最后提交 2016-08-28），照原样构建，无安全补丁需求。
- 库横幅版本 0.2.1 与包版本 0.0-git.915ae49 的差异属正常：前者是库内字符串，
  后者是本仓库快照口径版本号。
- dyad 内部 `dyad_init()` 会 `signal(SIGPIPE, SIG_IGN)`——消费者进程全局生效，
  属上游既定行为。
