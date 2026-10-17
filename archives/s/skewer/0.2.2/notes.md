# skewer 0.2.2 适配笔记

- 构建系统：**单个裸 Makefile**（无 configure / 无 CMake / 无 autotools，非 in-tree out-of-source）
- 语言：**纯 C++**（`src/*.cpp` 4 个 + `src/*.h` 4 个；**没有任何 .c 源文件**，
  候选台账里"c=4、cpp=4"把 4 个头文件当成了 C 源）
- 领域：NGS reads 的适配子修剪 / 质量过滤（生信 CLI），**与终端图像渲染无关**，
  不涉及 libpng / libjpeg / webp / sixel / 真终端能力
- 编译日期：2026-09-26  编译器：OHOS clang/clang++ 15.0.4（`/data/service/hnp/bin/clang++`）
- 构建主机：B 机（HarmonyOS PC aarch64，8C/31G），worktree `~/qzy/主理-63-skewer-0.2.2`
  分支 `feat/skewer-0.2.2`，`CONAN_HOME=$HOME/tmp/ch/home-skewer`
- 状态：`conan create` 绿（**1 个源码补丁** = `patches/0001-fix-char-eof-sentinel.patch`）
  + `conan-verify` G1/G2/G3 PASS（2026-09-26 打完 EOF 补丁后**重跑**过，非沿用旧判决）
  - 两处**构建系统**缺陷（S1/S2）仍是零补丁解法（make 变量覆盖 + package() 自 copy）；
  - 第三处是**运行期**可移植性缺陷（EOF 哨兵落进 plain char，奇数条 FASTQ 丢尾），
    只能改源码 ⇒ 见 §10。**§5/§6 的旧"零补丁/未定性"口径已被本节替换，以 §10 为准。**

---

## 1. 症状

上游 `https://github.com/relipmoc/skewer` tag `0.2.2`（**tag 无 `v` 前缀**）在
OHOS 工具链上有两处必然首错，且**都不需要读错误链就能定位**：

| # | 症状 | 位置 | 定性 |
|---|------|------|------|
| S1 | `make` 第一步就找不到编译器 | `Makefile:1` `CXX=g++`（简单赋值） | 构建系统层：烧死 GNU g++ 别名，OHOS 只有 clang/clang++ |
| S2 | `make install` 不可用 | `Makefile:47-48` `install: mv -f $(EXECUTABLE) /usr/local/bin` | 构建系统层：绝对路径烧死 + 无 PREFIX 变量 + 无 DESTDIR 支持 + 把产物**搬离**构建树 |

两处都属于"构建系统把宿主事实写死"，**不是** OHOS/工具链缺陷，也**不是**上游代码缺陷
（在 Linux+g++ 上游行为正常）。

## 2. 根因

- **S1**：GNU make 的变量优先级是「命令行 > makefile 内普通赋值 > 环境变量」。
  `CXX=g++` 没有 `override`，所以 `make CXX=<路径>` 可以直接接管——这是 make 官方
  推荐的"换编译器"姿势，也是本配方采用的姿势。
- **S2**：`install` 规则的目标目录是硬编码字面量，既不走 `$(DESTDIR)` 也不走
  `$(PREFIX)`，conan 的 `package_folder` 无法注入；而 `mv`（不是 `install -m755`）
  会把 `skewer` 从构建树搬走，即使目标存在也会破坏"构建产物可复验"。
  实测 `make -n install DESTDIR=<dir>` 仍原样打印 `mv -f skewer /usr/local/bin`
  ⇒ **DESTDIR 完全被忽略**（GNU make 对 recipe 行不做变量替换以外的处理）。
- **第三个坑（CI 复核确认）**：`Makefile:3` 的 `CXXFLAGS?=-c` 只在变量未定义时生效。
  CI 的 Conan 构建环境已导出 `CXXFLAGS=-fPIC -O2`，所以 `?=` 默认值被跳过；Makefile
  随后追加 `-O2`，但编译规则 `Makefile:35` 没有显式 `-c`，结果变成
  `clang++ -fPIC -O2 -O2 src/main.cpp -o src/main.o`，直接拿单个源文件链接。
  `cFQ`、`cMatrix`、`cParameter` 与 `gz*` 的未定义符号由此产生，不能据此单独推断缺 zlib。
  配方现在保留继承的 CXXFLAGS 并在缺失时补入 `-c`；链接规则 `Makefile:32` 不使用
  CXXFLAGS，因此 `-c` 仅影响对象编译。

## 3. 最小复现

在 B 机上对**未修改的上游源码树**执行（三条命令，逐条实测原文见 §7 日志路径）：

```bash
tar xzf skewer-0.2.2.tar.gz && cd skewer-0.2.2

# S1：默认 make
make -j1
#   g++ -c -O2 src/main.cpp -o src/main.o
#   make: g++: No such file or directory
#   make: *** [Makefile:35: src/main.o] Error 127

# S2：install 目标（/usr/local 在 OHOS 上根本不存在）
make install
#   mv -f skewer /usr/local/bin
#   mv: bad 'skewer': No such file or directory
#   make: *** [Makefile:48: install] Error 1

# S2 补充证据：DESTDIR 被无视（recipe 原文照打）
make -n install DESTDIR=/storage/Users/currentUser/tmp/uc2/z63-skewer/stage
#   mv -f skewer /usr/local/bin
```

⚠ **toybox `mv` 的误导性**：目标目录不存在时它报的是**源**操作数
（`mv: bad 'skewer': No such file or directory`），而 `ls skewer` 明明在。
照字面去找"skewer 哪去了"会白忙——真实原因是 `/usr/local/bin` 不存在。
（这条在 B 机两种状态下都复现过：产物存在与不存在时报错文本一字不差。）

