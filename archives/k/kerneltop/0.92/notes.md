# kerneltop 0.92 适配笔记

## 结论速览

- 路径 A，一次成功：源码一字未改（`patches_applied` 为空），交叉编译全部靠 `make`
  命令行变量覆盖完成。
- W3（`conan-verify kerneltop 0.92`）三处同判为绿：控制台正文「配方验证通过」、报告
  `**Verdict**: PASS`、命令退出码 0。八道门禁无一 FAIL。
- 包内产物 `bin/kerneltop` 经自查为 **not stripped**、`.codesign` 段在位、
  `file` 报 `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped`，
  直接 exec `kerneltop -V` 返回码 0 并打印 `kerneltop Version 0.92`。
- 消费者测试 10 个用例在真实 `conan create` 的 test_package 阶段全部执行，
  10 通过 / 0 失败 / 0 跳过；上游静态测试用例合计 0（有清点证据）。
- CI 侧本地 CI 模拟（与远端 CI 同源的五级判定）逐条为：`L0_RESULT=pass`、
  `L1_RESULT=pass: test_package executed`、`L4_RESULT=pass: patches clean`、
  `L5_RESULT=pass: bin/ has content`，`L2_RESULT=skip`（见"适用边界"）；
  L1e 破坏性反向验证把 `bin/` 移走后测试随即失败，据此判定
  "test genuinely depends on kerneltop"，即这批用例不是空壳。

## 包与构建面

官方 release tar 包 `kerneltop-0.92.tar.gz`（10675 字节）解压后**只有 3 个文件**：
`kerneltop.c`(27259B)、`makefile`(355B)、`vidsupport.h`(2880B)。构建系统是裸 POSIX
makefile，没有 configure、没有 cmake/meson、没有 `install` 目标。makefile 全文只有
`all` 与 `clean` 两个目标，两条编译/链接命令内联在规则里：

```make
all: kerneltop
DEBUG=
CC=gcc
ifeq "$(DEBUG)" "y"
CCFLAGS=-g $(CFLAGS)
else
CCFLAGS=-s $(CFLAGS)
endif
kerneltop: kerneltop.c
	$(CC) -c -O2 $(CCFLAGS) -I. -Wall -Wstrict-prototypes kerneltop.c -o kerneltop.o
	$(CC) $(CCFLAGS) kerneltop.o -o kerneltop
```

零外部依赖：源码 include 面是 libc + 内核 UAPI 头（`errno/stdio/stdlib/unistd/string/
sys/types/sys/stat/sys/poll/fcntl/pwd/time/ctype/termios/linux/kd.h`）。`linux/kd.h`
在 OHOS native sysroot 中实际存在（`.../sysroot/usr/include/linux/kd.h`），因此不构成
env_unsupported。运行面是 `/proc/profile`（需 `CONFIG_PROFILING` 且 root）加一个
`System.map`。

## 症状

`make` 的 else 分支把 `-s` 同时塞进编译行和链接行，也就是**链接期 strip**。OHOS 上
"被 strip 过的 ELF 跑不起来"是已记录的坑（`.codesign` 校验失败 → `exec` 得到
`Operation not permitted`），而本包**没有任何安装或打包目标**会在链后再碰这枚 ELF，
所以风险点被压缩成一句话：这枚二进制到底以什么形态进包，才能保证消费者 exec 不被内核
拒绝。

## 根因

OHOS 内核加载 ELF 时校验的是 native SDK 在**链接期**由 autocodesign 写入的 `.codesign`
段。判定"有没有被 strip 坏"的因果变量不是"符号表在不在"，而是**签名动作与 ELF 改写动
作的先后**：

- 链接期 `-s`：`ld` 先产出已 strip 的 ELF，SDK 随后签名 ⇒ 签名覆盖的就是最终字节。
- 链后 `llvm-strip`／`objcopy`：签名已经写进文件，改写段布局使签名失效 ⇒ 加载期拒绝。

所以"段还在"不等于"签名有效"，而"被 strip 过"也不等于"签名无效"。本包的最终形态选的
是**根本不 strip**：让签名之后的字节在整个链路上无人改动，把这一整类风险从配方里移除，
而不是依赖"后面没人会碰它"这个约定。

## 最小复现

在同一台 B 机、同一份源码、同一个 `/data/service/hnp/bin/clang` 上做的单变量对照：

