# xfsprogs 7.2.0 适配笔记

状态: built

## 基本信息
- 上游: XFS 文件系统工具集（mkfs.xfs / xfs_repair / xfs_db / xfs_io / xfs_quota / xfs_scrub 等）
- 构建系统: autotools（tarball 预生成 configure，无需 autoreconf）
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 日期: 2026-10-01
- 源码: https://www.kernel.org/pub/linux/utils/fs/xfs/xfsprogs/xfsprogs-7.2.0.tar.xz
  sha256: 501dfa363cd8e19997a4a1a71f70ded88241b45e9db233e8875c23b80520cc83（与官方 sha256sums.asc 一致）

## 编译步骤
1. `./configure --prefix=$HOME/usr/local --enable-gettext=no`
   （依赖 include 经 CFLAGS/CXXFLAGS 注入；LDFLAGS 指向依赖库私有目录；LIBS 仅 -lurcu）
2. `make -j2`
3. `make install DESTDIR=<staging>`

## 依赖版本
- inih/r58（ini.h / -linih）
- libuuid/2.40.4（uuid/uuid.h / -luuid）
- liburcu/0.15.6（urcu.h / -lurcu，含 atomic64 检查）
- libblkid/2.42.2（blkid_probe_get_topology / -lblkid）
- gettext/0.22.5 未使用（--enable-gettext=no，见问题 4）
- 产物为静态链接：readelf -d 显示 NEEDED 仅 libc.so

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | `uname -s` = HarmonyOS，config.guess 2024-01-01 不识别 | config.guess 增加 `*:HarmonyOS:*:*)` 分支 |
| 2 | config.sub: Invalid configuration 'aarch64-unknown-linux-ohos' | 缺 ohos 三元组支持 | config.sub 增加 ohos-linux / ohos* / linux-ohos* |
| 3 | config.status 报 `confXXXXXX/subs1.awk: Permission denied` | HMDFS 下 `(umask 077 && mktemp -d)` 目录带 setgid 且 0700，owner 不可写 | configure 内 `umask 077`→`umask 022` |
| 4 | FATAL ERROR: msgmerge not installed | OHOS 无 msgmerge（仅 msgfmt/xgettext）；gettext/0.22.5 conan 包仅 libintl | `--enable-gettext=no`（msgmerge 仅 update-po 维护目标用） |
| 5 | make 报 urcu.h / uuid/uuid.h not found | xfsprogs `%.o`/`-MM` 规则不使用 CPPFLAGS | 依赖 include 注入 CFLAGS 与 CXXFLAGS |
| 6 | libtool: cannot find the library '//lib/liburcu-common.la' | liburcu/libuuid 制品 .la libdir='//lib'、dependency_libs 指向不存在路径 | 依赖库复制到私有目录并丢弃 .la；LDFLAGS 只指向该目录 |
| 7 | 链接缺 -luuid（LIBUUID 为空） | configure 注入的 LIBS=-luuid 使 AC_CHECK_FUNCS(uuid_compare) 误判为 yes | configure 时 LIBS 仅 -lurcu |
| 8 | xfs_io 链接缺 fsmap_sizeof/fsmap_advance | OHOS SDK linux/fsmap.h 缺 UAPI inline 助手 | 新增 include/fsmap_compat.h（自 Linux UAPI 复制）；3 处调用方改 include |
| 9 | mkfs: reallocarray 未声明 | OHOS libc 无 reallocarray | mkfs/proto.c 本地实现 xfs_reallocarray（__builtin_mul_overflow + realloc） |
| 10 | io/healthmon.c: expected expression | clang 15 不支持 case 标签后声明（C23） | 声明移至函数顶部 |
| 11 | doc/CHANGES.gz: gzip Unknown option 'best' | toybox gzip 不支持 --best | doc/Makefile 改 -9 |
| 12 | install: ../install-sh: No such file or directory | install-sh shebang `#! /bin/bash`（设备无 /bin/bash）；id(1)/chown(1) 缺失 | shebang→/bin/sh；`REAL_UID=${OWNER:-1}`；CHOWN 判断拆两步；configure 传 INSTALL_USER/GROUP |
| 13 | configure: working directory cannot be determined（shell-init/job-working-directory getcwd 错误刷屏） | conan 构建环境无 PWD；profile `CONFIG_SHELL`/`SHELL` 指向 hnp bash 5.3.0，该 bash 在 PWD 缺失/陈旧时 getcwd 必失败（实测 env -i bash 全目录失败；mksh 正常）；configure 按 CONFIG_SHELL re-exec 后即死 | 配方注册尾置 env 脚本把 CONFIG_SHELL/SHELL 重置为 /bin/sh（显式 VirtualBuildEnv + Environment.save_script） |