## 4. 已试过的失败方案（都留了日志）

| 方案 | 结果 | 第一条真实错误 |
|------|------|----------------|
| A. 直接 `make -j1`（不动任何东西） | ❌ | `make: g++: No such file or directory`（Makefile:35，Error 127） |
| B. `make CXX=<clang++> CXXFLAGS=-O2`（顺手"规范化"优化参数） | ❌ | `ld.lld: error: undefined symbol: cFQ::readRecord(tag_REC*)`，随后 `clang-15: error: linker command failed`、`make: *** [Makefile:35: src/main.o] Error 1`——因为覆盖 CXXFLAGS 把 `-c` 丢了，"编译 src/main.cpp → src/main.o" 变成"只链 main.cpp" |
| C. `make install`（含 DESTDIR= 变体） | ❌ | `mv: bad 'skewer': No such file or directory`；`make -n` 证明 DESTDIR 被完全忽略 |

⇒ 结论：裸跑时不能把 CXXFLAGS 替换成缺少 `-c` 的值；配方保留原值并补 `-c`，且不调用 make install。

## 5. 最终方案（构建系统两处零补丁 + 运行期一处源码补丁）

1. `build()`：`make CXX="<resolved clang++>" -j1`，cwd = `self.source_folder`（上游是
   in-source 构建，`.o` 落在 `src/` 里）。编译器路径按 **R33** 取自 conan conf
   `tools.build:compiler_executables:cpp`（OHOS profile 已 pin 成
   `/data/service/hnp/bin/clang++`），仅当该路径 `isfile()` 不成立时退回 PATH 上的
   `clang++`（与已合入的 bwm/abbtr 同一兜底链；只用 `isfile`，不做 `X_OK` 探测，R49）。
   保留继承的 `CXXFLAGS` 并确保含 `-c`；`LDFLAGS` / `LDLIBS` 不改。
   `-pthread` 与 `-lrt` 由 OHOS musl + SDK sysroot 直接满足（实测链接通过）。
2. `package()`：**不跑 `make install`**，用 `tools.files.copy` 把 `skewer` → `bin/`、
   `LICENSE` → `licenses/`、`README.md` → `res/`，并对产物 `chmod 0755`
   （失败只 warning，E046 HMDFS 口径）。⇒ 产物里不存在任何 `/usr/local` 残留。
3. `package_type = "application"`、`settings` 四项齐全、`package_info()` 只声明
   `bindirs=["bin"]` 且 `includedirs/libdirs` 置空，**不导出 `cpp_info.libs`**。
4. `commands.json`（软件级，R38/PF8）：`name=skewer`、`type=tool`、
   `versions["0.2.2"].ref=skewer/0.2.2`（与 CI 不带 user/channel 的引用形态一致）。
5. 源码树**只改一个逻辑点**：`patches/0001-fix-char-eof-sentinel.patch` 把两处 EOF 哨兵的
   接收变量 `char` → `int`（`src/fastq.h:91` 的 `cFQ::tag`、`src/fastq.cpp:93` 的局部 `c`），
   两行、无平台宏、不动算法；由 `build()` 首行的 `apply_conandata_patches(self)` 应用，
   `export_sources()` 的 `export_conandata_patches(self)` 负责随配方导出，
   `conandata.yml` 的 `patches:` 段登记 `patch_file` / `patch_description` /
   `patch_type: "portability"` / `sha256`。写法照仓内既有配方（`archives/a/a52dec/0.7.4`
   的三补丁条目、`archives/a/aa3d/1.0` 的 sha256 字段），**未自创字段**。
   除这两行外源码树零修改（§10 有逐行 `diff -r` 证据）。

## 6. 适用边界

- 该"命令行覆盖 CXX + 配方自己 copy"的解法**只适用于** `CXX=...` 是普通赋值
  （非 `override`）、且 install 只是搬运二进制的裸 Makefile。若上游 Makefile 用
  `override CXX` 或 install 依赖 `install(1)/PREFIX` 分层安装，就要回到补丁路线。
- 覆盖 `CXXFLAGS` 在本包是**有害**的（`-c` 被丢）。同类 `FLAGS?=-c` 形态的裸 Makefile
  都要先读编译规则再决定覆盖什么。
- 断言里的 NEEDED 集合（`libc.so` + `libc++_shared.so`）与 `.codesign`/
  `.note.ohos.ident` 是**本机 clang 15.0.4 + OHOS SDK 26.0.0.18** 的实测事实；
  换 SDK 版本若 NEEDED 变化，A7 需要按实测更新，不要改成"宽松通过"。
- 上游 FASTQ 读段行为：**修复前记录数为奇数时最后一条被丢弃**（实测 5→4、7→6、9→8；
  偶数 4/6/8/12 全量通过）。这不是"上游 reader 的设计"，而是 plain char 吞掉 EOF 哨兵
  的直接后果，**已按知识库 DRAFT-8543 的处方修掉并用 A10 钉死**（全貌见 §10）。
  A9 的 8 条（偶数）fixture 与断言**原样保留**（它测的是 42bp 剪切成正确性），
  新增的 A10 用 5 条（奇数）测同一条管线，两者互不遮蔽。
- 编译告警现状（两条要分清，处置不同）：
  - `src/matrix.h:59` 的 libc++ `-Wuser-defined-warnings`（`ElementComparator` 不是
    const 可调用，`std::set` 的诊断）**仍未处理**——它只是类型特征告警，与本缺陷无关，
    不在本棒范围内（⛔ 不顺手修别的行为）。
  - `src/fastq.cpp:87/96/104` 的 `-Wtautological-constant-out-of-range-compare`
    **已随 0001 补丁消失**（打完补丁的 `conan create` 日志里 fastq.cpp 编译行后直接进链接行，
    0 条该告警）。它与"奇数条丢最后一条"的同源性**已做因果定性**（不是"很可能"，
    是三条独立证据闭环：编译器判决 + 类型探针 + 补丁前后同一用例 5→4 / 5→5），见 §10。

