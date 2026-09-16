# cwebx 3.52 适配笔记

## 编译环境
- 构建系统: makefile（raw Makefile，**不是** autotools）
- 编译日期: 2026-09-12
- 编译器: /data/service/hnp/bin/clang（Conan profile `tools.build:compiler_executables`）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 源码与来源确证

| 项 | 值 |
|---|---|
| URL | `http://wwwmathlabo.univ-poitiers.fr/~maavl/CWEBx/cweb-x3.52.tgz` |
| SHA256 | `92e57b4414388743bd0b91d81c91bea4645a8b04c8f744754b0855e90934186b` |
| 大小 | 255128 字节，`file` 判 gzip compressed data |
| 成员 | 27 项，顶层 `cweb-x3.52/` |
| 版本 | `intro.inc:1` `\def\currentCWEBxversion{x3.52}`；`intro.inc` 末 `@d version_string "x3.52"`；`ctanglex --version` 实跑输出 `This is CTANGLE (version x3.52)` |

**为什么只有这个源**（R39 取证过程）：

- 任务 API 的 `url` 字段为 null，需自行确认官方源。
- `ohc-run.py search-url cwebx 3.52` 报的 4 个「✅ 可用」URL 全部不可用：
  `download.savannah.nongnu.org/releases/cwebx/…` 302 到 `nongnu.niranjan.co/…` 后 **404**，
  且 `savannah.nongnu.org/projects/cwebx` 明确返回 `Group 'cwebx' does not exist`；
  `waterlan.home.xs4all.nl/cwebx/…` 302 到 `notxs4all.home.xs4all.nl` → `mijnweb.site`
  「Pagina niet gevonden」HTML 页（curl 拿到 12477 字节 `ASCII text`，`file` 判非归档）。
  即 search-url 的可用性标记与「Official」标签都不能作为选源依据。
- CTAN 收录 cwebx，但 JSON/包页给出 **Version 3.04**（`https://ctan.org/pkg/cwebx`），版本不符。
- 作者页 `http://wwwmathlabo.univ-poitiers.fr/~maavl/CWEBx/` 存活（HTTP 200），页面内相对链接
  `cweb-x3.52.tgz` 即目标包。该主机 443 端口证书 CN 为 `www-math.sp2mi.univ-poitiers.fr`
  且链不完整，四个主机名变体的 https 全部 `SSL certificate problem: unable to get local
  issuer certificate`，因此**没有可用的 https 官方源**。

**独立字节佐证**：Debian 的 `cwebx_3.52.orig.tar.gz`（`https://deb.debian.org/debian/pool/main/c/cwebx/`，
Version `3.52-3`，Format 3.0 quilt）与上述上游包 **SHA256 完全相同**、大小相同、成员布局相同。
Debian 的 URL 本身不能写进 conandata（PF7 把 `deb.debian.org` 无条件判为「Debian 下游重打包源」），
这里只用作上游包真实性的第三方印证。

**R39/PF7 例外留痕**：conandata 与版本 manifest 都只有官方 http 源，会命中 PF7「明文 http 源」。
按 PF7 自身指引（「确属官方托管例外须 PR 说明并 `--no-preflight` 跳过」）处理，并在最终 HEAD 上
手工执行 PF1–PF9+R52 自证，结果与命令记录在 PR 正文。

## 编译步骤（实际执行）

```bash
# 探索阶段（模式 B）
python3 scripts/ohc-run.py init-build cwebx 3.52 \
  --url='http://wwwmathlabo.univ-poitiers.fr/~maavl/CWEBx/cweb-x3.52.tgz'
# init-build 把 BUILD_SYSTEM 判成 autotools（被 ./configure 桩脚本误导），已改回 makefile
source .build-context-cwebx-3.52 && cd $BUILD_SRC_DIR

make ctanglex CC=clang -j1     # 由随包 ctangle.c + common.c 编出自举工具
./ctanglex --version           # This is CTANGLE (version x3.52) —— 未签名即可执行
make cweavex CC=clang -j1      # 触发 ./ctanglex cweave 生成 cweave.c 再编译
./cweavex --version            # This is CWEAVE (Version x3.52)
make install prefix=<staging>  # 生成 bin/ctanglex bin/cweavex
```

