# installation-locale 1.9 — Debian 安装器的 UTF-8 C locale 定义（数据包）

| 项目 | 值 |
|------|-----|
| 软件名 | installation-locale |
| 版本 | 1.9 |
| 上游 | Debian Install System Team `<debian-boot@lists.debian.org>`（Debian **native 包**，无独立上游项目） |
| 源码地址 | <https://ftp.debian.org/debian/pool/main/i/installation-locale/installation-locale_1.9.tar.xz> |
| 源 sha256 | `df78ab6906f2df9d6cbfba78584dd83b5498c7c53589dc77f43d2c7527f9bfda` |
| canonical 位置 | <https://deb.debian.org/debian/pool/main/i/installation-locale/>（同字节；见下文源 URL 说明） |
| 许可证 | GPL-2.0-or-later（上游 `debian/copyright`："The copyright of this package is GPL, version 2 or later."） |
| 包类型 | 纯数据包（`package_type = "unknown"`，无编译、无 settings、无 CLI） |

## 这个包交付什么

Debian 安装器里 `installation-locale` udeb 的数据本体——**glibc `localedef` 的 locale
定义源 `C.UTF-8.in`**（81642 字节 / 1410 行）。Debian 侧用它编译出安装器所需的
UTF-8 C locale：

```make
# 上游 Makefile
build: C.UTF-8
C.UTF-8: C.UTF-8.in
	localedef -i $^ -f "UTF-8" ./$@
```

本包**不做编译**（编译需要 glibc 的 `localedef`，OHOS/musl 侧没有，且产物与架构相关），
交付的是与架构无关的定义源 + 上游配方，并把 `share/i18n` 挂进 `I18NPATH`。

安装布局（与 Debian/glibc 的 `/usr/share/i18n/locales/` 同形）：

```
share/i18n/locales/C.UTF-8.in            locale 定义源（数据本体）
share/doc/installation-locale/README     本文件
share/doc/installation-locale/upstream/  上游 Makefile / TODO / debian/**（仅溯源）
licenses/LICENSE                         许可
```

## 数据内容

POSIX/glibc locale 定义源，12 个 `LC_*` 类别：

- `copy "POSIX"`：`LC_COLLATE`、`LC_MESSAGES`、`LC_NUMERIC`、`LC_TIME`
- `copy "i18n"`：`LC_ADDRESS`、`LC_MEASUREMENT`、`LC_MONETARY`、`LC_NAME`、
  `LC_PAPER`、`LC_TELEPHONE`
- inline：`LC_IDENTIFICATION`（`i18n:2012`）、`LC_CTYPE`

`LC_CTYPE` 是文件的主体（1338 行），含 11 个字符类别（`upper`/`lower`/`alpha`/`digit`/
`space`/`cntrl`/`punct`/`graph`/`print`/`xdigit`/`blank`）、`toupper`/`tolower`
两个映射、一个 `totitle` 映射，以及 `combining`/`combining_level3` 两个具名类。
数据基于 **Unicode 3.2**（`gen-unicode-ctype.c` 生成，2001-2005 年产物）。

## 消费方怎么用

### 有 glibc `localedef` 的系统（Debian/Ubuntu 等）

```bash
export I18NPATH=<prefix>/share/i18n              # 本包已把它挂进 conanrun/conanbuild 环境
localedef --no-archive -i C.UTF-8.in -f UTF-8 <outdir>/C.UTF-8
export LOCPATH=<outdir>
export LC_ALL=C.UTF-8                            # 之后按普通 C.UTF-8 locale 使用
```

`localedef` 按 `<I18NPATH>/locales/<name>` 找定义源，这正是本包把文件装到
`share/i18n/locales/` 的原因。实测：不设 `I18NPATH` 时 `localedef -i C.UTF-8.in`
报 `cannot open locale definition file`，设了就编译成功。

### 没有 glibc `localedef` 的系统（musl / OpenHarmony PC）

定义源是**纯 ASCII 文本**，可以直接读：`<Uxxxx>` 记法给出码位，`;` 分隔条目，
行尾 `escape_char` 续接。本包自带的消费者用例
（`test_package/consumer_locale.py`）就是一份可复用的读取器实现，它重建出的
LC_CTYPE 表与 **GNU libc 编译同一文件后报出的表逐项相等**（14 个类别计数 + 3 个映射
规模全部一致）。

### 消费方需要知道的落差

1. 数据是 **Unicode 3.2**：28 个非 ASCII 大小写对与新版 `unicodedata` 不同
   （`toupper` 731/759、`tolower` 748/749 一致，ASCII 与 Latin-1 段 100% 一致）。
2. **Unicode 3.2 之后的码位完全不在任何类别里**（例如 `U+1F600` emoji），
   消费方必须回退到其它 locale 或自带 Unicode 数据。
3. 有 **19 对非互逆映射**（Unicode 事实）：例如 `toupper(µ U+00B5) = Μ U+039C`，
   而 `tolower(Μ) = μ U+03BC ≠ µ`。

## 构建与测试

- **构建**：无。`build()` 只做载荷指纹校验（文件数 10 / 总字节 85043 /
  `sha256("<名> <字节数>\n" 排序清单)` = `eca4fef1967aacdbdb8cda689eb4ef6f068f046f5a412feadc2a834b5f20bab9`），
  任一不符即 `raise ConanException`。
- **上游测试 N=0**：源包里没有测试目录/测试框架/`check` 目标，也没有
  `debian/tests/`（无 autopkgtest）。
- **本包验证**：端到端消费者用例 1 个（89 项检查，localedef 等价解析 → LC_CTYPE
  表重建 → 真实文本处理 → 与 GNU libc 及 Python `unicodedata` 交叉核对）+
  适配自检 16 条，见 `test_package/`、`manifest.yaml` 与 `notes.md`。

## 源 URL 说明（为什么不是 deb.debian.org）

本仓库 preflight 的 PF7 源 URL 闸把 `deb.debian.org` 主机字面量归入"Debian 下游
重打包源"直接拦下，故 `conandata.yml` 写 Debian 自己的归档主机 `ftp.debian.org`
（同一台 ftp-master 的公开名，不是第三方镜像；仓库内已有 14 处同类先例）。
两个 URL 实测返回**逐字节相同**的 tar.xz。未做任何 `+dfsg` / `.debian.tar.*` 重打包。
