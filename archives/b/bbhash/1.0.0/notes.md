# bbhash 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（header-only 单头文件库，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15 (Target: aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 官方源码（GitHub 官方 archive 端点，SHA-256 已核验）
#   url: https://github.com/rizkg/BBHash/archive/refs/tags/v1.0.0.tar.gz
#   sha256: 1721e3b1afe915a6cbec6a578dfd9a2226f2dabd73fcc8e7cef00085e158480c
make CXX=clang++ CFLAGS="-O2 -std=c++11 -lpthread" all   # exit 0
make test                                                  # ./Bootest 10000 1 2 -check → working correctly
./Bootest 500000 4 2 -check                                # 多线程正确性 → working correctly
./example 100000 2 / ./example_custom_hash 100000 2        # 示例运行 exit 0
# Conan 配方验证（OHOS aarch64 profile）
python3 scripts/ohc-run.py conan-verify bbhash 1.0.0       # G1-G4 + L2/L4/L5 全过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `BooPHF.h:26: unknown type name 'u_int64_t'` | BSD 遗留 typedef（u_int64_t）由 `<sys/types.h>` 定义，glibc 会经 `<unistd.h>` 等传递引入；OHOS musl 系 libc 不传递提供 | 补丁 `patches/0001-BooPHF.h.patch`：BooPHF.h 显式 `#include <sys/types.h>` |
| 2 | conandata.yml codeload URL 无 `.tar.gz` 后缀，`get()` 误判 zip（BadZipFile） | conan `get()` 按 URL 扩展名识别格式 | 改用官方 `https://github.com/rizkg/BBHash/archive/refs/tags/v1.0.0.tar.gz`（SHA-256 与 codeload 一致） |
| 3 | conan create G2: `package_type=library` 缺 `shared` option | header-only 库不应为 library 类型 | `package_type = "header-library"` |
| 4 | 补丁含绝对路径无法 apply | diff 生成方式 | 以 `a/`、`b/` 相对路径重新生成补丁 |

## 源码修改

- `patches/0001-BooPHF.h.patch`：BooPHF.h 在 `<unistd.h>` 后添加 `#include <sys/types.h>`（一行，无平台宏）

## 上游测试枚举台账（双口径）

源码 4 个 C++ 文件：`BooPHF.h`（库头，非测试）、`bootest.cpp`（上游测试程序）、`example.cpp`（样例）、`example_custom_hash.cpp`（样例）。

| 入口 | 类型 | 是否独立上游用例 | 是否运行 | 结果 |
|------|------|------------------|----------|------|
| bootest.cpp → Bootest（`make test`: `./Bootest 10000 1 2 -check`） | 上游测试程序（正确性验证） | ✅ 是 | ✅ | PASS（working correctly，exit 0） |
| bootest.cpp `./Bootest 500000 4 2 -check`（多线程正确性） | 同一测试程序不同参数 | 同一用例 | ✅ | PASS |
| example.cpp → example | 样例 | ❌ 不计入 | ✅ | exit 0 |
| example_custom_hash.cpp → example_custom_hash | 样例 | ❌ 不计入 | ✅ | exit 0 |
| BooPHF.h | 库头/框架 | ❌ | — | — |

- source_declared_total: 1（bootest.cpp 正确性验证程序）
- configured_executable_total: 1（Bootest，makefile 构建目标）
- executed_passed_total: 1；失败 0；未运行 0
- 全量通过率: 1/1 = 100%；当前配置可执行集合通过率: 1/1 = 100%
- 样例（example/example_custom_hash）按规则不计入上游用例数，仅列台账

## 鸿蒙专项测试与消费者测试

- test_package/test.cpp（消费者用例）：仅经公开头 BooPHF.h 构造 10 万 key MPH 并核验 lookup 唯一 → Passed
- test_package/ohos_test.cpp（鸿蒙专项）：`-Werror` 严格编译 + 4 线程 pthread 构造 + save/load 流往返一致 → Passed
- conan create 内 CTest: 2/2 Passed

## 知识候选台账

| # | 候选（非噪声） | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 四范围查重 | 判定 |
|---|---------------|----------|------|------|------|----------|-----------|------|
| 1 | OHOS 上 BSD 遗留 typedef u_int64_t 需显式包含 `<sys/types.h>` | `unknown type name 'u_int64_t'; did you mean 'uint64_t'?` | OHOS（musl 系 libc）不传递提供 u_int64_t（glibc 经 unistd.h 等传递引入）；BSD typedef 定义于 sys/types.h | BooPHF.h 显式 `#include <sys/types.h>` | make exit 0；Bootest -check working correctly；conan create OHOS aarch64 G1-G4/L2/L4/L5 全过；消费者+鸿蒙专项 2/2 | 任何按名使用 u_int64_t/u_int32_t 且未显式含 sys/types.h 的 C/C++ 库（尤其 header-only）；已用 check_symbol_exists/HAVE_* 探测的不适用（见 E290） | 正式 E 条目无命中；doc 仅 Perl XS 类；graph 无；drafts 中 DRAFT-cahute（fd_set/timeval）同类根因不同符号 | **路径 B**（new_draft） |

查重七轴（详见 knowledge/drafts/DRAFT-bbhash-1.0.0-u-int64-sys-types-h.md）：
exact_duplicate=false, causal_duplicate=false, trigger_overlap=low, solution_overlap=partial,
combination_novelty=true, boundary_novelty=true, test_migration_novelty=true。
关系: similar_to=DRAFT-cahute-ohos-select-time-includes; caused_by=上游依赖 glibc 传递包含; conflicts_with=E290(类型探测路径)。

路径判定: **B（知识库扩展）**，`new_draft`：知识候选已验证、可跨库复用、查重未命中且存在新增差异；
草稿对：knowledge/drafts/DRAFT-bbhash-1.0.0-u-int64-sys-types-h.{kv,md}（同 stem 配对）。

## 验证结果

```bash
make test → "--- boophf working correctly ---"（exit 0）
conan-verify → 配方验证通过（G1-G4 + L2/L4/L5），test_package CTest 2/2 Passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/b/bbhash/1.0.0/conanfile.py | header-library 配方 |
| archives/b/bbhash/1.0.0/conandata.yml | 官方源 URL + SHA-256 + 补丁声明 |
| archives/b/bbhash/1.0.0/patches/0001-BooPHF.h.patch | sys/types.h 补丁 |
| archives/b/bbhash/1.0.0/test_package/ | 消费者 + 鸿蒙专项测试 |
| knowledge/drafts/DRAFT-bbhash-1.0.0-u-int64-sys-types-h.{kv,md} | 路径 B 草稿对 |

## 注意事项

- 库为 header-only，无 bin 产物 → 非 CLI 库，不创建 commands.json（R38）
- 无外部依赖（W0 预检通过）
- /tmp 只读（平台已知限制），构建临时目录使用 ~/tmp
---

**编译结束**: 2026-09-19 13:50
**最终状态**: published
