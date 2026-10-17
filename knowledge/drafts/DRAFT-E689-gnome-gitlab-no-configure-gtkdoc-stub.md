# DRAFT-E689：GitLab 归档无 configure + GTK_DOC_CHECK → autoreconf 引导需 gtk-doc stub 四件套

> Contributor: Awstme | Status: Draft | Updated: 2026-09-23
> Source: 任务卡 4316 libgsf 1.14.58.2（复用 1.14.58.1 六补丁配方，零源码 delta 实例）

## 背景

GNOME 项目的 GitLab release 归档（`https://gitlab.gnome.org/<group>/<pkg>/-/archive/<tag>/*.tar.gz`）
是仓库快照，**不含 configure / Makefile.in** 等 autoreconf 产物（对比发行 tarball
`download.gnome.org/.../*.tar.xz` 自带 configure）。从快照取源的配方必须在 `build()`
内 `autoreconf --force --install` 引导，而 GNOME 的 `configure.ac` 普遍含
`GTK_DOC_CHECK([1.12])`，引导链随即撞上沙箱没有 gtk-doc 工具链的问题。

## 现象（libgsf 1.14.58 归档实录）

```text
autoreconf: gtkdocize: command not found          # autoreconf 强制调用
aclocal: possibly undefined macro: GTK_DOC_CHECK   # 宏未收录
configure: missing required input file gtk-doc.make  # doc/Makefile.am include
configure: unable to guess system type             # autoreconf 用 automake 上游 config.guess 覆盖了 OHOS 补丁版
```

## 修复：gtk-doc stub 四件套 + config 备份恢复

以 libgsf `1.14.58.1` 六补丁配方为准（`archives/l/libgsf/1.14.58.1/patches/`，
1.14.58.2 原样复用，strip: 1）：

| 补丁 | 作用 |
|---|---|
| 0001-config.guess / 0002-config.sub | OHOS 识别（`aarch64-*-ohos` / `ohos*`）——**会被 autoreconf 覆盖，须前后备份恢复** |
| 0003-gtk-doc.make.patch | 源码根放 stub `gtk-doc.make`（初始化 CLEANFILES/EXTRA_DIST，撑住 `doc/Makefile.am` 的 `+=`） |
| 0004-gtkdocize.patch | stub `gtkdocize` 脚本，autoreconf 从 PATH 调到即生成最小 make 后 exit 0（**需 `chmod +x`，补丁不带执行位**） |
| 0005-m4-ohos-gtkdoc-stub.m4.patch | 定义 `GTK_DOC_CHECK` 宏（默认禁用 gtk-doc），aclocal 收录；**build() 先 `makedirs(m4/)`，patch 工具不建父目录** |
| 0006-configure.ac-gtkdoc.patch | 注释无条件 `GTK_DOC_CHECK` 调用（stub 宏未收录时防 shell 语法错） |

配套（配方内，非补丁）：

- `autoreconf` 前把 config.guess/sub copy 到 build_folder，autoreconf 后 copy 回 source；
- `env.define`：`AUTOM4TE/SED/AUTOCONF/AUTOHEADER`（E089 占位符）、`AUTOPOINT` +
  `gettext_datadir`（HNP 无 autopoint 且 gettext 安装树硬编码构建机路径）；
- `--disable-gtk-doc --disable-nls` configure 选项；
- tool_requires `automake/1.18` + `libtool/2.5.4`（CI 沙箱无全局 autotools，ohpcd 在档）。

## 禁止

- `sudo/brew/apt` 装 gtk-doc：改共享环境 + CI worker 没有 → 设备绿 CI 红（AGENTS §2）。
- 先删 config.guess/sub 再 autoreconf 且不备份：补丁版永久丢失，0001/0002 hunk 连锁失配。
- 在 `apply_conandata_patches` 之后才建 `m4/`：0005 的新增文件会应用失败。

## 复现/核验命令

```sh
grep -n GTK_DOC_CHECK configure.ac            # 命中 → 需四件套
grep -c '^AC_INIT' configure                  # 0 = 归档无 configure（走 autoreconf 引导）
grep -c patch_file <conandata.yml>            # 6 = 六补丁在档（含四件套+config 双补丁）
conan create . -pr:h=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 -pr:b=<同> --build=missing   # 全链通过
```

## 同族差异

- **E041/E071/E178**：autoreconf/automake 版本与再生成问题（时间戳、环境），不含 gtk-doc 断链。
- **E089**：`@am_AUTOM4TE@` 占位符未替换（env 覆盖修法），是本链配套步骤之一但非 gtk-doc 本体。
- **E007**：config.guess/sub OHOS 识别（补丁本体），本条额外覆盖「被 autoreconf 覆盖」的时序问题。
