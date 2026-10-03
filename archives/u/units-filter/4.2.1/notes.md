# units-filter 4.2.1 适配记录

## 上游信息

- 名称：units-filter（Debian science 包，物理量表达式解析过滤器）
- 版本：4.2.1（首次适配，无后缀）
- 上游仓库：https://salsa.debian.org/georgesk/units-filter（Vcs-Git，同 control 文件声明）
- 源码包：Debian orig 归档 `units-filter_4.2.1.orig.tar.xz`（76 个文件），sha256 见 conandata.yml
- 许可证：GPL-3.0-or-later（COPYING）
- 构建系统：纯 Makefile（`src/Makefile` 构建二进制；顶层 Makefile 还驱动 sphinx 文档与 `gui/`，本次仅构建 `src/`）
- 语言：C++（flex 生成词法器 + bison 生成语法器 + `decimal.cc` 高精度十进制）

## 依赖（W0）

- 运行库依赖：`gmp/6.3.0.1`（`decimal.h` 包含 `<gmpxx.h>`，需 libgmpxx；该版本以 `--enable-cxx` 构建，同时提供 libgmp 与 libgmpxx）
- 构建工具：仅 `perl/5.42.2`（运行上游 `units-test.pl` 测试 harness）。flex/bison 已彻底移除：预生成的 `src/uniteslex.cc`（flex 2.6.4 生成）、`src/unitesparser.cc`（bison 3.8.2 生成）与 `src/FlexLexer.h`（上游 flex 2.6.4 头，与官方 tarball 字节一致）经 `export_sources`/`copy` 以字节拷贝进源码树（刻意不走 conandata 补丁——conan 2.30 的补丁读取按 UTF-8 解码，上游注释中的 latin-1 字节会导致 `UnicodeDecodeError: 0xe9`，真机已复现），`patches/0001` 仅把 `src/Makefile` 的两条重生成规则置空。背景：ohpcd 无 m4 配方（`conan list "m4/*" -r=ohpcd` 为 0），任何走源码构建的 flex/bison 边都会把 conancenter m4 拉进构建图，而其 configure 在 profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash`（沙箱内不可访问）下重执行失败，真机预检已连续两次倒在同一 m4 节点（包 ID `579a4b17…` 完全一致，与 flex 取 2.6.4.2 还是 2.6.4 无关——此前曾试对齐 flex 版本，无效）。vendoring 之后依赖闭包只剩 gmp（库，无工具依赖）与 perl（无工具依赖），m4 彻底出图
- 无 librecode 依赖：`src/Makefile` 仅当 `/etc/issue` 含 Debian 时才加 `-DRECODE_SUPPORT=1 -lrecode`；HarmonyOS 走非 Debian 分支，仅 `-lm -lgmp`（配方另加 `-lgmpxx`）

## 上游测试盘点（R51）

上游自带真实测试套件（非空壳）：

|  fixture  | 用例数 | 内容 |
|-----------|--------|------|
| src/test.1 | 49 | 基本换算与 SI 前缀 |
| src/test.2 | 11 | 复合单位、除法与幂 |
| src/test.3 | 5  | `-o` 输出格式选项 |
| src/test.4 | 12 | 容差/不确定度与 LaTeX 输出选项 |
| 合计 | 77 | 口径：按 `units-test.pl` 配对逻辑（非空行两两成对，`options=` 行只设标志不计用例） |

- 驱动：`src/units-test`（`cat test.1 test.2 test.3 test.4 | perl units-test.pl`），顶层与 `src/` 的 `make test` 均调用它
- 输出契约：每例一行 `OK ...`，失败为 `***ERREUR***` 块；`conanfile.py` 以该日志文件为唯一计数源（`OK` 行数=通过，`***ERREUR***` 行数=失败），经恒等式自检后输出 `HMBS_UPSTREAM_TEST_RESULT`
- 证伪说明：harness 逐例比对二进制首行输出与期望值；若二进制被换成恒失败桩，全例都会落入 `***ERREUR***` 分支并使构建失败，不存在静默通过；日志尾部会在构建输出中打印，可核对参照输出非空

## test_package（R34，非空壳）

`test_package/test_units_filter.sh` 对打包后的 `bin/units-filter` 做 7 条真实断言：6 条换算（`1 m`→`1`、`1 km`→`1000`、`1 h`→`3600`、`1 cm^3`→`1e-06`、`1 g`→`0.001`、README 例 `1.5e3 nN.m.s^-1`→`1.5e-06`）各验证输出首字段非空且含期望子串；第 7 条为阴性对照（非法表达式 `!!!not-a-unit!!!` 必须被拒绝输出 `ERROR` 开头，证明 harness 能捕获失败；二进制在语法错误时打印 `ERROR ...` 并以 exit 1 退出，故脚本必须无视退出码直接读输出文件）。脚本输出 `RESULT: P passed, F failed` 尾行，由 `test_package/conanfile.py` 解析为 `HMBS_TEST_PACKAGE_RESULT`。

## 适配改动（vendored 生成源 + 1 个 Makefile 补丁 + 配方内 flags）

预生成源经 `vendored/src/` 随 `export_sources` 以字节拷贝进源码树（刻意不做成补丁：conan 补丁读取按 UTF-8 解码，上游注释的 latin-1 字节会触发 `UnicodeDecodeError: 0xe9`，真机已复现；且固定上下文补丁在真机报 `source file is different - b'Makefile'`，对空白/版本漂移脆弱，故本轮起不再使用 conandata 补丁）。`src/Makefile` 的 flex/bison 重生成配方改为配方内 Python 行级置空（`_neutralize_makefile`：仅匹配 TAB 开头的 `flex`/`bison` 配方行，改写为 TAB 注释，要求至少命中 2 条否则抛错中断），上下文无关、容忍空白差异。生成工具链与版本可复核：winflexbison 2.5.25（实测 `win_flex.exe 2.6.4` / `bison (GNU Bison) 3.8.2`）按 Makefile 原命令（`flex -ouniteslex.cc unites.l`、`bison --verbose -o unitesparser.cc unites.y`）生成；产物无绝对路径（仅相对 `#line "unites.y"`），换行统一为 LF；FlexLexer.h 与上游 flex-2.6.4.tar.gz 内同名文件逐字节一致。其余 OHOS 适配在配方内完成：

