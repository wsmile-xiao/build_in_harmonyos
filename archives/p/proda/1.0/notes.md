# 适配笔记 — proda 1.0

**软件**: ProDA (Probabilistic Database Alignment) — 概率式多序列比对命令行工具
**版本**: 1.0（任务版本 / Conan 版本 / 归档目录 / 分支名四处一致，未做任何"归一化"）
**上游论文**: Do C.B., Phuong T.M., Edgar R.C., Batzoglou S., *Nucleic Acids Research* 2006 34(20):5932-5942
**许可**: public domain（取证见下文『许可与来源取证』）
**构建日期**: 2026-09-25 · **构建主机**: B 机 · **档位**: 【易】

适配路径：路径 B（贡献创新）—— 本包在路径 A 的基础适配（裸 Makefile 配方 + 3 个可移植性补丁）之上，另主张 1 条新知识
使用知识库：是（`E547-draft-B5C3` 的 `declare-fgetc-result-as-int`；佐证 `DRAFT-8543-plain-char-eof-sentinel-infinite-loop`）—— 查重面为 `knowledge/graph/` **与** `knowledge/drafts/` 两处同批扫，详见『路径 B 判定』
知识库扩展：create 1 条 —— 机制①：上游把 `errno` 当**局部变量名**声明（该翻译单元原本不 `include <errno.h>`）。在把 `errno.h` 带入 include 链的 libc（musl）上编译期报 `error: illegal initializer`；在没带入的 libc（glibc）上照样编过，却把 `strtol` 的错误检查遮蔽成**恒假的死代码**。草稿 `knowledge/drafts/DRAFT-proda-1.0-libc-errno-name-used-as-local-variable.{kv,md}`（本包为首个实证先例）

关联 Issue：【知识库扩展】proda 1.0：上游把 `errno` 当局部变量名声明——musl 上编译期报 illegal initializer，glibc 上编过但 `strtol` 错误检查成死代码（Issue 标题，与上述草稿同名同机制；Issue **#3357** 已创建 —— https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3357（建单与编号已回填））
适用语言：C/C++（本例 C++）

---

## 0. 开工前静态预判的实测复核（**4 条里有 2 条被推翻**）

前窗的静态预判写在任务书里，明确要求"以盘上实测为准"。逐条复核结果：

| 预判 | 实测 | 判定 |
|---|---|---|
| 语言 c=18 / cpp=17（混合） | **0 个 `.c`**；17 个 `.cc` + 18 个 `.h`（+1 Makefile = 36 文件） | ❌ **推翻**：不是混合语言，是**纯 C++**。那 18 个被数成 "C" 的其实是 `.h` 头文件，而它们全是 C++ 头（被 `.cc` 包含、内含 class）。**结论不变的部分**：仍然不触发 `env_unsupported`（R47 的 c↔cpp 本就同族），但"混合语言"这个描述是错的，下游若据此配 `languages` 或做语言判定会拿到假信息。 |
| 裸 Makefile（非 autotools 非 cmake） | ✅ 整份 61 行，无 configure、无 am/proj 文件 | 成立 |
| 共 36 个文件 | ✅ `find -type f` = 36（17 cc + 18 h + 1 Makefile，无第 4 类文件） | 成立 |
| 零外部依赖 | ✅ 全部 `#include` 只有自家 `.h` 与 C/C++ 标准库（stdio/stdlib/string/ctype/math/errno + vector/list/map/string）；唯一链接行是 `-lm`（musl 自带） | 成立 |
| Makefile 里 `PREFIX` 是变量、"烧死系统路径=False" | ❌ **推翻**：Makefile 里**既没有 `PREFIX`，也没有 `install` / `DESTDIR` 目标**——只有 `all` / `proda` / `clean` 三个目标。上游从没打算被打包安装。 | 推翻 |

⇒ 直接后果：**本包不能照"裸 Makefile + PREFIX"那一族配方写**（那条路的前提是有 `PREFIX` 可传、有 `install` 可调）。改按 `archives/q/qbe`、`archives/a/aha`、`archives/a/abc` 这一族"in-source make + package() 手工 copy 二进制"的形态写。

