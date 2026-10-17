# proda — ProDA (Probabilistic Database Alignment)

## 软件简介

ProDA 是一个**概率式数据库比对 / 多序列比对（MSA）**命令行工具。它用隐马尔可夫模型在
序列库里找出彼此同源的区域，再把这些区域以"**块（block）**"为单位做渐进式多序列比对。
与普通全局/局部比对器的区别是：它专门处理**含重复与重排的蛋白序列**
（对应论文 Nucleic Acids Research 2006 34(20):5932-5942）。

- **上游主页**：http://proda.stanford.edu/
- **许可**：public domain（上游包内无任何许可声明文件，口径取自 Debian `debian/copyright` 的 `License: PD`）
- **语言**：C++（17 个 `.cc` + 18 个 `.h`，**没有 `.c` 文件**）
- **构建系统**：裸 Makefile —— 非 autotools、非 cmake，且**没有 `configure`、没有 `install` 目标、没有 `PREFIX` 变量**
- **外部依赖**：**零**（链接行只有 `-lm`）
- **产物**：单个可执行文件 `proda`（`package_type = "application"`，不产出库与头文件）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 1.0 | built ✅ | 2026-09-25 | 3 |

## 使用方法

```bash
proda [-L length] [-silent] [-posterior] [-tran] [-fasta] filename(s)
```

```bash
# 一个多序列 FASTA
proda sequences.fa > aligned.txt

# 多个独立 fasta 文件（支持 filename(s) 复数形式）
proda alpha.fa gamma.fa > aligned.txt

# 放宽最小块长（默认 30 个残基）
proda -L 20 sequences.fa > aligned.txt

# 只要结果、不要进度
proda -silent sequences.fa > aligned.txt
```

**输出约定**：比对结果写 **stdout**，版本横幅与进度写 **stderr**（重定向时别把两者混在一起）。
输出里的块报告形如：

```
alpha(1-105) gamma(1-105)

alpha    MKVILLFPVFPLPSVFVLTTSACVATAGMNLCTVSKLIDLGTELATLILEALYNKYQSDF
gamma    MKVILLFPVFPLPSVFVLTTSACVATAGMNLCTVSKLIDLGTELATLILEALYNKYQSDF
         ************************************************************
```

最后一行是逐列保守性标注：`*` 完全一致、`:` 强相似、`.` 弱相似、空格不保守。

### 选项

- `-L <length>`：最小比对块长度（残基数），默认 **30**。必须是整数，否则以退出码 1 报错退出。
- `-silent`：关掉进度输出，比对结果照常产出。
- `-posterior`：用后验概率代替 Viterbi 路径 —— **实测会把同源块边界扩宽**
  （同一输入默认模式给 `1-105`，后验模式给 `1-106`，把末端不一致的残基按概率纳进来）。
- `-tran`：启用传递性闭包（A~B、B~C 则 A~C）。
- `-fasta`：上游声明的输出模式开关。**已知限制见下**。

## 已知限制

1. **`-fasta` 在当前输入下与默认输出逐字相同**（`cmp` 实测）。源码里 `fastaOutput` 只有赋值、
   找不到产生差异的输出分支，疑为上游未完成特性。本适配**未修改上游该行为**。
2. **找不到达标同源块时 stdout 为空**（例如 `-L` 大于序列长度，或序列彼此无关）。
   这是 proda 的正常语义，不是失败 —— 退出码仍是 0。
3. **输入文件不存在时以 SIGABRT 退出（实测退出码 134）** 而不是优雅报错 ——
   上游 `ASSERT` 宏直接 abort，本适配未改其错误处理风格。
4. 上游 `LinkTable.h` 引用了一个不存在的 `Link.h`，但没有任何文件包含 `LinkTable.h`
   （**死代码**），因此不影响构建，未做修改。

## 适配要点（3 个 portability 补丁）

| 补丁 | 机制 | 症状 |
|---|---|---|
| `0001-Main.cc-name-shadowed-libc-errno` | 局部变量取名 `errno`，与 musl 的 `errno` **宏**冲突 | 编译期 `illegal initializer`（glibc 下静默通过且遮蔽真 errno） |
| `0002-Sequence.cc-missing-stdio-h-include` | 用了 `fprintf` 却没直接 `#include <stdio.h>`，靠 glibc 传递包含 | 编译期 `use of undeclared identifier 'fprintf'` |
| `0003-Utilities.cc-fgetc-EOF-into-unsigned-char` | `char ch;` 接 `fgetc()` 再与 `EOF` 比较；**aarch64/clang 上 `char` 默认 unsigned**，EOF 折成 255 永不相等 | **编译期零告警**，运行时读文件死循环 → `std::bad_alloc` → abort(134) |

第三条是本包真正的深坑：**它不在编译期暴露**，看起来像"OHOS 运行时/内存不行"，
实际是 `char` 有符号性在两个架构上语义不同。详见 `1.0/notes.md`。

编译器与 flag 通过 **make 命令行变量**注入（上游 `CXX = g++` 是无条件赋值，
环境变量注入对它完全无效）；`CXXFLAGS` 按 profile 重组，
因为上游 release 行带着 `-march=pentium4` 等 x86 专有开关，aarch64 上必炸。