1. `RECODE_SUPPORT=` 命令行覆盖，锁定非 Debian 分支（无需 librecode）
2. `LIBS="-L<gmp libdirs> -lm -lgmpxx -lgmp"` 命令行覆盖，补上 `decimal.cc` 所需的 gmpxx 链接
3. `CC/CXX` 经存在性校验解析：仅当 `tools.build:compiler_executables` 中的绝对路径真实可执行才采用，否则经 `CC/CXX` 环境与 `PATH` 回退（`cc/clang/gcc`、`c++/clang++/g++`），覆盖 `gcc/g++` 缺省；profile 曾指向真机不存在的 `/data/service/hnp/bin/clang++`（Error 127）
4. `CXXFLAGS` 追加 gmp 头文件 `-I` 路径与 vendored 头所在的 `src/` 目录 `-I`（供 `<FlexLexer.h>` 解析）
5. 仅构建 `src/`，跳过需 `python3-sphinx` 的文档与需 Qt 的 `gui/`（均为 Debian 二进制包 `units-master` 的范畴，不属本过滤器本体）
6. `build()` 内运行上游 77 例并硬门禁：任一失败即抛错中断，不吞结果
7. `package()` 仅安装 `bin/units-filter`、`licenses/COPYING` 与 man 页（若源码树含 `units-filter.1`）；`package_info()` 声明 `bindirs=["bin"]`，`libdirs/includedirs` 置空（application 包，R38 另在软件级目录提供 `commands.json`）

## 验证结果

- 本轮：完成未提交工作树；待 HMBS 后台真机预检（`conan create` 实测 77/77 与 7/7）后回填 PR 正文通过率
- PR 正文测试数字以真机预检日志为准，不估算、不照抄 README

## 已知限制

- `gui/units-master`（Qt 图形前端）与 sphinx HTML 文档不在本次交付内；`units-filter` 过滤器本体功能完整
- 归档含 `µ`（micro）字面量的用例以 latin-1 单字节存放，真机若出现编码相关失败将在日志中如实记录并归入 gaps，不改数字凑通过率
