# librcd

librcd 是 RusXMMS 项目的**俄文/西里尔文本编码自动检测库**（R. Charset Detection
Library）。上游自述它针对**很短的文本**优化——3-4 个字母的 ID3 tag、文件名等——在短
标题上的准确率优于 Enca，并且能识别 ISO-8859-1（非西里尔拉丁文）。

- 官方仓库/主页：http://rusxmms.sourceforge.net/ （源码镜像：https://github.com/RusXMMS/librcd）
- 许可证：LGPL-2.1-or-later
- 版本：0.1.14
- 上游下载源：上游发布机 `dside.dyndns.org` 与官网均已下线，使用 Debian 源码包的
  pristine 上游归档
  `https://deb.debian.org/debian/pool/main/libr/librcd/librcd_0.1.14.orig.tar.bz2`
  （sha256 `261db28bc864fd4b2d3ba88403b2e421944281e323c1e39c0e61f5160c16b664`，
  308041 字节，与 Debian `librcd_0.1.14-1.dsc` 的 Checksums-Sha256 逐字一致）
- 归档目录：`archives/l/librcd/0.1.14/`（conanfile.py + conandata.yml + manifest.yaml
  + notes.md + patches/ + test_package/）

## 功能概述

| 接口 | 说明 |
|------|------|
| `rcdGetRussianCharset(const char *buf, int len)` | 检测 `buf` 的编码，返回 `rcd_russian_charset` 枚举。`len=0` 时按 `strlen` 处理 |
| `rcd_russian_charset`（enum） | `RUSSIAN_CHARSET_WIN=0`(CP1251)、`KOI=1`(KOI8-R)、`UTF8=2`、`ALT=3`(CP866)、`LATIN=4`(ISO8859-1) |

产物：`lib/librcd.so.0.1.14`（`librcd.so` / `librcd.so.0` 为软链，soname
`librcd.so.0`）、`include/librcd.h`、`lib/pkgconfig/librcd.pc`。上游 `librcd.pc` 的
`Libs:` 写作 `-lrcd`，即链接的是 `librcd.so`（automake 直接采用 `librcd.la` 的基名），
配方因此声明 `cpp_info.libs = ["rcd"]`。

## OHOS 适配

**零源码逻辑改动**：4 个补丁全部是 autotools 生成脚本的可移植性修复，另有 1 处
构建期 shell 钉定（不改上游文件）。

| # | 内容 | 依据 |
|---|------|------|
| 0001 | `config.sub` 接受 `aarch64` 机器名与 `linux-ohos` OS | 2005 年版脚本不认识 aarch64，`./config.sub aarch64-linux-ohos` 报 `machine 'aarch64-linux' not recognized` |
| 0002 | `config.guess` 对 aarch64 直接回 `aarch64-unknown-linux-gnu` | 该脚本不认识 `uname -s` 报出的 `HarmonyOS`（报 `unable to guess system type`）；它自身的 LIBC 探测还要在 `umask 077` 建的临时目录里编译探针程序，OHOS 沙箱不允许 |
| 0003 | `configure` 里 `config.status` 的临时目录 `umask 077` → `022` | HMDFS 把 0700 目录落成 `drwx--S--- 2700` 且属主映射为共享属主，实测创建者随后 `touch` 仍 `Permission denied`；022 时目录为 `2751` 可写 |
| 0004 | `configure` 读 `cat "$srcdir/VERSION"` | 上游用 `cat VERSION`（相对当前目录），conan/Autotools 固定 VPATH 构建 → 取空 → `-version-info 0:0:0`（`librcd.so.0.0.0`）；修复后 `1:14:1`（`librcd.so.0.1.14`，soname 两种情形下都是 `librcd.so.0`） |

构建期 shell 钉定（`conanfile.py` 的 `_configure()`）：OHOS 上用
`CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh /system/bin/sh <srcdir>/configure ...`
显式跑 configure。原因见 `notes.md` 问题 5——profile 的 buildenv 把 `CONFIG_SHELL`
指向 hnp bash，而 configure 实际由 Toybox `/bin/sh` 执行；autoconf 在 Toybox 下选中
`ECHO='print -r --'`（Toybox 有 `print` 内建），该字面值随后在 bash 里失效，导致
libtool 生成时引号转义整段丢失、产出的 `libtool` 成为非法 sh
（`syntax error near unexpected token '}'`）。

## 上游测试

**上游无自动化测试套件，N = 0**（清点证据见 `0.1.14/test_package/MANIFEST.yml` 与
`0.1.14/reports/test-report.md`）：

- `make check` 是最小空实现：顶层 `Makefile.am` 只有 `SUBDIRS = src`，四个
  `Makefile.am` 全文无 `TESTS` / `check_PROGRAMS`；实测 `make check` 输出
  `Nothing to be done for 'check'.`；
- `examples/`（演示程序）与 `statgen/`（离线语料统计/生成工具）都不在 `SUBDIRS`
  内、目标体内 0 条断言，`statgen/doit` 还需 `dos2unix` + `iconv` +
  `ru_RU.KOI8-R` locale 与语料，属人工工具链；
- `examples/example.c` 与 `statgen/test.c` 是演示/工具程序，不是测试用例。

功能验证由 `0.1.14/test_package/test_librcd.c` 的 **34 项消费者断言**承担：同一段
俄文在 CP1251 / KOI8-R / CP866 / UTF-8 四种编码下的判定、`len=0` 与 `len=N` 两条
入参路径的一致性、6 字节短词、ISO-8859-1 拉丁文判定、返回码值域、幂等性与公开枚举
取值。

> `test_package` 的断言同时承担另一个作用：`src/russian_table.h` 是非 UTF-8 的字节
> 表，clang 会对它发 `-Winvalid-source-encoding` 警告（干净轮日志里 clang 汇总行为
> `14205 warnings generated`，约 1.42 万条）；五编码判定全对，
> 正是"编译器保留了原始字节值"的实证——否则会出现"编译零错误、检测全错"的假绿。

## 依赖关系

- 编译依赖：C 编译器 + libtool（configure/ltmain.sh/m4 均已随包预生成，**不需要**
  autoconf/automake）；无第三方库。
- 运行依赖：libc。

## 已知限制

- 上游 `CMakeLists.txt` 是 Windows 专用（首行 `FATAL_ERROR "Windows only, use
  autotools..."`），POSIX 平台只能走 autotools，本包即此路径。
- `librcd.spec` / `statgen/` / `examples/` 不参与构建与打包（上游 `SUBDIRS` 只有
  `src`）。
- 上游只认 CP1251 / KOI8-R / UTF-8 / CP866 / ISO-8859-1 五种编码，其他编码不在
  判定范围内（上游设计如此，非适配缺陷）。

## 参考资料

- Debian 源码包（本包源码来源）：https://packages.debian.org/source/librcd
- 上游源码镜像：https://github.com/RusXMMS/librcd
- 同族（老 autotools + config.guess/config.sub 可移植性）：`archives/a/aalib/1.4p5/`、
  `archives/a/abook/0.6.1/`、`archives/b/boolstuff/0.1.16/`
