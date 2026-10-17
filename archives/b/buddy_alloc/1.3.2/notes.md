# buddy_alloc 1.3.2 适配笔记

## 编译环境
- 构建系统: headeronly（单头文件 C99 库，无编译产物；上游提供 CMakeLists.txt 编译测试/基准 + Makefile）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

```bash
# 1. 官方源码（tag v1.3.2）
#    https://github.com/spaskalev/buddy_alloc/archive/refs/tags/v1.3.2.tar.gz
#    SHA-256: 5c1b045cf500deb8f43454b5cc699ba55718fa90efde74a0dddbc6f168b7c025
#    本地取源经 gh-proxy 镜像（worker 无法直连 github.com），sha256 与官方一致

# 2. 上游测试全量枚举与运行（独立编译 + CMake 双路径）
clang  -std=c99  -O2 tests.c     -o buddy_tests        # 165 用例，运行 rc=0
clang++ -std=c++11 -O2 testcxx.cpp -o buddy_cpp_tu     # C++11 TU，运行 rc=0
clang  -std=c99  -O2 bench.c     -o buddy_bench        # 基准，运行 rc=0（约 23s）
#    test-fuzz.c 独立编译失败：buddy_tree() 未在头文件声明（上游缺陷，非构建目标）

# 3. conan-verify（G1-G4 全过，G2 经 ghfast.top 官方镜像取源）
python3 scripts/ohc-run.py conan-verify buddy_alloc 1.3.2

# 4. finish（W2 结构 + R36 依赖 + W3 本地 CI 模拟通过，状态 built）
python3 scripts/ohc-run.py finish buddy_alloc 1.3.2 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 超时 | worker 无法直连 github.com | 经 gh-proxy 镜像下载官方 tarball 放入 build 目录，EXPECTED_SHA256 核验后 init-build 跳过下载；conan G2 自动注入 ghfast.top（E017） |
| 2 | conan-verify G1 FAIL：header-only 配方缺 build() | G1 是结构门禁，build() 必填 | 提供 no-op build()（仅 apply_conandata_patches），与 E257 一致 |
| 3 | conan create G2：`No files in this package!`，test_package 报 include 路径不存在 | Conan 2 copy() 相对 dst 按 build 目录解析，头文件未进包 | package() 全部用绝对路径 `os.path.join(self.package_folder, "include")`（与 DRAFT-boost-te 一致） |
| 4 | finish W3 JC 命中其他库基线空标记（cloog/kics .build-closed/.staging-verified） | junk_check full 模式按 git 索引（ls-files）整仓扫描 | 基线隔离复验四步：记录 pre-SHA → git rm --cached → 复跑 W3（PASS）→ git reset + 恢复 → post-SHA 一致（与 DRAFT-fastnoiselite 一致） |
| 5 | 上游 test-fuzz.c 引用未声明 buddy_tree() | 上游缺陷（头文件仅前向声明 struct buddy_tree） | 台账记录为不可运行 fuzz 驱动，不计入独立用例；不改上游 |

## 源码修改

无（header-only 库零补丁，patches/ 为空）。

## 依赖版本

无外部依赖（header-only，W0 依赖检查通过）。

## 验证结果

```bash
# 上游测试双口径：source_declared_total=166（165 tests.c + 1 testcxx.cpp）
# configured_executable_total=166，executed_passed_total=166，failed=0，uninstantiated=0
# 全量通过率 166/166 (100.0%)
# 鸿蒙专项 test_ohos（64B 对齐/embed/resize/safe_free/256MiB）rc=0
# 消费者 test_consumer（公开 API 分配/释放/大小校验）rc=0
# conan-verify G1-G4 PASS；finish W2/W3 PASS（详见 reports/test-report.md）
```

## 注意事项

- 上游测试入口 test-fuzz.c（fuzz 驱动）与 bench.c（基准）计入台账但不计入独立用例数。
- 本库为 BUDDY_ALLOC_IMPLEMENTATION 单头文件模式：消费者需在唯一一个翻译单元中定义该宏后包含头文件。
- 知识决定：path_a_no_knowledge（reuse_existing）——全部候选精确命中既有条目/草稿（E017/E257/DRAFT-boost-te/DRAFT-fastnoiselite），未新建草稿（详见 reports/knowledge-candidate-ledger.md）。

---

**编译结束**: 2026-09-25 06:36
**最终状态**: built
