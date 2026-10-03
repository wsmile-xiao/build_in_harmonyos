# spaced 1.2.0-201605 适配笔记

## 编译环境

- 构建系统：**没有构建系统**。整棵树 9 个文件，唯一的 `Makefile` 有 100 字节、
  只有 `all` 一个目标，写死
  `g++ -O3 -fopenmp -std=c++11 src/spaced.cc src/variance.cpp src/patternset.cpp -o spaced`，
  既没有 `install` 也没有 `check`。因此 `build()` 直接驱动 clang++，`package()` 自己捡产物
  （与 `archives/s/smem/1.5` 同一写法）。
- 编译日期：2026-10-03
- 编译器：clang 15（`tools.build:compiler_executables.cpp` = OHOS NDK 侧 clang++，
  target `aarch64-linux-ohos`）
- profile：`ohos-aarch64-wsl`（host/build 同 profile，与 CI 一致）
- 状态：built

## 编译步骤

`conan create archives/s/spaced/1.2.0-201605 --name=spaced --version=1.2.0-201605
-pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing`

实际执行的编译命令行（完整日志见本地 `reports/conan-create.log`；该文件被仓库
`.gitignore` 的 `reports/` 规则忽略、不随 PR 提交，文末「复现」一节给出完整命令）：

```sh
/opt/lpk-fixed/clang++ -O3 -std=c++17 -fopenmp -static-openmp \
    src/spaced.cc src/variance.cpp src/patternset.cpp \
    -o <build_folder>/spaced
```

上面的 `/opt/lpk-fixed/clang++` 只是**本机 WSL profile** 里
`tools.build:compiler_executables.cpp` 的取值（CI worker 上同一键指向 NDK 的
`/data/service/hnp/bin/clang++`）；配方本身不含任何绝对路径，换机器不用改。

- 编译器来自 `self.conf.get("tools.build:compiler_executables")`（R33：不裸用 `${CXX}`）。
- `-std=c++<cppstd>` 由 `compiler.cppstd`（profile 里是 17）推出，
  `gnu` 前缀会被剥掉再补回 `c++`，因此 `gnu17` / `17` 都能正确落到 `-std=c++17`。
- `-O3` 是上游 Makefile 的选择，原样保留。
- `-fopenmp` 是**必需**而不是优化项，见「问题 1」。
- `-static-openmp` 是本平台必需的，见「问题 4」。

编译输出只剩一条上游遗留警告，无 error：

```
src/spaced.cc:189:34: warning: while loop has empty body [-Wempty-body]
            while(str[++i]!='\n');
1 warning generated.
```

打包落点（`package(): Packaged 3 files: COPYING, README, spaced`）：

| 路径 | 内容 |
|------|------|
| `<pkg>/bin/spaced` | 主程序（0755，Conan copy 会规范化权限，recipe 里显式 `os.chmod` 复位） |
| `<pkg>/licenses/COPYING` | 上游 GPL-3 全文 |
| `<pkg>/share/doc/spaced/README` | 上游唯一的用户文档（选项说明） |

运行期依赖（实测 `readelf -d <pkg>/bin/spaced`）：

```
NEEDED   Shared library: [libc.so]
RUNPATH  Library runpath: [/usr/lib/llvm-15/lib]
```

