# snek 1.13 适配笔记

## 软件简介

Snek 是 Keith Packard 编写的面向嵌入式计算的小型 Python 风格语言解释器
（目标是只有几 KB Flash/RAM、跑不动 MicroPython 的处理器）。本配方适配其
主机侧 posix 解释器 `ports/posix/snek`，以命令行工具（application 包）形式
发布。上游仓库：https://github.com/keith-packard/snek（tag 1.13，
commit 164b5503a4d2d79ef8c6c110d823b91d0c44f980）。

## 源码

- URL（官方 GitHub tag 归档，CI 另有 gh-proxy 镜像回退）：
  `https://github.com/keith-packard/snek/archive/refs/tags/1.13.tar.gz`
- sha256：`3166ac00b6dcc7cdda90c57e4df3d398542f84afd8b791495f42d058431eb7ad`
 （实测 20883383 字节，与 conandata.yml 一致）
- 许可证：GPL-3.0-or-later（COPYING 为 GPLv3，源码头为 "either version 3
  or any later version"）

## 构建系统分析

- 类型：手写多层 Makefile（非 autotools/cmake/meson），顶层 Makefile 默认
  会同时构建嵌入式固件（avr/arm/riscv 的 hex/uf2）与 snekde/doc/examples，
  需要外部交叉工具链。本配方只构建 `ports/posix/snek` 单个目标。
- posix 链接：`$(CC) ... -o snek $(OBJ) $(LIBS)`，`LIBS` 默认为
  `-lreadline -lm`（STATIC=0）或 `-static -lm`（STATIC=1）。
- 代码生成：`snek-gram.h` 由 lola 解析器生成器产生（Debian 构建依赖
  `lola`），`snek-builtin.h` 由自带 `snek-builtin.py`（仅 sys/argparse）
  产生。

## 依赖决策（零 conan 依赖）

| 依赖 | 上游默认 | 本配方做法 | 理由 |
|------|----------|------------|------|
| readline | `-lreadline`（STATIC=0） | `STATIC=1` 且覆盖 `LIBS=-lm` | readline 仅影响交互式行编辑；STATIC=1 自带的 `-static` 在 OHOS 上不可用，故一并覆盖。脚本执行不受影响 |
| lola | 构建时运行 | 补丁预置官方 lola 1.8 的输出 | OHOS CI/制品仓无 lola 包；单文件纯 Python 工具，输出对固定 `snek-gram.ll` 确定（见下） |
| python3 | `snek-builtin.py` | 直接使用 HMBS 注入的 python3 | 自带脚本，只用标准库 |

lola 输出确定性验证（已在本机实测）：以干净相对路径运行
`lola -DSNEK_SLICE -DSNEK_DICT -o snek-gram.h snek-gram.ll`，
同名输出字节完全一致（101067 字节，
sha256 `3327c72a07ac8c8f9263c53615db89b04c080b2882c141c5eeceb83a50e2c32d`；
两次运行唯一的差异是 `#line` 中的输出文件名，固定输出名即消除）。
任何人都可用官方 lola 1.8 复现该补丁内容。补丁应用后
`ports/posix/snek-gram.h` 时间戳新于 `snek-gram.ll`，make 不会再调用 lola。

## 构建命令（配方 build() 实做）

```bash
make -j1 V=1 CC="<conan conf tools.build:compiler_executables:c>" STATIC=1 LIBS="-lm" snek
# cwd = ports/posix；R33：编译器取自 Conan conf，不用 shell 环境变量；R9：-j1
```

打包：仅拷贝 `ports/posix/snek` 到 `bin/`，`COPYING` 到 `licenses/`，
上游测试证据 `hmbs_upstream.json` 到 `res/`（供 test_package 缓存命中轮复述）。

## 上游测试盘点（总数 51，口径 auto）

来源：`test/Makefile` 变量（单一可解析框架，配方直接解析该文件计数）：

- `SUCCESS_TESTS`：35 个 `pass-*.py`，以构建出的 snek 运行，期望退出码 0
- `FAIL_TESTS`：13 个 `fail-*.py` + `$(SYNTAX_TESTS)` 展开的 3 个
  `fail-syntax-*.py`，共 16 个，期望退出码 1
- `test/generate-chain-op.py` 是用例生成器脚本，不是测试用例，不计入

配方在运行前做一致性校验：Makefile 名单与磁盘 `pass-*`/`fail-*` 文件集合
必须完全相等，否则直接报错（不静默跳过）。qemu-arm/qemu-riscv 两 leg 需要
异架构固件，在 OHOS aarch64 上无法构建更无法执行，未纳入计数；
python3 leg 只是在 CPython 下复核测试文件本身，不验证本产物，未纳入计数。
总数声明仍是完整的 51（非可运行子集）。

## 证伪（harness 有效性）

- 负对照内建：16 个 fail-* 用例期望退出码 1。若被测二进制是永远返回 0 的
  桩，这 16 个会全部失败，套件必然变红——harness 能抓到失败。
- 非空检查：配方要求被测二进制与每个测试脚本体积非零，否则直接报错。
- 无静默跳过：skipped 恒为 0；任何名单/磁盘不一致都按构建失败处理，不记为跳过。

## test_package（消费者视角，7 检查）

`test_snek.py` 用上游套件覆盖过的语言子集写 6 个检查（整数运算、字符串、
列表、字典、函数+循环、math 内建），每个成功打印一行 `CHECK-OK: <名>`，
失败打印 `FAIL` 并 `exit 1`；另加 `snek --version` 含 "1.13" 烟囱检查。
计数源：脚本内 `check(` 调用行数（期望 6，运行时先断言）与重定向日志中
`CHECK-OK: ` 前缀行数，不做 stdout 子串算术。