| 臂 | 构造方式 | `file` 读数 | `.codesign` 段 | exec 结果 |
|---|---|---|---|---|
| 未 strip 臂 | `make CC=clang CCFLAGS=` | not stripped | 在位 | `kerneltop -V` → rc **0**，stdout `./kerneltop Version 0.92` |
| 链后 `llvm-strip` 臂 | 对**上面那枚同一个 ELF** 的副本跑 `/data/service/hnp/bin/llvm-strip` | stripped（31104→14920 B，段头数 38→24） | **计数 1→0：该段被整个删掉** | `./kerneltop -V` → rc **126** `Permission denied` |
| 链后 GNU strip 臂 | 同一枚 ELF 的另一副本跑 `/data/service/hnp/bin/strip`（GNU Binutils 2.45） | stripped（→22360 B） | 计数仍为 **1**（段名与占位都还在） | `./kerneltop -V` → rc **126** `Operation not permitted` |
| 上游默认臂 | `make CC=clang`（即 `CCFLAGS=-s`） | stripped | 在位 | `kerneltop -V` → rc **0** |

对照臂纪律：未 strip 臂是**当场重新链接出来的产物**，不是拿 build 目录里已经被就地处理
过的件来充数；链后 strip 臂是对同一 sha256 的副本动手。三臂的 `sha256sum` 互不相同，
逐臂留痕。

**更正记录（本包独立审计指出、主理-70 窗一手复算坐实）**：本表前一版在链后 strip 行写的是「`.codesign` 计数仍为 1」，该读数**不成立**——它把上游 `-s` 链接臂的计数误记到了链后 `llvm-strip` 臂上。复算实测：`llvm-strip` 会把 `.codesign` 段整个删除（计数 1→0、14920 B、exec rc=126）。真正支撑下一节「段还在≠签名有效」这条结论的是**新增的 GNU strip 臂**——它保留该段（计数 1、22360 B）却仍然 `Operation not permitted`（rc=126）。三臂复算读数：base 31104 B / cs=1 / rc=0；llvm-strip 14920 B / cs=0 / rc=126；GNU strip 22360 B / cs=1 / rc=126；复算件与探针脚本留在 `~/tmp/uc2/z70-kerneltop-codesign-recheck/`：三臂件为 `base` / `llvm` / `gnu2`，逐臂哈希在 `arm-hashes.txt`，命令原样在 `probe-1.sh` / `probe-2.sh`。⚠ 同目录另有一枚 `gnu` 是**第一次探针里 GNU strip 臂没真正执行到**留下的 base 副本（逐字节等于 `base`），不要当它是 GNU 臂。段头数一律取 `readelf -S` 的 `There are N section headers` 读数；用 `grep -c` 数 `\[` 会把 `[Nr]` 表头行一起算进去（前一版就是这么多了 1）。

## 已试过的失败方案

1. **`DEBUG=y` 走 `-g` 分支绕开 `-s`** —— 放弃。`-g` 会把产物换成带调试信息的形态，
   等于为了迁就打包去改上游的发布语义，不是在"不 strip"，而是在"改成调试构建"。
2. **先按上游默认链接、链后再由配方重签**（`llvm-objcopy --remove-section .codesign`
   → 改 ELF → `binary-sign-tool sign -selfSign 1` → `chmod a+x`）—— 未采用。本包链路
   上没有任何一步必须改写 ELF，四步重签是为"确实要改二进制"的包准备的；在没有改写需求
   时引入它，等于凭空多一处会把产物弄坏的地方。留作后备路径，配方里不落码。
3. **把消费者测试降级成"文件存在 + `file` 能读"** —— 明确否决。一旦 exec 报 126，
   存在性检查照样全绿，这是缩分母；本包 10 个用例全部以 `exec` 返回码为断言的一部分。
4. **按 verify 报告里被点名的 Knowledge hit 去改配方** —— 未采用。本轮 G2 一次通过、
   未触发知识图谱匹配，也就没有"被点名条目"需要服从。

## 最终方案

- `build()`：`make CC="<profile 里的交叉 clang>" CCFLAGS= -j1`，`cwd=self.source_folder`。
  三个要点分别对应 E392 的三坑（显式 `filename=` 定死解码器、
  `tools.build:compiler_executables` 用 `check_type=dict` 整体取再 `.get("c")`、
  裸 makefile 只在 source_folder 存在）；`CCFLAGS=` 只在命令行覆盖，文件里那条
  `CCFLAGS=-s $(CFLAGS)` 一个字没动；`-O2 -Wall -Wstrict-prototypes` 全部保留，被摘掉
  的只有 `-s`。
- `package()`：只有 `copy("kerneltop", source_folder, dst=包目录下的 bin)`。上游没有 man page
  与文档件，因此包内产物数=1，不是漏装。
