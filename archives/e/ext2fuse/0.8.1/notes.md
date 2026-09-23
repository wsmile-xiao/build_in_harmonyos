# ext2fuse 0.8.1 HarmonyOS 适配记录

## 状态

- 当前状态：Shadow CI 已通过 OHOS armv8 编译、打包和 `test_package`；本轮前置
  适配完成。真实挂载仍需具备授权的 `/dev/fuse` 和 ext2 块设备。
- 分支：`feat/ext2fuse-0.8.1`
- Worktree：`D:\harmonyos\worktrees\ext2fuse`
- 目标平台：HarmonyOS arm64，Conan 设置为 `os=OHOS, arch=armv8`
- Issue：按本轮要求不再关联 issue 编号。

## W0 依赖检查

直接依赖只有 `libfuse/3.18.2`。ext2fuse 的 `lib/ext2fs` 和 `lib/et`
是上游源码内置的静态库，不应把 `e2fsprogs` 适配混入本 PR。

依赖 MR [3293](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/3293)
已经合入 `main`，并且 `ohpcd` 已可查询到 `libfuse/3.18.2` 的 OHOS armv8
Release 包。因此不再需要修改 libfuse 依赖本身。

构建工具依赖为 `autoconf/2.72`、`automake/1.18` 和 `pkgconf/3.0.5`。
这三个 OHOS armv8 包也已在 `ohpcd` 可查询。当前 Windows 上的 Conan 2.29.1
是标准发行版，不包含 `settings.os=OHOS`，不能代替 OHOS Shadow CI 做依赖图和
交叉构建验证。

## 源码与构建分析

- 源码：SourceForge `ext2fuse-src-0.8.1.tar.gz`。
- SHA256：`431035797b2783216ec74b6aad5c721b4bffb75d2174967266ee49f0a3466cd9`。
- 构建系统：Autotools；源码包自带 `configure`，但补丁修改了 `configure.ac`
  和 `Makefile.am`。OHOS 真机使用源码包内置的生成文件，避免在 HMDFS 上直接
  执行 Conan 缓存中的 Autotools 脚本。
- 上游原来检查 FUSE 2 的 `fuse_mount`，并硬编码
  `/usr/include/fuse`、`/usr/local/include/fuse`；配方改为消费 `fuse3.pc`
  的编译和链接参数。
- 上游使用 FUSE 2 低层 channel API；补丁改用 libfuse 3 的
  `fuse_session_new`、`fuse_session_mount`、`fuse_session_loop` 和
  `fuse_session_unmount`。目录读取改用 `fuse_add_direntry`，并保留
  `fuse_req_t` 请求上下文。
- 顶层 `make check` 没有注册测试目标。`tests/pjd-fstest-20080412` 实际包含
  12 类、184 个 `.t` 文件；完整盘点、真机尝试和每个阻塞原因见
  `test_package/UPSTREAM_TESTS.md`，不能把“未接入 make check”写成“上游没有测试”。

## Conan 配方要点

源码 URL 与 SHA256 已按仓库规范写入 `conandata.yml`，recipe 通过
`self.conan_data["sources"]` 下载并校验。`PKG_CONFIG` 显式指向 pkgconf 包中的
`pkgconf` 可执行文件，并把其 `share/aclocal` 加入 `ACLOCAL_PATH` 以展开
`PKG_CHECK_MODULES`。软件级 `archives/e/ext2fuse/commands.json` 声明
`ext2fuse/0.8.1` 的 CLI 入口，符合 R38。

OHOS 构建使用：

```text
--build=aarch64-unknown-linux-ohos
--host=aarch64-unknown-linux-ohos
```

构建固定为 `-j1`；`build()` 还将 Autoconf 生成的 `umask 077` 调整为 `umask 022`
以规避 HMDFS 沙箱临时目录权限问题。

平台兼容补丁不再使用 `__OHOS__` 条件编译。`imager.c` 使用 configure 生成的
`HAVE_SYS_TYPES_H` 判断是否需要 `ssize_t` 兜底，`llseek.c` 使用已有的
`HAVE_LINUX_FD_H` 能力宏选择 Linux 专用路径，同时由 recipe 注入
`EXT2FUSE_USE_PORTABLE_LSEEK` 关闭 OHOS 不可用的旧 `_llseek` ABI；公开头文件
无条件包含 POSIX 要求的 `<sys/types.h>`。这样判断依据是检测到的接口能力和
构建配置，而不是平台名。

## test_package

消费者测试只检查已安装的 `bin/ext2fuse`，并执行：

