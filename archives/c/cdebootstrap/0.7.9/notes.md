# cdebootstrap 0.7.9 适配笔记

## 编译环境
- **构建系统**: autotools（无现成 configure——autoreconf 生成）
- **编译日期**: 2026-09-19
- **编译器**: clang（OHOS aarch64 交叉工具链 /data/service/hnp/bin/）
- **平台**: aarch64-unknown-linux-ohos（OpenHarmony PC）
- **状态**: built（本地 scratch 全链路实测：configure RC=0 → make RC=0 →
  静态 ELF arm64 → --version 运行 OK）
- **补丁数量**: 1（canonicalize_file_name musl shim——独立补丁文件）
- **依赖**: libdebian-installer/0.121、bzip2/1.0.8、liblzma/5.8.1、zlib/1.3.2
  （静态链接，LDADD 顺序：frontend.a → -ldebian-installer-extra →
  -ldebian-installer → -lbz2 → -llzma → -lz）

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/cdebootstrap/0.7.9 --build=missing
```

### 1. 源码获取（source()）
Debian native 包（无 .orig.tar.xz）——`get(strip_root=True)` 去单一顶层
目录 `cdebootstrap/`（实测 tar 顶层结构）。

### 2. autoreconf 生成 configure
- **automake**：用 ohpcd automake/1.18 包（tool_requires——系统
  /usr/local/bin 属主 20001006 权限 770，CI worker uid 100 无读/执行权限，
  'Can't exec "aclocal"' 实测——同 libdi）
- **autoconf 路径**：`AUTOCONF` 环境变量指向
  `/data/service/hnp/autoconf.org/autoconf_2.72/bin/autoconf`（系统
  /usr/local/bin/autoconf exit 127 实测）；PERL5LIB 指向 automake 包内
  share/automake-1.18（含 Automake/Config.pm）
- **不需要 libtool**：configure.ac 无 AC_PROG_LIBTOOL（src/Makefile.am 纯
  `.c → .o` + `ar` 静态归档——无 .lo/libtool——全文核对实测）——比 libdi
  少一个 tool_requirement
- **configure.ac 修改**：`AC_INIT` 的 `m4_esyscmd(dpkg-parsechangelog)`
  取版本（环境无 dpkg——'AC_INIT should be called' 实测——同 libdi）→
  `replace_in_file` 硬编码 `0.7.9`

### 3. canonicalize_file_name musl shim（补丁 0001）
OHOS musl libc 无 glibc 扩展函数 `canonicalize_file_name`——
`src/frontend/standalone/main.c:230` 调用报
`incompatible integer to pointer conversion assigning to 'const char *'
from 'int'`（implicit declaration 后 int 返回——实测编译错误）。
补丁加 static shim：
```c
static char *canonicalize_file_name (const char *name)
{
  static char buf[PATH_MAX];
  return realpath (name, buf);
}
```
`realpath()` 是 POSIX 标准（musl 有）——语义一致（解析符号链接的绝对
路径、失败返 NULL 调用方查 errno）——`limits.h`（PATH_MAX）与 `stdlib.h`
（realpath）main.c 已包含。shim 后 make RC=0。

### 4. configure + config.status mktemp（同 libdi/dpkg）
`/tmp` 只读 + autoconf 相对路径 mktemp →
`./confXXXXXX/subs1.awk: Permission denied`。解法（SKILL 步骤 2——configure
尾部自动执行 config.status，事后改 ac_tmp 已来不及）：
- configure 执行前替换其 mktemp 模板：`mktemp -d "./confXXXXXX"` →
  `mktemp -d "${TMPDIR}/confXXXXXX"`
- configure 前 `os.environ["TMPDIR"] = "/data/storage/el2/base/cache"`
- 详见 SKILL: `docs/skills/autotools-config-status-mktemp-sandbox.md`

### 5. AutotoolsDeps 依赖注入（generate()，易漏）
`generate()` 必须同时生成 `AutotoolsToolchain`（编译器标志）+
`AutotoolsDeps`（依赖 -I/-L 注入）——只生成 Toolchain 时 libdi 的
include/lib 路径不进编译行，`'debian-installer.h' file not found`
（conan create 实测）。scratch 手动 -I/-L 会掩盖此问题。

### 6. configure 选项（generate()）
- `--build=aarch64-unknown-linux-ohos`：conan automake 的 config.guess
  无法识别 HarmonyOS（cannot guess build type 实测——同 libdi）
- `--enable-static`：LDFLAGS 加 -static 出静态 ELF；同时 configure.ac
  L41-47 逻辑——standalone frontend 仅 enable_static=no 时才
  PKG_CHECK_MODULES(libcurl)——一举两得免 libcurl 依赖
- `--with-dpkg-arch=arm64`：OHOS aarch64 对应 dpkg 架构（环境无
  dpkg-architecture——AC_MSG_WARN 走默认 arm64）
- `--with-frontend=standalone`：独立前端（免 libcurl/debconfclient）

### 7. 打包（package()）
`make install` 在 helper 段失败（helper/Makefile.am 用 dpkg-deb 打包
3 个 helper deb——OHOS 无 dpkg-deb——install-recursive 顺序 helper 先于
src 失败实测）——手动拷贝。Autotools helper 在 build_folder（basic_layout
下 = build-release，out-of-source）跑 configure/make，产物路径与源数据
路径不同（conan create package() FileNotFoundError 实测后核实）：
- 静态二进制 `build_folder/src/cdebootstrap` → `bin/`（编译输出在 build 树）
- 源数据 `source_folder/config/suites` + `config/generic/{action,packages,
  sections}` → `share/cdebootstrap/`（源数据文件留在源树，build 树
  config/ 只有生成的 Makefile）
- helper/*.deb 与 man 不打包（dpkg-deb 工具依赖 / man 非运行必需）

## 验证结果
- **构建**: 本地 `conan create`（CI 同款 profile + `--build=missing`）
  全链路通过——`Package ... created`，0 ERROR；产物
  `bin/cdebootstrap`——`ELF executable, 64-bit LSB arm64, static`（约
  1.7MB）+ `share/cdebootstrap/{suites, generic/}`
- **运行**: `--version` → `cdebootstrap 0.7.9`（exit 0）；无参 → 用法
  提示（exit 1）；`--help` → usage（exit 0）；上游 5 个集成测试真机
  实际执行 5/5 在 root 权限门真实阻塞（`E: Need root privileges` rc=1）；
  下载层 `--download-only` 真跑 bookworm 79 .deb/28MB 落盘（镜像经 CLI
  第 3 位置参数传 https://mirrors.aliyun.com/debian——包内 pristine
  config/suites 默认 deb.debian.org 跨海，CI 180s 拉不完，
  #58151/#59674/#59987 三次同因超时 debs=0；本地实测 79 .deb 全落盘
  <30s）——test_package 4 段实测 `test OK: cdebootstrap 0.7.9`
- **链接闭环**: 静态链接 libdebian-installer-extra.a + libdebian-installer.a
  + libbz2.a + liblzma.a + libz.a——LDADD 无需 -lsystem（main+extra 已覆盖
  di_system_* 全部引用符号——符号级核对）
- **上游测试**: 单元测试 0；集成测试 5（debian/tests/）——实际执行结果见
  下方"上游测试面"
- **R34 消费者验证**: test_package/test_cdebootstrap.py——4 段
  （A 冒烟 / B 上游 5 测试实际执行 / C 下载层真跑 / D chroot 探测）

## 已知限制
- **硬依赖 4 个（全部 self.requires，构建时缺一不可）**：
  libdebian-installer/0.121（di_* 核心库）+ bzip2/1.0.8 + liblzma/5.8.1
  + zlib/1.3.2（.deb 压缩层解包）——静态链接进二进制，运行时不依赖任何
  宿主动态库。4 个依赖的本地 binary 包均已核实存在（CI --build=missing
  可解析）
- **上游测试面（实测核对 tarball 全树 + 真机实际执行）**：单元测试 0（源码树
  无 test/ 目录、所有 Makefile.am 无 check 目标、无 test_*.c）；**集成测试
  5**——`debian/tests/` 的 Debian 自动化测试（bookworm-standard/sid-build/
  sid-minimal/sid-standard/trixie-standard），`control` 声明
  `Restrictions: needs-root`，每个 `exec cdebootstrap <suite> $ADTTMP/root
  --debug --flavour <X>` 实际 bootstrap 完整 Debian rootfs（libcurl 下载
  debs + chroot 内 dpkg 安装）。**OHOS 真机实际执行结果（test_package 逐条
  真跑，非"未执行"猜测）**：
  1. **5/5 在 root 权限门真实阻塞**：`E: Need root privileges` rc=1。源码
     `check_permission()`（frontend/standalone/main.c L194-198）
     `if (!noexec && getuid())`——bootstrap 安装层硬要求 root。环境实测：
     euid=20020084（非 root）、`sudo -n` 需密码且 `open /dev/tty` 失败、
     /etc/passwd root 账户 shell=/bin/false（锁定）——root 无法获取，
     工具级手段无解
  2. **install 层第二道系统级阻塞实测**：chroot(2) 系统调用
     （aarch64 __NR_chroot=51，asm-generic 表，OHOS sysroot
     aarch64-linux-ohos/bits/syscall.h 核对）在 OHOS 直接触发 **SIGSYS
     （signal 31，退出码 159）**——chroot 被禁；`--fakechroot` 需
     root 亦不可行（execute.c `di_exec_prepare_chroot` 安装路径强制 chroot）
  3. **下载层真跑通过**（`--download-only` 设 noexec=true 绕过 root
     检查）：镜像经 CLI 第 3 位置参数传 mirrors.aliyun.com
     （cdebootstrap 内置 CLI 能力，非源码补丁，上游测试未修改，仅
     测试层镜像覆盖——包内 pristine config/suites 默认 deb.debian.org
     跨海，#58151/#59674/#59987 三次同因 180s 超时 debs=0；本地实测
     aliyun 79 个 .deb 全落盘 <30s）；bookworm 依赖解析 + **79 个
     .deb（28MB）真实下载落盘**，libcurl/镜像解析/Release+Packages.xz
     索引/依赖求解全链路验证——5 个集成测试的共同前置阶段在 OHOS
     可执行且通过
  结论：bootstrap 安装层 = 双重系统级阻塞（非 root + chroot 被 OHOS 禁），
  OHOS 无解；能跑的部分（下载层）已真跑，不是"跳过了测试"
- helper deb（cdebootstrap-helper-apt/makedev/rc.d）不打包——dpkg-deb
  工具依赖（OHOS 无 dpkg 工具链）；generic 配置已打包，standalone 运行
  不依赖 helper

---

**编译结束**: 2026-09-19 17:45
**最终状态**: built