- `package_info()`：`bindirs=["bin"]`、`libs=[]`；`package_type="application"`，
  软件级 `commands.json` 已按 R38 声明。
- 无补丁、无 `tool_requires`、无 `requires`。

## 适用边界

- 上述"链后改写 ELF 会破坏 `.codesign`、链接期 `-s` 不会"的结论，是在 OHOS native
  SDK 26.0.0.18 + clang 15 + `os.version=6.0` profile、B 机这台 HarmonyOS PC 上测出的，
  换 SDK 大版本或换签名策略需要重测，不要当成跨版本常数。
- "不 strip 而交付"这一手只适用于**打包链路本来就不需要改写 ELF** 的包。凡是必须在链
  后动二进制的（改段、注资源、加符号），仍然要走四步重签，顺序不可变，且签名后必须
  `chmod a+x`（签完权限会归零）。
- `kerneltop` 的 `--version` / `--help` 长选项在**上游语义里就不存在**：`getopt`
  短选项串是 `m:p:s:l:t:uV`，长选项会落进 `default:` 分支 → 打印 usage → `exit(1)`。
  本轮没有为了让 smoke 类检查"好看"去打补丁改这个语义；版本可读性由短选项 `-V` 承担，
  并已作为消费者用例第一条。实测该取舍的代价与判定：CI 侧 L2 因此报
  `--version/--help failed (non-blocking)` → `L2_RESULT=skip`，不阻塞任何门禁，且与仓内
  已合入的同类先例（同为"无长选项的 CLI 包"）记法一致；同型包若真需要 L2 转绿，正确做法
  是补上游长选项，不是把 L1 用例改成存在性检查。

## 上游测试清点（R51 第一步）

release tar 包内文件数 = 3（`kerneltop.c` / `makefile` / `vidsupport.h`）。清点结果：

| 项 | 数量 | 证据 |
|---|---|---|
| tests/ 目录 | 0 | tar 包内不存在该目录 |
| makefile 的 check/test 目标 | 0 | `make -n check` 与 `make -n test` 均 `make: *** No rule to make target`，返回码 2 |
| 测试源文件 / 断言驱动 | 0 | 无测试驱动文件，无 ctest/pytest/meson test 注册 |
| CI 配置 | 0 | 上游是单 tar 包发布，无仓库内 CI 描述件 |
| **合计** | **0** | 四类清点逐条为 0，故上游静态测试用例合计 0 |

## 适配后测试用例统计

上游 0 条，全部由本包补全，且每条都真正 `exec` 打包后的二进制。

| 行名 | 用例数 | 断言点 | 实测通过 | 跳过 | 失败 |
|---|---|---|---|---|---|
| 消费者用例（test_package/test_kerneltop.sh） | 10 | 23 | 10 | 0 | 0 |
| 鸿蒙特有测试 | 0 | 0 | 0 | 0 | 0 |
| PC 特有测试 | 0 | 0 | 0 | 0 | 0 |
| **合计** | **10** | **23** | **10** | **0** | **0** |

用例清单（断言点 = 退出码断言 + 输出文本断言逐条计，2+3+2+2+2+2+4+2+2+2 = 23）：

| # | 用例 | 覆盖的代码路径 |
|---|---|---|
| 1 | `kerneltop -V` 打印 `Version 0.92` 且 rc=0 | 真实 exec + getopt 短选项分支 |
| 2 | `kerneltop -Z` 未知选项打印 usage 且 rc≠0 | `usage()` 与退出码语义 |
| 3 | `-m` 指向不存在的 map → ENOENT 且 rc≠0 | `myopen()` + 显式指定时不回退默认路径 |
| 4 | map 行格式非法 → `wrong map line` | `sscanf` 三元组校验 |
| 5 | map 内无 `_stext` → `can't find '_stext'` | 文本段起点查找 |
| 6 | map 地址递减 → `descending address order in map line` | 地址单调性校验 |
| 7 | 合成 map + 合成 profile，排序轮：`func_gamma=10 func_beta=2 _stext=1`，总量 `(    13)` | `profile_read` → 差分入桶 → `lookup` → `copy_freqs` → `insertionSort` → 打印 |
| 8 | 同输入加 `-u`：`_stext=1 func_beta=2 func_gamma=10` | 与用例 7 构成**差分对照**，证明 7 真的排过序 |
| 9 | `-t 5` 只剩 `func_gamma=10` | 阈值过滤 |
| 10 | 合法 map + 不存在的 profile → `enable kernel profiling [profile=N]` | `mapfile_read` 成功之后才到达 `profile_read` |

