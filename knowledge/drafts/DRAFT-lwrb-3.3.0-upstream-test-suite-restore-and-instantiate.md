# DRAFT-lwrb-3.3.0-upstream-test-suite-restore-and-instantiate：官方 tarball 缺测试框架 submodule + 孤儿测试文件时，source() 补齐 + wire/API 移植/runner 三段式实例化

> Contributor: pc4-52 | Status: Draft | Updated: 2026-09-27
> Source: lwrb 3.3.0 HarmonyOS PC adaptation（archives/l/lwrb/3.3.0，r01）
> 对应：knowledge/drafts/DRAFT-lwrb-3.3.0-upstream-test-suite-restore-and-instantiate.kv
> 关系：similar_to `DRAFT-bandit-2.0.0-github-tarball-submodule-locked-commit`（submodule 官方源补齐）、E294（第二构建树跑上游测试）、E589 draft（runner 派发计数）

## 现象

lwrb 3.3.0 官方 tarball 中 `third_party/Unity` 与 `third_party/sanitizers-cmake`
两个 submodule 均为空占位（0 文件）。上游测试项目（`lwrb/test/CMakeLists.txt`，
独立 CMake 项目 `project(lwrb-testing)`）硬性依赖两者，首次配置/构建首错：

```text
CMake Error at CMakeLists.txt:28 (add_sanitizers):
  Unknown CMake command "add_sanitizers".          ← sanitizers-cmake 缺失
fatal error: 'unity.h' file not found              ← Unity 缺失
```

同时 `lwrb/test/test_ex.c`（10 个 Unity 用例）被 `#ifdef TEST` 守卫、从未被任何
构建目标引用；手工接入后出现旧 API 错误与缺失入口：

```text
error: no member named 'w' in 'struct lwrb'        ← 3.3.0 已更名 r_ptr/w_ptr
implicit declaration of function 'lwrb_copy'       ← 已更名 lwrb_move
undefined symbol: main                             ← 该文件只定义用例，无 main()
```

## 根因分析

1. GitHub archive 生成器只打包 git 跟踪树：submodule 目录在 tarball 中为空占位
   （`.gitmodules` 只声明 path/url）。测试框架（Unity）与测试构建辅助
   （sanitizers-cmake）属于**测试专用硬依赖**，缺失时上游测试项目无法配置/编译。
2. 上游仓库会保留守卫宏隔离、从未接入构建目标的遗留测试文件（lwrb 的 test_ex.c
   按 3.3.0 之前的公开 API 编写：结构体字段 `r`/`w` → `r_ptr`/`w_ptr`，
   `lwrb_copy` → `lwrb_move`，且 overwrite_5 断言旧 overwrite 语义）。照抄上游
   构建只会构建 test.c（lwrb_test），10 个扩展用例整组漏跑。

## 解决方案

**① 配方 source() 官方源补齐测试框架 submodule**（conandata 多数据源）：

```python
get(self, **self.conan_data["unity"], destination="third_party/Unity", strip_root=True)
get(self, **self.conan_data["sanitizers_cmake"], destination="third_party/sanitizers-cmake", strip_root=True)
```

```yaml
unity:
  url: "https://github.com/ThrowTheSwitch/Unity/archive/refs/tags/v2.7.0.tar.gz"
  sha256: "e84eb301..."
sanitizers_cmake:
  url: "https://github.com/arsenm/sanitizers-cmake/archive/refs/heads/master.tar.gz"
  sha256: "8d40d50f..."
```

> 要点：有 release tag 用 tag 归档；**仓库无任何 tag 时用官方分支归档**
> （sanitizers-cmake 全仓库无 tag，`v0.1.0` 归档返回 404 → 改用 `refs/heads/master`）。

**② 孤儿测试文件三段式实例化**（三个最小补丁，不改被测库语义）：

- **wire 目标**：在测试 CMakeLists 中新增独立可执行目标（lwrb_test_ex），
  声明守卫宏需要的编译定义（TEST/LWRB_DEV/LWRB_EXTENDED）与两个 include 目录
  （`<src>/include` 与 `<src>/include/lwrb`，因该文件直接 `#include "lwrb.h"`）。
- **API 移植**：把旧字段/旧函数名替换为当前公开 API（`r`→`r_ptr`、`w`→`w_ptr`、
  `lwrb_copy(`→`lwrb_move(`），并校正随语义变更的旧断言（overwrite_5 按
  3.3.0 的 reset+尾部写入语义对齐，与同文件 overwrite_6 一致）。
- **runner**：新增 `lwrb_test_ex_main.c` 提供 `main()`，`UNITY_BEGIN()` 后
  `RUN_TEST` 派发全部用例，`return UNITY_END()`。

**③ 上报证据**：conan create 内以 `HMBS_UPSTREAM_TEST_RESULT` JSON
（discovered/executed/passed/failed + 各套件 tail）上报双套件真实运行结果。

## 验证

```bash
# 独立复跑（配方补丁已应用）
CC=clang CFLAGS="-fPIC -O2" cmake ../lwrb/test -DCMAKE_BUILD_TYPE=Release   # exit 0
make -j4                                                                    # exit 0
./lwrb_test    → "5 Tests 0 Failures" / OK                                  # exit 0
./lwrb_test_ex → "10 Tests 0 Failures" / OK                                 # exit 0

# conan create 内
# lwrb_test:   declared=5  executed=5  passed=5  failed=0  exit=0
# lwrb_test_ex: declared=10 executed=10 passed=10 failed=0 exit=0
# HMBS_UPSTREAM_TEST_RESULT: status=passed discovered=15 executed=15 passed=15 failed=0
```

全量通过率 15/15 = 100%，与源码声明总数一致（test.c 5 + test_ex.c 10）。

## 适用边界

- 适用：测试框架/测试辅助以 submodule 形式存在且官方 tarball 不含其内容；
  上游存在守卫隔离、未接线、旧 API、无 main 的孤儿测试文件。
- 反例：submodule 内容不影响测试运行（可选依赖，按 E425 占位裁剪）；
  测试文件已由上游构建目标接线且无守卫（无需 wire）；API 未更名（无需移植）——
  此时套用本模式属于过度改造。

## 查重差异

- 既有条目覆盖部分：bandit 草稿（官方源补齐 submodule，但面向编译期头文件硬依赖
  且用 Trees API 锁 commit）；E294（第二构建树跑上游测试，构建策略层面）；
  E589 草稿（注册数 vs runner 派发计数口径）。
- 本轮新增部分：测试专用 submodule 恢复（含"无 tag 仓库用分支归档"边界）、
  孤儿测试文件"wire + API 移植 + runner"三段式实例化、双套件
  HMBS_UPSTREAM_TEST_RESULT 证据格式。
- 组合/边界/迁移三轴均为新增（详见 reports/knowledge-candidate-ledger.md 七轴表）。
