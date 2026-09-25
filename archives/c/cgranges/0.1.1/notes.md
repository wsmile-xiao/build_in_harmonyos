# cgranges 0.1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，无 configure 脚本）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. init-build 下载官方 tag v0.1.1 tarball（SHA-256 9445ec0cab97e736981db440cb306069d6fe33f638fbd142c106a0408ba10d6c）
2. 库对象编译: `clang -fPIC -O2 -c cgranges.c`（无 configure，直接 make）
3. 上游测试编译: `cd test && make`（4 个可执行测试目标）
4. conan-verify 全门禁通过（G1-G4 + L2/L4/L5），conan create 干净构建成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bedcov-iitree-bfs 编译失败: `IITreeBFS.h:65: use of undeclared identifier 'max_level'` | 上游 v0.1.1 的 cpp/IITreeBFS.h 在 overlap() 中引用从未声明的 max_level 成员（仅非 BFS 版 IITree.h 有该成员），属上游源码缺陷 | 最小补丁: 空树守卫改为等价判断 `if (a.size() == 0) return false;`（patches/0001-cpp-IITreeBFS.h.patch），修复后编译运行通过 |
| 2 | test_package 消费者测试 SIGTRAP | Release 构建定义 NDEBUG，assert() 中初始化调用被剥离，后续断言触发信号 | test.c 改用显式错误检查（CHECK 宏 + 返回值判断），不依赖 assert 初始化 |

## 源码修改

- cpp/IITreeBFS.h（经补丁 0001-cpp-IITreeBFS.h.patch）：`max_level < 0` → `a.size() == 0` 空树守卫修正，不改算法逻辑、无平台宏。

## 依赖版本

- zlib（系统 /usr/lib/libz.so.1.2.13，上游测试 -lz 链接）
- 无 Conan 外部依赖

## 验证结果

```bash
cd test && make          # 4 目标全部编译通过（含 IITreeBFS.h 修复）
for e in bedcov-cr bedcov-itree bedcov-iitree bedcov-iitree-bfs; do ./$e test1.bed test2.bed; done  # 全部 exit 0，输出一致
# HarmonyOS 专项测试: 12/12 断言通过 (ohos-cgranges-api-test)
# conan create: 干净构建 + test_package 消费者测试 PASS
# 上游全量通过率: 4/4 = 100%
```

## 交付物

- archives/c/cgranges/0.1.1/: conanfile.py + conandata.yml + test_package/ + patches/（1 个补丁）
- 库类型（静态库 libcgranges.a + 公开头文件），非 CLI，无需 commands.json

## 注意事项

- 上游 python/js 基准脚本（bedcov-*.py/js）为辅助对比脚本，非独立测试用例；python 需 Cython 构建绑定、node 脚本在 OHOS 运行时崩溃，均不影响库交付。
- 知识候选台账见 reports/knowledge-candidate-ledger.md，查重结论 path_a_no_knowledge。
---

**编译结束**: 2026-09-22 01:17
**最终状态**: built