### 另外两个"看一眼就会误判"的点

1. **`LinkTable.h` 包含了一个不存在的 `Link.h`** —— 全仓 grep：没有任何 `.cc` 或 `.h` 包含 `LinkTable.h`，它自己是**死代码**，预处理器根本走不到那行。所以这不是编译错误，**不要为它打补丁**（打了反而是无谓改上游）。
2. **`-DVERSION="\"1.00\""` 这个宏在 35 个源文件里从未被引用**（版本串是 `Main.cc` 里硬编码的 `"ProDA version 1.0"`）。配方覆盖 `CXXFLAGS` 会把它丢掉 —— 实测无副作用，属于可以安全丢弃的项，已在 conanfile 注释里写明原因。

---

## 1. 三个补丁：症状 → 根因 → 最小复现 → 最终方案 → 适用边界

### 补丁 1 `patches/0001-Main.cc-name-shadowed-libc-errno.patch`

- **症状**：`Main.cc:119:7: error: illegal initializer (only variables can be initialized)`，紧跟一行 note 指向 `errno.h:16:17: expanded from macro 'errno'`。
- **根因**：`GetInteger()` 里写了 `int errno = 0;` —— **声明了一个和 libc `errno` 同名的局部变量**。
  glibc 下 `Main.cc` 的包含链里没有 `<errno.h>`，`errno` 只是个普通标识符，于是"居然能编过"；
  musl/OHOS 的 `<errno.h>` 被传递包含进来了，`errno` 是宏 `(*__errno_location())`，
  这行被展开成 `int (*__errno_location()) = 0;` —— 给一个函数调用"初始化"，语法上就不合法。
  **顺带暴露一个上游真 bug**：即使在 Linux 上，这个局部 `errno` 也**遮蔽**了 libc 的 errno，
  所以后面 `if (errno != 0 ...)` 读到的永远是刚赋的 0，strtol 的出错判定是死代码。
- **最小复现**：`echo 'int main(){ int errno = 0; return errno; }' > t.c` 用 OHOS sysroot 编 → 同一报错。
- **最终方案**：显式 `#include <errno.h>`（不再赌传递包含）+ 把 `int errno = 0;` 改成 `errno = 0;`。
  **行为中性证明**：该函数唯一的调用点是 `-L <length>` 的参数解析。
  ① 非数字 → `strtol` 置 ERANGE/EINVAL 但 `retVal==0 && data==endPtr` 这条已经拦住了；
  ② 溢出 → `retVal==LONG_MAX/LONG_MIN`，改前落到 `retVal < INT_MIN || > INT_MAX` 也照样 return false。
  两条路径改前改后结论相同 ⇒ 修掉了遮蔽 bug，**不改变任何可观测行为**。
- **适用边界**：凡是"局部变量/形参取名 `errno`"的老代码，在 musl 上必炸；glibc 上静默。同族症状：`expanded from macro 'errno'`。

### 补丁 2 `patches/0002-Sequence.cc-missing-stdio-h-include.patch`

- **症状**：`Sequence.cc:208:3: error: use of undeclared identifier 'fprintf'`，clang 还给了个误导性提示 `did you mean 'fwprintf'?`。
- **根因**：`Sequence.cc` 用了 `fprintf`/`FILE` 却**没有直接 `#include <stdio.h>`**，
  靠 glibc 头文件的传递包含侥幸通过；musl 的传递包含面明显更窄，一断就露馅。
- **最小复现**：同一 tarball 里只给 `Sequence.cc` 打补丁 1 不打补丁 2，`make -j1` 即在第 208 行报此错。
- **最终方案**：按 IWYU 补 `#include <stdio.h>`。不动逻辑。
- **适用边界**：`use of undeclared identifier 'printf/fprintf/fopen/...'` + 该文件没直接 include `<stdio.h>`。
  **注意本包只有 `Sequence.cc` 中招**：`Matrix.cc`(21 处)、`MultiSequence.cc`(38 处)、
  `ScoreMatrix.cc`(21 处)、`SparseMatrix.cc`(11 处) 同样没有直接 include，
  但它们的自家头文件里已经带了 `<stdio.h>`，实测能编过 ⇒ **不许"顺手"给它们也加**
  （R1 参数最少化；没坏的不修，也不许照抄别包的补丁）。

