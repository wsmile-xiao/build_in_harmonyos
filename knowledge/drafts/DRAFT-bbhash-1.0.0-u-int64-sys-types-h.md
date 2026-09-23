# DRAFT-bbhash-1.0.0-u-int64-sys-types-h — OHOS 上 BSD 遗留 typedef u_int64_t 需显式包含 <sys/types.h>

> **Contributor**: pc4-9 | **Status**: DRAFT | **Updated**: 2026-09-19
> **Severity**: medium | **Category**: headers / portability / ohos / libc / compat / typedef
> **Audience**: 任何在 OHOS 上编译时使用 u_int64_t/u_int32_t 等 BSD 遗留 typedef 的 C/C++ 三方库
> **Stem**: DRAFT-bbhash-1.0.0-u-int64-sys-types-h（与同名 .kv 配对，字段逐一对齐）

## 问题（Symptom）

bbhash 1.0.0（单头文件 minimal perfect hash 库）在 OHOS aarch64 上用 clang++ 编译报：

```text
./BooPHF.h:26:2: error: unknown type name 'u_int64_t'; did you mean 'uint64_t'?
./BooPHF.h:28:3: error: unknown type name 'u_int64_t'; did you mean 'uint64_t'?
```

上游 BooPHF.h 只包含 `<stdio.h>/<unistd.h>/<memory>/<vector>...` 等头，依赖传递包含提供 `u_int64_t`；在 Linux/glibc 与 macOS 上成立，OHOS（musl 系 libc）上不成立。

## 根因（Root Cause）

`u_int64_t` 是 BSD 遗留整数 typedef（定义于 `<sys/types.h>`），与标准名 `uint64_t`（`<stdint.h>`/`<cstdint>`）不同。glibc 会通过 `<unistd.h>`/`<stdio.h>` 等头传递引入 `<sys/types.h>`；OHOS 的 musl 系 libc 头文件不做这种传递包含，导致按名字使用 `u_int64_t` 的翻译单元报 unknown type name。属于平台头文件传递性差异，非代码逻辑错误。

## 方案（Solution）

在使用 `u_int64_t` 的头文件/翻译单元显式添加 `#include <sys/types.h>`（普适 POSIX 头，非平台宏），一行最小补丁：

```cpp
#include <memory> // for make_shared
#include <unistd.h>
#include <sys/types.h> // u_int64_t (not pulled in transitively on all libc)
```

bbhash 1.0.0 实测：唯一此补丁后 `make`（clang++ -O2 -std=c++11）通过，上游 `make test`（`./Bootest 10000 1 2 -check`）输出 "boophf working correctly"；conan create 在 OHOS aarch64 profile 下 G1-G4/L2/L4/L5 全过，消费者与鸿蒙专项测试 2/2 通过。

备选方案：全局替换 `u_int64_t` → `uint64_t`（`<cstdint>` 标准名），改动面更大但更彻底，仅在无法加 POSIX 头时选用。

## 适用边界与反例（Boundary & Counter-examples）

- **适用**：单头文件/简单 C/C++ 库直接按名使用 BSD 遗留 typedef（`u_int64_t`/`u_int32_t` 等）且未显式包含 `<sys/types.h>`。
- **反例（不适用）**：
  - 已正确包含 `<sys/types.h>` 或 `<stdint.h>` 的翻译单元（补丁多余）。
  - 错误仅涉及标准名 `uint64_t`（那是 `<stdint.h>` 缺失，应加 `<cstdint>`/`<stdint.h>`，本条目不覆盖）。
  - CMake 等构建系统已自带类型探测（如 `check_symbol_exists` + `HAVE_U_INT64_T` 条件编译宏）的库，应走配置宏路径而非硬编码补丁（E290 覆盖该探测模式）。

## 查重结论（四范围）

| 范围 | 命中 | 说明 |
|---|---|---|
| index.tsv ↔ graph/*.kv | E035/E194/E208/E257/E321/E322 | 均为 header-only 配方/Perl XS/`sys/types.h file not found`（缺文件报错）或配方完整性，无一覆盖 BSD typedef 无名错误（unknown type name） |
| knowledge/doc/ | E190/E194/E208 | Perl XS 构建参数/CPATH 类，本库非 Perl 路径 |
| knowledge/drafts/ | DRAFT-cahute-ohos-select-time-includes（同类根因，不同符号） | cahute 是 `fd_set`/`struct timeval` 需显式 `<sys/select.h>`+`<sys/time.h>`；bbhash 是 `u_int64_t` 需显式 `<sys/types.h>`。同属“OHOS 头文件传递性差异 → 显式包含缺失 POSIX 头”大类，但符号、头文件、修复位置均不同 |
| knowledge/operations/ | 无命中 | — |

**七轴查重**：
- exact_duplicate: false（无任何条目以 unknown type name 'u_int64_t' 为签名）
- causal_duplicate: false（E194/E208 是 Perl XS 构建参数与 CPATH，非头文件传递性；cahute 草稿为不同符号，根因同类但不可归并为同一 entry）
- trigger_overlap: low（与 E194/E208 的 `sys/types.h.*No such file` 仅共享头文件名，错误形态不同：No such file vs unknown type name）
- solution_overlap: partial（cahute 同为“补显式 POSIX include”，可作兄弟知识引用）
- combination_novelty: true（BSD 遗留 typedef 缺失类是知识库空白）
- boundary_novelty: true（唯一给出 "check_symbol_exists/HAVE_* 已覆盖则不走硬补丁" 边界与 cstdint 备选）
- test_migration_novelty: true（bbhash 实测补丁后 conan create OHOS 全绿 + 消费者/鸿蒙专项 2/2，验证证据可跨库复用）

**关系字段**：`similar_to`: DRAFT-cahute-ohos-select-time-includes（显式 include 缺失类）；`caused_by`: 上游依赖 glibc 传递包含；`prerequisite_of`: 无；`conflicts_with`: E290（类型探测路径，二选一）。

**路径判定**：**B（知识库扩展）** — 候选已验证、可跨库复用、四范围查重未命中且存在新增差异（BSD typedef 类），建立同 stem .md/.kv 草稿对。

## 验证（Verification）

1. `make CXX=clang++` 退出码 0（补丁后）。
2. `make test`（`./Bootest 10000 1 2 -check`）→ "boophf working correctly"，退出码 0。
3. `conan create`（OHOS aarch64 profile，G1-G4/L2/L4/L5）→ PASS，`test_package` 2/2（test_bbhash + test_bbhash_ohos -Werror）通过。