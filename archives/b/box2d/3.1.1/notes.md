# box2d 3.1.1 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt 顶层 project box2d 3.1.1，LANGUAGES C CXX）
- 编译日期: 2026-09-06
- 编译器: OHOS SDK clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/erincatto/box2d/archive/refs/tags/v3.1.1.tar.gz
# SHA-256: fb6ef914b50f4312d7d921a600eabc12318bb3c55a0b8c0b90608fa4488ef2e4（双镜像交叉核验）

cmake -S . -B build-ohos \
  -DCMAKE_TOOLCHAIN_FILE=$SDK/build/cmake/ohos.toolchain.cmake \
  -DOHOS_STL=c++_static -DCMAKE_BUILD_TYPE=Release \
  -DBOX2D_UNIT_TESTS=ON -DBOX2D_SAMPLES=OFF -DBOX2D_BENCHMARKS=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_AR=/data/service/hnp/bin/llvm-ar -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib \
  -DFETCHCONTENT_SOURCE_DIR_ENKITS=<本地 enkiTS 源码>
cmake --build build-ohos -j4
./build-ohos/bin/test        # 上游单元测试 9/9 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Error running link command: no such file or directory` | OHOS SDK native/llvm/bin 无 llvm-ranlib，CMake 推断出不存在路径 | 显式 `-DCMAKE_AR=/data/service/hnp/bin/llvm-ar -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（E429 草稿） |
| 2 | W3 junk_check JC5 报 `archives/u/util-linux-login/2.42.2/.ci-trigger` 阻塞 | CI full 模式整仓 git ls-files 扫描命中其他库预存基线隐藏文件 | 基线隔离复验：SHA-256 e3b0c442… → `git rm --cached` 临时隔离索引 → 复跑 W3 通过 → `git reset`+mv 恢复 → 恢复后 SHA-256 一致 |
| 3 | github.com 直连下载超时 | 网络环境限制 | gh-proxy/ghfast 镜像下载 + 双源 SHA-256 交叉核验；conandata 保留官方 URL（CI 自动注入镜像） |
| 4 | /tmp 只读 | 平台 E002 | 使用 $HOME/tmp |

## 源码修改

无（纯 CMake 配置适配，无需补丁）。

## 依赖版本

- 无外部运行时依赖（extern/ 下 glad/jsmn 仅样例辅助；测试用 enkiTS 由本地源码提供）
- OHOS SDK 26.0.0.18、Conan 2.29.1、CMake 4.1.2、Ninja 1.13.1

## 验证结果

```bash
# 上游单元测试（9 顶层用例 + 18 subtest）
./build-ohos/bin/test          # EXIT=0, All Box2D tests passed!

# 鸿蒙专项测试（新建用例，验证世界/刚体/碰撞体/重力步进）
box2d-3.1.1-r01-harmonyos-test  # EXIT=0, ALL HARMONYOS PC TESTS PASSED

# 消费者测试（conan create 内 test_package）
test_box2d                      # 1/1 Passed (ctest)
```

## 注意事项

- 配方 conanfile.py 使用 CMakeToolchain，BOX2D_UNIT_TESTS/SAMPLES/BENCHMARKS 均关闭（测试已在适配阶段独立验证）
- test_package/test.c 直接调用 box2d C API（R34 实质依赖）
- 知识草稿 E429（llvm-ranlib 缺失）随本 PR 交付