# pngmeta 1.11 适配笔记

## 编译环境
- 构建系统: autotools（configure 由 autoconf 2.13 生成，Makefile.am 走 automake）
- 编译日期: 2026-09-20
- 编译器: clang (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built（conan-verify + W3 通过；upload 由合并后的发布流水线执行）

## 源码来源

| 项 | 值 |
|---|---|
| 官方上游 | https://pmt.sourceforge.io/pngmeta/ （作者 Dave Beckett，SourceForge 项目 `pmt`） |
| 源码 tarball | `https://downloads.sourceforge.net/project/pmt/pngmeta/1.11/pngmeta-1.11.tar.gz`（39860 B） |
| sha256 | `4f740d12cf5d803e321b2cb3afb1b1c1897f16cdd0167a56595db79fbbd8bc66` |
| 适配参考 | https://salsa.debian.org/debian-phototools-team/pngmeta.git （Debian 打包仓库，其 `debian/patches/` 提供了同类问题的修复思路） |

本仓库此前没有 pngmeta 的历史归档，W0b 无历史结论可继承。

## 编译步骤

```bash
# 依赖（W0：二者均已发布到 ohpcd 制品仓）
conan download libpng/1.6.58.3 -r=ohpcd --only-recipe
conan download zlib/1.3.2      -r=ohpcd --only-recipe

# 交叉编译（AutotoolsToolchain + AutotoolsDeps 提供 CC/CPPFLAGS/LDFLAGS/LIBS）
<srcdir>/configure --prefix=/usr/local --host=aarch64-linux-ohos --build=x86_64-linux-gnu
make
make check          # 上游 TESTS = test1 test2 test3 test4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pngmeta.c` 使用 `#define PNG_INTERNAL` + `png_handle_IHDR/tIME/tEXt/zTXt/iTXt/IEND`、`png_ptr->idat_size`、`png_ptr->mode`、`info_ptr->width` 等私有符号 | 上游写于 1998-2001 年，针对 libpng 1.0；libpng 1.4 起结构体私有化，`PNG_INTERNAL` 不再暴露内部头 | `patches/0001-pngmeta.c.patch`：删除自带的 `png_skip_till_end()`，改用 `png_read_png()` 一次读完（IDAT 之后的 tEXt/tIME 同样进 info），并全面改用 `png_get_IHDR` / `png_get_tIME` / `png_jmpbuf` / `png_destroy_read_struct` |
| 2 | `error: use of undeclared identifier 'ZLIB_VERSION'` | libpng 1.6 的 `png.h` 不再间接包含 `zlib.h`；旧代码依赖 `PNG_INTERNAL` 路径带进来的 zlib 声明 | 同一补丁中显式 `#include <zlib.h>` |
| 3 | `png_convert_to_rfc1123()` 在 libpng 1.6 中带 `PNG_DEPRECATED` 属性 | 1.5.4 起推荐改用带调用方缓冲区的接口 | 改用 `png_convert_to_rfc1123_buffer(char out[29], ...)`，并在其返回 0（tIME 字段非法）时显式报错退出 |
| 4 | RDF/XML 输出不合法：主语属性写成 `about=`，且 PNG 关键字里的空格被直接写进元素名 | 上游 bug（RDF 规范要求 `rdf:about`；XML 元素名不允许空白） | 同一补丁修正为 `rdf:about`，并新增 `html_quote_element()` 用于元素名（丢弃空白，与值的 `html_quote_string()` 区分） |
| 5 | `conan create` 中 `configure` 报 `invalid option` | 该 configure 由 autoconf 2.13 生成，不认识 `--datarootdir` 等后来才引入的选项，而 Conan 默认会注入 | `generate()` 中用白名单过滤 `tc.configure_args`，只保留 autoconf 2.13 支持的安装目录/三元组选项 |
| 6 | VPATH（out-of-source）构建下 `make check` 找不到期望输出 | 上游测试脚本用 `for dir in . ..` 定位 `*.xpt` 与样本 PNG，只看当前目录与上一级 | `build()` 在跑测试前把 `*.xpt` 与 `*.png` 复制到 build 目录 |
| 7 | 本机（x86 runner）无法执行动态链接的 aarch64 OHOS 二进制 | qemu-user 能跑静态 OHOS 二进制，但 OHOS musl 动态加载器在 qemu 下入口即 SIGSEGV（`/lib/ld-musl-aarch64.so.1` 本机亦不存在） | `build()` 先用一次真实调用探测目标二进制能否执行：能则跑 `make check`（CI 为 aarch64 原生构建机）；不能时只有在构建机与目标**架构不同**（`platform.machine()` vs `settings.arch`）才打 warning 跳过，同架构上跑不起来直接判构建失败，不伪装成通过。本地另用静态链接 + qemu 完整实跑了 4 项上游测试（见下） |
| 8 | CI 第 1 轮（#57964）`make check` 4 项全部 FAIL：`diff: Unknown option 'c' (see "diff --help")` | OHOS 的 `diff` 是 toybox 实现，只支持 unified 输出，不认识上游测试脚本里的 `diff -c`（context 格式）。二进制本身没问题：同一轮 CI 里 `build()` 的探针已在 aarch64 原生机上跑出与 `test1.xpt` 一致的输出 | `patches/0002..0005`：四个测试脚本的 `diff -c $OUTPUT -` 改为 POSIX 的 `diff -u $OUTPUT -`（toybox 与 GNU diffutils 均支持；giflib 5.2.2 已合并配方在 CI 上用过 `diff -u FILE -`）。期望输出与比对逻辑不变 |
| 9 | （预防）test_package 原有 `os.access(pngmeta, os.X_OK)` 断言 | HMDFS 模式位固定，`X_OK` 恒为 False，即使二进制能正常执行（E524） | 删除该断言，改以 ELF 头 + 实际执行结果判断；同时按 ELF `e_machine` 与宿主架构区分"异构无法执行 → SKIP"与"同构跑不起来 → FAIL" |

## 源码修改

| 补丁 | 改动 | 说明 |
|---|---|---|
| `patches/0001-pngmeta.c.patch` | +58 / -103 | 私有 libpng API → 公共 API 移植（问题 1/2/3/4） |
| `patches/0002-test1.patch` ~ `0005-test4.patch` | 各 +1 / -1 | 上游测试脚本 `diff -c` → `diff -u`（问题 8） |
| `patches/0006-test4.xpt.patch` | +1 / -1 | 上游 test4 的期望输出随 `rdf:about` 修正同步更新 |

补丁中不含任何平台宏（无 `__OHOS__`），改动对所有使用 libpng 1.6 的平台同样成立。

## 依赖版本

| 依赖 | 版本 | 来源 |
|---|---|---|
| libpng | 1.6.58.3 | ohpcd 制品仓（含 aarch64 预编译包） |
| zlib | 1.3.2 | ohpcd 制品仓 |

## 验证结果

### 上游测试（R51 清点 → 实跑）

上游测试入口：`Makefile.am` 的 `TESTS = test1 test2 test3 test4`（automake `make check`），无 `tests/` 目录，合计 **4 个**测试。

本机为 x86 runner，动态链接产物无法在 qemu 下执行（问题 7），因此用**静态链接 + qemu-aarch64** 完整实跑了同一份源码的全部 4 项上游测试：

```bash
$ qemu-aarch64 ./pngmeta --version
pngmeta 1.11 (built with libpng 1.6.58 and zlib 1.3.2)

$ ./test1   # tEXt, plain 格式     → PASS
$ ./test2   # zTXt, SOIF 格式      → PASS
$ ./test3   # ISO-8859, HTML 格式  → PASS
$ ./test4   # RDF/XML 格式         → PASS
=== SUMMARY: PASS=4 FAIL=0 ===
```

上游 4 项测试全部通过（4/4）。测试脚本改为 `diff -u` 后（问题 8）在同一环境复跑，仍为 4/4。

CI 侧为 aarch64 原生构建机，`build()` 会直接执行 `make check` 跑同一组测试。CI 第 1 轮（#57964）
正是在这里暴露了 toybox `diff -c` 的问题：4 项全部因 `diff: Unknown option 'c'` 失败，而非输出不符。

### test_package（消费者视角）

`test_package/test.py` 用 Python 现场构造一个带 tEXt（IDAT 前）与 tIME（IDAT 后）的 PNG，然后校验：

- artifact：二进制存在、ELF 头正确（2 项；不用 `os.access(X_OK)`，见问题 9）
- 可执行性探针：`--version` banner 含 `built with libpng`；探不通时按 ELF `e_machine` 与宿主架构区分——
  异构（x86 runner 上的 aarch64 产物）打印 `[SKIP]` 与原因，同构则判 FAIL
- plain 输出含两个 tEXt 键值与 `Modification Time`
- SOIF 输出含 `image-format{3}` / `image-width{1}` 与带长度前缀的键值
- RDF/XML 输出含 `rdf:RDF` 根元素与 `png:Image rdf:about` 主语
- HTML 输出为完整骨架且含 `<dd>` 包裹的关键字
- 非 PNG 输入退出码非 0

合计 14 条断言（artifact 2 + 运行时 12）。本地验证四种情形：qemu 可执行的 aarch64 静态版 → 全部通过；
conan 包内动态版（x86 宿主无法执行）→ `[SKIP]`；截断的同构 ELF → `[FAIL]`；`bin/` 缺失（模拟 CI 的 L1e）→ 断言失败。

## 注意事项

- pngmeta 是命令行工具（`package_type = "application"`），软件级 `commands.json` 已声明；包内不含库文件。
- 许可证沿用 libpng（`README` 明确 "distributed under the same copyright as the PNG Reference Library"），`README` 已安装到 `licenses/`。
- `--help` / `--version` 按上游设计输出到 stderr 并以退出码 1 结束，这是上游行为，未做改动。
---

**编译结束**: 2026-09-23 23:28
**最终状态**: built
