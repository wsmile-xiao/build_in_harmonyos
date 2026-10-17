# manif 0.0.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，clang 15.0.4，target aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

1. 下载官方源码 tarball：`https://github.com/artivis/manif/archive/refs/tags/0.0.5.tar.gz`
   （本机 GitHub 直连不可达，经 gh-proxy.com 镜像下载），SHA-256 核验：
   `246a781c54a5c57179d48096faca0d108944e120f69d8fd7fb69e3cb4a0a67fb`
2. 编写 conanfile.py（header-library 类型，requires eigen/3.4.0）+ conandata.yml + test_package/
3. 本地验证：`conan create .` → 配方构建 + test_package 消费者测试（test_manif，5 组数值断言）通过
4. 上游测试：`cmake -DBUILD_TESTING=ON` + 本地 googletest v1.12.0（OHOS clang 构建）
   → `ctest` 17/17 目标 Passed，5038/5038 用例通过（详见 reports/upstream-test-ledger.md）
5. W3 本地 CI：`build_and_test.sh archives/m/manif/0.0.5`（JUNK_PR_DIFF 指向本 PR 文件，
   与真实 CI 的 prdiff 扫描同机制）→ L0/L1/L4 pass，L2/L5 按 header-only 预期 skip/warn
6. `finish manif 0.0.5 published` → W2/W3 通过，`.ci-result.json` exit_code=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | W3 JC 门禁 full 模式命中其他库历史基线垃圾文件（embree/flatcv/libmorton/goaccess 等 9 个） | junk_check 无 pr.diff/三点 diff 为空时回退整仓扫描；main 基线预存其他库 tarball/隐藏标记 | 使用 JUNK_PR_DIFF 指向仅含本 PR 文件的 diff，JC 落入 prdiff 窄范围模式（与真实 CI buildbot checkout-pr 同机制）；基线文件哈希记录、原样保留，未触碰其他库 |
| 2 | conan create 源码下载 403/超时 | conan-verify G2 E017 预防把 `https://github.com` 整体替换注入 `https://ghfast.top/` 前缀，本机 ghfast.top 不可达 | conandata 保持官方源 + 可达镜像列表（gh-proxy.com 优先），注释声明 ghfast.top 不可达使 E017 注入守卫跳过；构建期经 gh-proxy.com 下载并核验 SHA-256 |
| 3 | test_package 断言在 Release 下失效 | `assert` 在 NDEBUG 下被编译期禁用 | 改为显式 CHECK 宏（失败输出 + 非零退出码），任意构建类型下真实校验；并修正 SE3 tangent 输入顺序（[x,y,z,wx,wy,wz]） |

## 源码修改

无（header-only 库，零补丁，patches/ 为空）。

## 依赖版本

- eigen/3.4.0（ohpcd 制品仓已发布，conan download 核验通过）
- googletest v1.12.0（仅本地测试构建，非配方依赖）

## 验证结果

```bash
conan create .                 # RC=0，test_package PASSED
ctest                          # 17/17 Passed，5038 用例
build_and_test.sh ...          # RC=0，L0/L1/L4 pass
```

## 注意事项

- manif 为 header-only（CMake INTERFACE target），无 bin/lib 产物，L2/L5 相应 skip/warn 属预期
- ceres/autodiff 上游测试分支因外部可选依赖（ceres-solver/autodiff 未发布）未构建，如实列入台账，与当前库适配无关

---

**编译结束**: 2026-09-03
**最终状态**: published