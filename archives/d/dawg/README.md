# Dawg — 带 indel 的 DNA 序列演化模拟器

Dawg（DNA Assembly With Gaps）是一个 DNA 序列演化模拟器：给定 Newick 格式的系统发育树、
核苷酸替换模型（GTR/JC/K2P/K3P/HKY/F81/F84/TN）与 indel 形成模型（NB/PL/US），它按连续时间
模拟整棵树上每个位点的替换与插入/缺失事件，并记录每条谱系的 gap 历史，从而直接输出**已知
真实比对**（FASTA/Nexus/Phylip/Clustal 四种格式）。真实比对与真实系统发育树在实测数据中几乎
不可得，因此这类模拟器是评估比对算法与建树方法准确性的标准工具。

上游为 Reed A. Cartwright 2004-2009 年的研究软件，v1.2 于 2009-04-26 发布后再无新 tag
（master/2.0 分支长期处于未发布开发状态）。

## 功能概述

- 按系统发育树模拟核苷酸替换，支持 8 种替换模型与速率异质性（Gamma/Alpha/Iota）
- indel 形成模型：NB（负二项）、PL（幂律）、US（用户给定大小分布），配合 Lambda/GapParams
- 输出树中任意节点的序列（`Tree` 语句里给节点加标签即落盘），可输出任意内部节点
- 四种比对格式：Fasta / Nexus / Phylip / Clustal，按输出文件名扩展名自动推断
- 输出前后可插入自定义文本块（`Out.Block.Head/Before/After/Tail` + `Out.Subst` 变量替换）
- `Seed` 可显式指定，同一配置输出逐字节可复现（本包测试即依赖该性质）
- 可输出多条重复数据集（`Reps`）、`Translate` 直接输出氨基酸序列

## OHOS 适配要点

- **CMake 下限过低**：上游 `CMakeLists.txt` 首行是 `CMAKE_MINIMUM_REQUIRED(VERSION 2.6 FATAL_ERROR)`，
  CMake 4.x 已删除 <3.5 的兼容策略，未处理时报
  `Compatibility with CMake < 3.5 has been removed from CMake.`。配方在
  `cmake.configure()` 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（Debian 打包用同一手段）。
  该策略检查发生在 CMakeLists 顶部，早于依赖 toolchain 生效的变量注入，必须走命令行缓存变量。
- **flex/bison 是硬依赖**：`src/CMakeLists.txt` 用 `CMakeUserUseBison/Flex` 现成生成
  `parser.tab.*`/`lex.parser.cpp`，缺任一直接 `SEND_ERROR "Bison and Flex are required"`。
  二者按构建期工具用 `tool_requires("bison/3.8.2")`、`tool_requires("flex/2.6.4")` 提供，
  配合 `VirtualBuildEnv` 注入 PATH，不依赖设备或 CI worker 的系统 PATH。
- **平台名**：CMake 无 OHOS 平台模块，按仓库惯例显式声明 `CMAKE_SYSTEM_NAME=Linux`
  （OHOS 即 Linux 内核，本程序只用标准 C/C++ 与 POSIX 基础接口）。
- **C++17 可移植性补丁（补丁 0002）**：上游是 2009 年代码，使用 `std::auto_ptr`
  与 `std::unary_function`，二者在 C++11 弃用、**C++17 移除**，而本仓库 profile 强制
  `compiler.cppstd=17`，因此必须补丁：4 处 `std::auto_ptr` → `std::unique_ptr`
  （这些成员只做 `.get()`/`.reset()`/解引用，无所有权转移式拷贝，语义等价），
  `LinearFunc` 去掉已移除的基类并自带 `argument_type`/`result_type` typedef。
  该补丁与平台无关（任何 C++17 工具链都需要），实测不改变程序输出。注意：裸 `cmake`
  （clang 15 默认 gnu++14）只会报 deprecated 警告，该错误仅在按 profile 的 C++17 构建时暴露。
- **bison 运行时数据目录**：ohpcd 的 `bison/3.8.2` 把 pkgdatadir 硬编码成 `/share/bison`，
  直接调用会报 `bison: /share/bison/m4sugar/m4sugar.m4: cannot open`。配方把
  `BISON_PKGDATADIR` 指向包内真实位置，并用 `M4` 指向 `m4/1.4.19`。
