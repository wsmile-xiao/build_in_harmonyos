# hashmap 0.8.1 适配笔记

## 编译环境
- 构建系统: custom（单文件 C 库，无 configure/make/CMake；配方直接编译 hashmap.c）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（OHOS aarch64 profile: ci/conan/profiles/ohos-aarch64）
- 状态: published

## 编译步骤

1. 官方源码: https://github.com/tidwall/hashmap.c/archive/refs/tags/v0.8.1.tar.gz
   SHA-256: ebd1396d65fbe1081d5b3ed93a53c29d8c10c212a3a8c51ae990c84aaeda1c1e
2. init-build → lang-preflight（detected=c，任务语言 cpp，c↔cpp 兼容族，匹配通过）
3. 探索编译（work 目录）:
   - clang -c -O2 -fPIC hashmap.c -o hashmap.o && llvm-ar rcs libhashmap.a hashmap.o
   - clang -O2 -DHASHMAP_TEST hashmap.c -o hashmap-test（上游内置测试）
   - ./hashmap-test → PASSED（seed 随机、N=2000）
4. conan-init 生成配方后重写为 custom 配方（编译单 TU → libhashmap.a，安装 hashmap.h）
5. conan-verify 8 道门禁全部通过（G0-G4 + L2/L4/L5），可标记 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直接传仓库页 URL 下载到 HTML | 需传 tarball URL 而非仓库主页 | 改用 `https://github.com/tidwall/hashmap.c/archive/refs/tags/v0.8.1.tar.gz`（tag 带 v 前缀） |
| 2 | conan-verify G2 失败：`tools.build:compiler_executables:c` 不存在 | Conan 2.29.1 中该 conf 是 dict 类型，不是 `:c` 子键 | 改为 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后取 `["c"]` |
| 3 | test_package 运行时 `set alice failed` | 误解 API 语义：`hashmap_set()` 成功插入时**返回 NULL**（非 NULL 表示替换旧值），应使用 `hashmap_oom()` 判失败 | 重写 test.c，插入后检查 `hashmap_oom()`，替换路径检查返回值非 NULL |
| 4 | 镜像注入残留 conandata.yml.ghfast-bak | conan-verify 临时注入 ghfast.top 镜像后残留备份 | 已清理（不进入 PR） |

## 源码修改

无补丁（patches/ 为空）。单文件库源码零修改，仅提供 custom 配方编译打包。

## 依赖版本

无第三方强制依赖（纯标准 C 库实现，stdlib 即可）。

## 上游测试台账（R51 双口径，2026-09-17 实际运行）

### 枚举结果

上游**无独立测试文件、无 ctest、无 make check 目标**：测试全部内嵌在
`hashmap.c` 的 `#ifdef HASHMAP_TEST` 块（官方 README 声明入口
`cc -DHASHMAP_TEST hashmap.c && ./a.out`）。

| 枚举项 | 位置 | 分类 | 是否独立上游用例 |
|---|---|---|---|
| `all()` 测试函数（int/string 键压力测试） | hashmap.c:882-1039 | 官方内置自检（真实用户用例） | ✅ 是（唯一独立用例） |
| 哈希向量断言（sip/murmur/xxhash3） | hashmap.c:891-893 | all() 内部断言 | 计入 all()（3 条断言） |
| `benchmarks()` 基准函数（BENCH=1） | hashmap.c:1074-1135 | 基准，非通过性测试 | ❌ 否（基准模式，单独运行验证可执行） |
| 宏/框架内部代码（xmalloc/xfree/shuffle 等） | hashmap.c:821-880 | 测试辅助设施 | ❌ 否（工具函数，非用例） |
| SECTION/子节 | 无 | — | — |
| 样例/示例 | README Example（使用说明） | ❌ 否（文档示例） | — |

### 双口径统计

- `source_declared_total`（官方 tag 源码按枚举规则发现的独立测试声明总数）: **1**
  （`HASHMAP_TEST` 内置自检 `all()`，官方 README 明确为唯一测试入口）
- `configured_executable_total`（当前 OHOS 配置实际实例化的独立可执行用例数）: **1**
  （`clang -DHASHMAP_TEST hashmap.c` 编译出的单一自检可执行）
- `executed_passed_total`: **1**（默认模式 + SEED/N 变体均 PASSED，exit 0）
- 失败数: 0；未运行/未实例化: 0

### 源码声明 → 实际执行映射

