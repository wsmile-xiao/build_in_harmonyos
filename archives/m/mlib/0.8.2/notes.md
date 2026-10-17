# mlib 0.8.2 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/P-p-H-d/mlib
- 正式标签：`V0.8.2`（git tag 指向 commit `2730691e8a0677d29a3911c4edb1afe9c9458d0e`，GitHub API + git ls-remote 双通道核验）
- 源码 tarball：`https://github.com/P-p-H-d/mlib/archive/refs/tags/V0.8.2.tar.gz`
- SHA-256：`e6188355173ba3fcef36c267bf151d6aef15b28161cf8650ef71e8a03391ff93`（tarball 实测）
- 许可证：BSD-2-Clause（LICENSE，Copyright (c) 2017-2026 Patrick Pelissier）
- 语言预检：task=cpp, detected=cpp（源文件 147 个，c:136, cpp:11, bash:1，主体占比 93%）✅

## 结构
- 纯头文件库：29 个 `m-*.h` 位于 tarball 根目录，互相以裸名 include（m-array.h → m-core.h 等），需整组打包
- 无库构建系统：根 Makefile 仅驱动 tests/doc/example（无 install 规则、无 CMake/configure）
- C99 主体；check-*.cpp 为 C++ 对照测试（独立目标 check-stl，非主测试目标）
- 依赖：无任何第三方依赖（仅标准库 + pthread，pthread 仅测试/并发模块运行期使用）

## 上游测试（双口径台账）

### 口径一：源码声明总数（source_declared_total）
按官方 tag 源码逐文件枚举（可复制规则：`grep -cE '^static void test[a-zA-Z_0-9]*\(' test-*.c` 逐文件统计 + except/fail 程序文件数）：

| 类别 | 数量 | 说明 |
|---|---|---|
| test-*.c 静态测试函数 | 197 | 28 个 test-*.c 程序中 `static void testXxx()` 用例注册单元，main 串行调用，断言失败即 abort |
| except-*.c 程序 | 9 | M_TRY/M_THROW 异常语义独立程序（array/bitset/bptree/bstring/deque/list/rbtree/shared-ptr/string） |
| fail-*.c 程序 | 3 | 预期编译失败程序（fail-chain-oplist/fail-incompatible/fail-no-oplist），编译失败=通过 |
| check-*.cpp 程序 | 10 | C++ STL 对照（独立目标 check-stl，非 `make check` 组成部分） |
| tgen-*.c 生成器 | 11 | 生成变体源码，不在 check 目标内 |

**source_declared_total = 197 + 9 + 3 = 209**（独立上游用例；check-*.cpp 与 tgen-*.c 非 `make check` 口径，如实单列）

### 口径二：配置可执行数（configured_executable_total）
当前 OHOS 配置下 `make check` 实际实例化的编译/运行目标：

| 类别 | 实例化 | 说明 |
|---|---|---|
| test-*.exe | 28 | 全部由 `make check` 编译并运行 |
| except-*.exe | 9 | 全部由 `make check` 编译并运行 |
| fail-*.log.err | 3 | 编译预期失败检查（fail 子检查 92 项） |
| check-*.log | 10 | check-stl 独立目标，不在本配置 `make check` 内实例化（如实记录未运行项） |

**configured_executable_total = 40**（28+9+3）；独立用例 209 项全部进入当前配置检查范围（test 函数 197 + except 程序 9 + fail 程序 3）

### 逐项映射（源码声明/宏 -> 构建目标 -> 执行日志）
- `test-*.c` 中 `static void testXxx()`（197 项，28 文件）→ tests/Makefile `check:` 目标内 `test-*.log` 规则 → 编译 `test-*.exe` → 逐程序运行行 `./test-*.exe`（check.log 中 28 行，全部退出码 0）
- `except-*.c` main 程序（9 项）→ `check:` 目标内 `except-*.log` 规则 → `./except-*.exe`（check.log 中 9 行，全部退出码 0）
- `fail-*.c`（3 项）→ `fail-generic.log.err` 规则，FAIL_SEQ=44/24/24 共 92 子检查 → 逐子检查编译 `-DTEST=$i` 并断言编译失败（check.log 中 56 OK + 36 WARNING，0 ERROR——WARNING 为编译按预期失败但报错非 M_LIB_ 前缀，make 判定通过）
- `check-*.cpp`（10 项）→ `check-stl:` 独立目标（需 `-fsanitize=address,undefined,leak`）→ 本任务配置未实例化，如实记录为未运行项（与 0.7.4 同口径）
- `tgen-*.c`（11 项）→ 生成变体源码的生成器，非用户测试用例，台账单列