## 源码修改（补丁 11 个）
0001-config.guess.patch / 0002-config.sub.patch / 0003-configure.patch /
0004-doc-Makefile.patch / 0005-include-fsmap_compat.h.patch / 0006-install-sh.patch /
0007-io-fsmap.c.patch / 0008-io-healthmon.c.patch / 0009-mkfs-proto.c.patch /
0010-scrub-spacemap.c.patch / 0011-spaceman-freesp.c.patch

## 上游测试清点（R51）
- in-tree 无测试套件：`make -n check` → "No rule to make target 'check'"
- 全树无 tests/ 目录；ncheck/quotacheck/crc32cselftest 为运行时子命令而非测试框架
- 上游功能测试在独立仓库 xfstests-dev（需要真实块设备与破坏性格式化，CI 不可行）
- 实测 N=0，N'=0

## 验证记录
- configure / make / make install：RC=0
- 版本冒烟：12 个工具 `-V` 全部 rc=0
- 探索期 make install DESTDIR 暂存（prefix=$HOME/usr/local）：69 个文件，工具在 usr/local/sbin/
- conan 包布局：工具在 bin/（AutotoolsToolchain 将 sbindir 映射为 ${prefix}/bin），lib/libhandle.so*、include/xfs、libexec/xfsprogs、share/man 等
- test_package（R34/R53）：5 工具 AArch64 ELF 校验 + 5 工具 -V 实跑 rc=0
- W3 本地 CI（finish step [5/10]）：L0 pass / L1 pass / 构建通过率 100%，`.ci-result.json` exit_code=0（integrity_hash b68060e8d19cbf69，log_sha256 5ba6cb9b…）

## 已知限制
- NLS 本地化消息关闭（平台无 msgmerge）
- xfs_scrub 未编入 libicu（unicode 名称扫描，上游 probe 项）
- 未运行 xfstests（需块设备与破坏性操作）

---

**编译结束**: 2026-10-01 15:33
**最终状态**: built

### 对话 #1

- 任务: xfsprogs 7.2.0 首适配（HarmonyOS PC aarch64），分支 feat/xfsprogs-7.2.0
- 关键决策: ① 平台无 msgmerge → `--enable-gettext=no` 关闭 NLS（gettext 制品包仅 libintl）；② 依赖 include 注入 CFLAGS/CXXFLAGS（上游规则不吃 CPPFLAGS）；③ 依赖 .la 损坏（libdir='//lib'）→ 私有目录只放静态库；④ hnp bash getcwd 缺陷 → 配方尾置 env 将 CONFIG_SHELL/SHELL 重置为 /bin/sh；⑤ 保持 in-tree 构建（configure 依赖 `. ./VERSION`）
- 验证: conan-verify G0-G4/L2/L4/L5 全 PASS；W3 本地 CI L0/L1 pass、构建通过率 100%、.ci-result.json exit_code=0
- 遗留: L2 smoke 使用 GNU 风格 --version/--help 不适用本包（工具用 -V/-h），skip 非阻塞；xfs_scrub 无 ICU；未跑 xfstests