### 补丁 3 `patches/0003-Utilities.cc-fgetc-EOF-into-unsigned-char.patch` ★本包真正的深坑

- **症状**：**编译链接全部通过，二进制也在**，一跑就死：
  `libc++abi: terminating due to uncaught exception of type std::bad_alloc`，
  stderr 停在 `Loading: <file>`，`Signal 6 (core dumped)`，退出码 134。
  最容易误判成"aarch64 内存/运行时不兼容"或"31G 的机器居然 OOM"。
- **根因**：`Utilities.cc::GetData()` 写的是
  ```c
  char ch;
  while ((ch = fgetc (file)) != EOF){ ... 缓冲区成倍增长 ... }
  ```
  `char` 的**有符号性是实现定义**的：x86-64 上 gcc/clang 默认 signed，`EOF`(-1) 截进 `char` 得 -1，
  比较成立 → 循环正常结束；**aarch64 上 clang 默认 `char` 为 unsigned**，`EOF` 折成 **255**，
  `255 != -1` **永远为真** → 读到文件尾之后继续"读"，`new char[capacity *= 2]` 无限倍增
  → 抛 `std::bad_alloc` → 析构链上 `abort`。**同一份二进制语义在两个架构上不一样。**
- **最小复现**：`printf 'x' > f; ` 用只有一行、**结尾不带终止符 `>`** 的 fasta 喂 proda —— 只要走到
  "读到底返回 EOF"这条路径就死（`-L 999` 那种提前退出的分支除外）。
- **最终方案**：`char ch;` → `int ch;`（1 行）。`isTerm[(unsigned char) ch]` 的下标转型本来就在，
  `int` 之后依然正确；EOF 不再被截断。
- **适用边界**：**这是"编译过了但跑不动"的一类，不是编译期错误，静态扫不出来。**
  凡是 `char`/`unsigned char` 变量接 `fgetc/getc/getchar/towctrans` 等返回 `int` 的函数再和 `EOF` 比较，
  移植到 aarch64/ARM（char 默认 unsigned）都会死循环或读到 255 这个合法字节。
   grep 口径：`grep -n "char ch" *.cc` 配合 `grep -n "!= EOF"`。

---

## 2. 构建配方要点（为什么长这样）

- **编译器只能走 make 命令行变量，不能用环境变量注入。**
  上游 `CXX = g++` 是**无条件赋值**。make 的优先级是「命令行 > Makefile 内赋值 > 环境变量」，
  所以只在 buildenv 里 `export CXX=...` 对这个 Makefile 是**彻底的 no-op**。
  ⇒ 这就是本配方**故意不挂 `GnuToolchain`** 的原因：它注入的是环境变量，
  留着只会让下一个读配方的人误以为编译器生效了（`aha` 那种 Makefile 用 `?=` 的包才适用它）。
  编译器一律从 `self.conf.get("tools.build:compiler_executables", ...)` 取（**R33**，
  release worker 上 `os.environ` 的 CC/CXX 是空的）。
- **`CXXFLAGS` 必须重组，不能沿用。** 上游的 release 那两行注释里带
  `-mmmx -msse -msse2 -mfpmath=sse -march=pentium4 -mcpu=pentium4` —— **x86 专有开关，aarch64 上直接报错**。
  配方按 profile 重组：保留上游的 `-W -Wall`，`build_type` 决定 `-g` 还是 `-O2 -DNDEBUG`，
  `compiler.cppstd` 决定 `-std=`。实测 Release 产物 141 KB、Debug 748 KB，功能一致。
- **in-source 构建**：`.o` 和 `proda` 都落在源码目录，所以 `basic_layout(self)` 之后要
  `self.folders.build = "."`，否则 make 会在空 build 目录里找不到 Makefile。
- **`package()` 手工 copy**：上游无 install 目标；且设备上**没有 coreutils 的 `install(1)`**，
  补一个 `make install` 目标只会引入新坑（§2.3）。
