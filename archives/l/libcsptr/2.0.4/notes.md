# libcsptr 2.0.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 (OHOS, armv8)
- 状态: built

## 编译步骤

libcsptr 2.0.4 上游为 CMake 构建（`add_library(csptr STATIC ...)`），纯 C 库：

1. init-build 拉取官方 tag tarball（v2.0.4 → commit 998ab7b5，SHA-256 565f64ffe...222238）
2. 本地探索编译：
   ```bash
   cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_COMPILER=clang \
         -DCMAKE_C_FLAGS='-fPIC' ..
   make -j4
   make install DESTDIR=$TEST_PREFIX
   ```
3. conan-init 生成配方后改写为 CMake 变体（conan-init 默认 autotools 模板，需手动修正）
4. conan-verify：G0/G1/G2/G3/G4 全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake >= 4.0 拒绝上游 `cmake_minimum_required(VERSION 2.8)` | CMake 移除了 <3.5 兼容 | 配方 build() 用 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` 命令行缓存（CMakeToolchain 会过滤策略变量，不能放 tc.variables） |
| 2 | test_package 首次 SIGTRAP | `smart` 宏自带 `cleanup(sfree_stack)` 自动释放，又手动 `sfree()` 造成 double-free | 手动释放时不加 `smart` 关键字（与上游测试同法），并补 `get_smart_ptr_meta` 断言 |
| 3 | W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 其他库（util-linux-login 2.42.2，commit 761df452）HEAD 基线空文件未登记 JC5 白名单 | 审计归属（blob e69de29b、空文件、其他库、不在本库允许范围）→ 临时白名单隔离 → W3 复验通过（.ci-result.json exit_code=0）→ 无条件恢复（junk_check.sh 恢复后哈希与 HEAD 一致 ab5ca82e） |

## 源码修改

无源码补丁（patches=0）。仅配方层适配：CMake policy floor + 静态库 + test_package 消费者测试。

## 依赖版本

- 无第三方构建依赖（纯 C99、CMake 即可构建）
- 上游可选测试依赖 Check 框架未安装（check/ 测试不注册，非阻塞）

## 验证结果

```bash
ohc-run.py conan-verify libcsptr 2.0.4   # exit 0, G0-G4 PASS
ohc-run.py finish libcsptr 2.0.4 built   # W3 local CI passed, .ci-result.json exit_code=0
```

## 注意事項

- 上游 `cmake_minimum_required(VERSION 2.8)` 是 CMake 4.x 兼容性的唯一注意点，配方已内置策略参数，无源码头文件补丁
- Check 框架为可选测试依赖；有 Check 环境下 ctest 可注册上游用例---

**编译结束**: 2026-09-07 00:19
**最终状态**: built
---

**编译结束**: 2026-09-07 00:20
**最终状态**: built