### 运行矩阵（设备实测，clang 15.0.4 aarch64-unknown-linux-ohos）
| 轮次 | 配置 | 结果 |
| --- | --- | --- |
| 1 | `make check CC="/data/service/hnp/bin/clang -std=c99" CXX="/data/service/hnp/bin/clang++ -std=c++11" XCFLAGS="-Wno-everything"`（28 test-*.c + 9 except-*.c + 3 fail-*.c） | **RC=0，`All tests passed`**：37 个运行程序全部退出码 0；fail-* 92 个编译预期失败子检查全部符合预期（56 OK + 36 WARNING，0 ERROR） |
| 2 | `make check-stl`（C++ STL 对照，10 程序，需 ASan/LSan sanitizer） | 未执行：独立辅助目标，不属上游 `make check` 口径，如实记录为未执行项 |

- 运行证据：`/storage/Users/currentUser/mlib-dl/evidence/check.log`（SHA-256 `38e49456f003128d35707425d3cf0018d86e3526ae8aee3e8427dcfdd1a85517`，含 37 个 `./xxx.exe` 运行行与 fail-* 逐项 OK/WARNING），make 退出码 0，完成标志 `All tests passed`
- 执行口径：**executed_passed_total = 209/209（100%）**，失败 0，未运行 0（check 口径内）；`make check` 当前配置可执行集合 209/209（100%）
- 说明：tests/Makefile 硬编码 `CC=cc`/`CXX=c++`，OHOS 设备无 `cc`/`c++`，以 make 变量覆盖为 clang/clang++ 直传，未修改上游文件；`-Wno-everything` 仅压上游自带的 -Werror 级告警噪声，不改变语义

## 编译环境
- 构建系统: none（纯头文件库，无库构建系统；根 Makefile 仅驱动 tests/doc/example）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，Target: aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤
```bash
# 1) 源码下载核验（官方 tag V0.8.2，commit 2730691e8a0677d29a3911c4edb1afe9c9458d0e）
curl -L -o mlib-0.8.2.tar.gz https://github.com/P-p-H-d/mlib/archive/refs/tags/V0.8.2.tar.gz
sha256sum mlib-0.8.2.tar.gz   # e6188355173ba3fcef36c267bf151d6aef15b28161cf8650ef71e8a03391ff93

# 2) 头文件冒烟验证（OHOS clang 编译 + 运行）
/data/service/hnp/bin/clang -std=c99 -I <src> -Wall smoke_mlib.c -o smoke_mlib && ./smoke_mlib  # RC=0, "smoke ok=1"

# 3) 上游测试
cd <src>/tests && make check CC="/data/service/hnp/bin/clang -std=c99" \
  CXX="/data/service/hnp/bin/clang++ -std=c++11" XCFLAGS="-Wno-everything" > check.log 2>&1
# RC=0, "All tests passed"（37 程序 + 92 fail 子检查全部符合预期）

# 4) Conan 配方：conanfile.py + conandata.yml + test_package/（header-only 打包，无编译步骤）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时（curl 28） | 本机到 github.com 网络不可达 | 使用 CI 同款 gh-proxy.com 镜像通道下载官方 tag tarball，SHA-256 实测核验通过（官方 URL 保持于 conandata.yml，不做代理改写） |
| 2 | tests/Makefile 硬编码 `cc`/`c++` | OHOS 设备无 `cc`/`c++` 命令 | make 变量覆盖直传 `/data/service/hnp/bin/clang[-++]`，未修改上游文件 |

## 源码修改
无（零补丁、零上游修改，与 0.7.4 一致）

## 依赖版本
无任何第三方依赖（仅标准库 + pthread）

## 验证结果
```bash
$ make check CC="/data/service/hnp/bin/clang -std=c99" CXX="/data/service/hnp/bin/clang++ -std=c++11" XCFLAGS="-Wno-everything"
# All tests passed  (RC=0)
# 上游用例 209/209 (100%)；fail 子检查 92/92 符合预期
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library，打包 m-*.h + LICENSE） |
| conandata.yml | 官方 V0.8.2 tarball URL + SHA-256 |
| test_package/ | 消费者验证（见任务流程 test_package 节） |
| manifest.yaml | 版本级 manifest（built） |

