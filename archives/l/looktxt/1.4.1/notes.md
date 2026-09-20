# looktxt 1.4.1 适配笔记

## 编译环境
- 构建系统: makefile（上游为纯 POSIX Makefile + 单文件 `looktxt.c`（4513 行），**无 configure/autotools**；init-build 的启发式把它探测成 autotools，已按实际改为 makefile）
- 编译日期: 2026-09-19
- 编译器: clang 15（来自 conan profile `tools.build:compiler_executables.c`；设备上为 Harmonybrew/OHOS SDK clang，目标 `aarch64-unknown-linux-ohos`）
- 状态: built（conan-verify 通过：G1/G2/G3 显示 PASS，G0 为知识图谱预查询、G4/L2/L4/L5 同轮执行，末行「配方验证通过」退出码 0；上游 `make test` 6/6 + test_package 15/15）

## 编译步骤
```bash
# 探索编译（模式 B）
cd $BUILD_SRC_DIR
make -j1 CC=<ohos-clang> NEXUS_NAPI=            # 产出 ./looktxt
# 实际命令（取自本地 build.log，该日志不随 PR 分发；此处内联引用以供复核）：
#   <ohos-clang> -O2 -o looktxt -g looktxt.c        ← 末尾无 -DUSE_NEXUS/-lNeXus（NeXus 后端已关）

# 上游回归（唯一入口，6 项检查）
make -j1 CC=<ohos-clang> NEXUS_NAPI= test       # ./looktxt --version + --verbose --test examples/*（5 个数据文件）
# → 末行 "Test OK"，退出码 0

# Conan 配方验证
python3 scripts/ohc-run.py conan-verify looktxt 1.4.1 --profile ohos-aarch64-device
# 内部 conan create 真实执行：
#   build(): make -j1 CC=<conf> NEXUS_NAPI= + 上游 make test（外层 `timeout -k 5 600`；"Test OK" 强校验，失败/挂起即中止）
#   test_package: sh test_looktxt.sh → 15/15 断言通过（真实执行已安装二进制）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make test` / 任何扫描含数据区的文本文件的调用无限挂起（设备 100% CPU，永不返回） | `file_scan()`（looktxt.c L2336–L2700）用 `char c`（L2382）承接 `c = lk_tolower(getc(...))`（L2419）并与 `EOF` 比较（L2422、`while (c != EOF)` L2692）。OHOS clang 目标 `aarch64-unknown-linux-ohos` 的 plain char **默认无符号**（实测 `CHAR_MIN=0`、预定义 `__CHAR_UNSIGNED__`），EOF(-1) 经 char 转换后变成 255，比较永不成立，扫描主循环失去唯一出口 | 补丁 `0001-looktxt.c.patch`：`char c` → `int c`（getc() 的标准返回域）。三组同机对照实验见「验证结果」；与 Debian 源码包的 `fix_infinite_loop.patch` **语义等价**（同一处 `char c` → `int c`；本包未取该补丁原文，故不作「逐字/逐字节」断言），单行、无平台宏（R8/PF5 合规） |
| 2 | 构建不可复现：Makefile 自动探测宿主 `/usr/include/napi.h` 头文件 | `NEXUS_NAPI = $(shell [ -f /usr/include/napi.h ] && echo -DUSE_NEXUS -lNeXus \|\| echo "")` —— 宿主装有 libNeXus 就会 `-lNeXus`，CI worker 与本机结果不同；且 `nexus` 未发布到 ohpcd 制品仓（W0），届时是断链 | 命令行传 `NEXUS_NAPI=`：make 命令行变量优先级高于 ifeq 内的普通赋值，因此宿主探测分支被彻底屏蔽，产物只依赖 libc。本笔记「编译步骤」一节内联的编译行即取证结果，不含 `-lNeXus`（本地 build.log 不随 PR 分发）；NeXus/HDF5 导出列为已知限制 |
| 3 | R33：Makefile 用 `${CC}` | CI worker 上 shell 无 `CC`，`make` 会退化为内建 `cc`（交叉编译静默失效） | 编译器取自 `self.conf.get("tools.build:compiler_executables")`，以 `make CC="<sdk-clang>"` 显式传入；绝不使用裸 `${CC}`/`${CFLAGS}` |
| 4 | 上游 `make install` 报 `install: inaccessible or not found` | 上游 install 目标依赖 `install(1)`，OHOS/toybox 不提供 | `package()` 直接 copy `looktxt` → `bin/`（chmod 0755）+ `LICENSE` → `licenses/` + `README.md` → `share/doc/looktxt/` |
| 5 | 消费者测试若按「非零即失败」断言会全错 | `main()` 返回的是**已处理文件数**：无输入 → rc=0（仅告警）、不可读文件 → rc=0、两个输入 → rc=2、覆盖保护触发时仍 → rc=1；`--test` 模式强制 ret=0 | 全部退出码断言按实测语义写（见 test_package 断言 02/05/06/07/12/14/15），并在 MANIFEST.yml 与本笔记中记录该语义 |
| 6 | 不加 `--fast` 时数值错位（`1.0 2.0 3.0 / 4.0 5.0 6.0` → `1 1 2 / 3 4 5`） | 上游慢路径（逐字符回填）既有缺陷：用**未打补丁**的源码 + `-fsigned-char` 亦逐字复现 → 与本次 EOF 补丁无关，非适配引入；上游 `make test` 为干跑模式，不比对数值，故上游自身从未暴露 | 不越界修改上游算法（超出适配范围）；数值保真断言统一走 README 推荐的 `--fast` 路径（`1 2 3 / 4 5 6` 逐字正确），缺陷在本地质量报告 `reports/test-report.md`（按 PR 禁止文件清单不随 PR 分发，此处不视为交付证据）与本条笔记中如实披露 |
| 7 | `search-url` 报告的 4 个「可用」URL 全是假阳性（Savannah 发布目录 404、XS4ALL 镜像为失效主页）；`init-build --url=…savannah…` HTTP 404 | 上游 GitHub 只到 v1.4，1.4.1 只在项目自托管处发布 | 由 Debian 源码包 `looktxt (1.4.1-3)` 的 `.dsc`（Homepage + orig sha256）反查官方源，并核验 GitLab tag `v1.4.1` 归档的 sha256 与 Debian `.dsc` 为 orig tarball 记录的哈希相同：`a586e12a8706cd3e49e8ce836593720f3824e84cb8fd8d3f22f40987b778aac8`（344832 字节，凭据 `https://deb.debian.org/debian/pool/main/l/looktxt/looktxt_1.4.1-3.dsc` 的 Checksums-Sha256 段，另见 #13）（R39：官方源，非二次分发） |
| 8 | 本地 CI 门禁（`ci/conan/build_and_test.sh`）L1 失败：`NotADirectoryError: .build-cache/predl_cache/acb8fbe0_looktxt/-/archive/v1.4.1/looktxt-v1.4.1.tar.gz`（同一配方在 conan-verify 下 G1/G2/G3 PASS、整体「配方验证通过」） | conandata.yml **注释**里写了项目主页裸 URL，而它是 `sources.url` 的严格前缀；预下载步骤先按正则抓出全部 URL（含注释），再对每个 URL 执行 `content.replace(url, 'file://<缓存文件>')`，注释 URL 在文件中先出现 → 真实 URL 被改写为 `file://<GitLab 主页 HTML><剩余路径>` 这种不存在的路径 | 注释中不保留任何 `sources.url` 前缀型裸 URL（主页信息移至软件级 README.md 与 manifest.yaml，二者不被门禁解析）；`conandata.yml` 顶部写下该约束的显式提醒。经验：conandata.yml 内任何一处 URL 文本都会被视为下载源 |
| 9 | 首次 `finish` 在 Step 4 conan-verify 抛 `ConanException: Patch file does not exist: .../0001-fix-eof-infinite-loop-int-c.patch`，W3 因此未执行（无 `.ci-result.json`） | finish Step 1 的 `refresh-patch --auto` 以 work 目录的编辑追踪器（`.edit-tracker.json` 的 `edited` 永久累积，基线不刷新）为输入，按 `{序号}-{变更文件路径}` 规则重新生成并**改名**补丁（`0001-looktxt.c.patch`，内容与手工命名版逐字节相同），但不改 `conandata.yml`；同时把 manifest 的 `patch_classification` 重置为工具默认（`type: auto` / `platform_only: True` / `guard: pending`） | conandata.yml、manifest.yaml、test-report、PR 正文统一改用工具生成的规范名，使 finish 可幂等重跑（重跑后 `patch_generation` 仅时间戳/work-hash 变化，补丁名与内容稳定）；`patch_classification` 在最后一次 finish 之后人工回填为 `portability / false / none` 且不再重跑（先例：`archives/i/is_utf8/1.4.1` notes P3） |
| 10 | W4 独立审计（提 PR 前）判 P1：全部交付文档把死循环的位置写成 `data_get_double()`，与源码事实矛盾 | 早期定位时把两件事混为一谈：`data_get_double()`（L2056–L2154）确实有 README 所说的 fast/slow 两条数值路径（L2075 `fscanf` 快路径 / L2108 `fread+sscanf` 慢路径），但它**不含任何 getc/EOF**；全文件唯一的 `getc()` 在 `file_scan()` 的扫描主循环里（L2419），唯一 `char c;` 在 L2382。审计代理重新下载官方归档、grep 函数边界后指出矛盾 | 按官方归档逐处核对并改正：notes/manifest/conandata/软件级 README/test-report/PR 正文/DRAFT-8543-plain-char-* 统一写 `file_scan()`；同时补做机制级实验（下节三组对照），把「结论来自实测」而不是「来自函数名猜测」写进证据链。补丁本身不受影响（内容、行号、上下文均正确），故属文档与源码矛盾而非欺骗（R52 一致性） |
| 11 | 交付文档中 `patch_type: "bugfix"` 与 code_style §12（`patch_type` 固定 `"portability"`）不符，`patch_description` 也是多行折叠段而非空一格词组 | 只按「这是上游 bug」的直觉取值，未对照 §12 与同类归档的实际写法（实测本仓库 conandata.yml 的 `patch_type` 取值：全仓 `portability` 6406 次 vs `bugfix` 253 次；`archives/a/*` 611 vs 38，少数包仍写 bugfix 属存量差异） | 改为 `patch_type: "portability"`（plain-char 符号性是实现定义行为，属跨平台可移植性缺陷，与 §12 口径一致）+ 单行 `patch_description`；长段论证保留在 notes.md（随 PR 分发）与本地 reports/test-report.md（不随 PR 分发）中 |
| 12 | W4 复审（改正 #10 之后）verdict=pass / P0=0 / P1=0，但留 2 条 P2：知识草稿 `DRAFT-8543-refresh-patch-rename-conandata-desync.md` 仍写回填分类为 `bugfix`（与已改的 conandata/manifest 不一致）；`test_looktxt.sh` 只用 `set -u` 却未像同类归档那样留下偏离说明 | 改正 #10 时只扫了交付正文，没扫草稿里的历史叙述；测试脚本的 `set -e` 取舍是功能必需（断言要观察非零退出码、`grep -c` 命中 0 次返回 1），但缺 NOTE 会让评审误判为不合规 | 草稿改为 `type: portability` 并注明取值依据（§12 固定口径 + 与 `patch_type` 同值）；测试脚本补 `NOTE: deliberately not set -e`（沿用 `archives/u/unifdef/2.12`、`archives/x/xa/2.4.1` 同一写法与理由），仅注释变更，改后用同一已安装二进制重跑消费者套件（`PATH="<conan package>/bin:$PATH" sh test_looktxt.sh`）仍 **15 passed / 0 failed**，退出码 0；同时把 notes 里指向不随 PR 分发的 `reports/test-report.md` 的引用改为自解释（标注本地报告 + 逐条断言标题内联到本文件） |
| 13 | W4 第三轮（终版快照）判 **P1**：`notes.md` 把输出格式数写成「7 种 / 格式表共 7 项」，与源码矛盾；另有 2 条 P2（Debian 哈希相等主张缺凭据；版本级 `manifest.yaml` 的 `L2056–L2158` 未与 notes 同步） | 上一轮把「6 种」改成「7 种」时，依据是上游 looktxt.c **L70 的文件头注释**（只列 Matlab/Scilab/IDL/XML/HTML/Octave/Raw）——那是过期注释，不是格式表项数：`NUMFORMATS` 为 13（L474），`Global_Formats` L487–L646，默认构建下 Name 非 NULL 的是 **8** 项（多出 L600 的 **YAML**），`print_usage()`（L2317–L2320）逐项打印这些非 NULL Name。教训与 #10 同源：**不能拿注释当事实，要以二进制实际宣传/行为为准** | 用设备实测重写口径：`--help` 的格式行逐字抄入本笔记，8 种格式逐个 `-f <FMT>` 跑通（8/8 生成产物、退出码=已处理文件数），并同步 README/commands.json/软件级 manifest 的格式清单（补 YAML）；哈希凭据补实：从 `https://deb.debian.org/debian/pool/main/l/looktxt/looktxt_1.4.1-3.dsc` 的 `Checksums-Sha256` 段取到 `looktxt_1.4.1.orig.tar.gz` = `a586e12a…778aac8`（344832 字节），与本包固定值同一 ⇒ 同一份字节内容（URL 不写进 `conandata.yml`，避免 #8 的前缀/多 URL 陷阱，凭据链接放在 notes/README）；`manifest.yaml` 的函数边界同步为 `L2056–L2154`；另按 P3 建议加固配方（conf 未提供 C 编译器时在 `build()` 里抛 `ConanException` 硬失败（与 `validate()` 用 `ConanInvalidConfiguration` 处理设置不兼容是两条不同通道），而不是静默回退 PATH 上的裸 `clang`；上游 `make test` 外层加 `timeout -k 5 600` 使「补丁失效 → 挂起」变成干净诊断而不是占满 CPU 到 CI 外部 kill），加固后 `conan create` + `conan test` 全绿 |