## 运行面披露（不缩分母、不做平台能力缺失定性）

`kerneltop` 的完整体验需要两样沙箱给不了的东西：`/proc/profile`（要
`CONFIG_PROFILING` 且 root）和一个前台终端（`keypressed()` 会 raw 化 termios）。
但这两样各自只卡住一层，卡不住被测的那一层：

- **符号表解析、地址→符号映射、tick 差分、阈值过滤、插入排序、结果打印这一整层不需要
  特权也不需要终端。** 因为 `mapfile_read()` / `profile_read()` 都只是普通的
  `open()`+`read()`，而"top 式界面"是 `vidsupport.h` 里把 ANSI 转义序列 `printf` 到
  `stdout`——重定向到文件照样是合法字节流。于是用 `-m`、`-p` 指向两个当场造出来的普通
  文件（一个 5 行的合成 `System.map`，一个 `sampling_step=4` + 4 个桶的合成 profile），
  就能把用例 7–9 的整条计算链真实跑通并逐值断言，包括"总量 13"和"排序后从上到下递减"
  这种数值级期望。
- **退出不靠外部信号**：往 stdin 灌一个 `q`，程序走自己的 `keypressed()` →
  `do_key('q')` → `fini:` → `exit(0)` 路径收尾，stdio 缓冲区正常刷出。这一点是被实测
  逼出来的：早先用 `timeout` 直接杀进程时，`stdout` 是重定向到文件的块缓冲，前 115
  字节之后的整轮表格还留在缓冲区里，随 `SIGTERM` 一起丢了，读起来像"程序什么都没打印"。
- **确实被测不到的一层**：真实 `/proc/profile` 的内核侧可读性、以及有终端时的交互式
  体验（`h` 帮助页、`l/s/t` 改参数）。用例 10 覆盖的是"内核 profiling 不可得时的**文档
  化失败路径**"，也就是这个工具在无特权环境里的真实表现；这不构成对内核 profiling 能力
  本身的判定，本笔记也不把它写成平台缺陷。

### 对话 #1：取源址与哈希，先把自己不信的通道排除掉

第一步不是写配方，是确定"源码从哪来、以什么为准"。Debian sid 的 `.orig` 哈希是现成的
权威参照，但 Debian 池址属于重打包通道，进配方会被源 URL 闸直接判死，所以它只当**旁证**
用，绝不当来源。做法是先实测作者官方目录
`https://www.infradead.org/~rdunlap/src/kerneltop-0.92.tar.gz` 拿到 HTTP 200 与 10675
字节，再在本机对**实际下载到的字节**自算 sha256，得到
`a18b048dd06409e3e9b085863b9c115b05011f792f6f3b47f90260f749a3d6aa`，与 Debian `.orig`
逐字相等。到这里"官方址 + 自算哈希 + 第三方池哈希"三方对齐，配方里只写官方址。
同目录还确认了 `kerneltop-0.91.tar.gz` 与 0.8/0.9 子目录，说明这个址是作者的活跃发布
位，不是偶然挂着的旧文件。

第二条是否证：任务版本、Conan `version`、归档目录名、分支版本四处必须逐字是 `0.92`，
而源码里的 `#define VERSION "0.92"` 与 `-V` 的实际输出第三处对上，才敢往下走。

### 对话 #2：把"strip 会让产物跑不了"这条先验当成待验假设，而不是结论

接手时带的先验是"链接期 `-s` 会让产物在本机不可执行，所以必须从源头不 strip"。这个先
验的**动作建议**（别 strip）是对的，但它的**因果表述**在本包上经实测是半错的。于是做了
单变量三臂对照（见"最小复现"表）：

- 先造"未 strip 臂"，并且是**当场重新链接**的产物——不能拿 build 目录里已经被别的步骤
  就地处理过的文件当"未 strip 臂"，那是假对照（这一步差点踩，及时换成重链一份）。
- 再对这枚 ELF 的副本跑链后 `llvm-strip` → rc=126，`Operation not permitted`，先验的
  这一半成立。
- 最后跑上游默认（`CCFLAGS=-s`）→ **rc=0，能执行**。也就是说链接期 `-s` 并不破坏可执行
  性：`ld` 先出已 strip 的 ELF，SDK 随后才签名，签的就是最终字节。