## 7. 实测证据（B 机绝对路径）

| 文件 | 内容 |
|------|------|
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-repro1-make-default.log` | S1 原文（`make: g++: No such file or directory`，Makefile:35 Error 127） |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-repro1-make-install.log` | S2 原文（未构建状态下） |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-repro1-make-install2.log` | S2 原文（产物存在状态下仍同样报错 → mv 误导文本证据） |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-repro2-cxxflags-override.log` | 失败方案 B 原文（`ld.lld: error: undefined symbol: cFQ::readRecord`） |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-repro1-make-cxxovr.log` | 最终方案在源码树裸验证：`make CXX=<clang++> -j1` rc=0，链接行 `-pthread ... -lrt` |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-standalone-testrun1.log` | test_skewer.sh 对 repro 产物独立跑：9/9 PASS |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-conan-create-1.log` | `conan create`（CI 同参，不带 user/channel）rc=0 + 9/9 断言 + 两条 HMBS 标记 |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-conan-verify-1.log` | `conan-verify` G1/G2/G3 PASS 全流程（W3 门禁） |
| `archives/s/skewer/0.2.2/reports/conan-verify-report.md`、`.../reports/conan-create.log` | harness 生成的正式验证报告 |
| `/storage/Users/currentUser/tmp/uc2/z63-skewer/dl/skewer-0.2.2.tar.gz` | 官方 tag 归档实拉件，`sha256sum` = `bc37afccdf55de047502b87fe56d537cdf78674ccaec1a401b2d29552d6b2dfc`（与 conandata 逐字符一致） |

### 7b. 2026-09-26 EOF 整改新增证据（B 机绝对路径，全在 `/storage/Users/currentUser/tmp/uc2/z63-skewer-fix/`）

| 文件 | 内容 |
|------|------|
| `before-odd-count.log` | 修复前 5/8 条对照取证全程 stdout（`sh run_case.sh before <旧产物>`） |
| `after-odd-count.log` | 修复后同一组用例（`sh run_case.sh after <新产物>`），5→5 / 8→8、0 条 malformed |
| `before/run5.before.log`、`before/run8.before.log`、`after/run5.after.log`、`after/run8.after.log` | 单用例的 skewer stdout+stderr 原文 |
| `before-warnings-from-create.log` | 未打补丁构建的三条 `-Wtautological...` 告警原文（含 `^ ~~~` 指示行） |
| `charmin-probe.out` | 运行时读数：`CHAR_MIN=0 CHAR_MAX=255 sizeof(char)=1`、`(char)(-1) as int = 255` |
| `probe/p.cpp`、`probe/charmin_probe.cpp` | `clang++ -dM -E` 预定义宏探针与运行时探针两个源 |
| `0001-fix-char-eof-sentinel.patch` | 补丁生成件（与 `archives/s/skewer/0.2.2/patches/` 内那份同 sha256） |
| `gen_patch.py`、`install_patch.py`、`add_assertion.py`、`add_notes.py`、`run_case.sh`、`run_create.sh`、`run_verify.sh` | 本棒可复跑脚本（锚点式精确替换，命中数不对即抛错，不留半改状态） |
| `logs-conan-create-fix1.log` | 只打补丁时的 `conan create`：SLOT_OK → Building from source → Apply patch(portability) → 9/9 → rc=0，**fastq.cpp 三条告警消失** |
| `logs-conan-create-fix2.log` | **最终**一次 `conan create`（含 A10，10/10） |
| `logs-conan-verify-final.log` | **最终** W3 门禁 `ohc-run.py conan-verify skewer 0.2.2`（G1/G2/G3） |
| `standalone-test-after.log` | 断言脚本对修复后产物的独立跑：10/10 |
| `a10-negative-control.log` | **反向验证**：同一脚本对未打补丁旧产物 → `[FAIL] A10`、`failedCount:1`（A9 仍 PASS ⇒ 未放宽旧断言） |
| `base/`、`apply/`、`ngtest/` | pristine 解包树 / `patch -p1` 应用树 / `patch_ng` 应用树（`diff -r` 只报 2 文件各 1 行的证据来源） |

## 8. 测试账本（五维，与 HMBS 标记同源）

| 维度 | 数 | 依据 |
|------|----|------|
| 上游静态测试总数 | **0** | 三条清点证据（`ls -d tests test t` 全部 No such file；`make -n check` → `No rule to make target 'check'`；10 文件清单无测试源），见 `test_package/MANIFEST.yml` |
| 本包可执行断言数 | 10 | `test_skewer.sh` 的 `TOTAL=10`（A1..A10） |
| 实测通过数 | 10 | `HMBS_TEST_PACKAGE_RESULT={... "passedCount":10 ...}`（conan create 的 test 阶段真机输出）；A10 另做**反向验证**：对未打补丁的旧包产物跑同一脚本 → `failedCount:1`、`[FAIL] A10`（证明该断言不是恒真） |
| 跳过数 | **0** | skewer 无终端/sixel/GPU//dev 依赖 ⇒ 不存在能力缺口用例；未使用 `test_skipped` 申报 |
| 失败数 | 0 | 同上 |