## 已知限制

- 交互式 REPL 无 readline 行编辑（fgets 回退），属功能降级而非缺陷。
- `snek.desktop`/`snek.1` 不打包（桌面集成文件，OHOS 无需）。
- 嵌入式固件目标（avr/arm/riscv）不在本包范围内。

## 验证状态

- 本机：源码哈希、上游名单解析（35+16=51）、lola 输出确定性、配方语法
  （py_compile）已验证。
- 真机：待 HMBS 预检回填上游 51 项与新增 7 项的实测通过率，再定稿 PR 正文数字。

## 真机 hardening 记录（预检 51 项中 42 通过、9 失败之后）

- 现象：fail-arg-dup1/dup2/fail-arg-unknown 三例只打印出 `bad arg "` 前缀
  随后进程 SIGSEGV（rc -11），而上游 `test/Makefile` 对 fail-* 的判定是
  退出码 == 1。
- 根因：`snek_error_arg()` 与 `snek_undefined()` 把 `snek_name_string()` 的
  返回值直接传给 `%s`，而该函数在 id 未知时明确返回 NULL；`puts_clean()`
  无条件解引用即崩。重复/未知实参的检测逻辑本身正常，崩的是报错打印。
- 修复：配方在 build() 中对两处加 NULL 守卫——查不到名字时改报
  `bad arg id %d` / `undefined id %d`，依然走 `snek_error` 置 abort 并以
  exit 1 退出；检测逻辑不动，查找成功时行为与上游完全一致。
- 其余 6 例（pass-for-range/pass-math/pass-op/pass-random/
  pass-interpolate-str 为 rc1，pass-args 为 rc-11）尚缺失败输出证据；
  harness 已改为记录每个用例合并输出并在失败时打印末尾 50 行，待下轮
  预检日志定位后再修，不做无证据改写。
- 策略周期 3（上一周期连续三次未通过）：上一方案（无输出证据的源码猜测
  改写）对剩余 6 例无效——NULL 守卫把 fail-arg-* 三例从崩溃转为通过
  （42→45），但 pass-args 仅从 rc-11 转为 rc1，其余 5 例纹丝不动，证明
  剩余失败与报错打印路径无关，盲改语义只会浪费真机轮次。本轮换路线：
  不再改解释器语义，只改 harness 证据存活率——每失败用例只发一行
  `HMBS diag fail-detail <file>: rc=.. expect=.. last=<末非空行>`，并把
  同样短证据拼进抛出的 ConanException 消息（摘要必逐字引用异常消息，
  而多行输出会被判"无关"截掉）。计数口径、判定逻辑、源码语义均未动，
  待下轮预检带回 6 例各自末行证据后再做定点语义修复。
- 策略周期 4（单行证据已带回 6 个首错行，仍不足以定根因）：6 个首错为
  `for-range（空输出）/ math factorial(9)错值 / op（空输出）/
  random r=-96 / args具名id非法 / interpolate（12串,None）错配`。
  本轮通读上游 1.13 全套源码（exec/func/code/name/poly/string/list/
  lex/parse/gram.ll/math/random/print/def）逐项证伪：字节码读写宽度、
  调用栈平衡、名字表顺序、内建分发表、字面量编码、比较器精度、
  lola 语法动作与构建标志（-DSNEK_SLICE/-DSNEK_DICT）均与上游一致，
  无证据指向某个确定语义补丁，故继续禁盲改，改用主动实验探针：
  配方在官方 51 项跑完、标记发射后，对失败用例在 build_folder 内运行
  诊断变体（不计数、不发标记、不改上游文件、不抛异常）：静默失败用
  同行 `;` 插入 announce print 定位行号（不移行号）；for-range 打印
  product 真值（区分循环次数/值损坏/比较器）；math 最小复现打印
  factorial(9)（区分派发错误与历史状态污染）；random 单元素/逆序元组
  （区分值相关与位置相关）；args 最小具名调用（机制死活）；interpolate
  小规模复现（尺寸相关性）。探针摘要拼入异常消息，待下轮日志回填后
  做定点修复并删除探针代码。另记：snek-code.c 的 snek_op_operand_size
  漏了 snek_op_dict 分支（写/读均为 2 字节偏移，唯遍历步长返回 0），为
  已确认的上游潜在缺陷，但 6 个失败语句块均不含 dict 字面量，与本轮
  失败无关，暂不改动，后续跟进。

- 策略周期 5（上一周期连续三次未通过，换路线）：上一方案（打印末非空行 + 单元素/逆序/最小复现等机制隔离探针）已带回 6 个首错行，但仍无法区分“值损坏”与“比较器损坏”（for-range 打印 product 为 362880 却仍进 exit(1)；math 孤立 factorial 正确而全量比较失败；op 卡在 (2**3)**4 处；random 大 mod 报负值；args 连最小具名调用都报负 id；interpolate 大串失败而小串通过）。本轮不再沿用行号定位路线，改走两条可证伪路线：① 修两个与证据最吻合的确定性源码缺陷——snek-code.c 的 snek_op_operand_size 漏 snek_op_dict 分支（与 list/tuple 同为偏移操作数，漏则 code walk 失步；interpolate-str 末尾即含 dict 字面量），以及 snek_code_add_number 对越界 float→int8 先强转的 UB（大字面量 362880/4096/300/100000 等全部越界，clang -O3 可据此假设值域而误编码；小字面量 30 不越界故小串通过——与观测到的尺寸相关性一致；越界检查后 dormant，不影响已通过的 45 项）；② 探针升级为值级对比证据——for-range/math/op 打印值、==、!=、差值三件套，args 同脚本内对比 positional 与 named，interpolate 打印各段 len，直指下轮定点修复。
