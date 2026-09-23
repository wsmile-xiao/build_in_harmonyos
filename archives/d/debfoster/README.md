# debfoster

`debfoster` 是一个 dpkg 包管理的「keeper 列表」工具：它读取 dpkg 的状态数据库，
算出哪些已安装的包已经不再被任何管理员明确需要的包依赖，并维护一份显式的
keeper 文件记录「当初是特意装上的」包。被拒绝的包会以 `-<包名>` 记入 keeper 文件，
下次运行时不再重复询问。它只做记账与决策，真正的装卸动作交给配置里的
`InstallCmd` / `RemoveCmd` / `InfoCmd` 执行。

## 功能概述

- 读取 dpkg `status` 数据库，构建包、依赖、Provides 关系图
- 交互式逐包询问是否保留（`Y` 保留 / `n` 拒绝 / `-` 移除 / `q` 退出等选项）
- 维护 keeper 文件：一行一个包，`-` 前缀表示已拒绝的包
- 六种只读查询：`-a` keeper 列表、`-s` 孤立包、`-d` 依赖、`-e` 依赖者、
  `-p` 提供者、`-r` 该包唯一带入的包
- Debian 版本号比较（`vercmp`）与带版本约束的依赖（`Depends: libfoo (>= 1.0)`）
- 配置项（`/etc/debfoster.conf`）覆盖安装/删除/信息命令、默认规则、
  优先级与 section 策略；命令行 `-o OPT=VAL` 可逐条覆盖
- keeper 文件的读写带 `flock` 排他锁，避免并发运行互相破坏

## OHOS 适配

上游 2.8 的发行 tarball 是 `make dist` 产物，`Makefile.am` 的 `dist-hook` 会把
`config.guess`、`config.sub`、`install-sh`、`missing`、`depcomp`、`aclocal.m4`
从发行目录里删掉，却保留生成好的 `configure` 与各目录 `Makefile.in`。Debian 用
`dh_autoreconf` 重新生成这些文件，本设备与 CI worker 都没有 autotools 工具链
（且 `configure.ac` 用了 `AX_CFLAGS_WARN_ALL`，还需要 autoconf-archive），
因此配方把这些辅助文件随 `generated/` 一起交付并复制回源码树（详见
`2.8/generated/PROVENANCE.md`）。

适配要点：

1. `generated/config.guess` 增加 `*:HarmonyOS:*:*` 分支：设备 `uname -s` 返回
   `HarmonyOS`，2024-07-27 版上游脚本只认 `Linux`/`GNU`，会直接
   `cannot guess build type`。
2. `configure` 内嵌的 `config.status` 用 `umask 077 && mktemp -d ./confXXXXXX`
   建临时目录；该目录在 hmdfs 上落盘为 `2700` 且属主不是当前 uid，随后写
   `subs1.awk` 报 `Permission denied`。补丁把 umask 改成 `022`。
3. `etc/Makefile.am` 的 `install-data-local` 硬编码 coreutils 的 `install -d`，
   OHOS 没有 `install` 命令（`make install` 报 exit 127）；改用 autoconf 的
   `MKDIR_P` 变量。
4. `src/keepers.c` 调用 `open()` 却只包含 `<sys/file.h>`，glibc 会间接引入
   `<fcntl.h>` 而 OHOS 的 musl 不会；补上显式包含。
5. 上游没有测试套件（任何 `Makefile.am` 都没有 `TESTS`，也没有测试目录），
   `make check` 在四个子目录都是 no-op；真实测试由 `test_package/` 的 36 项
   CLI 行为断言承担，见 `2.8/test_package/MANIFEST.yml`。
6. 依赖的静态 `gc/8.2.12` 在 OHOS 上每次运行都会向 stderr 打印
   `GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region`。
   这是该包自身的既知现象（仓库内 poke/guile/asymptote 等包同样记录为良性），
   不影响功能；`test_package` 因此只比对 stdout。
7. 二进制按上游 `sbin_PROGRAMS` 编译，但装到 `${prefix}/bin`（Conan 的
   `cpp.package.bindirs = ["bin"]` 会同时改写 `--bindir` 与 `--sbindir`），
   与 OHOS 无独立 `sbin/` 的惯例一致。
8. `--localstatedir` / `--sysconfdir` 未改写，仍是 `${prefix}/var` 与
   `${prefix}/etc`：默认 keeper 文件与 dpkg 状态路径因此指向包前缀内的绝对路径，
   实际使用时应通过 `-c` / `-k` / `-o` 指定真实路径。

## 依赖关系

- 编译期：`gc/8.2.12`（Boehm-Demers-Weiser 保守式垃圾回收器，`configure.ac` 用
  `AC_CHECK_LIB(gc, GC_malloc)` 检测，`src/error.c` 用 `GC_malloc` /
  `GC_malloc_atomic` / `GC_strdup` 实现 `xmalloc` 系列）
- 运行期：只有 C 库；NLS 在上游 `configure` 中因找不到 libintl 自动关闭
- 不需要 dpkg/apt 本身：状态数据库只是一个文件，通过 `DpkgStatus` 配置项指定

## 参考资料

- 上游仓库（Debian 维护）：<https://salsa.debian.org/debian/debfoster>
- 发行 tarball：<https://deb.debian.org/debian/pool/main/d/debfoster/>
- 手册页：`debfoster(8)`
