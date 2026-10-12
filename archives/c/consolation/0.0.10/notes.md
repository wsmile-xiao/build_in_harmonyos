# consolation 0.0.10 适配笔记(HarmonyOS PC / aarch64)

## 基本信息

- 构建系统: **autotools**(configure + make)
- 上游版本: 0.0.10(Debian 源包 `0.0.10-1` 的 orig;Debian 无额外补丁)
- 源 URL: `https://deb.debian.org/debian/pool/main/c/consolation/consolation_0.0.10.orig.tar.xz`
  sha256 `50ecf54a5b3b0e34c10eb9ed07d4de5acebe044bbe8c4caff2574d7bab3aa853`(实测)
- 包类型: **application**(唯一产物 `sbin/consolation` 守护进程)
- 补丁: **1 个** — `patches/0001-ohos-musl-program-invocation-name-fallback.patch`
- 依赖(全部来自 main 上已发布组合,保证本 PR 独立可构建):
  `libinput/1.26.2`(经其 transitive 声明带入 `libevdev/1.13.7`、
  `mtdev/1.1.7`、`eudev/3.2.14`)

## 补丁说明(musl:program_invocation_short_name fallback)

`src/input.c` 在 usage() 输出中使用 glibc 全局
`program_invocation_short_name`(errno.h 在 _GNU_SOURCE 下声明)。
musl(OHOS PC)不提供该符号 → 编译失败。补丁:

```c
#if !defined(__GLIBC__) && !defined(program_invocation_short_name)
static const char program_invocation_short_name[] = "consolation";
#endif
```

仅影响 usage() 输出的程序名展示;glibc 行为不变。与仓内 libinput
1.26.2 / eudev 系列对同一 musl 缺口的处理同族。

## 非补丁适配:man 页规则中性化(交叉构建必踩雷)

上游 `src/Makefile.am` 有内联规则:

```make
dist_man_MANS = ../consolation.8
../consolation.8: ../README consolation $(top_srcdir)/configure.ac
	./consolation | sed ... > consolation.8.new && mv ...
```

且生成的 `src/Makefile.in` 把 `$(MANS)` 挂进 `all-am` —— **`make` 会
执行刚交叉编译出的 aarch64 守护进程来排版 man 页**,在 x86_64 构建机
(或任何非目标运行环境)上必然失败。该包 configure 没有
`--disable-manpages` 开关,因此配方在 configure 前

- 清空 `src/Makefile.in` 的 `dist_man_MANS` 行(生成物继承空值,
  `install-man` 变 no-op),

与其它包 `-Ddocumentation=false` / `--disable-manpages` 同口径。
已验证:上游全部源码改动仅 `src/input.c` 一处(补丁),无其它修改。

## 依赖解析

configure.ac 三组 `PKG_CHECK_MODULES`:libinput(>= 1.5,逐级探测到
>= 1.26 为最优)、libudev、libevdev(>= 0.4)。本配方单条
`requires("libinput/1.26.2", transitive_*=True)` + `PkgConfigDeps`:
libinput 自身对 libevdev/mtdev/eudev 的 requires 均为 transitive
声明,故 libinput.pc / libudev.pc / mtdev.pc / libevdev.pc 全部出现在
依赖 .pc 输出中,三组探测全部命中。

## 平台构建要点

| 要点 | 原因 |
|------|------|
| `TMPDIR` 指到可写目录 | HarmonyOS `/tmp` 是只读 erofs(E002) |
| man 规则中性化 | 见上节 |
| 无需 ELF 重签名 | automake install 为纯复制,不改写 RUNPATH(meson install 才需要;eudev 同例) |
| `make -j1` | 小包,日志可读 |

## 验证记录(本地,未交叉编译)

- 补丁对 Debian orig 解包树 `git apply --check` **通过**;
- 本地树与 orig 全量 diff 确认:除 `src/input.c` 外**零改动**
  (Debian 0.0.10-1 无补丁);
- musl 兼容性静态检查 6/6 通过;工具链无 OHOS 交叉环境,实际构建由
  CI `conan create` 完成;
- sha256 为下载原包实测值。

## test_package(L0c 真实执行测试)

eudev 同款 shell 脚本(`test_consolation.sh`,3 项断言):

1. 定位包内 `sbin/consolation`;
2. `consolation --version` 成功退出(input.c 的 `case OPT_VERSION:
   version(); exit(0)`,不触碰 VT,构建机可安全执行);
3. `consolation --help` 成功退出且输出含 `Usage:`(同上,
   `case 'h': usage(); exit(0)`)。

上游无测试套件(无 TESTS 声明),如实申报 `upstream_test_in_build: false`。

## 运行前提(OHOS 集成阶段确认,非构建问题)

- 内核 `CONFIG_VT` 启用且存在 `/dev/tty0`;
- eudev(udevd)运行,输入设备可见;
- 上游 systemd 单元 `consolation.service.in` 需改写为 OHOS 启动方式
  (OHPCD 无 systemd)。

## 交付物

| 路径 | 说明 |
|------|------|
| `sbin/consolation` | 守护进程本体 |
| `licenses/LICENSE` | GPL-2.0-or-later 许可证文本 |