- **`make -j1`**：HMDFS 上 GNU make 的 jobserver FIFO 不可靠（平台已知项）。
- **`package_info()` 显式清空 `includedirs`/`libdirs`/`resdirs`**：application 包没有任何库和头，
  不清空会让下游消费者拿到不存在的搜索路径。
- **没有踩到 config.status / `umask 077` 那个 E011/E052/E112/E114/E129 家族** —— 本包非 autotools，
  压根没有 `config.status`。**因此不打该类补丁**（实测没踩就不打，也不照抄别包的）。

---

## 3. 上游测试清点与五维账本（R51）

### 取证命令与实测输出

```sh
cd pristine/proda                      # 从 sha256=439a93bf… 的 orig tarball 干净解包
find . -type f | wc -l                        # → 36
ls *.cc | wc -l ; ls *.h | wc -l              # → 17 ; 18
find . -type f | grep -v '\.cc$\|\.h$\|Makefile$' | wc -l   # → 0（除源码和 Makefile 外没有任何文件）
find . -type f | grep -ic 'test\|check\|spec'  # → 0（没有任何按测试命名的文件）
grep -n '^[a-zA-Z_.][a-zA-Z_. ]*:' Makefile    # → 只有 all / proda / clean 三个目标 + .o 依赖行
grep -ci 'TESTS\|check_PROGRAMS' Makefile      # → 0
```

⇒ **上游 1.0 提供 0 个自动化测试**，也没有 `make check` / `make test` 入口，
所以不存在"有但跑不了"的灰区（`可执行数` 的分母天然为 0，不是被我缩小的）。

### 五维账本

| 维度 | 数字 | 口径 |
|---|---|---|
| 上游测试静态总数 | **0** | 上面 6 条取证命令，静态清点全量 36 文件 |
| 上游测试可执行数 | **0** | 无 check/test 目标，无 TESTS 注册，无可执行入口 |
| 上游测试实测通过数 | **0** | 0 的 0% —— 不存在"跳过一部分"的说法 |
| 上游测试跳过数 | **0** | 没有可跳过的对象 |
| 上游测试失败数 | **0** | 无失败 |

**消费者测试（本次适配补齐，赛道二门禁）**：**14 个场景 / 31 条断言，实测 31 通过、0 失败、0 跳过**。
账面由 `test_package/run_tests.sh` 结尾自检并打印
`SCENARIOS=14 ASSERTIONS=31 PASS=31 FAIL=0 MIN_PASS=31`；
其中 `MIN_PASS=31` 由 `test_package/conanfile.py` 注入。三项账面自检（场景数 / 断言数 / 通过下限）
**在汇总行之前**完成，任一漂移额外打印 `SELF_CHECK_DRIFT` 并以 **rc=2** 终止
（W4 r1 P2：原实现的汇总行印在三项自检之前，而自检在其后才把 `FAIL` 自增，
漂移时人读到的是 `SCENARIOS=.. FAIL=0` 的假绿、脚本却以非 0 退出 ⇒ 判决文字与退出码相反）。
⇒ 这四个数（run_tests.sh 打印 / MANIFEST.yml / conanfile.py 下限 / 本笔记）逐字同源。

proda 是 `package_type="application"`，**不产出库、不装头文件**，所以"使用者"就是命令行调用方；
`run_tests.sh` 全部走**真实调用 + 退出码 + 对输出内容的判定**。
为防断言退化成"匹配固定字符串"，里面放了 **3 组负向对照**：
`-L 999`（阈值超过序列长度）、`alpha`+`beta`（互不相关序列）两种情况下 proda **不得**产出比对块，
输入文件缺失必须以非 0 退出。这三条只有 HMM 概率判定真的在 aarch64 上跑起来才成立。

最强的一条是 `-posterior`：默认(Viterbi) 给 `alpha(1-105) gamma(1-105)`，
后验模式把末端那个不一致残基按概率纳进来，块边界**扩展到 `alpha(1-106) gamma(1-106)`**，
保守性行尾由 `*` 变 `:`。断言的是**更宽的那个边界**，因此它同时证明了"这个开关不是被解析后空转"。