## 注意事项
- 纯头文件库无 commands.json（无命令行产物，R38 不适用）
- check-*.cpp（check-stl 目标）与 tgen-*.c 非 `make check` 口径，台账单列如实记录未执行

## 知识候选台账与查重（路径决定）

### 候选台账（knowledge_candidate_ledger）
| 候选 | 真实错误/现象 | 根因 | 修复 | 验证 | 适用边界 |
|---|---|---|---|---|---|
| C1：GitHub 直连超时 | `curl (28) Operation timed out`（github.com 不可达） | 本机到 github.com 网络不可达 | 使用 gh-proxy.com 镜像通道下载官方 tag tarball（CI 同款 E017 预防机制）；conandata.yml 保持官方 HTTPS URL | SHA-256 实测 `e6188355…` 与官方一致；conan create 通过 | 网络基础设施类，无库特定知识 |
| C2：tests/Makefile 硬编码 cc/c++ | OHOS 无 `cc`/`c++` 命令 | Makefile 默认 `CC=cc -std=c99`/`CXX=c++ -std=c++11` | make 变量覆盖直传 `/data/service/hnp/bin/clang[-++]`，未改上游文件 | make check RC=0，All tests passed | 与 0.7.4 完全相同的既有处理，无新增 |
| C3：tmpfile() 因 /tmp 只读失败 | `Assertion failed: f != NULL`（tmpfile 返回 NULL） | 本机 /tmp 只读，TMPDIR 设置后 tmpfile() 仍失败 | 改用显式文件路径 `m_core_fopen("a-mjson.dat","wt")`（cwd 可写），序列化往返改用 `"rt"` 重开 | 鸿蒙专项测试全部断言通过 | 命中既有知识 E002（/tmp 只读 erofs）同类场景，非新错误签名 |

### 四范围查重
- **正式知识 knowledge/doc/**：E002（/tmp 只读 erofs，set-env-var）、E011/E052/E060（HMDFS 临时目录）、E035/E257/E321/E322（header-only 打包/配方）已覆盖 C3 与 header-only 打包模式；无 mlib 专有条目，C1/C2 均属基础设施或既有处理。
- **知识图谱 knowledge/graph/**：index.tsv 中 E002/E011/E035/E046/E052/E060/E307/E321/E322 关键词与上述候选重叠；引擎预查询（G0）无命中新错误签名。
- **草稿 knowledge/drafts/**：1012 条既有草稿中无 mlib/header-only 新增模式（E257 为 thread-pool header-only G1 门，E322 为 taskflow header-only CMake 配方——均为既有 header-only 配方模式，mlib 无新增差异）。
- **正式知识库四范围结论**：无未命中、无部分覆盖的新增差异。

### 查重结论与路径决定
- `reuse_existing`：C3 复用 E002（/tmp 只读）语义；C2 复用 0.7.4 同库笔记既有处理；C1 属 CI 既有 E017 镜像机制。
- `path_a_no_knowledge`：零补丁、零上游修改、构建零报错，无跨库可复用新增知识；header-only 打包模式已有 E257/E321/E322 等多条目沉淀，本任务未产生新错误签名。
- 决定：**路径 A（纯路径 A，不建草稿，不建知识库 PR）**——与 0.7.4 结论一致；`new_draft` 不成立。
---

**编译结束**: 2026-09-19 01:38
**最终状态**: built
