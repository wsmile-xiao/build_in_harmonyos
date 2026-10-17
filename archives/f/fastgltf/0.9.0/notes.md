# fastgltf 0.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++（OHOS SDK 15.0.4，aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 下载官方 v0.9.0 tarball（https://github.com/spnda/fastgltf/archive/refs/tags/v0.9.0.tar.gz，
   sha256=0bb564e127b14c22f062db50f89381dd2e0a20dbaf4987ca138a4ae8728712f9）。
2. 编写 conanfile.py（CMakeDeps + CMakeToolchain），声明 simdjson/4.6.3 依赖，
   FASTGLTF_ENABLE_TESTS/EXAMPLES/DOCS 均 OFF。
3. conan create（profile: ci/conan/profiles/ohos-aarch64）→ 构建通过，test_package 消费者测试 1/1 通过。
4. ohc-run.py conan-verify（G0-G4 PASS）+ finish（W3 本地 CI 模拟：JC/L0/L1/L4/L5 全 PASS）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试在 OHOS 工具链编译失败：`__crc32cd` 等未声明 | OHOS clang 15 默认未启用 ARMv8 CRC 特性（arm_acle.h 受 __ARM_FEATURE_CRC32 保护） | 编译标志加 `-march=armv8.2-a+crc`（conanfile 按 os=OHOS 且 arch=armv8 限定） |
| 2 | `std::pmr`（<memory_resource>）在 OHOS libc++15 缺失 | OHOS libc++ 仅提供 experimental/memory_resource，无标准头 | 库本体经 FASTGLTF_MISSING_MEMORY_RESOURCE 自动回退普通容器；仅上游测试曾用临时 shim 编译运行，配方构建不依赖 |
| 3 | W3 本地 CI 模拟曾被 JC 全仓扫描其他库历史垃圾文件拦截 | junk_check full 模式扫描整仓，其他库历史残留 .orig/.ghfast-bak | 提交本库变更后 JC 进入增量模式（只检查本 PR diff），通过 |

## 源码修改

无（未修改上游源码，无 patches）。

## 依赖版本

- simdjson/4.6.3（ohpcd 制品仓）
- 测试侧：Catch2 v3.7.0、glm 1.0.1（仅上游测试，不进入配方）

## 验证结果

```bash
conan create archives/f/fastgltf/0.9.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → 构建通过，test_package: 1/1 tests passed
python3 scripts/ohc-run.py finish fastgltf 0.9.0 built
# → conan-verify G0-G4 PASS；W3 本地 CI：JC/L0/L1/L4/L5 全 PASS（.ci-result.json exit_code=0）
# 上游测试（OHOS 工具链实测，见执行端台账）：独立用例 79，通过 76，断言 267724/267726 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（simdjson 依赖 + OHOS ARM CRC 标志） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | 消费者测试（真实调用 fastgltf API） |

## 注意事项

- OHOS 工具链 clang 15 需要 `-march=armv8.2-a+crc` 才能编译 fastgltf 的 ARMv8 CRC 路径。
- 上游测试的样例资源（glTF-Sample-Models）不在 PR 内，测试统计以执行端台账与日志为准。