---

## 4. 许可与来源取证（含 R39/PF7 的已知张力，**不隐藏**）

### 许可
tarball 里**没有任何 LICENSE/COPYING 文件，35 个源文件和 Makefile 里也没有一行版权或许可声明**
（`grep -in "copyright\|license\|GPL\|author\|stanford" *.cc *.h Makefile` → 空）。
所以不能凭空写 SPDX。授权口径取自 Debian 的 `debian/copyright`：

```
Upstream-Contact: Phuong Tu Minh <phuongtm@fpt.com.vn>
Source: http://proda.stanford.edu/proda_1_0.tar.gz
License: PD
 ProDA is released under public domain, ...
```
⇒ 配方写 `license = "Public-Domain"`（与本仓既有 18 个 PD 包同写法）。
⚠ **取证边界要写清**：该授权口径的依据**全部来自权威再分配方的元数据**
（Debian `debian/copyright` 的 `License: PD` 及其 `ProDA is released under public domain` 正文），
**不是上游自证** —— 上游 tarball 内 0 处版权/许可声明（上面那条 grep 即其取证）。
因此本包**只主张**"权威再分配方如此标注、且上游无任何相反声明"，
**不主张**"上游明确声明 public domain"。若审查要求上游自证，本包无据可依，只能按现状披露。

### 源码 URL：官方上游**只有 http**，https 通道只能借 Debian 池

| 候选 | 实测 | PF7 判定 |
|---|---|---|
| `http://proda.stanford.edu/proda_1_0.tar.gz` | **HTTP 200，活着的官方上游**（B 机 2026-09-25 本轮复测：`http_code=200`、38868 B、`sha256` 见下） | ❌ 命中"明文 http 源（R39 要求 https）" |
| `https://proda.stanford.edu/proda_1_0.tar.gz` | **TLS 握手即失败，拿不到任何 HTTP 状态码**：B 机 2026-09-25 实测 `curl` rc=60 `SSL: no alternative certificate subject name matches target host name 'proda.stanford.edu'`、`http_code=000` | — 不存在可用的官方 https 通道 |
| `https://deb.debian.org/debian/pool/main/p/proda/proda_1.0.orig.tar.gz` | HTTP 200 | ❌ 命中"Debian 下游重打包源" |

**已证同一份字节**（所以 https 那条并不是"重打包"）：

```
sha256(http 官方 proda_1_0.tar.gz)      = 439a93bf35e1a29ac1d5dde51e61f2cb174618596afaaaaa27d33a8ea1868a08   (38868 B)
sha256(https Debian proda_1.0.orig...) = 439a93bf35e1a29ac1d5dde51e61f2cb174618596afaaaaa27d33a8ea1868a08   (38868 B)
```
且该哈希同时命中 `proda_1.0-13.dsc` 的 `Checksums-Sha256`；Debian 用的是 Format 3.0 (quilt) 的
**pristine `.orig.tar.gz`**（无 `+dfsg`、无 repack），按定义就是上游原始包。

⇒ **结论（事实句，不给因果）**：官方上游**从 B 机可达**（`http://proda.stanford.edu/proda_1_0.tar.gz`
HTTP 200、38868 B，sha256 与 Debian pristine `.orig.tar.gz` **逐字相同**：
`439a93bf35e1a29ac1d5dde51e61f2cb174618596afaaaaa27d33a8ea1868a08`）；
官方**只有明文 http** 这一种通道 —— 其 https 版 URL 的服务器证书不覆盖 `proda.stanford.edu`
主机名（curl rc=60，见上表），因此**不存在"既官方又 https"的 URL**。
这是上游 2006 年发布、站点后改造成的客观缺口，**不是可以改配置凑过去的绿灯**。