消费者测试覆盖：版本精确串（A1）、`--help` 用法段（A2）、无参数诊断语义（A3）、
版本串内嵌产物（A4）、ELF64+AArch64+DYN/PIE（A5）、musl 解释器双向一致（A6）、
NEEDED 集合白名单 + glibc 专有 soname 黑名单（A7）、`.codesign`×1 +
`.note.ohos.ident` + 无 RPATH/RUNPATH（A8）、真实 FASTQ 适配子 100bp→42bp 全管线
功能断言（A9，偶数 8 条）、奇数条不丢尾的缺陷回归断言（A10，5 进 5 出 + `@read5` 仍在 +
0 条 `Malformed fastq record` 指纹）；另附产物内无宿主绝对路径（`/storage`、`/home`、`/data/service/hnp`、
`/tmp`、`/build`）的静态扫描证据行。

## 9. 给主理窗判 B 用的一手观察（只报事实，不下结论）

两处预判症状都**真撞出来了**（原文见 §3/§7）。以下三条是客观观察，供判 M18 家族关系：

1. **S1 的形态与 dmenu 5.4（M18 记录的主机）不同一处**：M18 记的是
   `make: cc: No such file or directory`（`CC=cc`）＋ `X11/Xlib.h` file not found；
   skewer 撞的是 `make: g++: No such file or directory`（`CXX=g++`），
   且**没有任何第三方头文件缺失**（零依赖包，链接只用到 musl 的 `-lrt`）。
   即"烧死的是 C++ 编译器别名 + 完全不涉 X11/依赖头文件"这一组合。
2. **S2 的形态落在 M18 备注所指的另一侧**：M18 的 `similar_to` 写着
   "症状在 `package()` 的 install 命令"。skewer 的 install 是
   `mv -f $(EXECUTABLE) /usr/local/bin` —— **无 PREFIX 变量、无 DESTDIR、且用 mv 搬走产物**；
   修法不在 `package()` 里传 DESTDIR（实测被无视），而是"根本不叫 make install"。
   vamps 0.99.2（已合入，同为裸 Makefile）notes 记的是
   "install 依赖 install(1) 且 PREFIX 写死 ⇒ package() 直接 copy"，与本包同型。
3. **本包多出一条与前两点不同族的实测事实**：`CXXFLAGS?=-c` 里的 `-c` 被编译规则
   依赖，因此"顺手覆盖 CXXFLAGS"是**负向**操作（实测把编译变链接并死在
   `ld.lld: error: undefined symbol`）。裸 Makefile 的"能覆盖什么"取决于
   规则是否引用该变量——这一点在 M18/vamps 两份记录里都没写过。
   同时 toybox `mv` 把"目标目录不存在"报成"源文件不存在"，是同一次排障里的误导源。

（本窗按分工不写 DRAFT、不建 Issue；以上是判重/判 create 所需的原始事实与出处路径。）

---

## 10. 运行期可移植性缺陷：plain char 吞掉 EOF 哨兵 ⇒ 奇数条 FASTQ 丢最后一条

> 本节由 2026-09-26 的定点整改补写（主理-63 的整改棒）。它**取代** §5/§6 里
> "零补丁 / 未做因果定性 / 不要去修" 的旧口径；§1..§4 关于两处构建系统缺陷的内容不变。

### 10.1 症状（含编译器判决原文）

`conan create` 编译 `src/fastq.cpp` 时 clang 报三条
`-Wtautological-constant-out-of-range-compare`（原文抄自
`/storage/Users/currentUser/tmp/uc2/z63-skewer/logs-conan-create-1.log:121-129`，
前一根棒的未打补丁构建）：

```
src/fastq.cpp:87:9: warning: result of comparison of constant -1 with expression of type 'char' is always false [-Wtautological-constant-out-of-range-compare]
        if(tag == EOF)
           ~~~ ^  ~~~
src/fastq.cpp:96:24: warning: result of comparison of constant -1 with expression of type 'char' is always true [-Wtautological-constant-out-of-range-compare]
                while (c != '>' && c != EOF) {
                                   ~ ^  ~~~
src/fastq.cpp:104:9: warning: result of comparison of constant -1 with expression of type 'char' is always true [-Wtautological-constant-out-of-range-compare]
                if (c != EOF) {
                    ~ ^  ~~~
3 warnings generated.
```

运行期外显（用**已安装的包产物**实测，同一台 B 机、同一份 100bp 读段、`< /dev/null` + `timeout 60`）：
5 条输入的 FASTQ 只出 4 条，并且 stderr 冒出一条把 EOF 当格式错误的假诊断：

```
$ skewer -t 1 -x AGATCGGAAGAGC -o o5 in5.fastq ; grep -o 'reads processed' ...
4 reads processed
Malformed fastq record 6: no '@' for id        <- 出现 2 次（格式探测 pass + 正式 pass）
exit_code=0                                     <- 注意：退出码仍是 0，失败是"静默少一条"
```

### 10.2 根因（符号性 + 哨兵不可表示 + 丢弃路径逐行定位）

1. **接收变量**：`cFQ::tag` 在 `src/fastq.h:91` 声明为 `char tag;`，在
   `src/fastq.cpp:86` 执行 `tag = fgetc(in);`、`src/fastq.cpp:87` 执行 `if(tag == EOF)`；
   局部 `char c = fgetc(in);` 在 `src/fastq.cpp:93`，比较在 `:96`（`while (c != '>' && c != EOF)`）、
   `:104`（`if (c != EOF)`），重赋值在 `:102`。
2. **符号性实测**（OHOS clang 15.0.4，`/data/service/hnp/bin/clang++`）：
   `clang++ -dumpmachine` = `aarch64-unknown-linux-ohos`；
   `clang++ -dM -E` 含 `#include <limits.h>` 的探针 ⇒ `#define CHAR_MIN 0`、
   `#define CHAR_MAX UCHAR_MAX`、`#define __CHAR_UNSIGNED__ 1`；
   真跑一次读数 ⇒ `CHAR_MIN=0 CHAR_MAX=255 sizeof(char)=1`、`(char)(-1) as int = 255`、
   `char == EOF(=-1)` 恒 false。⇒ EOF 在 plain char 里**不可表示**。
