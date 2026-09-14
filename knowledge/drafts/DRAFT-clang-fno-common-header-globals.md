# DRAFT-clang-fno-common-header-globals

## 一句规则

clang 默认 `-fno-common`：头文件里"定义"（而非 extern 声明）的全局变量会在每个包含它的编译单元生成强符号，链接期报 `duplicate symbol`（GNU ld 措辞 `multiple definition`）；正解是头文件全 extern + 新增单一 .c 定义点，并同步注册 Makefile.am 与 Makefile.in。

## 根因（机理链）

旧惯例依赖 `-fcommon` 把各 TU 的 tentative definition 合并为 common symbol；现代 clang（LLVM 上游默认，GCC 10+ 同）默认 `-fno-common`，每个 TU 生成强定义 → N 个 TU 包含同一头即 N 重定义 → 链接失败。案例（dirb/2.22）：`src/variables.h` 被 8 个 TU 包含。

## 方案空间

- **rec**：extern 化 + 单一定义点；注册 `src/Makefile.am`（base）与 `src/Makefile.in`（base 与 `am__objects_1`）——tarball 预生成时 make 实际读 `.in`，两处缺一不可。
- **fallback**：`-fcommon`——只掩盖声明/定义缺陷，按 P-CFLAGS-001 记录技术债务，仅退路。
- **forbid**：默认加 `-fcommon`；`__attribute__((weak))` 掩盖重复定义。

## 验证（自包含三段探针）

见 .kv `verification_cmd`：默认链接失败（duplicate symbol）→ `-fcommon` 通过 → extern+单点定义通过。设备实证存档：run dirb-2.22 `reports/curator/probes/fno-common/`（clang-15 + ld.lld 实测）。

## 证据与诚实边界

- 原始链接失败发生在 CI 启动前的本地首建，CI run1..7 无该报错存证（候选自 run1 起已含修复 patch）；探针为机理级完整复现，run4 的 `tentative definition has type 'struct opciones' that is never completed`（variables.c 漏 include dirb.h）为修法落地的次生错误实录。
- 去重声明：DRAFT-swftools-autotools-hmdfs-2168 已捆绑覆盖同机理（extern+单点、forbid -fcommon）；本条为其专门化（规则化标题、自包含探针、Makefile.in/am__objects_1 注册细节、ld.lld/GNU ld 双签名），similar_to 已挂接，入图时与该草稿的合并/并行由知识库主编裁定。
