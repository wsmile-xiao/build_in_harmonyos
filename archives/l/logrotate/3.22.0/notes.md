# logrotate 3.22.0 — 适配笔记

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | logrotate |
| 版本 | 3.22.0 |
| 状态 | built |
| 构建系统 | autotools（release tarball 自带 `configure`） |
| 上游 | https://github.com/logrotate/logrotate |
| 源码 | logrotate-3.22.0.tar.xz，sha256 `42b4080…57618` |
| 目标平台 | aarch64（HarmonyOS PC / OHOS） |
| 编译器 | clang 15 |

## 二、依赖处理：vendored libpopt

logrotate 硬依赖 libpopt——`configure.ac` 中 `AC_CHECK_LIB([popt],[poptParseArgvString])`
未命中即 `AC_MSG_ERROR([libpopt required but not found])`，无回退。

制品仓（ohpcd）中当前**没有** popt（`conan download popt/* -r ohpcd` 报 system
acceleration policy not enabled，即不存在），仓库内 `archives/p/popt/1.16` 也只有
`built` 记录、无 conanfile.py，无法作为 conan 依赖引用。

为保持 PR 原子性（一个 PR 一个库）且配方自包含，采用 **vendoring**：
- `conandata.yml` 增加 `popt` 源（popt 1.16，OpenBSD distfiles 权威镜像，
  sha256 `e728ed…04cc8`）。
- `source()` 将 popt 解压到 `./popt`。
- `build()` 先以 `--enable-static --disable-shared --disable-nls` 编译 popt，
  安装到构建目录内的 `poptinst/`。
- 通过 toolchain 的 `extra_cflags -I.../include` 与 `extra_ldflags -L.../lib`
  让 logrotate 的 configure/编译/链接找到静态 libpopt。

结果：libpopt 静态并入 logrotate 二进制，运行期**仅依赖 libc**，无 libpopt.so 运行依赖。

SELinux / ACL 为 configure 的可选项（check 模式），目标平台无对应库，保持关闭。

## 三、HarmonyOS 适配点

1. **E007 config.guess**：HarmonyOS 下 `uname -s = HarmonyOS`，stock `config.guess`
   无法识别而报 “cannot guess build type”。给出显式 `--build=aarch64-unknown-linux-gnu`；
   由于未设 `--host`，autoconf 令 host=build，构建仍为 native（`cross_compiling=no`），
   规避了 `--host` 绕过引发的 AC_RUN_IFELSE 跳过等级联问题（F069）。popt 同样处理。
2. **mktemp 临时目录**：HarmonyOS 的 `mktemp -d` 产生权限受限的临时目录（hmmac MAC
   的 drwx--S---），令 `config.status` 失败。对策：`generate()` 用 PATH 前置一个恒返回
   失败的 `mktemp` shim，迫使 autoconf 的 `AS_TMPDIR` 回退到普通 `mkdir`（可正常创建）。
   该方案不触碰生成产物 configure/config.status（R6/R14），也无需补丁。构建前另置
   `os.umask(0)` 放宽默认文件权限。

## 四、本机容器验证

在与 CI 同源的 `hmbs-builder` 容器内执行
`conan create archives/l/logrotate/3.22.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`：
- popt 静态库编译通过 → logrotate 编译通过（clang 15，`make -j1`）。
- 产物 `bin/logrotate`（ELF aarch64），man 页安装到 `share/man`。
- test_package 真实驱动一次日志轮转（写入 test.log → `logrotate -f` → 断言
  生成 test.log.1），通过。

> 容器工具链在 `/data/service/hnp/bin`、GNU coreutils（expr/awk）在
> `/root/usr/local/bin`，本机验证时需并入 PATH（CI worker 的系统 PATH 已含之）。

## 五、上游测试

上游在 `test/` 下有 shell 驱动的功能测试（`make check`），依赖完整 GNU userland，
与配方正确性无关，未在 `build()` 中运行；改由 test_package 从消费者视角做真实轮转验证。

## 鸿蒙真机复测

- 日期：2026-07-19
- 环境：HarmonyOS HAD 206.1.0 真机（aarch64 musl，OHOS SDK clang 15.0.4）
- 结果：✅ 通过（conan create + test_package 真机原生执行）
