# apache-arrow 24.0.0 高难度与路径 B 证据说明

## 基本信息

- 库名称: apache-arrow
- 上游版本: 24.0.0
- 上游源码: https://archive.apache.org/dist/arrow/arrow-24.0.0/apache-arrow-24.0.0.tar.gz
- SHA-256: `9a8094d24fa33b90c672ab77fdda253f29300c8b0dd3f0b8e55a29dbd98b82c9`
- 关联 PR: !3033
- 分支: `feat/apache-arrow-24.0.0-F72D`
- 当前申报口径: 路径 A 基础适配 + 路径 B 贡献创新候选, 不申报 Path C

## 申请路径 B 的理由

apache-arrow 24.0.0 不是单一 C/C++ 小型库。其 C++ 侧覆盖 Arrow Core、Compute、IPC、CSV、JSON、Filesystem、Parquet、Dataset、Acero 等模块, 上游测试体系由 CMake/CTest/GTest 驱动, 同时依赖官方测试数据、timezone 数据、动态库加载路径、C++20 标准库能力和若干第三方 bundled 组件。

HarmonyOS Conan 真机环境无法按普通 Linux 开发机方式直接闭环完整上游测试。实际适配过程中需要先识别哪些测试目标可以迁移执行, 哪些失败属于测试环境缺口, 哪些属于 HarmonyOS 系统或工具链差异, 再对可收敛项进行窄范围修复。

本 PR 沉淀的不是单个编译参数修补, 而是一类“大型 C++ 数据处理库在 HarmonyOS 上进行 CTest/GTest 分层迁移、环境依赖补齐和平台差异归因”的方法。

## 与普通路径 A 的区别

路径 A 基础适配已经完成:

- Conan recipe 可构建并安装 apache-arrow 24.0.0。
- shared 和 static 消费链路均已在 HarmonyOS 真机验证通过。
- `test_package` 可链接并调用 Arrow 运行时 API。

路径 B 证据在于额外完成了以下工作:

- 识别并执行上游 C++ CTest 可迁移目标, 最大完成范围为 89 个 target。
- 对 Parquet、Dataset、Acero 等扩展模块完成分层测试验证。
- 补齐官方测试数据、timezone 数据、GTest 临时目录、动态库加载路径等运行环境。
- 识别 OHOS LLVM 15 libc++、make jobserver FIFO、HarmonyOS loader、`posix_fadvise`、目录尾斜杠 open/append 等差异。
- 将可稳定修复项收敛为 OHOS 窄范围 patch 或 recipe 配置, 将暂未解决项单独记录, 不冒充完整上游通过。
- 进一步复验核心失败目标: `arrow-array-test` 经 GTest TMPDIR 迁移后 1038 passed, 1 skipped; `buffer/misc/stl/cast` 排除已定位 OOM/timezone 缺口后主体用例通过; vendored date 新增通用 `TZDIR` 支持后 timezone lookup 错误收敛。
- 继续复验低风险 target: `arrow-scalar-test`、`arrow-compute-internals-test`、testing 工具层 target 合计 627 passed, 14 skipped。
- 新建 `ARROW_COMPUTE=ON` 专项测试树, 解决 Boost.Context 架构识别和测试库 `NEEDED` 重链接问题后, 12 个 compute target 完整通过, 合计 3272 passed, 25 skipped; `arrow-compute-scalar-temporal-test` 全量 46 passed, 1 skipped, 7 个历史 DST/offset 差异失败, 过滤已定位差异后 46 passed, 1 skipped。
- temporal DST 轻量探针进一步对照 Python `tzdata 2026.3`、系统 `/etc/zoneinfo` 和 unset `TZDIR`: Python tzdata 下主体用例保持 46 passed, 1 skipped; `/etc/zoneinfo` 或 unset `TZDIR` 会扩大为 17 failed, 因此当前 PR 保留 `TZDIR` 外部注入而不扩大库行为 patch。
- OOM/allocator 单用例轻量探针确认剩余失败不是构建产物或测试入口问题: `allocator.TestOOM` 未抛 `std::bad_alloc`, `TypedTestBuffer/0.ResizeOOM` 为 `Signal 11`, `Default/TestMemoryPool/0.OOM` 返回 OK 而非 `OutOfMemory`; 当前按 OHOS 内存极限语义差异记录。

## 证据文件

本目录下的证据文件按用途拆分:

- `upstream-test-inventory.md`: 上游测试入口和已执行 CTest target 清单。
- `upstream-test-results.md`: 已完成测试结果、RUN_DIR 和未通过项。
- `ohos-difference-analysis.md`: HarmonyOS 环境差异、已解决项和暂缓项。
- `quality-report.md`: Conan 包质量、消费者验证和当前限制。

知识沉淀 draft:

- `knowledge/graph/draft/E217-draft-apache-arrow-cpp-test-ohos.kv`
- `knowledge/graph/draft/E217-draft-apache-arrow-cpp-test-ohos.md`

## 当前不声明的范围

- 不声明 Apache Arrow 官方完整上游测试套件 100% 通过。
- 不声明 Python、Java、R、Flight、CUDA、Gandiva、ORC 等语言运行时、服务或硬件相关子集通过。
- 不声明 Path C。

当前路径 B 申请基于“C++ 可执行子集真实执行 + 环境依赖补齐 + 未执行/未通过项原因说明 + Conan test_package 消费者验证”的证据链。

## 最新 compute-on 专项证据

新增 RUN_DIR:

```text
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-v2-20260726-012420-29629
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-temporal-filtered-v5-20260726-020638-570
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-core-batch-v1-20260726-021148-4888
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-vector-row-batch-v1-20260726-021842-12033
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-compute-aggregate-expression-v1-20260726-022734-17441
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-temporal-dst-probe-v1-20260726-192802-38911
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-stl-single-v1-20260726-193736-42432
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-buffer-single-v1-20260726-193822-42713
/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-oom-misc-single-v1-20260726-193854-42969
```

新增完整通过 target:

- `arrow-compute-scalar-if-else-test`
- `arrow-compute-scalar-math-test`
- `arrow-compute-scalar-type-test`
- `arrow-compute-scalar-utility-test`
- `arrow-compute-kernel-utility-test`
- `arrow-compute-vector-test`
- `arrow-compute-vector-selection-test`
- `arrow-compute-vector-sort-test`
- `arrow-compute-vector-swizzle-test`
- `arrow-compute-row-test`
- `arrow-compute-expression-test`
- `arrow-compute-aggregate-test`

合计 3272 passed, 25 skipped。`arrow-compute-scalar-temporal-test` 全量结果保留为 46 passed, 1 skipped, 7 failed; 失败集中在历史 timezone/DST 规则差异, 不写作完整 target 通过。

补充 DST 对照结论: 当前真机缺少 `/usr/share/zoneinfo` 和 `/system/usr/share/zoneinfo`; Python `tzdata 2026.3` 提供的 `zoneinfo` 路径是已验证的稳定输入源。系统 `/etc/zoneinfo` 与 unset `TZDIR` 会扩大 temporal 失败范围, 不适合作为默认回退策略。