⇒ 三条处置：① `sources` 取 **Debian 官方池的 pristine `.orig.tar.gz`**
（Format 3.0 quilt、无 `+dfsg`、无 repack，按定义就是上游原始包），
② 官方明文 http URL **只记在软件级 `manifest.yaml` 的 `source.upstream_official_url`——
那是信息字段、不是下载字段**，CI 不会去下它，
③ **不把明文 http 塞进 `sources`**（那会让 CI 去下载明文 http，比取 Debian 更不合规）。
`conanfile.py`/`conandata.yml` 顶部注释同时写明官方 http 源与逐字相同的 sha256。
**需要主窗处置**：`create-pr` 的 PF7 会拦这 2 行（`1.0/conandata.yml` 的 `sources.url`
与软件级 `manifest.yaml` 的 `source_url`），按 PF7 自己给的路径处理 ——
**PR 正文说明"官方托管例外" + `--no-preflight` 跳过**。
本仓已有 **307 个已合入配方**的 `conandata.yml` 用 `deb.debian.org`
（同形 `.orig.tar.gz` 的先例：`a52dec/0.7.4`、`aalib/1.4p5`、`abx/0.1`），
PF7 是 v12.20 才加的闸，属"新闸 vs 存量惯例"的口径冲突，应交主窗/主编定夺，不由本包擅自改 URL。

**提交态 conandata 清洁度**：`file://` 无、`gh-proxy`/`ghfast` 等镜像域名无 —— 只有上面这一处
`deb.debian.org` 是**官方原始包的 https 载体**，已完整披露，未做任何隐藏。

---

## 5. 已试过的失败方案（真踩过的，不是推演）

1. **用 `... | tail -40` 判构建成败 → 假绿灯。**
   第一次裸编译时管道把退出码换成了 `tail` 的退出码，屏幕上打出 `RAW_MAKE_RC=0`，
   而 `make` 实际返回 **2**、`proda` 根本没生成。靠"`ls -la proda` → No such file"才发现。
   ⇒ 之后一律先 `> log 2>&1; echo RC=$?`，再单独 grep 日志。
2. **`ssh -n ... 'cat > 设备文件'` → 落盘 0 字节，测试套件"全过"。**
   `-n` 会把 ssh 的 stdin 重定向到 /dev/null，于是 `cat` 写出空文件，
   `sh 空文件` 退出码 0 —— 打出 `SUITE_RC=0` 却一行结果都没有。
   ⇒ 上传文件时**不能带 `-n`**（带 `-n` 的只读通道和"喂 stdin"是两种调用）。
   发现方式：`ls -la` 见 0 字节。**这是本轮最危险的一次假绿**，因为它长得像"测试通过"。
3. **`-posterior` 的断言初版写错，实测 FAIL。**
   我照 `pair.fa` 的块边界写了 `alpha(1-105) gamma(1-105)`，跑出来 A20 FAIL。
   根因不是工具坏了，是**我拿默认模式的期望值去套后验模式**。查实际输出后改成断言
   `alpha(1-106) gamma(1-106)`，反而得到一条强得多的断言（见 §3）。
   ⇒ 教训：期望值必须来自被测对象的实测输出，不能来自"同一程序另一个分支的输出"。
4. **排除掉但没试错的写法**：沿用上游 `CXXFLAGS`（会带上 x86 专有 `-march=pentium4`，aarch64 必炸）、
   以及给 `LinkTable.h` 补 `Link.h`（死代码，无谓改上游）。这两条是**静态排除**，
   没有真跑过失败版本，记录时按"排除项"看待，不算实测失败方案。

---

## 6. 已知限制 / 未执行项（供正文『未执行、未覆盖的检查』单列）

1. **上游 `-fasta` 选项在本输入下输出与默认模式逐字相同**（`cmp` 实测一致）。
   源码里 `fastaOutput` 只被赋值、找不到产生差异的输出分支 ⇒ 疑似上游未完成特性。
   **未改上游**（属路径 C 范畴，需用户批准），A24 只断言"`-fasta` 下仍产出正确比对块"，
   不宣称它改变了输出格式。
2. **`-L 999` / 不相关序列时 stdout 为空**（负向对照 A12/A14）—— 这是 proda 的正常语义
   （找不到达标块就不输出块），**不是** "程序没跑起来"。断言里连退出码 0 一起判，避免混淆。