只剩 `libc.so`（见问题 4）。RUNPATH 是 clang 宿主工具链的 resource dir，
交叉场景下无意义，但程序不依赖它，故不处理。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-fopenmp` 不是可选项 | `src/sort.h` 有 7 处 `#pragma omp parallel for`（行 273/423/438/470/567/658/671）以及 `omp_get_thread_num()`、`omp_set_num_threads()`、`omp_set_dynamic()`；`sort.h:35` 还直接 `#include <omp.h>`。不打开 OpenMP **不会编译失败**，而是把 `#pragma omp` 当未知 pragma 忽略、退化成错误结果 | `build()` 里硬编 `-fopenmp`。这类「静默降级」比编译错误危险，所以写进 notes 而不是当作可选项 |
| 2 | `src/sort.h:29:10: fatal error: 'tr1/unordered_map' file not found` | `<tr1/unordered_map>` 是 libstdc++ 专有的 TR1 遗留头，libc++ 不提供。整棵树从未使用 `tr1::` 命名空间（`grep -n 'tr1' src/` 只命中这一行 include），真正用的是第 32 行的 C++11 `<unordered_map>` | 补丁 `0001` 删除该 include。**这一条是 libc++ 专属**：libstdc++ 有这个头 |
| 3 | `src/patternset.cpp:25:6: error: no type named 'default_random_engine' in namespace 'std'` | 顶层 `std::default_random_engine generator(time(0));` 依赖 `<random>`。实测**两条工具链都不传递包含**该头：aarch64 clang15+libc++ 与 x86_64 g++ 11.4+libstdc++ 在未 include 的原始树上都报同一句 | 补丁 `0001` 在 `patternset.cpp` 顶部显式 `#include <random>`。**这一条与 libc++ 无关** |
| 4 | 二进制带一个 loader 找不到的 `DT_NEEDED: libomp.so`，`spaced -h` 直接 `Error loading shared library libomp.so: No such file or directory`（后续 8 条 `Error relocating ...: omp_set_dynamic: symbol not found`） | `-fopenmp` 动态链 OHOS SDK 的 `libomp.so`，但 clang 把 RUNPATH 写成宿主工具链的 resource dir `/usr/lib/llvm-15/lib`，不是交叉 sysroot；目标镜像的默认搜索路径里也没有 libomp | `build()` 里改用 `-static-openmp`，静态链 OpenMP 运行时 ⇒ `DT_NEEDED` 收敛到只剩 `libc.so`，消费者测试能真跑起来。本仓 `archives/a/aaphoto/0.45` 证明 OHOS NDK 确实带 libomp（其 0001/0002 补丁删掉写死的 `-lgomp`、交给 clang 的 `-fopenmp`），但它是动态链；CLI 工具还要被 CI 的 test_package 真执行，本地起不来就没法验，因此选静态 |
| 5 | `src/patternset.cpp:188/195/196/203: error: call to 'abs' is ambiguous` | `std::abs()` 作用在 `uint32_t` 成员上：OHOS sysroot 的 `int abs(int)`（`<stdlib.h>:58`）与 libc++ 的 `long abs(long)` / `long long` / `float` / `double` / `long double` 对 `unsigned int` 实参**都是同秩转换**，而「有符号类型能容纳另一有符号类型」这条打破平局的规则在实参无符号时不适用 ⇒ 重载决议失败。**实测 aarch64 clang15+libc++ 与 x86_64 g++ 11.4+glibc 报同一批错**，所以这不是 OHOS/libc++ 专属缺陷 | 补丁 `0001` 删掉那三段。它们分别以 `if (size < 0)`、`if (max_dontcare < 0 || min_dontcare < 0)`、`if (weight < 0)` 为条件，而这些成员都是 `uint32_t`（`patternset.h` 的构造函数签名即 `uint32_t`），条件恒假、分支不可达，删除不改变任何行为。Debian 自己的 quilt 补丁 `0004-signed.patch` / `0005-fix-absolute-value-of-unsigned.patch` 做的正是同一件事 |
| 6 | **`spaced -f <pattern>` 静默失效**：stderr 打出 `FORMAT-ERROR: Pattern containes illegal characters!` + `ERROR! File 'x' is an empty file!` + `Wrong values for weight, pattern number or pattern length!`，然后**回退到随机种子集照常输出结果**，退出码仍是 0 | AAPCS64 规定 plain `char` **无符号**（与 AArch32 相反）。`patternset::ReadPattern()` 把 `ifstream::get()` 的 `int_type` 收进 `char c`，EOF 的 `-1` 变成 `0xff`，于是 `-1 == (int)c` 不再命中，落进 `else { bad = true; SecureMessage("format", -1); }`。这是**只有 aarch64 才暴露**的缺陷：同一份源码用 x86_64 g++ 编，原生跑同一个 pattern 文件无任何错误 | 补丁 `0002` 把局部变量改成 `std::char_traits<char>::int_type c`，EOF 判定恢复。测试断言 A6 专门盯这条（stderr 不得出现 `FORMAT-ERROR` / `is an empty file`） |

### 问题 6 的取证（这是本包唯一的平台专属缺陷）

同一份源码、同一份 pattern 文件 `11001`，只换目标架构：

| 目标 | 编译 | `spaced -f 11001 -t 2 seq.fasta` 的 stderr |
|------|------|-------------------------------------------|
| x86_64 Linux / g++ 11.4 / libstdc++，**打 0002 后**（或任何 plain char 有符号的目标） | `g++ -O2 -fopenmp -std=c++17` + 补丁 | 空（pattern 文件被正常读取） |
| aarch64 OHOS / clang 15 / libc++，**打补丁前** | `clang++ -O3 -fopenmp -std=c++17` | `FORMAT-ERROR` + `is an empty file` + `Wrong values ...` |
| aarch64 OHOS / clang 15 / libc++，**打 0002 后** | 同上 + 补丁 | 空 |