## 源码修改

仅 1 个补丁（正确性/可移植性修正，无平台宏，不改变任何上游断言或用例）：

- `patches/0001-looktxt.c.patch`（原名 `0001-fix-eof-infinite-loop-int-c.patch`，见问题表 #9）
  - **修改文件**: `looktxt.c`（`file_scan()` 内的接收变量声明，第 2382 行；函数体 L2336–L2700）
  - **修改原因**: OHOS clang（target `aarch64-unknown-linux-ohos`）的 plain char 默认无符号，`char c` 无法表达 EOF，`file_scan()` 的扫描主循环（L2419 读字符、L2422 与 L2692 判 EOF）在文件结尾失去出口；`make test` 与任何需要扫描数据区的调用因此永不返回
  - **修改内容**: 单行 `char c;` → `int c;`（hunk 上下文逐字节保留；与上游/Debian 的同名修复语义等价）

未修改 `Makefile`、`examples/`、`README.md`、`LICENSE`；补丁新增行不含 `__OHOS__` 等平台宏，未注入任何系统前缀（PF5/PF6/R49 合规）。

## 依赖版本

无第三方依赖（W0：上游 README 自述 "pure C code, with no dependency"，产物仅链接系统 libc；未声明 `requirements()`（依赖集为空））。
构建期宿主工具：`make`、`clang`（由 Conan profile 提供）。可选 NeXus/HDF5 后端因 `nexus` 未发布而显式关闭（见问题 2）。