1. `--version` 输出 0.8.1 且返回上游约定的 9；
2. `--help` 输出用法且返回 9；
3. 无参数时返回非零并输出用法。

消费者测试共 4 个断言：安装的二进制可执行、`--version`、`--help` 和无参数
路径。不会把 `/dev/fuse` 挂载失败当成这 4 个断言的构建失败，但会在上游测试
台账中如实记录挂载阻塞。

## 上游测试完整台账

本轮不是“跳过上游测试”，而是先发现全集、再逐级尝试前置条件：

| 项目 | 发现/尝试结果 |
|---|---|
| 上游测试文件 | 12 类，共 184 个 `.t` 文件 |
| 源码解包 | 通过，设备端再次统计为 184 |
| 官方 `make` | 已执行，返回 2；上游 Makefile 硬编码 `gcc`，设备返回 `gcc: Permission denied` |
| OHOS Clang fallback | 通过；使用可写 `TMPDIR` 编译 `fstest.c`，无参数启动 rc=1，`stat/create/stat/unlink` 辅助调用均 rc=0 |
| `prove` / `perl` | 未安装，无法启动官方 TAP 递归运行器 |
| ext2 镜像 | 通过；`dd` 创建 32 MiB 镜像，`mke2fs -t ext2 -F` 返回 0 |
| ext2 mount | 已尝试；返回 1，`mount: bad /etc/fstab: No such file or directory` |
| `/dev/fuse` | 读写检查均失败，`Permission denied` |
| 184 个 `.t` | 真机普通 HMDFS 目录直跑：执行 184、通过 111、失败 73、阻塞 0；官方 `prove` + ext2/FUSE 挂载闭环仍因设备能力单独阻塞 |

因此本轮上游脚本直跑结论是 **fail**，不是 pass，也不是“没有测试”；
官方 `prove` + ext2/FUSE 挂载闭环结论是 **blocked**。完整
命令、输出摘要和恢复条件见
[`test_package/UPSTREAM_TESTS.md`](test_package/UPSTREAM_TESTS.md)。

### 本机补齐工具后的复跑记录（2026-09-12）

为继续推进用例执行，已在仓库外临时目录进行本机工具补齐和实测：

- Strawberry Perl：已通过 `winget` 尝试安装，但安装器下载阶段返回
  `0x80072efd`，未完成系统安装；
- Test-Harness：复用 Git for Windows Perl，准备 CPAN `Test-Harness 3.52`，
  `App::Prove`、`TAP::Harness` 和 `TAP::Harness::Env` 可加载；
- `fstest.c`：使用 DevEco SDK 的 OHOS Clang 交叉编译成功，生成 AArch64
  ELF；Windows 主机不能执行该目标文件；
- `prove --dry -r`：返回 `0`，只证明官方测试运行器可以启动和解析目录；
- `mkdir/00.t`：实际执行 36 个断言，5 通过、31 失败；
- `open/00.t`：实际执行 47 个断言，9 通过、38 失败；
- 完整 `prove -r`：实际启动 41 个文件，120 秒后返回 `124`；
  日志持续显示 `../../fstest: No such file or directory`。

上述两个代表性文件和完整套件均是真实启动后的结果，没有把失败改写成跳过。
但它们运行在 Windows/Git Bash 主机，不具备 OHOS 的文件系统、用户/组权限、
设备节点和 FUSE 挂载语义，因此不计入 OHOS 目标设备数字。随后新真机已逐个
启动 184 个上游 `.t` 脚本，当前目标脚本执行数字为：
`184 discovered / 184 executed / 111 passed / 73 failed / 0 blocked`。
当前本机 `hdc list targets` 为空，QEMU AArch64 也未安装；此前真机 SSH
`10.62.229.155:2222` 曾不可达，后续已切换到可达的
`10.62.178.77:2222` 并完成新的 OHOS 目标执行证据，详见下方真机记录。

## 本轮验证

- 已下载并校验源码 SHA256：通过。
- 已完成源码 API、FUSE3 头文件和现有配方对照：通过。
- 本机标准 Conan 已完成 recipe `inspect`，但会直接报 `Invalid setting 'OHOS'`，
  不能代替 OHOS 交叉构建。
- 已通过补丁顺序应用检查、Python 语法检查和 `git diff --check`。
- Shadow CI 首轮已取得设备全局锁，等待 6716 秒后于 2026-09-11 20:09:33
  结束；失败原因是上传包中的 `0006-fuse3-session-direntry.patch` 行号上下文
  与 Conan 解压的源码不匹配，尚未进入源码编译。
- 第二轮 Shadow CI 已取得设备全局锁，但仍因 `0006` 两个 hunk 起始行偏移
  在编译前失败；已用 Conan 实际使用的 `patch_ng` 验证修正版。