3. **横扫（不只看报出来的两处）**：全源码树 `grep -n "get[cf]\?\|fgetc(\|getc(\|getchar("`
   只有 4 个命中，全在 `cFQ::readRecord()` 内（`fastq.cpp:86/93/102` + `:105` 的 `ungetc`）；
   `grep -n EOF src/*.cpp src/*.h` 只有 3 处比较（`:87/:96/:104`）+ 1 行注释。
   其余 `char chr;`（`fastq.cpp:278`、`matrix.cpp:1068`、`parameter.{h:44,cpp:599}`）
   接收的是**字符串里的字节**或 CLI 选项字母，不是 `fgetc()` 返回值 ⇒ **不改**。
   ⇒ 两个声明（`fastq.h:91`、`fastq.cpp:93`）覆盖全部三处死比较，兄弟调用点无遗漏。
4. **为什么外显是"丢最后一条"而不是挂起**：文件读尽时 `tag` 得到 255，`tag == EOF` 不成立，
   于是继续 `read_line()`（`getline` 返 -1），走到 `fastq.cpp:123` 的
   `tag != '@'` ⇒ 打印 `Malformed fastq record N: no '@' for id` 并 **return -2**（解析错误），
   而 `readRecord()` 的契约（`fastq.cpp:76-80` 注释）要求 EOF 返 -1。
   消费方 `src/main.cpp:936-940`：

   ```
   if(rc < 0){ pTaskMan->finish();
               if(rc < -1) continue;      // 被当成"错误"，整块已读记录直接丢掉
               if(nItemCnt == 0) continue; }
   ```

   读取块大小 = `nBasicSize * n_threads`，`nBasicSize = (len > 800MB) ? 10 : (len/100MB + 2)`
   （`main.cpp:819`）⇒ **< 100MB 的输入恒为 2**（按该式实算：1/50/99MB→2、100/150MB→3、
   250MB→4、799MB→9、800/1600MB→10）⇒ 奇数条时最后一个块里正好躺着 1 条已读成功的记录，
   `rc=-2` 让它被整块丢弃；
   偶数条时最后一块恰好读满、`rc>0`，所以只掉奇数尾巴。**5→4 / 7→6 / 9→8、偶数全过**由此定量解释。

### 10.3 最小复现与前后对照（B 机绝对路径）

同一条用例脚本（5 条=奇数、8 条=偶数，逐字对照）：
`/storage/Users/currentUser/tmp/uc2/z63-skewer-fix/run_case.sh`

| | 修复前（未打补丁产物，前一根棒 02:29 建）<br>`/storage/Users/currentUser/tmp/ch/home-skewer/p/b/skewe223c7897f453a/p/bin/skewer` | 修复后（打补丁产物，本窗最终一次 `conan create` 03:12 建）<br>`/storage/Users/currentUser/tmp/ch/home-skewer/p/b/skeweeeb191ca43154/p/bin/skewer` |
|---|---|---|
| 5 条 | `input=5 output=4 rc=0 malformed=2`，`4 reads processed`，输出只到 `@read4` | `input=5 output=5 rc=0 malformed=0`，`5 reads processed`，`@read1..@read5` 全在 |
| 8 条 | `input=8 output=8 rc=0 malformed=2`（偶数不丢，但假诊断照样冒） | `input=8 output=8 rc=0 malformed=0` |
| 序列/质量长度 | 两列均 42bp（剪切本身没错） | 同前，**无回归** |

- 修复前日志原文：`/storage/Users/currentUser/tmp/uc2/z63-skewer-fix/before-odd-count.log`
  （分用例 stdout：`.../before/run5.before.log`、`.../before/run8.before.log`）
- 修复后日志原文：`/storage/Users/currentUser/tmp/uc2/z63-skewer-fix/after-odd-count.log`
  （分用例 stdout：`.../after/run5.after.log`、`.../after/run8.after.log`）
- 符号性探针：`.../z63-skewer-fix/probe/p.cpp`、`.../probe/charmin_probe.cpp`、
  运行读数 `.../z63-skewer-fix/charmin-probe.out`
- 告警原文留档：`.../z63-skewer-fix/before-warnings-from-create.log`
- 补丁前后源码树逐文件 `diff -r` 只有 2 行不同（`fastq.h:91`、`fastq.cpp:93`），
  证据命令与输出见 §10.4 最后一条。


> ⚠ conan 2 的包目录名跟着 recipe revision 走，本包在整改过程中出现过 `skeweb2f84b5d2c3f7`（只打补丁那次）与 `skeweeeb191ca43154`（最终那次）两个打补丁产物目录，内容等价；判决与路径一律以两边日志里打印的绝对路径为准，未打补丁的对照产物始终是 `skewe223c7897f453a`。

### 10.4 修法（最小、可提交上游）

`patches/0001-fix-char-eof-sentinel.patch`（sha256
`74803cdfd9739b3454049f0c76ff1c2fafddf3202825de286375c3cff9791fb2`）：

```
--- a/src/fastq.h
+++ b/src/fastq.h
@@ -88,7 +88,7 @@
-	char tag;
+	int tag;
--- a/src/fastq.cpp
+++ b/src/fastq.cpp
@@ -90,7 +90,7 @@
-		char c = fgetc(in);
+		int c = fgetc(in);
```

