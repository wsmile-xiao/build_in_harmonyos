# 处理策略：大小写不敏感文件系统上中间产物与源文件撞名

配套检测脚本 `detect-case-insensitive-build.sh`、复现脚本 `reproduce.sh`，
样例库 `archives/m/mbr/1.2.2`。策略按代价从低到高排列，命中风险后按序尝试。

---

## S1 改中间后缀（最小改动，样例采用）

**思路**：把「源 → 中间产物」中那个只差大小写的中间后缀换成一个不再冲突的名字
（mbr 用 `.s86` → `.i86`），构建语义与产物字节完全不变。

**必须同时改到的编辑点**（缺一处就会留下一条仍然撞名的规则）：

| # | 位置 | 说明 |
|---|---|---|
| 1 | `SUFFIXES`（`.s86` → `.i86`） | automake/make 的后缀规则注册表 |
| 2 | `CLEANFILES` / `DISTCLEANFILES` 中的 `*.s86` → `*.i86` | 中间后缀改名后清理列表要同步（shell glob 按目录项做大小写敏感匹配，故原列表不会误删 `mbr.S86`，但会漏清理中间产物） |
| 3 | 模式/后缀规则 `%.s86: %.S86` → `%.i86: %.S86` | 规则本体 |
| 4 | 由中间后缀派生的下游规则：`%.b: %.s86`、`%.o86: %.s86` → `%.i86` | 否则下游找不到中间产物 |
| 5 | 显式规则：`y2k.s86: mbr.S86`、`testdisk.s86: mbr.S86` → `.i86` | 逐文件规则 |
| 6 | `Makefile.am` **与** `Makefile.in` **双写** | CI 直接用 `.in`；`autoreconf` 才会从 `.am` 重建 `.in`，两者必须一致 |

**要点 / 坑**：

- 补丁里**不加平台宏**（不写 `#ifdef __OHOS__`、不注入 `-D__OHOS__`）：这是构建规则的可移植性
  修复，在大小写敏感的系统上同样成立（中间后缀本就可以任取）。框架规则 R8 / preflight PF5 会
  拦截补丁新增行中的平台宏。
- 先确认「中间产物确实撞源」再动刀。判定：规则目标的小写 == 前置的小写（本脚本风险 B）。
- 修完后必须验证三件事：①源文件与原始副本逐字节一致（`cmp`）；②构建日志里预处理配方确实执行
  （命中 `E -xc`）；③汇编器 0 报错、产物尺寸正确。
- 产物字节应与上游一致（本样例 `mbr.b` / `testdisk.b` = 512 B）。

模板：把上面 6 个编辑点当 checklist，逐条在补丁里体现；本样例的完整补丁见
`../patches/0001-case-distinct-intermediate-suffix.patch`（Makefile.am 9 处 + Makefile.in 10 处，
由原始 tarball 与改动后副本 `diff -u` 生成，`patch -p1` 干净应用）。

---

## S2 源外构建 + 显式规则（规则不便打补丁时）

**适用**：后缀表/规则由生成器写出（如 `configure` 生成的 `Makefile` 中规则被写死），或上游拒绝
变更时。

**做法**：把源码树挂/复制为只读，用构建系统本身的能力把中间产物放到独立目录：

- CMake：`cmake -S <src> -B <build>`（生成式构建天然分离）。
- Autotools：`mkdir <build> && cd <build> && <src>/configure && make`（VPATH 构建）。
- 自研 Makefile：显式加 `-o <build>/...` 或 `make -C <build> -f <src>/Makefile VPATH=<src>`。

**实测注意（重要）**：单纯换到源外构建**不能**解决「撞名」这一类失效——make 仍会在 srcdir 里把
`mbr.s86` 解析到源文件 `mbr.S86`，认为中间产物已存在而跳过配方，报错照旧。S2 只对「配方会执行、
但产物写回源码树」的变体有效；撞名情形仍需 S1 改名，或在 VPATH 下显式补一条别名规则
（如 `%.i86: %.S86`）。方向性依据：本样例 A 阶段源文件**未被改动**，说明问题是「配方没执行」
而不是「产物写回源码树」。