tar 保留了 2007–2012 年的原始时间戳，随包生成物（`common.c`/`common.h`/`ctangle.c` 均为
2012-06-25 15:35:17）不早于其 `.w`/`.inc` 依赖，`make -n ctanglex` 直接回答
`make: 'ctanglex' is up to date.`，因此不会在自举前误触发 `./ctanglex`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 生成 Autotools 骨架，`conan-init` 跟着产出 `autotools.configure()` 配方 | 发行包的 `./configure` 只有 82 字节：`echo "No configuration needed for CWEBx, just run the command 'make'"`；探测按「有 configure 即 autotools」误判 | 按 raw Makefile 手写 `build()`/`package()`，并纠正 `.build-context` 与版本 manifest 的 `build.system` |
| 2 | 默认 `make`（`all: cweb doc listings`）需要 TeX | `doc`/`listings` 会 `tex manual.tex` 并排版源码清单，平台无 TeX | 只构建 `cweb` 目标（`ctanglex` + `cweavex`） |
| 3 | 自举需要运行刚编出的 `./ctanglex` | OHOS 要求可执行 ELF 带 `.codesign`；早期 cweb 归档据此加了 `binary-sign-tool` 步骤 | 实测**无需签名**：`llvm-readelf -S ctanglex` 显示链接产物已含 `.codesign`（PROGBITS @0x10000, 0x1000）与 `.note.ohos.ident`，且 `ci/` 全目录无签名步骤。故配方不调用签名工具，避免对已签名产物重签 |
| 4 | `make install` 无 DESTDIR 语义 | 上游 install 只 `$(CP) ctanglex cweavex $(prefix)/bin` | 用命令行 `prefix=<package_folder>` 覆盖（make 命令行变量优先于文件内赋值），`install` 的 `test -s $(prefix)/bin || mkdir $(prefix)/bin` 自建目录，**无需补丁** |
| 5 | `make cautiously` 返回 rc=2 | 见下节 | 不改上游 Makefile；改为单独实跑等价验证并如实报告 |

## 上游自举自检 `make cautiously` 的失败根因

`make cautiously` 按发行包默认参数实跑 **rc=2**，日志 1785 行，失败点是**第一个**比较
`diff common.c SAVEcommon.c`（日志中只有一条 `diff` 回显即报错）。逐项量化：

| 比较 | 差异行 | 忽略空白后 | 重生成物含 `/*:N*/` | 随包文件含 `/*:N*/` |
|---|---:|---:|---:|---:|
| common.c | 1734 | 694 | 84 | 0 |
| common.h | 141 | 113 | 21 | 0 |
| ctangle.c | 1909 | 737 | 86 | 0 |

根因在源码里可直接读到：`ctangle.w:790`

```
if (line_output) C_printf("/*:%d*/",cur_val); @+ else C_newline();
```

而 `line_output` 即 `flags['l']`。随包的 `common.c`/`common.h`/`ctangle.c` 是用 **`-l`**
（不输出 `#line` 与段号注释）生成的，而 Makefile 的 `cautiously` recipe 硬编码
`./ctanglex common $(CCHANGES)`，**不经过 `$(CTANGLE) = ./ctanglex $(CTFLAGS)`**，所以命令行传
`CTFLAGS=-l` 也到不了那一行，默认参数下段号必然出现、逐字节比较必然失败。

用正确参数复现上游自验证（从干净解包目录实跑）：

```bash
./ctanglex -l common    # diff vs 随包 common.c  -> 0 行差异
                        # diff vs 随包 common.h  -> 0 行差异
./ctanglex -l ctangle   # diff vs 随包 ctangle.c -> 0 行差异
```

即随包生成物**可被本包编出的 ctanglex 逐字节复现**，自举链是自洽的；失败只是上游 Makefile
的 `cautiously` 少传了一个选项。另外 `cweave.c` 不随包提供，上游对它测的是 ctanglex 的确定性：
连续两次生成 `cweave.c` 得 2979 行且完全一致。

结论：不修改上游 Makefile（避免把上游缺陷固化成我们的补丁），在 `test_package/MANIFEST.yml`
与 PR 正文中按上述量化口径如实报告。