- `int` 就是 C 标准给 `fgetc()` 规定的返回值域 ⇒ EOF 重新可表示，三处死比较复活。
- **无平台宏**（R8/PF5：这是可移植性缺陷，不是平台特性），不动算法、不动 `isspace()`/`ungetc()`
  调用（这两者本来就要求 `int`，改完反而回到正确用法），换回 plain-char-signed 的 x86 目标行为不变。
- 命名去掉了我最初想用的 `-ohos` 后缀：补丁里没有任何 OHOS 特判，名字带平台会误导评审。
  仓内命名规范 `{seq}-{desc}.patch`（`docs/TEST_QUALITY_SPEC.md` L0i）已遵守。
- 生成与验证链：在**官方 tar 包重新解包**的 pristine 树上用
  `/storage/Users/currentUser/tmp/uc2/z63-skewer-fix/gen_patch.py` 生成（不在任何已改动过的树上做），
  再 `patch -p1 --dry-run` / `patch -p1` 双向通过（`APPLY_RC=0`），
  并按 conan 的真实调用姿势跑一遍 `patch_ng.fromfile(...).apply(strip=0, root=<src>)`
  ⇒ `True`（conan 的 `apply_conandata_patches` 默认就是 `strip=0`，
  `patch_ng` 自己会规范化 `a/`、`b/` 前缀，故 conandata 里**不需要** `strip:` 字段）。
  `diff -r pristine patched` 只报 2 个文件各 1 行 ⇒ 没有顺手改别的。

### 10.5 适用边界

- 只解释并只修"**奇数条丢尾**"这一条。**偶数条同样会冒 `Malformed fastq record N` 假诊断**
  （修复前 8 条用例里也有 2 条），补丁一并消掉了它——同一根因的另一个外显，不是我另改了什么。
- 输入 ≥ 100MB 时 `nBasicSize` 就已经大于 2（100..800MB 区间是 3..9，> 800MB 恒 10），
  `-t` 还会再乘一遍 ⇒ 丢的是"最后一个不完整块里的 1..blockSize-1 条"，不是恒 1 条。
  本包只在 **KB 级 fixture、`-t 1`（blockSize=2）** 这一个区间里实测过 5/7/9 → 各少 1 条，
  别拿"只丢 1 条"当通用结论，也别拿没测过的区间当结论。
- 补丁**不覆盖** FASTA 分支以外的其他 reader 行为，也不碰 `gzformat()`（`:286` 的
  `while(fq.readRecord() > 0)` 在修复前后都会正常收敛）、`read_line()`（用 `getline()`，
  返回值本就是 `int`）、以及 `src/matrix.h:59` 的 libc++ 类型特征告警。
- 若 CI/评审换 SDK 或换编译器，判据不变：**A10 必须绿**，且 `conan create` 日志里
  `src/fastq.cpp` 编译行后**不得**再出现 `-Wtautological-constant-out-of-range-compare`。

### 10.6 与知识库条目的关系（8543 的哪一种表现形态）

命中条目 **`DRAFT-8543-plain-char-eof-sentinel-infinite-loop`**，按其 `rec_command`
口径执行（"仅改接收变量类型一行"），未新增机制：

- **同一根因**：plain char 承载 `getc()/fgetc()` 返回值再与 `EOF` 比较，EOF 不可表示。
- **不同外显（如实记，不夸大成新机制）**：那里（looktxt/1.4.1）EOF 是 `do-while` 的**唯一出口条件**
  ⇒ 控制流没有出口 ⇒ 100% CPU 永久挂起（`timeout` rc=124）；这里 skewer 的
  `readRecord()` 在 EOF 之后还会走到"格式校验"分支 ⇒ 控制流有出口但**出口值错**
  （-2 而非 -1）⇒ 不挂起，而是**静默少一条记录 + 一条假的 malformed 诊断**（退出码仍 0）。
  即"哨兵值不可表示"家族里的**第二种收敛方式**，不是同一条 bug 的重复报告，也不构成新条目。
- 条目 §5 清单第 6 条的教训已照做：定位用的是**符号级证据**（`grep` 出读取点 + 打印
  `cFQ::readRecord()` 函数边界 `fastq.cpp:81-139` + 编译器行号原文），没有凭函数名猜。
- 条目建议的 `-fsigned-char` 兜底路线**没有采用**（`forbid_3`：只把平台拉回上游假设、
  还会改变同包其它 char 语义），采用 `rec_priority=1` 的类型修正。

## 11. CI 2026-09-26 编译链接失败复核

PR #12803 的 CI build #61428 在 HEAD 711cba48 的首个编译命令为
`clang++ -fPIC -O2 -O2 src/main.cpp -o src/main.o`，命令缺少 `-c`。
CI 日志同时显示 make 在 `Makefile:35` 失败；因为 `main.cpp` 被直接链接，
报告中的 `cFQ`、`cMatrix`、`cParameter` 和 `gz*` 未定义符号是未参与链接的
其它对象/库带来的连锁结果。修复是在 `build()` 中保留环境 CXXFLAGS 并确保包含
`-c`，不新增依赖。该配方变更后需对最终提交 HEAD 重跑 W3 和 CI。

**本地复核（CIW-S4k1，2026-09-27，一手读数）**

- 前提逐字核对上游 Makefile（conan 缓存 8 份副本 md5 同为 `3ffb723f14de5108c642a3bd7003227a`）：
  `:3 CXXFLAGS?=-c`、`:21 CXXFLAGS += -O2`、`:32 $(CXX) $(LDFLAGS) $(OBJECTS) -o $@ $(LDLIBS)`
  —— 链接规则**不使用 CXXFLAGS**，故前置 `-c` 不可能打断链接（否证条件不成立）；
  `:35 $(CXX) $(CXXFLAGS) $< -o $@` —— 编译规则**不写 -c**。
