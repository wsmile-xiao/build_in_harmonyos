# libint 2.13.1 适配笔记

## 编译环境
- 构建系统: cmake（官方 release 预生成库 tarball，非 GitHub tag 源码包）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 1. 源码：官方 release 预生成库资产（v2.13.1 tag）
#    https://github.com/evaleev/libint/releases/download/v2.13.1/libint-2.13.1.tgz
#    sha256=029e1347774bbf740e8ef9118d736413b52c023b85a5f76b61ce6fbf1ab8e43b
#    （libint 仓库是"编译器+预生成库"双态架构：tag 源码包需先构建 build_libint
#      再 export 生成库源码，串行且极慢；release 预生成库 tarball 可直接 CMake 构建）

# 2. 配置 + 编译（探索期）
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX \
  -DCMAKE_PREFIX_PATH=<eigen-prefix> -DBUILD_SHARED_LIBS=OFF
cmake --build build -j$(nproc)
cmake --build build --target install

# 3. 上游测试
ctest --test-dir build --output-on-failure   # 13/13 全部通过

# 4. Conan 配方
python3 scripts/ohc-run.py conan-verify libint 2.13.1   # G0-G4/L2/L4/L5 全绿
python3 scripts/ohc-run.py finish libint 2.13.1 built    # W2/W3 通过，.ci-result.json exit_code=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tag 源码包无法直接构建（G0 clean-verify configure exit 127） | libint 源码树无 autotools configure；tag 源码包需先运行 libint 编译器（build_libint）+ export | 改用官方 release 预生成库 tarball（libint-2.13.1.tgz）作为 sources.url |
| 2 | test_package 编译错误：Engine 模板用法失败 | libint2 2.13 Engine 由模板类改为非模板类 | `libint2::Engine engine(libint2::Operator::overlap, 1, 0)`（operator, max_nprim, max_l） |
| 3 | test_package L0d stub_test_method 门禁失败 | test() 方法只调 cmake.test()，未实质运行被测包二进制（R34） | test() 改 `self.run(<bindir>/test_libint, env="conanrun")` 实跑消费者测试 |
| 4 | W3 JC5 拦截其他库遗留隐藏标记（cloog/kics .build-closed 等） | 其他库历史基线文件在整仓扫描中被 JC5 白名单拦截 | 按基线隔离规则临时 index 级隔离 → 复验 W3 → 无条件恢复（blob 哈希 e69de29b 空文件，已恢复验证） |

## 依赖版本

- eigen/3.4.1（header-only，C++11 API 必需，transitive_headers）
- Boost：可选；系统缺失时 CMake 配置期自动解包 external/boost.tar.gz

## 验证结果

```bash
# 上游测试：13/13 通过（eritest/unit/hf/hf++）
100% tests passed, 0 tests failed out of 13
# conan-verify：G1/G0/G2/G3/G4 + L2/L4/L5 全绿
✅ 配方验证通过: libint 2.13.1
# finish W3 本地 CI 模拟：1/1 包构建测试成功
Success: 1, Failed: 0, Pass rate: 100.0%
# test_package 消费者验证：重叠积分 S_ss ≈ 1.0
PASS: libint2 overlap integral ok
```

## 注意事项

- 预生成库 tarball 的 lmax=6 与标准积分类型由官方发布固定；若需自定义 AM/orderings，
  必须走 tag 源码包 + build_libint 导出流程（不适用本配方）。
- 知识路径：路径 B，草稿对
  knowledge/drafts/DRAFT-libint-2.13.1-pre-generated-library-tarball.{md,kv}。

---

**编译结束**: 2026-09-22 23:26
**最终状态**: built