## 验证结果

```text
# 上游回归（make test：1 次 --version + 5 个 examples 文件 --test 干跑）：6/6 PASS
./looktxt 1.4.1 (23 Mar 2022) by Farhi E. [emmanuel.farhi@synchrotron-soleil.fr]
VERBOSE[file_write_target]: file 'examples/socket.off': classify 1 section:
 looktxt_root: {  socket  socket_1 }
Test OK
looktxt-upstream-suite-exit=0

# 补丁必要性三组同机对照（同一设备、同一 clang、同一输入 examples/Al.lau，68137 字节，stdin=/dev/null）
#   编译命令统一为 <ohos-clang> -O2 [-fsigned-char] -o looktxt -g looktxt.c
A. 未打补丁 + 默认编译选项        → timeout 25 rc=124（挂起）；插桩：getc 返回 -1 时 char 接收变量值为 255，pos 恒为 68137，额外空转 1.93e6 次后仍不退出
B. 未打补丁 + -fsigned-char       → rc=0（正常完成）→ 证明症状确由 plain char 的符号性/EOF 不可表示引起，而不是文件内容或其它逻辑
C. 打补丁（int c）+ 默认编译选项  → rc=0，上游 make test → "Test OK"；插桩：EOF 处接收变量值即 -1，循环恰好读 68138 次（= 文件大小 + 1）后退出
   工具链事实：clang -dumpmachine = aarch64-unknown-linux-ohos，limits.h 实测 CHAR_MIN=0，预定义 __CHAR_UNSIGNED__

# test_package 功能断言（sh test_looktxt.sh）：15/15 PASS，逐条标题（与脚本内 ok/nok 文案一致）：
#   01 packaged looktxt is on PATH
#   02 --version exits 0
#   03 --version prints '1.4.1 (23 Mar 2022)'
#   04 --help exits 0 and documents --test
#   05 no arguments warns 'No file to process' and exits 0
#   06 missing input reports 'can not be accessed', status 0 files processed
#   07 two inputs exit with status 2 and both outputs are written
#   08 Matlab export carries both data sets (1 2 3 / 4 5 6)
#   09 default format is Matlab and 't1.txt' becomes 't1_txt.m'
#   10 Raw export is stamped 'generated by looktxt.c 1.4.1'
#   11 XML export contains the source-file element
#   12 -o out.m writes the requested file and function name
#   13 -b binary block holds 200 doubles (1600 bytes)
#   14 overwrite guard triggers without -F and clears with -F
#   15 --test exits 0, classifies the input and writes no output file
# （逐条断言代码即 test_package/test_looktxt.sh 本身，随 PR 分发；reports/test-report.md 为本地质量报告，不随 PR 分发）
# conan-verify：G1/G2/G3 PASS，G0（知识图谱预查询）/G4/L2/L4/L5 同轮执行，末行「配方验证通过」退出码 0（conan create 干净复现）
# 文档改正之后的端到端复跑（同一设备、同一 profile，2026-09-19 19:58）：
#   conan create archives/l/looktxt/1.4.1 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
#                --build=missing --user=ohpcd --channel=stable          → 退出码 0
#     · "Apply patch (portability): 0001 looktxt.c file_scan widen EOF receiver char to int ..."
#     · build() 内上游 make test → "Test OK"，looktxt-upstream-suite-exit=0
#     · create 自带 test_package → "looktxt test_package: 15 passed, 0 failed"
#     · Created package revision 79b7af2285c9220e5206719e4e63b0d3
#   conan test archives/l/looktxt/1.4.1/test_package looktxt/1.4.1@ohpcd/stable → 再次 15 passed / 0 failed（退出码 0）
# 配方加固后的最终复跑（W4 第三轮之后；同一设备同一 profile）：
#   build() 实际执行行（conan 日志逐字）：
#     RUN: timeout -k 5 600 make -j1 CC="/storage/.../ohos-sdk@26.0.0.18/native/llvm/bin/clang" NEXUS_NAPI= test > upstream-tests.log 2>&1; rc=$?; ...
#   → "Test OK" + "looktxt-upstream-suite-exit=0"，CREATE 退出码 0，包修订 113feb8b19967a868d1d011fa80bbbc2
#   → create 内嵌 test_package 与随后显式 `conan test` 均为 15 passed / 0 failed
# 最终态复跑（W4 第四轮文案改正之后；共享 conan 锁此后长期被同机他人任务占用，故这是最后一次完整的 conan create 证据）：
#   conan create → 退出码 0、
#   "Apply patch (portability)" + `timeout -k 5 600 make … test` + "Test OK" + suite-exit=0，
#   包修订 5b65f66e05c797a67a768e7ff9424d1a（修订号随配方/元数据变化，属正常 cache 行为；
#   79b7af22 / 113feb8b 分别是「文档改正后」与「配方加固后」两个里程碑的修订），
#   create 内嵌 test_package 与随后显式 conan test 均 15 passed / 0 failed
# 5b65f66e 之后仅追加了「注释/文档字符串」级改动（conanfile.py 的 header 说明与 build() 注释、
#   test_looktxt.sh 的 §10 说明注释、MANIFEST/notes/README 文案），不改任何执行语句：
#   设备侧复核 `python3 -m py_compile conanfile.py` → 0、`sh -n test_looktxt.sh` → 0、
#   四个 YAML/JSON 文件解析 → 0、两个 .kv 字段解析 → 0（同一轮跑完，见提交 86b22cabe）。
#   再跑一次完整 conan create 只因共享 conan 锁被同机他人任务长期占用而未执行；若执行，修订号会继续前移（缓存正常行为），构建/测试语句与上述结果不变。
# 格式矩阵实测（本轮复核，同一设备、同一已安装二进制，输入 "x = 1 2 3 / y = 4 5 6"，--fast）：
#   --help 宣传 8 种：Available output formats are (default is Matlab): "Matlab" "Scilab" "IDL" "XML" "YAML" "HTML" "Octave" "Raw"
#   逐一执行 -f <FMT>：8/8 退出码=1（= 处理了 1 个文件）且各自生成 t1_txt.{m,sci,pro,xml,yaml,html,m,txt}，文件头模板与源码 Global_Formats 一致
#   附带发现（与本次补丁无关的上游健壮性问题）：`-f <未知格式> -o /dev/null` 会让 looktxt 以 SIGTRAP 结束（rc=133），
#   机制（按官方源码核对）：`try_open_target()` L1325 `parts.Path = str_free(parts.Path)` 后重新赋值，而 `parts` 是按值传入的，调用方 `file_open()` 里的 `parts.Path` 因此悬垂 → L1825–L1827 的诊断行打印已释放内存，L1850 `parts = fileparts_free(parts)` 再释放一次（UAF + 双重释放）；
#   同一命令第二次执行时因 cwd 已生成 null.m 而落入覆盖保护分支（rc=1，不崩溃）。消费者测试未覆盖该畸形 -o 路径。
```