- 第三轮已进入设备并完成构建，但链接阶段发现 OHOS Clang 对旧式
  `extern __inline__` 辅助函数生成外部定义，造成重复符号；配方加入
  `-DNO_INLINE_FUNCS` 后重新提交。
- 最终隔离 Shadow CI run 于 2026-09-11 15:38:56Z 至 15:41:02Z 执行完成，
  runner 返回码为 0。`conan create`、`test_package`、补丁洁净检查和 `bin/`
  内容检查均通过；完整设备日志保留在本机/设备任务目录，不提交到 Git。
- AI 审核修复后的首轮真实复跑于 2026-09-12 01:31:58Z 至 01:33:21Z；
  `HAVE_LINUX_FD_H` 在 OHOS 上为真，但旧 `_llseek` 宏 ABI 不可用，编译在
  `lib/ext2fs/llseek.c` 失败。最终改为由 recipe 注入
  `EXT2FUSE_USE_PORTABLE_LSEEK`，并在补丁中用能力宏加该开关选择 POSIX
  `lseek` 路径。
- AI 审核修复后的第二轮真实 Shadow CI 于 2026-09-12 01:36:53Z 至
  01:38:31Z 执行完成，runner 返回码为 0；日志确认编译命令包含
  `-DEXT2FUSE_USE_PORTABLE_LSEEK`，`conan create` 和 `test_package` 均通过。
- 通用 CI 的 L2 `--version/--help` smoke 检查标为 warning/skip；这是因为上游
  CLI 对这两个选项按约定返回退出码 9，而 `test_package` 已按该约定验证通过。
- 新真机 `10.62.178.77:2222` SSH 连接成功；源码包 SHA256、184 文件盘点、
  OHOS Clang fallback 编译、`fstest` 启动和 `stat/create/stat/unlink` syscall
  smoke 均已实际复跑。随后 184 个 `.t` 文件也逐个用 `/bin/sh` 启动，得到
  文件级 111 通过、73 失败，以及 1115 个 `ok` 和 833 个 `not ok` TAP 断言；
  这是真实的上游脚本执行结果。由于运行在普通 HMDFS 目录而非 ext2/FUSE 挂载点，
  且不是官方 `prove` runner，它不能作为 ext2/FUSE 挂载闭环通过证据。
- 新真机的 `prove`/`perl` 仍不存在；已创建 32 MiB ext2 镜像并再次执行
  `mke2fs`，但 mount 返回 `bad /etc/fstab: No such file or directory`，
  `/dev/fuse` 读写均 `Permission denied`，因此官方 `prove` + 真实 ext2/FUSE
  挂载闭环仍如实统计为 blocked，并与上面的普通 HMDFS 脚本执行结果分开。

## 路径 B / B 类知识库扩展候选

本节只声明“路径 B 候选材料”，不宣称已经获得 B 类认定；最终分类和分值以
知识库维护者及赛事评审结论为准。与普通适配说明相比，本轮沉淀的内容具有
独立错误特征、跨项目适用范围、推荐/禁止策略和目标环境验证证据。

| 草稿 | 可复用问题 | 本轮证据 | 适用边界 |
|---|---|---|---|
| `knowledge/drafts/E6339-draft-11A1.{md,kv}` | FUSE 2 低层 channel API 迁移到 FUSE 3 session API，同时处理回调签名和目录项编码 | FUSE3 补丁序列通过；最终 `conan create` 和 `test_package` 通过 | 适用于低层 FUSE 文件系统；高层 FUSE API 需单独判断 |
| `knowledge/drafts/E6340-draft-4C48.{md,kv}` | OHOS Clang 对旧式 `extern __inline__` 生成重复符号 | Shadow CI 链接失败复现；加入 `-DNO_INLINE_FUNCS` 后 runner 返回 0 | 适用于头文件 inline 实现与 `inline.c` 外部实现并存的 C 项目 |
| `knowledge/drafts/E6341-draft-4C48.{md,kv}` | HMDFS 上 Autotools 的 `/tmp`、umask、脚本执行、生成文件重生成和 jobserver 组合限制 | 配方采用 build-local TMPDIR、native shell、umask 022、禁用生成器、`make -j1` 后通过 | 适用于带可信生成文件的老式 Autotools 项目；没有生成文件时需另行设计 |
| `knowledge/drafts/E6342-draft-4C48.{md,kv}` | 将可无特权验证的 CLI 契约、普通目录脚本执行和需要 `/dev/fuse`/块设备的真实挂载能力分层，并完整记录上游 184 文件台账 | CLI 4/4 通过；真机普通 HMDFS 直跑 184 个脚本，111 通过、73 失败；官方 prove/ext2/FUSE 挂载闭环按权限/runner/mount 原因阻塞 | 适用于 FUSE、挂载、设备节点和特权运行时测试 |
| `knowledge/drafts/E6343-draft-202B.{md,kv}` | 让 Conan `patch_ng` 与本地 Git patch 使用同一源码快照和补丁顺序 | 前两轮在 0006 hunk 失败；干净源码 `patch_ng` 验证修正版后最终 Shadow CI 通过 | 适用于 Conan 连续补丁和 generated-file 修改，不应以单一 patch 工具代替 |