## 测试清点（R51）

单位严格分列，不混加：

| 套件 | 单位 | 原始清单 N | 实际执行 N′ | 结果 |
|---|---|---:|---:|---|
| `make check`（默认注册） | make 目标 | 1 | 1 | rc=0；正文仅 `@echo 'Did you expect a check from me?'`，**0 个断言** |
| `make cautiously`（可选，不在 `all` 内） | diff 比较 | 3 | 1 | rc=2 FAIL，第 1 个比较即失败（根因见上） |
| 等价自举验证 `-l` 重生成 | 文件逐字节比较 | 3 | 3 | PASS，差异均 0 行 |
| ctanglex 确定性（cweave.c） | 比较 | 1 | 1 | PASS，2979 行两次一致 |
| `examples/` 往返 | .w 程序 | 4 | 4 | PASS 4/4（wc / treeprint / wmerge / compare） |
| 端到端编译运行 | 程序 | 1 | 1 | PASS，`wc.w → wc.c → clang → ./wc README` 得 125 行 / 1121 词 / 6855 字符 |
| `test_package/test.sh`（适配后新增，鸿蒙特有） | 断言 | — | 10 | 见下节 |

`make check` 与 `make cautiously` 分属默认与可选套件，不合并计数；上游无测试入口的那部分
按「1 个目标 / 0 个断言」如实写，不以上游 0/0 为由省略消费者测试。

## 验证结果

`test_package/test.sh` 的 10 个断言（脚本自身打印 `[result] assertions passed: N`）：

1. `ctanglex --version` 横幅为 `This is CTANGLE (version x3.52)`
2. `cweavex --version` 横幅为 `This is CWEAVE (Version x3.52)`
3. `ctanglex hello` 产出非空 `hello.c` 且含 `#include <stdio.h>`
4. `@d GREETING "hello-from-cwebx"` 展开进 C 输出
5. 默认输出含 `#line` 行号映射
6. 默认输出含 `/*:N*/` 段号标记
7. `-l` 输出不含段号标记但保留代码
8. `cweavex hello` 产出含程序文本的 `hello.tex`
9. 提取出的 C 能编译出可执行文件
10. 该程序运行输出恰为 `hello-from-cwebx`

设计测试前先在设备上实跑过候选 `.w`，确认 `@f` 只是排版声明、不生成 typedef，因此没有把
`@f` 写成编译断言（会假失败）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ctanglex | 72064 | 从 .w 提取 C |
| bin/cweavex | 129408 | 从 .w 提取 TeX |
| share/texmf/tex/generic/cwebxmac.tex | — | CWEAVE 输出所需 TeX 宏 |
| share/texmf/tex/generic/cwebcmac.tex | — | 兼容模式附加宏 |
| share/texmf/tex/generic/cwebhmac.tex | — | 超链接可选宏 |
| share/man/man1/cweb.1 | — | 手册页 |

上游 `install` 只安装两个二进制，TeX 宏与手册页由配方按上游目录布局显式收录。
README 文件清单里提到的 `cweb.el` 实际不在发行包中，故不收录（与 cweb 4.12.2 不同）。

## 注意事项

- 与仓库既有 `cweb` 包**同域不同包**：`cweb` 是 Levy/Knuth 分支（`ctangle`/`cweave`），
  `cwebx` 是 van Leeuwen 分支（`ctanglex`/`cweavex`）。两者的补丁、签名结论与文件清单都不可互抄。
- 平台无 TeX，`cweavex` 的 `.tex` 产物无法在本机排版成 dvi/PDF；这不影响 `.tex` 生成正确性。
- 上游 `ctanglex --help` 不是帮助选项，会被当作文件名并触发 `! Usage:` fatal error；
  CI 的 L2 冒烟用 `--version`，两者都可用。
- `make cautiously` 失败后会残留 `SAVEcommon.c`/`SAVEctangle`，且已把 `common.c` 覆盖为重生成
  版本；复现该测试必须用独立解包目录，不能在被改写过的目录里做「前后对比」。
---

**编译结束**: 2026-09-12 03:11
**最终状态**: built