三面对照共同把根因钉死在「plain char 符号性」：只有**未打补丁且目标是 plain char
无符号架构**这一格会出错；同源码在有符号目标上正常，同架构加补丁后正常，
同架构加 `-fsigned-char`（把 plain `char` 变回有符号）也正常。
独立审计复核时另测了一格更强的组合：aarch64 + **未打补丁** + `-fsigned-char`
⇒ 18/18 通过且 `dna.err` 为 0 字节，与本表第三行等价。

本包选择改源码而不是加 `-fsigned-char`：改源码对有符号目标行为完全不变，
而编译开关会被任何自行重建的下游漏掉。

## 源码修改

全部以 `patches/` 下 2 个补丁交付，由 difflib 逐文件生成，补丁文本未手工编辑。
`0001` 对「未改动的 `+dfsg` 原始树」生成；`0002` 对「`0001` 应用后的累积状态」生成
（与 Conan `apply_conandata_patches` / quilt 的顺序应用语义一致），因此 **`0002` 必须在
`0001` 之后应用**，其 hunk 行号对应 `0001` 之后的源码。两个补丁都不含任何平台宏
（`__OHOS__` / `OHOS` / `HarmonyOS` 一律没有，R8 合规）。

| 补丁 | 被改文件 | 内容 | 是否含平台宏 | 是否平台专属 |
|------|----------|------|--------------|--------------|
| `0001-libcxx-portability.patch` | `src/sort.h`、`src/patternset.cpp` | 删 `<tr1/unordered_map>`；加 `#include <random>`；删三段不可达的 `std::abs(uint32_t)` 分支 | 否 | 否。其中 `<tr1/...>` 那一条 libc++ 专属；`<random>` 与 `std::abs` 两条在 g++ 11.4 + glibc 上同样必需（已实测） |
| `0002-aarch64-char-signedness-eof.patch` | `src/patternset.cpp` | `ReadPattern()` 的 `char c` → `std::char_traits<char>::int_type c` | 否 | 是（仅 AAPCS64 plain char 无符号暴露） |

## 依赖版本

**Conan 主机依赖：0 个。** `requirements()` 不声明任何包，`package_id` 里只有 settings。

- 唯一非标准头是 `<omp.h>`（`sort.h:35`），来自编译器/OpenMP 运行时，不进 Conan 依赖。
- 唯一链接的外部运行时是 OHOS NDK 的 libc++（静态）与 OpenMP 运行时（静态）。
- 不链接任何系统同名库（R26），也不需要预编译依赖（R36 对下游无约束）。
- `conan download "spaced/1.2.0-201605" -r=ohpcd --only-recipe` → `error:system acceleration
  policy not enabled`，即该版本尚未发布。同批对照三个**不在本地缓存里**的包
  （`spaced/9.9.9`、`curl/8.14.1`、`libarchive/3.7.9`）返回完全相同的错误，
  而已缓存的包返回 `Skip recipe ... already in cache`（不联网，无法作为可达性对照）。
  「制品仓可达」这一点的独立佐证是门禁的 `L0j: version not in registry yet (first publish)`。
  （注：`conan download` 是 R35 规定的唯一正确判据；不要用 `conan list`。）

## 上游测试清点与五维数字（R51）

**上游测试程序数：0。** 五条清点证据（均在 `spaced_1.2.0-201605+dfsg.orig.tar.xz` 内实测）：

1. `Makefile` 全文 100 字节，目标全集只有 `all`
   （`grep -nE '^[a-zA-Z_-]+:' Makefile` → `2:all:`）。
2. `make -n check` → `make: *** No rule to make target 'check'.  Stop.`
3. `find . -iname '*test*' -o -iname '*spec*' -o -iname '*example*'` → 空。
4. `grep -rn 'assert(\|EXPECT_\|TEST(\|CHECK(' src/` → 空。
5. 非标准头只有 `<omp.h>`（`sort.h:35`）；README 只写
   「to compile type: make / run with: ./spaced [options] <sequence file>」。

**HarmonyOS 上可运行的上游测试程序数：0。** 没有跳过任何东西：上面 5 条检查都真跑过，
「没有测试」是被实测确认的事实，不是环境缺失。因此 `build()` 里不写 `make check`
（写了必红），与 `archives/s/sarg/2.4.0` 同一结论、同一取证形态。