## W4 预提 PR 独立审计（五轮，终判 pass）

| 轮次 | 终判 | 要点 |
|---|---|---|
| 1 | fail（1 P1） | 交付文档把 EOF 死循环的位置写成 `data_get_double()` → 见问题表 #10 |
| 2 | pass（0 P0/0 P1，2 P2） | 草稿里的历史叙述未同步、测试脚本缺 `set -e` 偏离说明 → 见 #12 |
| 3 | fail（1 P1，2 P2） | 输出格式数写成「7 种/共 7 项」（照抄上游 L70 注释）；Debian 哈希相等主张缺凭据；版本级 manifest 行号未同步 → 见 #13 |
| 4 | fail（1 P1，5 P2） | 异常类名旁注不实、EOF 比较漏 L2464、门禁正则原文被转义吞掉、`EXTRA_CFLAGS` 回退命令对本 Makefile 无效、格式清单未在 README/配方同步 |
| 5 | **pass（P0=0 / P1=0 / P2=3 / P3=5）** | 审计代理自行重放补丁 hunk、核对全部 `L<行号>` 引用与 8 格式清单；结论 JSON 随 PR 入库在 `reports/audit-result.json` |

第 5 轮的 3 条 P2 已在同一批提交里落实（Debian 等价性从「逐字」降级为「语义等价 + 未取原文」、草稿里指向未入库文件处补标注、`build()` 异常类旁注改为可由 PR 内证据支撑的说法），因此入库的 `audit-result.json` 对应的快照比 HEAD 早一个「仅文案」提交，逐条差异可见 `git show 86b22cabe`。

