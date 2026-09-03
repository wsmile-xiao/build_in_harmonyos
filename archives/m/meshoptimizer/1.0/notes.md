# meshoptimizer 1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++ (aarch64-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 源码: 官方 GitHub tag v1.0
#   https://github.com/zeux/meshoptimizer/archive/refs/tags/v1.0.tar.gz
#   sha256: 30d1c3651986b2074e847b17223a7269c9612ab7f148b944250f81214fed4993

# 上游验证编译（含 demo 测试）
cmake -S . -B build-ci -DMESHOPT_BUILD_DEMO=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-ci -j4
./build-ci/meshoptdemo            # 无参数运行 runTests()，exit=0 即全部通过

# Conan 配方
python3 scripts/ohc-run.py conan-init meshoptimizer 1.0
python3 scripts/ohc-run.py conan-verify meshoptimizer 1.0   # G1-G4 全过
python3 scripts/ohc-run.py finish meshoptimizer 1.0 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 主页 URL 返回 HTML | --url 用了仓库主页而非 tarball | 改用 `.../archive/refs/tags/v1.0.tar.gz` |
| 2 | conan-init 生成 autotools 配方 | 模板按 URL 后缀猜测构建系统 | 重写为 CMake 配方（CMakeToolchain/CMake） |
| 3 | test_package 往返测试失败（rc=-3 → round-trip mismatch） | ① decode 需传实际编码长度而非 bound；② 编码器 getEdgeFifo 隐式旋转三角形顶点，解码结果三角形集合等价而非字节一致 | 传 encoded_size；按排序三角形集合等价比较（详见知识草稿） |
| 4 | finish W3 JC 门禁失败 | 本地无 refs/remotes/origin/main 且无新 commit 时 junk_check 退化为整仓 full 模式，命中其他库历史基线 junk（embree/flatcv/libmorton/goaccess） | `git fetch origin main:refs/remotes/origin/main` + 提交本包变更 → JC 回增量 diff 模式 |
| 5 | 本地出现 conandata.yml.ghfast-bak 残留 | conan-verify 镜像注入备份未清理 | 提交前删除并 git rm --cached |

## 源码修改

无上游源码补丁（patches/ 为空）。仅新增 Conan 配方与 test_package 消费者测试。

## 依赖版本

- 无运行时依赖（CI 纯 C++ 单库）
- 工具链: clang 15.0.4, cmake 4.1.2, conan 2.29.1

## 验证结果

```bash
# 上游测试: demo/tests.cpp runTests() 93 个独立用例 + 328 处 assert，全部通过（exit=0）
./build-ci/meshoptdemo

# 消费者测试（conan create 内 ctest 1/1 PASS）
test_meshoptimizer: simplify 36->36 idx, vcache optimized, codec roundtrip 52 bytes

# W3 本地 CI: JC_RESULT=pass, L0 pass, L1 pass (test_package), Pass rate 100%
```

## 注意事项

- 上游测试入口为 `demo/meshoptdemo`（无参数运行 runTests()），无 make check / ctest 目标；断言静默式，exit=0 即全过。
- 索引编解码往返验证必须按三角形集合等价比较，不能 memcmp（详见 DRAFT-meshoptimizer-1.0-index-codec-triangle-rotation）。
- 共享仓库执行 W3 前先确保 refs/remotes/origin/main 存在并已提交本包变更，避免 junk_check 整仓 full 模式误报。
---

**编译结束**: 2026-09-03 14:22
**最终状态**: published