### B 类候选的工程化价值

这些草稿不是把同一条 workaround 拆成多个文件，而是覆盖了适配链路中的
五个不同决策点：

1. **协议/API 迁移**：识别 FUSE 2 与 FUSE 3 不只是库名变化，而是生命周期、
   callback 和 wire-format 语义变化。
2. **编译器语义差异**：通过 `nm` 区分链接顺序问题和 inline/ODR 问题，并
   使用项目提供的 `NO_INLINE_FUNCS` 开关。
3. **目标文件系统构建约束**：把 HMDFS 的 shell、临时目录、umask、生成器和
   jobserver 限制统一纳入配方设计。
4. **测试能力分层**：不把 CLI 可执行性、安装完整性和真实 FUSE 挂载混成一个
   不可解释的 pass/fail。
5. **补丁引擎一致性**：用实际 Conan patch_ng 在干净源码上复现，而不是把本地
   Git patch 的通过结果当作目标环境证据。

### 可迁移验证模板

后续遇到同类库，可以按以下顺序复用：

```text
1. 扫描 FUSE_USE_VERSION、fuse_mount、fuse_kern_chan_new 和旧目录项 API。
2. 检查头文件是否包含 extern inline，库是否提供 inline.c 或唯一外部实现。
3. 检查 configure、Makefile.in、aclocal.m4 是否已随源码归档发布。
4. 在干净源码副本按 conandata.yml 顺序执行 Git patch + patch_ng 双验证。
5. 在 OHOS 配方中固定 TMPDIR、CONFIG_SHELL、SHELL、AR 和 make -j1。
6. 递归盘点所有上游测试文件，分别记录 discovered、executed、passed、failed、
   blocked，不能用“未接入 make check”代替测试数量。
7. 先完成安装/CLI consumer test，再准备测试 runner、ext2 镜像和挂载权限；
   每一个无法执行的前置步骤都记录命令、返回码、原始错误和恢复条件。
8. 记录失败阶段、根因、修复和复跑结果，不能只记录最终绿色状态。
```

## 下一步真机 / shadow CI

依赖 MR 3293 已合入且制品已发布。本轮已通过隔离的 OHOS 真机 SSH 任务提交
单包 Shadow CI：

```text
job: ext2fuse-0.8.1-shadow
state: completed; pass
log_policy: full device path and connection details are retained outside Git
```

仓库既有 runner 的命令模板如下，具体 runner 参数以当前 CI 工具帮助为准：

```bash
python3 scripts/ohc-run.py conan-verify ext2fuse 0.8.1
```

建议真机顺序：

1. 在具备授权 `/dev/fuse` 和可丢弃 ext2 镜像/块设备的真机窗口执行：
   `conan create archives/e/ext2fuse/0.8.1 --build=missing`，确认编译、安装和
   CLI `test_package`。
2. 在设备上准备 `prove`/Perl、可丢弃的 ext2 镜像或块设备、挂载点和
   `/dev/fuse` 权限；本轮镜像虽已创建，但 mount 与 `/dev/fuse` 仍阻塞。
3. 再在独立测试目录创建可丢弃的 ext2 镜像或块设备与挂载点，执行：
   `bin/ext2fuse <ext2-device> <mountpoint> -o ro`。
4. 进入挂载点执行 `prove -r tests/pjd-fstest-20080412`，保存 TAP 原始结果、
   通过数和失败数。
5. 保存首次失败点和完整日志；若失败位于 `open("/dev/fuse")`，标记为运行时
   权限限制，不回改配方来伪造挂载通过。

当前 `conan create`、Shadow CI 和 `test_package` 已通过，可按仓库流程进入
PR/发布环节。真实挂载属于额外的能力验证；若后续取得授权的 `/dev/fuse` 和
可丢弃 ext2 镜像，再补做挂载闭环并更新验证记录：

```bash
python3 scripts/ohc-run.py finish ext2fuse 0.8.1 published
```