明确保留的建议（附理由，供评审复核）：

1. `knowledge_gained` 的 `knowledge_ref` 仍写在条目文本末尾而非独立键——`check-knowledge-gap` 以文本匹配 `knowledge_ref|ref:|reference:` 判定引用，改成结构化键需先确认工具与新结构的解析契约，本包不在此任务里改工具口径（现 10 条全部有 ref，`unreferenced=0`）。
2. `test_looktxt.sh` 首行 `#!/bin/sh`（§6 示例为 zsh）、且只 `set -u`（§7 要求 `set -euo pipefail`）——设备 toybox 与 CI worker 双跑的必需取舍，理由已写在脚本 NOTE 里，与 `archives/u/unifdef/2.12`、`archives/x/xa/2.4.1` 同口径。
3. 未跟踪的 `reports/conan-create.log` / `reports/w3-local-ci.log` 仍保留改正前的 `patch_description` 与 `patch_type: bugfix` 字样——它们是 W3 时刻的时间序记录，`.ci-result.json` 的 `log_sha256` 绑定后者，任何“事后美化”都会破坏门禁完整性校验；两份日志按 `.gitignore` 不入库。
4. `patch_generation.source_orig_dir/work_dir` 的设备绝对路径保留（见「注意事项」）。
5. `-f <未知格式> -o /dev/null` 的上游 UAF/双重释放只做披露不修（改动上游 `file_open()`/`try_open_target()` 的内存所有权超出适配范围；本包测试不覆盖该畸形入参路径，已在「验证结果」给出复现行）。

