# cryptmount 6.4.0 HarmonyOS PC 适配说明

## 上游与构建

- 上游仓库：<https://github.com/rwpenney/cryptmount>
- 上游版本：tag `v6.4.0`（tag commit `b7b0bf662ef29ed8dcd425df5bd626211989e15d`）
- 源码归档 SHA256：`5ea65c48e854f486116230ea0fb092bdd731d36148e8083b2817a7696e28d688`
- 构建系统：Autotools；tag archive 不带生成后的 `configure`。CI worker 有 autoconf，没有 `aclocal` 和 `autopoint`（`autoreconf` 会停在第一个缺失的工具上）。配方 `tool_requires` `automake/1.18` 提供 `aclocal`。该包里的脚本写死 `#!/data/service/hnp/bin/perl`；解释器不存在时改写为当前 `perl`。`PKG_CHECK_MODULES` 需要 `pkg.m4`，CI 没有系统 pkg-config，因此再 `tool_requires` `pkgconf/3.0.6`，把 `pkg.m4` 放进 `m4/`，并把 `PKG_CONFIG` 指到该包的 `pkgconf`。`configure.ac` 的 `AM_GNU_GETTEXT_VERSION([0.23.1])` 比制品仓 `gettext/0.22.5.1` 的 `autopoint` 新，该程序会直接拒绝，因此配方只复制该包的 `share/aclocal/*.m4` 到源码 `m4/`（`ACLOCAL_AMFLAGS = -I m4`），并用 `AUTOPOINT=true autoreconf --force --install` 跳过 `autopoint`。`--disable-nls`：musl 没有预装 GNU gettext，消息宏走 `cryptmount.h` 的无翻译分支。
- HarmonyOS PC armv8 使用 `--host=aarch64-linux-gnu` 与 `--build=aarch64-unknown-ohos`，使 Autoconf 识别交叉编译并避免在 configure 阶段运行目标程序。
- 包类型：命令行应用；依赖 `libdevmapper/1.02.198` 与 `libgcrypt/1.12.2`。关闭 LUKS、crypt-swap 和 fsck 集成。

## 适配依据

HarmonyOS PC 的 libc 有 `mntent.h` 和读端接口，但 configure 链接探测未找到 GNU 扩展 `addmntent`。配方探测该函数；缺失时用 mntent 字段规则序列化，并转义空格、制表符、换行和反斜杠。

Autoconf 生成的 `config.status` 临时目录受 umask 077 限制，设备 HMDFS 对后续写入返回 `Permission denied`。构建阶段仅将生成的 `configure` 脚本 umask 调整为 022。

上游 Automake 安装钩子在 Conan `DESTDIR` 暂存目录上设置 root 所有权和 setuid。打包补丁仅在直接系统安装时保留这些特权操作；HarmonyOS PC 不使用 Linux sysinit/systemd/modules-load 安装目标，因此将其从 `SUBDIRS` 移除。递归安装的顶层钩子通过 `$(srcdir)` 定位 `cmtab.example`。

## 验证与限制

- 真机：HarmonyOS PC AArch64，设备 UID/GID `20020085`，`CapEff=0x2a`、`Seccomp=2`。本轮从固定上游 tag `v6.4.0` 源码构建；设备上的 `testing/mudslinger.in` 与本地文件 MD5 均为 `a06675a8348466c30ec632971bc078c8`。
- 真机 Conan `create` 本轮退出码 0；包内消费者 `test_package` 为 2/2：`cryptmount --help` 正常退出；`--version` 在缺失受保护配置时按预期以 101 退出并输出 `Security failure`。
- 上游 `testing/mudslinger.in` 主测试块共 37 项。原始 runner 假设 `/tmp` 可写、`/bin/su` 可用并能调用 `chgrp`；HarmonyOS PC 上 `/tmp` 返回 `Read-only file system`，且 `/bin/su`、`/bin/bash` 不存在。新增 `test_package/run_mudslinger_ohos.sh`：从固定上游 runner 提取原函数，不改上游测试源码；将临时目录放在 Conan build 目录，以当前 UID shim 替代只用于列表命令的 `su`，并只运行不要求特权的函数。配方执行顺序为独立 `make clean` → `make cmtest`（上游 Makefile 明确以 `-DTESTING` 开启这些测试入口）→ 安全子集 → 再次 clean 并重建正式二进制。分开执行 clean/cmtest 是必要的：Conan 注入 `-j20` 时同命令的多个目标会并行竞争，曾导致 clean 在测试二进制之后删除产物。
- 真机最新完整 Conan create：退出码 0；build 阶段上游函数输出 `test_version`、`test_null`、`test_listing`、`test_defaults` 4 项通过，`test_binary` 在 `cryptmount.c:206` 中止：`fs_test_blkgetsz` 检查 `/dev/hda`、`/dev/nvme*`、`/dev/sda`、`/dev/vda`、`/dev/xvda`、`/dev/sr*` 均未成功打开，`n_open=0`，按上游设计标记 ABORT；BLKSSZGET/BLKGETSIZE/BLKGETSIZE64 断言没有执行。0 项失败；随后正常重建发布二进制并完成 `test_package` 2/2。`test_listing`/`test_defaults` 的原断言在当前 UID 下通过，但 shim 不模拟 `bin`/`nobody` 的身份切换，因此不声称覆盖权限隔离。
- 累计唯一尝试 23/37：有效通过 4 项，失败 16 项，中止 1 项，2 项在 root 权限检查处未到目标断言并单独记为 blocked，不计通过；14 项没有启动，因为源码要求 root、loop/device-mapper、挂载或用户切换。`test_bad_keyfmt` 和 `test_bad_keyhash` 的上游函数虽打印 pass，但日志只有 `Only root can use option`，目标错误分支未执行，故仍列为 blocked。未把这些状态或 2 项消费者用例算入 4/37。逐项结果见 `test_package/MANIFEST.yml`。
- 真机权限取证命令：`cat /proc/self/status | grep -E '^(Uid|Gid|CapEff|NoNewPrivs|Seccomp):'`、`uname -r`、`sudo -n true`、对 `/dev/loop0`、`/dev/loop-control`、`/dev/mapper/control` 执行 `test -e`、`losetup -f`、`cryptsetup --version`、在任务目录执行 `mount -t tmpfs tmpfs <task-writable-dir>`。输出：UID/GID `20020085`，`CapEff=0x2a`、`NoNewPrivs=0`、`Seccomp=2`，HongMeng Kernel 1.12.0；sudo 报 `open /dev/tty for write failed` 且退出 1；三个设备节点均不存在（`losetup -f` 仅给候选 `/dev/loop0`）；cryptsetup 缺失并退出 127；mount 触发 Signal 31、退出 159。设备没有可用 dm/loop 节点或 root 授权，不能创建映射、绑定 loop、格式化或挂载文件系统、启用 swap，也不能切换到 `bin`/`nobody`。配方显式关闭 LUKS、crypt-swap、fsck；这些功能不计通过。
- 统计取数命令：`sed -n '/^# Run all tests:/,/^test_summary/p' testing/mudslinger.in | grep -E '^test_[A-Za-z0-9_]+$' | wc -l` 得 37；设备和本地源码 MD5 均为 `a06675a8348466c30ec632971bc078c8`。当前有效通过率为 `4/37`（10.8%），消费者 `test_package` 独立为 2/2。