- CI 条件复现（源码副本上 `env CXXFLAGS="-fPIC -O2" make CXX=<clang++> -j1`）：首行
  `clang++ -fPIC -O2 -O2 src/main.cpp -o src/main.o`，随后
  `ld.lld: error: undefined symbol: cFQ::readRecord(tag_REC*)` 与
  `make: *** [Makefile:35: src/main.o] Error 1`，与 CI 日志同形
  （`~/tmp/uc2/ciw-s4-skewer-b1/expA.log`）。
- 形态选择实证：`make CXXFLAGS=-c -n` 打印 `clang++ -c src/main.cpp -o src/main.o`
  （`+= -O2` 被命令行变量覆盖）；`env CXXFLAGS="-c -fPIC" make -n` 打印
  `clang++ -c -fPIC -O2 ...`（`+=` 仍生效）⇒ build() 必须用 **env 前缀**而不是
  `make CXXFLAGS=...`。
- 修复后 conan 内双环境实测：导出 `CXXFLAGS=-fPIC -O2` 时构建命令为
  `RUN: CXXFLAGS='-c -fPIC -O2' make CXX=/data/service/hnp/bin/clang++ -j1`，编译行
  `clang++ -c -fPIC -O2 -O2 src/main.cpp -o src/main.o`，链接通过、
  test_package `10/10 passed`、rc=0；未导出时仍是 `clang++ -c -O2`（与修复前一致 ⇒ 无回归）。
- 门禁：`conan-verify` → `**Verdict**: PASS`（G0-G4 PASS；L2/L4/L5 该行原文
  `⏭️ 跳过（无 cache 路径）`）；`finish skewer 0.2.2 built` → `✅ W3 本地 CI 模拟通过`，
  `.ci-result.json` 为 `exit_code=0`、`log_sha256=d648158dfd5e0f2e1030a4a4f5dba4d43cbbc7332066b2780bb5906dce2f9c90（2026-09-27T15:17:39）`。【已作废：后继 CIW-S4k4 清 conandata 镜像 URL 改了构建输入，两道门禁已重跑，新读数见 §12.5】

## 12. conandata 首选镜像 URL 清理与取源自证（CIW-S4k4，2026-09-27，B 机一手读数）

### 12.1 问题与定性

HEAD `443b8fd654708f68019ba65a205fcb12f2840acb` 的 `archives/s/skewer/0.2.2/conandata.yml`
第 9 行是一枚镜像前缀 URL：

```
sources:
  url:
    - "https://gh-proxy.com/https://github.com/relipmoc/skewer/archive/refs/tags/0.2.2.tar.gz"
    - "https://github.com/relipmoc/skewer/archive/refs/tags/0.2.2.tar.gz"
  sha256: "bc37afccdf55de047502b87fe56d537cdf78674ccaec1a401b2d29552d6b2dfc"
```

这与**同文件自己的头注释**（第 2-5 行：「sha256 由本窗在 B 机上 curl 实拉后 sha256sum
自算核对……故 conandata 只写 GitHub 官方 tag 址，不加镜像、不改哈希」）直接矛盾——申报与内容不符。

`gh-proxy.com` 是框架源 URL 闸的镜像黑名单首项，`scripts/ohc/preflight.py:356-360` 原文：

```python
_PF7_MIRROR_HOSTS = (
    "gh-proxy.com", "ghfast.top", "ghproxy.net", "ghproxy.com",
    "mirror.ghproxy.com", "gitclone.com", "kkgithub.com", "gh-proxy.xyz",
    "moeyy.cn", "moeyy.xyz", "fastgit.org", "hub.fastgit.org",
    "gh.api.99988866.xyz", "cnb.cool")
```

成因不是人工手写：镜像回退本由构建期框架注入，`ci/conan/build_and_test.sh:1217` 原文
`mirrors = ['https://gh-proxy.com/' + url, url]`；注入写进**活文件**后由退出 trap 还原，
本轮改动是在还原落地前被提交，于是把临时态固化进了版本库。

### 12.2 取源自证：官方址可达 + 三向同哈希

**可达性**（B 机，`curl -sS -o /dev/null -w ...` 对官方址，命令与返回原文）：

```
$ curl -sS -o /dev/null -w "http_code=%{http_code} size_download=%{size_download} url_effective=%{url_effective}\n" \
      -L --max-time 120 "https://github.com/relipmoc/skewer/archive/refs/tags/0.2.2.tar.gz"
http_code=200 size_download=36382 url_effective=https://codeload.github.com/relipmoc/skewer/tar.gz/refs/tags/0.2.2
$ curl -sSIL --max-time 120 "https://github.com/relipmoc/skewer/archive/refs/tags/0.2.2.tar.gz" | grep -E '^HTTP/|^Location:'
HTTP/1.1 302 Found
Location: https://codeload.github.com/relipmoc/skewer/tar.gz/refs/tags/0.2.2
HTTP/1.1 200 OK
```

即官方址**不需任何镜像即可直连**（302→codeload→200，36382 字节），第 9 行的镜像条目是冗余项。

**三向哈希**（三者逐字符相同 ⇒ 删镜像不改变取源语义）：