---

## 交付物

| 文件 | 说明 |
|------|------|
| bin/looktxt | 文本数值域 → Matlab/IDL/Scilab/Octave/XML/YAML/HTML/Raw 转换器（arm64 ELF） |
| licenses/LICENSE | GPL-2.0 全文（上游 LICENSE 原件） |
| share/doc/looktxt/README.md | 上游使用说明原件 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/l/looktxt/commands.json` 声明（R38）。
- 本 `manifest.yaml` 的 `patch_generation.source_orig_dir/source_work_dir` 是 `refresh-patch` 自动写入的设备侧构建目录（`/storage/Users/currentUser/...`），属工具遥测而非配方配置：仓库内 1952/6977 份版本级 manifest 带同类路径，删除只会让补丁再生成信息不完整；构建真正读取的是 `conandata.yml` 的官方 HTTPS URL 与 `patches/` 相对路径。
- 退出码语义特殊（= 已处理文件数），脚本化调用应判断产物文件而非退出码；`--test` 为干跑，不写文件。
- 输出格式能力（实测口径，非上游注释口径）：默认构建（`NEXUS_NAPI=` 置空，`USE_MAT`/`USE_MEX`/`USE_NEXUS` 均未定义）下，格式表 `Global_Formats`（looktxt.c L487–L646，`NUMFORMATS 13` 定义在 L474）里 Name 非 NULL 的 **8 项全部可用**：Matlab / Scilab / IDL / XML / **YAML** / HTML / Octave / Raw；`print_usage()`（L2317–L2320）逐项打印这些非 NULL Name，故 `--help` 宣传的正是这 8 种。其余 5 个槽位（MATfile/HDF L510、MEX L516、NeXus5/HDF5 L522、NeXus4/HDF4 L524、NeXus/XML L526）在本构建中 Name 为 NULL（对应后端未启用），`-f NeXus` 不可用。注意上游 looktxt.c L70 的头注释只列 7 个名字（漏 YAML），那是过期的文件头注释、不是格式表项数，本包文档不沿用该计数。
- 批量/大文件调用建议 `--fast`：既避免上游慢路径的既有数值缺陷（问题 6），也是上游 README 的推荐口径。
- 首次执行新二进制时设备可能弹安全确认框（R7）；本任务的设备验证已在解锁状态下完成。
- 上游无 releases/CHANGELOG，版本串内嵌于源码 `#define VERSION "1.4.1"` / `DATE "23 Mar 2022"`，`--version` 因此恒打印编译期版本。
---

**编译结束**: 2026-09-19 17:35
**最终状态**: built