3. **输入文件缺失时以 SIGABRT 退出（实测 rc=134）而非优雅报错** —— 上游 `ASSERT` 宏直接 abort。
   消费者测试按**退出码白名单 1 / 2 / 134** 判定（W4 r1 P3 整改：不再"非 0 即过"，
   否则连二进制都找不到时的 rc=127 也会被记成通过），不去改上游的错误处理风格。
4. **产物未 strip**（Debug 748 KB / Release 141 KB）。签名由 CI 的 `ci/artifacts/sign.sh` 负责；
   本地真机 exec 前需自签，本轮测试在设备原生 shell 下完成。
5. **finish 框架面存量红项**（未改表单凑绿灯，读数如实记录）：
   step5b `unreferenced>0`（判据要求 `knowledge_gained` 每行含 `ref:`，而本包在
   `knowledge/graph/` 正式条目里确实**零命中** ⇒ 无 graph 级 E 编号可引，不编造 `ref:`。
   补充口径：W4 r1 判定的机制③命中项 `E547-draft-B5C3` / `DRAFT-8543-*` 住在
   `knowledge/drafts/` 层、不是 graph 条目，故该红的性质不变）、step8 `gen_summary` 失败、
   step3 G0「找不到原始 tarball」、step10 `packaging/` 与 `.staging-verified`。
6. **本轮 `conan-verify` 的 G2 是 recipe/binary 双 Cache 命中、未重编**（`reports/conan-create.log:54`）：
   整改只动文档与判决件绑定，`git diff --name-only d0ba16d3ee..HEAD` 证明 `conanfile.py`、补丁、
   `test_package/conanfile.py` 字节未变 ⇒ recipe revision 必然不变。**全量编译证据仍是首适提交
   `941ce3353b`**，本节不把它冒充成本轮新证据；而 `test_package` 不属该 revision 且**确已重跑**
   （W3 日志 `:1344` 出现只存在于新脚本的 S13 退出码白名单文案，旧文案全文 0 命中）。
7. **finish 的两个退出码都如实记录**：内层 step 汇总 `EXIT_CODE=0`、外层 `rc=2`
   （取证 `~/tmp/uc2/z32c-proda/finish.out:127,140`）。`rc=2` 由上面第 5 条的存量红项给出，
   **两个值都没有被写成"通过"**。
8. **W4 独立审计不在本子代理职责内**（主窗另派第三方）。

---

## 7. 路径 B 判定（W4 r1 **改判**：机制③ `hit`，机制① `create`）

**定案：本 PR 主张的 1 条新知识 = 机制①（上游把 `errno` 当局部变量名声明）。
机制③（`char` 承接 `fgetc()` 再与 `EOF` 比较）判 `hit` —— 库里已有两条，不再为它开 Issue、不再写草稿。**

### 机制③ 判 hit（主引 E547-draft-B5C3，佐证 DRAFT-8543）

- `knowledge/drafts/E547-draft-B5C3.kv:36` 标题
  『fgetc() 返回值存入 char 变量：AArch64 无符号 char 下 EOF 永不匹配，读输入死循环挂死』，
  `:49 rec_approach=declare-fgetc-result-as-int`、`:50` 推荐处置「把承接 fgetc/getchar 返回值的
  变量声明为 int，优先于全局 -fsigned-char」—— 与补丁 0003 的 `char ch;` → `int ch;` 是
  **逐字同一处置**（1 行改动面，审计已复算）。
- `knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv:16` 同机制，
  且已**独立实测** `CHAR_MIN==0` 与 `__CHAR_UNSIGNED__`（与本包 §1 补丁 3 的根因同一前提）。
- 两条与本包机制**同层次**（都是"plain char 承接 int 返回值再比 EOF"，不存在父子/上下游关系）
  ⇒ 按 `hit` 处理，不升 `create`。

### ★ 错因（如实记下，给后来人）

初判写的『使用知识库：否（`knowledge/graph/index.tsv` 全量检索零命中）』**是不实陈述**：
**查重面只扫了 `knowledge/graph/`，漏扫 `knowledge/drafts/`** —— 而 `E547-draft-B5C3`、
`DRAFT-8543-*` 恰恰住在 drafts 层，`index.tsv` 天然收录不到它们。