**验证**：构建后源码树无新增文件；构建日志中配方确实执行；产物与 S1 路径一致、字节正确。
**代价**高于 S1，且只读挂载在部分环境（HMDFS/FUSE）上可能需要额外权限，故 S1 优先。

---

## S3 `env_unsupported` 标记（无法在配方内规避时）

**适用**：规则无法修改、也无法分离输出目录（例如源码树被工具硬编码到固定路径且必须可写）。

**做法**：在 `validate()` 中按环境抛 `ConanInvalidConfiguration`，并在 `notes.md` /
`reports/test-report.md` 附**可执行复现证据**（`reproduce.sh` 的阶段 A 日志）与「需要大小写
敏感卷（或在支持大小写区分的挂载选项下构建）」的说明；结果按 `env_unsupported` 上报。

**禁止**：伪造/篡改产物、用 dummy 包顶替、静默降级（例如忽略 as86 / 编译器报错，把没构建成功的
状态当作成功）。

---

## S4 配套：非目标架构构建工具用 `tool_requires` 补齐

本类软件常见「目标架构的宿主程序 + 其它架构的汇编/二进制产物」组合（mbr = aarch64 宿主内嵌
8086 引导扇区）。当构建期需要 as86/ld86/xxd/nasm 之类工具、而系统与 OHOS SDK 都不提供时，
**不要**尝试改构建系统绕开，直接在配方里声明构建期工具：

```python
def build_requirements(self):
    self.tool_requires("dev86/0.16.21")   # as86 / ld86
    self.tool_requires("xxd/9.1.0")       # xxd -i
```

```python
def build(self):
    # 工具在构建期 PATH 上（VirtualBuildEnv 注入 builddir/bin），宿主编译器由 Toolchain 注入
    autotools = Autotools(self)
    autotools.configure()
    autotools.make(args=["-j1"])
```

要点：

- 工具走 **build profile**；CI 用 `-pr:h` / `-pr:b` 同一份 `ohos-aarch64` profile，故工具也是
  aarch64 原生构建（as86 生成 8086 代码与自身架构无关）。
- 先探测制品仓再写配方（**禁止**用 `conan list` 判存在，cnb.cool 的搜索接口对 binary 返回不全）：
  `conan download dev86/0.16.21 -r=ohpcd --only-recipe`。
- 工具包未发布时，按 R36 先适配并发布工具包，再适配上层。
- HMDFS 上 `make -j` 的 jobserver 会用 `mkfifo` 而被拒（EPERM），配方里用 `make -j1`。

---

## 验证清单（任一策略落地后逐条确认）

```sh
# 1. 源文件未被改动（与原始副本逐字节一致）
cmp -s <src>/mbr.S86 <pristine>/mbr.S86 && echo unchanged   > cmp.txt 2>&1

# 2. 预处理配方确实执行（构建日志里应出现规则体命令；未修复时为 0）
grep -c 'E -xc' <work>/make.log                            > cpp.txt 2>&1   # 期望 > 0

# 3. 产物字节正确（注：make 用完会删除隐式中间产物 mbr.i86，勿以「中间文件仍在」作判据）
wc -c <work>/mbr.b                                         > size.txt 2>&1  # 期望 512

# 4. 上游测试与消费者测试（见 ../reports/test-report.md）
```

**已知局限**：本机 `/dev/shm` 虽为大小写敏感卷，但 `mkdir` 被拒（`Permission denied`），
未能在大小写敏感文件系统上做「未打补丁」的对照构建做产物字节比对。结论改由同卷 A/B 对照
支撑：A 阶段（未打补丁）预处理配方执行 0 次、as86 报 87 处 `unbound label`、`make rc=2`，
源文件未被改动；B 阶段（`.i86`）预处理配方执行 3 次、as86 0 报错、`make rc=0`、`mbr.b` 512 B。
另一条独立证据：把同一 `mbr.S86` 手工 `clang -E -xc` 后交给 as86，得 rc=0、0 错误。