1. 源码声明: `#ifdef HASHMAP_TEST` 块 `main()` → `all()`
2. 预处理/构建条件: `-DHASHMAP_TEST` 宏开关（官方入口，非互斥分支）
3. 构建目标: `clang -O2 -Wall -DHASHMAP_TEST hashmap.c -o hashmap-test`
4. 注册项: 单一可执行 `hashmap-test`（无 ctest/GTest 注册）
5. 实际执行日志:
   - `reports/upstream-tests/02-run-default.log`（N=2000, PASSED, exit 0）
   - `reports/upstream-tests/03-run-seed.log`（SEED=12345 N=5000, PASSED, exit 0）

### 通过率

- 全量通过率: **1/1 (100.0%)**（通过数 / 源码声明总数）
- 当前配置可执行集合通过率: **1/1 (100%)**
- 基准模式（BENCH=1）: `reports/upstream-tests/04-run-bench.log`，6 组基准全部正常执行
  （set/get/delete × cap 变体，N=100000，exit 0）——基准为性能测量，不计入通过率分母

### 日志 SHA-256

| 日志 | SHA-256 |
|---|---|
| 01-build-test.log | 3e6d132c8f10e1827ebee4c77380f389ca4c0d5e13bb24fd9e2751f943bf08d4 |
| 02-run-default.log | 58b102c46e9899c197f00a4d7612412883229524495bd714bf3f86a0a44ed9bb |
| 03-run-seed.log | 9c6ebcb31d1815443ddbedf9d996064e422c026d489ef00ecdb4e5f3aa52b1a1 |
| 04-run-bench.log | df45e8c5440d00f7efab9d839f41081d9e347e66f65531b06cf803fe0fc46f1d |

## 验证结果

```bash
# 上游内置测试（work 目录）
clang -O2 -Wall -DHASHMAP_TEST hashmap.c -o /tmp/hashmap-test && /tmp/hashmap-test
# → Running hashmap.c tests... seed=..., count=2000, item_size=4
# → PASSED (exit 0)

# conan-verify 8 门禁
python3 scripts/ohc-run.py conan-verify hashmap 0.8.1
# → G0-G4 + L2/L4/L5 全部 PASS，status 可标记 published
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | custom 配方：编译 hashmap.c → libhashmap.a（可选 .so），安装 hashmap.h |
| conandata.yml | 官方源 + SHA-256（ebd1396d...） |
| test_package/test.c | 消费者测试：经 hashmap.h 调用 new/set/get/delete/count/iter（真实断言） |
| test_package/MANIFEST.yml | 上游测试声明（HASHMAP_TEST 入口） |
| manifest.yaml | 版本元数据（custom 构建、published 状态） |
| reports/upstream-tests/*.log | 上游测试实际运行日志（含 SHA-256） |

## 注意事项

- `hashmap_set()` 成功插入返回 NULL（替换旧值时返回旧值指针），失败判据是
  `hashmap_oom()`——消费者代码极易踩坑，test_package 已按正确语义编写。
- 官方 tag 为 `v0.8.1`（带 v 前缀），下载 URL 必须用 tarball 地址。
- 无构建系统库（单 TU）走 custom 配方，编译器从
  `tools.build:compiler_executables`（dict）读取，符合 R33。

## 知识路径决定（Path B — 知识库扩展）

完整台账与七轴查重见 `reports/knowledge-candidate-ledger.md`（磁盘证据，
reports/ 不入 PR，随最终回报提交绝对路径与 SHA-256）。摘要：

| 候选 | 四范围查重 | 决定 |
|---|---|---|
| hashmap_set() 成功插入返回 NULL / hashmap_oom() 判据 | 全仓未命中 | **new_draft**（C1） |
| tools.build:compiler_executables 为 dict | 与 E392 完全一致 | **reuse_existing**（E392） |
| 无构建系统单 TU C 源库 custom 配方 direct-compile | 与 E257/E392/DRAFT-enet 部分重叠，存在新增差异 | **new_draft**（C3） |

- 草稿：`knowledge/drafts/DRAFT-hashmap-0.8.1-set-returns-null-on-insert.{kv,md}`
  `knowledge/drafts/DRAFT-hashmap-0.8.1-no-build-system-single-tu-lib.{kv,md}`
- PR 前缀：【知识库扩展】
---

**编译结束**: 2026-09-17 20:39
**最终状态**: published