- **测试基准刷新（补丁 0001）**：见下节「已知问题」。

## 已知问题（上游）

1. **上游自带测试的基准过期**：`tests/test0.fasta` 仍是 v1.0.0 RNG 语义下生成的输出；
   v1.1 起 `rand_real()`/`rand_bool()` 由 ILP32 位拼接改为 `(double)u/2^32`、
   比较由 `<=` 改为 `<`，模拟结果随之改变，基准却从未重生成。
   上游在 CMake 化 v1.2 时也没有迁移该测试（`tests/CMakeLists.txt` 是 0 字节空文件，
   脚本仍在读 autotools 的 `top_srcdir`），因此 ctest 从不运行它；Debian 自 1.2-2 起在
   `debian/rules` 里以 `|| true` 显式忽略该失败。本包用补丁 0001 以 v1.2 的真实确定性
   输出刷新基准（该输出与 Debian 在 amd64/glibc/GCC 上用未修改源码得到的输出一致）。
   上游缺陷追踪编号为 `#56`，其依据是 Debian 官方源码包 `debian/rules` 的注释与 Debian 邮件
   列表归档（两者原始字节已入库于本包 `archives/d/dawg/1.2/reports/evidence/`，见该目录 README）；
   注：该设备访问该 issue 路径返回 HTTP 404（`https://github.com/` 本身返回 200），
   故本包未直接读取该 issue 页面，编号依据见 `reports/evidence/`。
2. **`-o`/`File` 的格式推断大小写敏感且报错信息不渲染**：`src/dawg.cpp:477-491` 按扩展名
   匹配 `Fasta|fas|Nexus|nex|Phylip|phy|Clustal|aln|poo|txt|out`（大小写敏感），
   `-o out.fasta` 会被判 `Unknown file format, "%s".` —— 连 `%s` 都没有被格式化。
   使用短名（`fas`/`nex`/`phy`/`aln`）或与配置里 `Format` 一致的长名即可绕过。
3. **Power Law 模型参数域**：`GapModel = "PL"` 要求 `GapParams = {a>=1.0, Max>=1}`，
   不能沿用 NB 的 `{r,p}` 形式，否则报 `Power Law Model requires Max >= 1.`。

## 依赖关系

### 编译依赖

- `bison/3.8.2`（tool_requires，生成 parser.tab.cpp/hpp）
- `flex/2.6.4`（tool_requires，生成 lex.parser.cpp）
- `m4/1.4.19`（tool_requires，bison 运行时宏库）
- CMake ≥ 3.5 兼容模式（CMake 4.x 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`）
- 语言标准：C++17（profile 强制；上游代码需补丁 0002 才能编过）

### 运行依赖

- `libc++_shared.so`（C++ 运行时库）与系统 libc；无第三方运行时依赖。
  实测 `bin/dawg` 的 `NEEDED` 仅两条（`libc++_shared.so`、`libc.so`）——OHOS/musl 下 libm 符号
  已并入 libc，不单独出现在 NEEDED。

## 交付物

- `bin/dawg` — 唯一可执行产物
- `share/dawg-1.2-release/{examples/*.dawg,lambda.pl,outsplit.pl,nexus2fasta.pl,varrep.pl}`
- `share/applications/dawg.desktop`、`share/pixmaps/dawg.png`
- `doc/dawg-1.2-release/{copying.txt,readme.txt,changelog.txt}`、`licenses/copying.txt`

## 参考资料

- 上游仓库：https://github.com/reedacartwright/dawg （tag `v1.2`）
- 项目主页：http://scit.us/projects/dawg
- 论文：Cartwright, R.A. (2005) DNA Assembly With Gaps (Dawg): Simulating Sequence Evolution.
  *Bioinformatics* 21 (Suppl. 3): iii31-iii38
- 上游测试缺陷追踪：`reedacartwright/dawg` issue **#56**（编号依据见本包
  `archives/d/dawg/1.2/reports/evidence/`：Debian 官方包 `debian/rules` 注释 + Debian 邮件列表归档）
- Debian 源码包（1.2-5，含忽略该测试的 `debian/rules`）：https://sources.debian.org/src/dawg/