| # | 来源 | 读数 |
|---|---|---|
| ① | 线上 HEAD `conandata.yml` 声明值（`git show HEAD:… \| sed -n 's/^  sha256: \"\(.*\)\"/\1/p'`） | `bc37afccdf55de047502b87fe56d537cdf78674ccaec1a401b2d29552d6b2dfc` |
| ② | 本轮 B 机实拉官方 tar 后 `sha256sum`（`skewer-0.2.2-official.tar.gz`，36382 字节） | `bc37afccdf55de047502b87fe56d537cdf78674ccaec1a401b2d29552d6b2dfc` |
| ③ | 设备上先前的独立实物 `~/tmp/uc2/z63-skewer/dl/skewer-0.2.2.tar.gz`（2026-09-26 拉，36382 字节）`sha256sum` | `bc37afccdf55de047502b87fe56d537cdf78674ccaec1a401b2d29552d6b2dfc` |

共享下载缓存 `~/tmp/ch/dlcache` 内**没有**该 tar（`find ~/tmp/ch/dlcache -iname '*skewer*'` 无输出），
故第三读改用上述设备实物，未把「缓存没命中」写成「缓存已核对」。

### 12.3 清理动作与形态选择

只删第 9 行那枚镜像条目，**官方址与 `sha256` 一字未动**；单址仍写成列表里的**一枚** `- "…"`，
不自造形态——同仓既有先例即此形态：`archives/a/abgate/1.2.0`、
`archives/a/adobe-source-code-pro/2.042u`、`archives/a/advai-cli/1.0.12` 都是 `url:` 下单枚列表项。
清理后 `sources:` 段（本 PR 内可核对的最终内容）：

```yaml
sources:
  url:
    - "https://github.com/relipmoc/skewer/archive/refs/tags/0.2.2.tar.gz"
  sha256: "bc37afccdf55de047502b87fe56d537cdf78674ccaec1a401b2d29552d6b2dfc"
```

头注释「不加镜像」的申报无需改写——本轮正是把内容拉回与申报一致。

### 12.4 PF7 闸的前后对照（同一检查器，非引用外部日志）

改前基线（把 HEAD 的旧 blob 取到临时目录喂给 `ohc.preflight.check_source_urls`）：

```
PF7 violations (pre-fix blob) : ['PF7 源URL闸(R39): archives/s/skewer/0.2.2/conandata.yml:9 镜像前缀 gh-proxy.com（CI 自动加镜像回退，手写即 R39 违规 579 例）——conandata 只写上游官方源 URL，镜像回退由 CI 自动处理；确属官方托管例外须 PR 说明并 --no-preflight 跳过']
```

改后同一函数对活文件：`PF7 violations (post-fix file): NONE`。
对照是必要的——第一次跑对照时临时目录建在 `/tmp`（HarmonyOS 上只读）而 `mkdir` 失败，
「NONE」其实是空文件造成的假绿，重做到可写目录后才拿到上面这条真实违规文本。

### 12.5 因本改动而重跑的门禁

改 conandata 属动构建输入（配方修订含 conandata 及其注释），§11 的旧 W3 证据作废，全部重跑：

- `python3 -m py_compile archives/s/skewer/0.2.2/conanfile.py` → rc=0（该文件本轮未改）。
- `sh ~/tmp/uc2/gate.sh 4000` →
  `GATE_PASS:probe=clang MemAvailable=19290MB MemFree=7248MB Cached=17353MB swap余=50821MB inode余=21753574 load=20.183 20.326 20.256 PSI_full=avg10=25.88 编译器进程=0 RSS=0MB`，rc=0。
- 槽位 `~/tmp/uc2/build-slot.sh --status` → `本机长杆 0/2 · 机动 0/3（总 5 槽）`，conan-verify 与 finish 各走一次 `--kind short --mem 2500`。
- `scripts/ohc-run.py conan-verify skewer 0.2.2` → rc=0；验证报告 `reports/conan-verify-report.md`
  （该路径被 `.gitignore:96` 的 `reports/` 规则排除、**不随 PR**，故此处**原文摘录**而非行号引用）：
  第 3 行 `**Verdict**: PASS`，G0/G1/G2/G3/G4 均 PASS，L2/L4/L5 三处该行原文
  `⏭️ 跳过（无 cache 路径）`。
- `scripts/ohc-run.py finish skewer 0.2.2 built` → `✅ W3 本地 CI 模拟通过`，
  `.ci-result.json`（同样不随 PR，原文摘录其字段）为 `exit_code=0`、
  `log_sha256=816b1ed7c23deafb1ed74c6040731782aa5bccf7761883e64361da879b0c19a5`
  （timestamp `2026-09-27T15:29:54.862448`，晚于本轮 conandata 改动；`integrity_hash`
  由 `ee169d59ee6498e5` 变 `8a0cb27fab6cb26f`，即配方修订确实换了）；该 `log_sha256` 与随
  构建重生的 `reports/w3-local-ci.log` 实测 `sha256sum` 相等（同源核对）；
  w3 日志 `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":10,"passedCount":10,"failedCount":0,"skippedCount":0}`。
  命令本身返回 rc=2，非本轮引入：Step5b（缺 debug 包 / notes-vs-manifest 一致性 2 项）与 Step8
  （`gen_summary 失败: 'str' object has no attribute 'append'`）在上一棒 CIW-S4k1 的同名命令上是
  **同样两项、同样 rc=2**（其 `失败步骤: step5b, step8`），阻塞门禁 W3 自身为绿。
- 构建期镜像注入与还原**不采信日志文字**（`🔄 已恢复原始 conandata.yml`）：跑完直接
  `git diff -- …/conandata.yml` 核对，差异仍只有那一行删除；`sha256sum` 由改后
  `10df6e68f578f9ae83a33145b752ce4fb135fcdd658ddf69633434855b48fa44` 到跑完仍是同一值（逐字节相同），
  活文件里 `gh-proxy|ghfast|ghproxy|kkgithub|gitclone|moeyy|fastgit|cnb.cool|file://` 全部无命中。

---

**编译结束**: 2026-09-27 15:29
**最终状态**: built
