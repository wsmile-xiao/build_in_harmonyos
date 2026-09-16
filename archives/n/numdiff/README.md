# numdiff

## 简介
GNU numdiff（nongnu 项目）是一款"数值差异比较"命令行工具：逐行、逐字段比较两个结构相似的文件，
并忽略小的数值差异和/或不同的数值格式（如 `1.0e-6` 与 `0.000001`）。同一源码包还附带配套工具
`ndselect`，用于按列/字段挑选输入行。上游主页：https://www.gnu.org/software/numdiff/

## 功能概述
- 数值容差比较：绝对阈值 `-a`、相对阈值 `-r`，可按字段范围限定
- 字段/列选择：`-F`（首字段）、`-L`（末字段）、`-I`（步长）、`-s`/`-D`（分隔符集合）
- 数值格式适配：自定义货币符号 `-c`、小数点、千位分隔符
- 同步过滤器：`-f`（仅显示过滤/同步结果）、`-O`（并排概览）、`-z`/`-Z`（模糊/幽灵字段）
- 内置公式与统计（`--formula`、`-S`），可选 GMP 任意精度算术
- 配套命令 `ndselect`：按列范围/步长抽取字段

## OHOS 适配
- **E011（HMDFS 权限）**：autoconf 生成的 `configure`/`config.status` 用 `umask 077` 创建临时目录，
  HMDFS 上该目录不可写，configure 中止；已打补丁将 `umask 077` 改为 `umask 022`（见版本级 patches/0001）。
- **E027 / PSCAN-MUSL-005（NLS）**：OHOS 无 `libintl`（gettext）开发库，而 numdiff 默认启用 NLS；
  本包以 `configure --disable-nls` 构建。
- **musl 内存未初始化崩溃**：`linesplit.c` 的 `ssplit()` 在分隔符串以分隔符结尾时多计子串数，
  留下未初始化的指针槽位；glibc 常因 malloc 返回清零内存而掩盖，musl 上会 SIGSEGV。
  已打补丁 `malloc → calloc`（见版本级 patches/0002）。
- **已知限制**：因 `--disable-nls`，非英文（意大利语）界面消息/文档不生效。
- **与 Linux 差异**：功能行为一致；上述崩溃在 glibc 上属潜在 UB（通常被掩盖），在 musl/OHOS 上必现。

## 依赖关系
- 编译依赖：C 编译器（clang）、GNU Make；tarball 已自带 `configure`，无需 autoconf/automake 重新生成。
  可选 gettext（NLS，已禁用）；可选 GMP（`--enable-gmp` 默认开，本平台无 gmp 时自动回退到内置多精度实现）。
- 运行依赖：仅系统 libc（Conan 依赖链为空）。

## 参考资料
- 官网 / 文档：https://www.gnu.org/software/numdiff/
- 源码托管（GNU Savannah nongnu）：https://savannah.nongnu.org/projects/numdiff/
- 发布目录：https://download.savannah.gnu.org/releases/numdiff/