否证的价值有两层：一是把"能跑/不能跑"的分界从"有没有 strip 过"修正成"签名之后有没有再
被改写"，写进 notes 的根因段，避免下一个包拿着错的原因去做对的事；二是据此确认**不采用
四步重签**——本包链路上没有任何一步必须改写 ELF，引入重签只会凭空多一处能弄坏产物的地方。
最终仍然选择命令行 `CCFLAGS=` 不 strip，但理由换成了诚实的那个：把整类"签后被改写"的
风险从配方里删掉，代价是二进制大 8960 字节，不是"绕过一个观测到的失败"。

顺带被否掉的还有一个偷懒方案：既然 makefile 的 DEBUG 分支正好不带 `-s`，用 `DEBUG=y`
最省事。否决理由是它改的是发布语义（产出调试形态），不是"不 strip"。

### 对话 #3：消费者测试要测到哪一层，以及一次假失败怎么变成真知识

设计测试时最大的诱惑是"这个工具要 root 要终端，那就只查文件存在"。这条路明确不走，因
为它恰好把最该报警的失败形态（rc=126）变成绿灯。于是把可测面拆开：读源码确认
`mapfile_read()`/`profile_read()` 都是普通文件读，`vidsupport.h` 的"界面"只是 `printf`
转义序列，`lookup()`/`insertionSort()`/`copy_freqs()` 是纯计算——也就是说**除了真读
`/proc/profile` 那一步，其余全链条不需要特权**。这就把"测不了"变成了"喂两个合成文件就
能逐值断言"。

合成输入不是随便造的：`sampling_step=4`、`adr0=0x1000`、四个桶 `1,2,3,7`，配合
`_stext / func_alpha / func_beta / func_gamma / _etext` 五行 map，按 `lookup()` 的
"命中区间、越界回退到上一个符号"语义，期望值可以手算成 `func_gamma=10`、`func_beta=2`、
`_stext=1`、总量 13，而 `func_alpha` 恰好 0 tick 被阈值滤掉——一个用例同时验证映射、
差分、累加、过滤四件事。再加 `-u` 做差分对照，防住"排序断言其实恒真"。

第一次跑出来的却是"只有 uname 那一行、什么都没有"，返回码 124。真实原因不是程序坏：
`stdout` 重定向到文件是块缓冲，`timeout` 发 `SIGTERM` 时整轮表格还在缓冲区里被丢了。
改成往 stdin 灌 `q` 让程序走自己的退出路径后，10 条断言全部拿到真实输出。这个假失败最
后变成了"退出不靠外部信号"这条设计约束，写进运行面披露。

另外记录一处框架侧的读数噪声，供上游参考、不影响本包判定：本轮 W3 的八道门禁报告里，
G4 取到的是"无法找到程序包 ID"，L2/L4/L5 因此按"跳过（无 cache 路径）"这一种读数记为
PASS——真因不在正则（前一版那句「正则不吃带点号的四段版本号」是错解，本窗已一手否证：`scripts/ohc/conan_verify.py` 取包 ID 时读 `listing["Local Cache"][software][ref]["revisions"]`，而 conan 2.29.1 的 `conan list "kerneltop/0.92:*" --format=json` 在 `Local Cache` 下的顶层键只有 `kerneltop/0.92`，**没有裸包名 `kerneltop` 这一层** ⇒ 索引抛 `KeyError`，又被该处的 `except (KeyError, IndexError, StopIteration)` 吞掉 ⇒ G4 记「无法找到程序包 ID」却仍以 `passed=True` 返回，L2/L4/L5 随之按「跳过即绿」记账）。属框架缺陷、另开框架 PR，本包不改任何框架文件。本包没有把这份"跳过即绿"当产物证据，
而是自己对包内 ELF 补做了 `file` / `llvm-readelf --sections` / 真实 exec 三项自查，
证据见上表。

## 路径 B 最小声明（3+2）

- 适配路径：A —— 裸 makefile 的零修改交叉编译，`make` 命令行变量覆盖 `CC` 与 `CCFLAGS`，
  无补丁、无外部依赖、无框架改动。
- 使用知识库：E392（raw-makefile-conan-recipe-pattern 三要素：显式 `filename` /
  `tools.build:compiler_executables` 用 `check_type=dict` 整体取 / `make` 必须
  `cwd=source_folder`）；E077（`.codesign` 与 strip 的关系、四步重签机制）作为**边界
  参照**使用——本包据它判定"无需重签"，因此没有调用其任何落地形状。
- 知识库扩展：无。本轮未新增知识条目、未写 `knowledge/drafts/`、未建 Issue。
- 关联 Issue：无 —— 本包走路径 A，B 档位由主代理终判
- 状态：built
---

**编译结束**: 2026-09-26 16:58
**最终状态**: built