⇒ 口径修正（本包已按新口径重做过，见下）：**B 判级的检索面必须是
`knowledge/graph/` 与 `knowledge/drafts/` 两处同批扫**；只扫 `index.tsv` 得到的"零命中"
**不得**写进申报。另一面也要记住：`engine`/grep 命中 ≠ 语义命中，
初判把 E292（Arrow 系 CTest 迁移，Phase B 5 分）与 E190（Perl XS 构建参数，0 分）判为假命中
**这一步是对的**，它只是漏掉了真命中的那一条。

### 机制① 判 create（本 PR 唯一可主张的新知识）

**四范围零命中**（第 1/2 范围 = graph 的 `.kv` 与 `index.tsv`，第 3 范围 = `knowledge/drafts/*.kv`，
第 4 范围 = `archives/**/notes.md`）：
`knowledge/graph/` 按 `index.tsv` 关键词列命中 `errno` 的 4 行分别是 E008 / E190 / E405 / E415；
按 `.kv` 正文 grep `errno` 命中 **13 个 .kv**——两个口径都逐条读了原文，无一讲
"把 errno 当变量名声明"（E190 是 Perl XS `Makefile.PL` 参数）；`E400` 关键词
`__errno_location` 重合，但其 `error_signature` 是 Node.js/V8 **运行期** `Check failed`，
与本条"编译期-静默双态"**不同层次** ⇒ 假阳性。`knowledge/drafts/` 定向检索
「局部变量 × errno 宏 × illegal initializer」= **0 命中**。
`archives/**/notes.md` 第 4 范围的最近邻是「`extern int errno`」族（daemontools `notes.md:18,27,43`
＋其 `manifest.yaml:77` 的 `ref:E999`、bootp、bsdutils、iozone、buffer）：该族讲的是**自己写
`extern int errno` 去取全局 errno**（POSIX 已不推荐的旧写法，处置是补 `#include <errno.h>`），
与本条**把 `errno` 当局部自动变量名声明、把宏遮蔽掉**是根因不同、处置面不同、症状不同的两种写法
（那族在各 libc 都能编过，本条在 musl 上直接编不过）⇒ 判不同机制，本条仍为 `create`。

一句话机制：**`errno` 在 glibc 与 musl 上都是宏 `(*__errno_location())`；上游在解析辅助函数里
写 `int errno = 0;` 把这个保留名当普通局部变量声明，而该翻译单元原本不 `include <errno.h>`** ⇒
这行能不能编译只取决于 `errno` 宏有没有被某条 include 链带进来：带进来（musl）就展开成
`int (*__errno_location()) = 0;` ⇒ clang 报 `error: illegal initializer`（症状与根因相距很远）；
没带进来（glibc）就**照过**，但此后所有 `errno != 0` 读的都是这个局部变量、`strtol` 写的却是
真线程 errno ⇒ **错误检查恒为假 = 死代码**。
**同一段上游代码在两种 libc 上表现相反：要么编不过，要么静默失效。**

落点与影响面：`Main.cc:119` 所在的解析辅助函数 `GetInteger()`，
**唯一调用点是命令行 `-L <length>` 的取值解析**（行为中性论证见 §1 补丁 1：非数字与溢出两条
非法路径改前改后都由 `retVal==0 && data==endPtr` 与 `INT_MIN/INT_MAX` 边界拦住 ⇒ 修掉遮蔽 bug
而**不改变任何可观测行为**，故本包不额外主张"输入集改变"）。

草稿（随本 PR 原子提交）：
`knowledge/drafts/DRAFT-proda-1.0-libc-errno-name-used-as-local-variable.{kv,md}`。
其来源是仓内通用池草稿 `DRAFT-PKG-VER-libc-errno-name-used-as-local-variable`，
本包为**首个实证先例**，取用后已把 `id`/`doc_file`/`source_*`/`affected_scope` 换成本包实测值。

**注意**：本节只改判定与申报，**未写登记表、未建 Issue、未 promote 知识条目** —— 定案与建 Issue 归主窗。
---

**编译结束**: 2026-09-25 03:02
**最终状态**: built
