# DRAFT-lld-shlib-undefined-host-contract — 共享库按宿主契约保留 UND 导入时，lld 默认 --no-allow-shlib-undefined 使消费方链接期即失败，消费方必须提供定义块

> 案例库：dieharder 3.31.1.4（条目本身为问题类命名，泛化到一切"宿主契约"式共享库）
> Status: UNMATCHED — needs human/AI review to promote to E-entry（配对 .kv 同名）

## 现象 (What happened)

dieharder 3.31.1.4 的 OHOS conan 包构建与打包全部成功，`conan create` 的 test 阶段
test_package 作为真实消费方执行 `clang test.c … -ldieharder -lgsl -lgslcblas -lm`
链接探针时失败：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: dh_num_dieharder_rngs
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: dh_num_R_rngs
…（逐符号重复）
ld.lld: error: too many errors emitted, stopping now (use --error-limit=0 to see all errors)
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
```

数量口径分两层如实记录：

- **实测展示数**：链接日志逐符号展示 **19 个**不同符号（`dh_rng_types`、`dh_test_types`、
  `dh_num_rngs/dieharder_rngs/gsl_rngs/R_rngs/hardware_rngs`、
  `dh_num_diehard/sts/other/user_tests`、`gsl_types`、`verbose`、`rng`、`ntuple`、
  `overlap`、`kspi`、`rmax_bits`、`rmax_mask`）后被 lld error limit 截断。
- **推算总数**：对构建制品 `llvm-nm -D --undefined-only` 实测 119 个 UND 导入，
  扣除 libc/libm/gsl 后属宿主契约全局的**约 50 个**——按上游唯一定义点
  `dieharder/globals.c`（81 行全局定义、部分一行多符号）推算。

## 根因 (Root cause)

| # | 环节 | 事实 |
|---|------|------|
| 1 | 工具实现 | OHOS 工具链 lld 对**可执行链接**默认 `--no-allow-shlib-undefined`：DT_NEEDED 闭包内解析不了的 UND 导入直接报错。GNU ld 历史默认宽松，同一代码在 glibc/GNU ld 平台常不显形。musl 动态链接器对数据符号**立即绑定**（relocation 加载期完成），漏定义同样在加载期显形。 |
| 2 | 宿主契约 | 上游按 gcc10 `-fno-common` 后的"唯一定义点"约定（上游 globals.c 头注释自述 "defining globals _exactly once_"），共享库本体把 CLI 专属全局状态留为 UND 导入，由主程序提供唯一定义；R 接口（embeddieharder 式）同款契约。这是**上游设计**，不是库的移植缺陷。 |
| 3 | 失败面 | 每个消费方（test_package、任意第三方程序）链接期必然命中；错误信息即 `undefined reference due to --no-allow-shlib-undefined: <符号>`。 |
| 4 | 归类 | 链接域工具链语义差异；复发面由平台默认值保证，无需第二实例即具泛化价值。 |

判别方法：`llvm-nm -D --undefined-only libX.so` 出现非 libc/libm/依赖库的"应用层全局"
符号，且上游源码存在 globals.c 式唯一定义点。

## 解法 (Fix)

消费方按上游唯一定义点逐项补全局定义块，使自己成为与上游 CLI 同等地位的真实宿主：

- 定义集合：对构建制品 `llvm-nm -D --undefined-only` 核出宿主契约符号全集；
- 定义类型：以安装头文件的 `extern` 声明为准逐项对齐；
- 案例实现：仓内 `archives/d/dieharder/3.31.1.4/test_package/test.c` 的
  "消费方全局符号"定义块（逐项对齐上游 `dieharder/globals.c`）。

**不要**（forbid）：把全局定义块打进库本体 / 用 patch 给库源码补定义——违反上游宿主
契约，R embeddieharder 等合法消费方将遇符号重复，行为偏离上游、升级即冲突。

## 验证 (Verification)

四步探针（全新 shell 可复跑，不依赖任何仓库/日志；clang 为 OHOS 构建环境自带 LLVM clang）：

```console
$ P=$(mktemp -d); cd $P
$ printf 'extern int host_global;\nint get(void){return host_global;}\n' > libu.c
$ printf 'int host_global=7;\nextern int get(void);\nint main(void){return get()==7?0:1;}\n' > consumer_ok.c
$ printf 'extern int get(void);\nint main(void){return get()==7?0:1;}\n' > consumer_missing.c
$ clang -shared -fPIC libu.c -o libu.so                    # STEP1 库可带 UND 导出
$ clang consumer_missing.c -L. -lu -o probe_missing        # STEP2 期望 rc!=0
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: host_global
$ clang consumer_ok.c -L. -lu -o probe_ok && LD_LIBRARY_PATH=. ./probe_ok   # STEP3 期望 rc=0
$ clang -Wl,--allow-shlib-undefined consumer_missing.c -L. -lu -o probe_masked
$ LD_LIBRARY_PATH=. ./probe_masked                         # STEP4 期望 rc!=0
Error relocating ./libu.so: host_global: symbol not found
```

四步真机实录全部吻合（STEP2 rc=1、STEP3 rc=0、STEP4 rc=127）。

### fallback 的诚实权衡

`-Wl,--allow-shlib-undefined` 只是把检查推迟：musl 立即绑定下失败移到加载期
（STEP4 rc=127）。仅当真实宿主程序另行提供全部符号时才成立——属掩盖兼容性而非修复，
只作诊断/退路。

## 适用边界 (Applicability / Scope)

- 适用：任何提供「宿主应用提供全局状态」契约的共享库（统计/科学计算库、嵌入式解释器
  接口、R/Python 扩展式宿主接口）的 Conan test_package 及一切消费方。
- 不适用：依赖链缺符号的掩码场景（如 fortify 符号 `__fd_chk` 不被 sysroot libc 导出）——
  那是 casablanca/2.10.16、address-standardizer/3.7.0 配方内 `--allow-shlib-undefined`
  的既有用法，机理不同，不得互推。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

独立去重（两轮不同检索词）均零覆盖：

- `knowledge/graph`（全文）：`shlib-undefined|allow-shlib|fno-common|fno_common` → 0 命中；
  宽泛词 `undefined reference` 命中 20 文件，逐条收窄后均为泛化"链接缺符号/缺 -l/
  libdl/libintl"类（E013=缺 libdl、E015=dgettext/libintl），无一覆盖本机理。
- `knowledge/drafts`：精确词 0 命中；`fno-common` 仅出现在 DRAFT-swftools-autotools-hmdfs-2168
  （主题 HMDFS/umask/legacy-autotools，"common symbol merging" 仅一笔带过），未覆盖
  "宿主契约 UND × lld 默认值 × 消费方定义块"机理与修法。
- 经验仓：`shlib-undefined|allow.shlib|宿主契约|undefined reference due` → 0 命中。
- 相关条目：E004（musl BIND_NOW 符号族——同属 musl 立即绑定符号解析）、E013、E015
  （均为依赖符号缺失/动态链接错误族），与本条"消费方须提供定义块"的宿主契约机理互补。

## Principle 提案 (Principle Proposal)

现 `knowledge/principles.yaml` 仅有 **P-LINKAGE-001"静态库优先原则（系统库冲突防护）"**
（scope [E042,E019,E067]，statement 讲 `--without-shared`/系统库覆盖），与本条机理无关，
故不改挂。本条以如下内联原则陈述代挂钩，并**提案**知识库主编采纳：

> **P-LINKAGE-002（提案）**：共享库按宿主契约保留的 UND 导入由消费方提供唯一定义；
> 工具链对可执行文件的 `--no-allow-shlib-undefined` 默认值使该契约在链接期显形，
> 掩码选项（`--allow-shlib-undefined`）只把失败推迟到加载期。

（写入边界：本 run 仅允许新增 `knowledge/drafts/DRAFT-*`，principles.yaml 的正式增补
由知识库主编流程处理。）

## 参考 (References)

- 上游唯一定义点：上游源码树 `dieharder/globals.c`（头注释自述 gcc10 -fno-common 约定，
  Dirk Eddelbuettel, Dec 2019/Dec 2022）
- 案例实现：仓内 `archives/d/dieharder/3.31.1.4/test_package/test.c`（消费方全局符号定义块）
- 配对结构化条目：`knowledge/drafts/DRAFT-lld-shlib-undefined-host-contract.kv`