**补全的消费者测试：18 项断言**（`test_package/test_spaced.sh`，全通过）。
spaced 是 CLI 工具，真正的消费者测试必须把 FASTA 喂进去、把距离矩阵断言出来，
而不是「跑起来没报错」。

| 维度 | 数字 |
|------|------|
| 上游单元测试 | 0 |
| 上游集成测试 | 0 |
| 适配后单元测试 | 0 |
| 适配后集成测试 | 18（全通过） |
| 其中鸿蒙特有 | 1（A6：`-f` 模式文件必须被接受，用于钉死 AAPCS64 plain char 无符号回归） |
| 适配后合计 | 18 |

断言清单（`test_spaced.sh`）：包内 `bin/spaced` 可执行；`-h` 退 0 且打出 Usage；
帮助里有 `-f <file>`；`--version` 退 0（L2 冒烟契约）；四次数据调用全部退 0；
stderr 无 `FORMAT-ERROR`/`is an empty file`（A6，鸿蒙特有）；DNA 输入报
`3 DNA sequences read`；蛋白输入报 `3 protein sequences read`（覆盖 DNA / 蛋白两条分支）；
两个矩阵文件非空；矩阵首行是 3；矩阵行数 = 序列数 + 1；行标签与输入顺序一致；
DNA 矩阵对角线全 0；蛋白矩阵对角线全 0；DNA 矩阵对称；DNA 非对角距离存在且非 0；
蛋白非对角距离存在且非 0；`-t 1` / `-t 2` / `-t 4` 三次结果逐字节相同。

### 为什么测试必须用 `-f`

`patternset.cpp:25` 是 `std::default_random_engine generator(time(0));`，
而 `spaced.cc` 在没有 `-f` 时会走 `variance_obj.Improve(5000)` —— 用 `time(0)` 播种的
5000 轮随机种子改进。所以**不给 `-f` 的输出每次都不一样**，写不成可复现断言。
给了 `-f`（本包用长度 5、权重 3、首尾均为匹配位的 spaced seed `11001`）之后，
种子集合被钉死，矩阵逐位确定，A18 才能拿 `-t 1` 和 `-t 4` 做逐字节比对，
顺带把 OpenMP 归约的确定性也一起验掉。

## L1e 反向破坏自测（本地已跑）

把包目录里的 `bin/spaced` 移走再跑同一条 `conan create` 测试命令：
`ASSERTS=18 PASS=2 FAIL=16`，退出码 1 ⇒ 测试确实依赖被测包产物，不是空壳。

## 已知限制

- **上游站点已下线**：`http://spaced.gobics.de/content/spaced.tar.gz`（`debian/copyright`
  记录的官方 Source）不再解析，且它当年提供的是「预编译 x86 二进制 + 源码」而不是干净的
  发布包。`conandata.yml` 因此指向 Debian pool 的 `+dfsg.orig.tar.xz`：Debian 的
  `get-orig-source` 只重命名顶层目录并删掉 `Files-Excluded` 声明的预编译二进制，
  源码文件与上游逐字节一致；同一份 orig.tar.xz 在 Ubuntu universe 也在，sha256 相同，
  构成第二个发行源的交叉核对。若评审要求上游官方 URL，只能走 Issue 通道（源码不可得），
  不适合本 PR 的形态。
- **命令行动作依赖 `-f`**：不打补丁 0002 的话 `-f` 在 aarch64 上静默失效，
  工具会改用随机种子而不报错。已用 A6 钉死。
- **无上游测试可比对**：适配后 18 项断言全部是补全的消费者测试，
  PR 正文里的「上游用例数」必须写 0。
- `-t` 默认值是 15 线程（`spaced.cc:32` 的帮助文本写「default: 25 threads」，
  与代码里的 `threads = 15` 不一致 —— 上游自己的文档 bug，未改）。

## 附：与本仓先例的关系

| 先例 | 借鉴点 |
|------|--------|
| `archives/s/smem/1.5` | 无 Makefile / Makefile 不可用时，build() 直接调编译器、package() 自己 copy |
| `archives/s/sarg/2.4.0` | 上游 0 测试时的 MANIFEST 取证形态与 R51 五维数字口径；CLI 工具用 `test_xxx.sh` + `package_folder` 驱动真二进制 |
| `archives/a/aaphoto/0.45` | OHOS 上 OpenMP 的可用性证据（clang `-fopenmp` 能拿到 NDK 的 libomp） |
| `archives/r/rtl-wmbus/1.1.0` | `reports/audit-result.json` 的落位（`reports/` 被 .gitignore 全局忽略，需 `git add -f`） |
