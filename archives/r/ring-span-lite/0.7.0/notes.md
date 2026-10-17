# ring-span-lite 0.7.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，无 autotools/configure）
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

header-only 库，无需真正编译产物；conan create 在 OHOS (aarch64, armv8) profile 下：

```bash
conan create archives/r/ring-span-lite/0.7.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

G2（conan create）在 OHOS 交叉 profile 下成功：CMakeToolchain 将 `os=OHOS` 映射为
`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（E092 预防，与 nonstd-lite
家族其它库一致）；`RING_SPAN_LITE_OPT_BUILD_TESTS/EXAMPLES` 关闭（测试在 test_package
消费者侧验证）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时/返回 HTML | 本机 GitHub 主域不可达，仅 codeload 官方归档端点可达 | conandata 用官方 `github.com/.../archive/refs/tags/v0.7.0.tar.gz` URL，SHA-256 用 codeload 官方字节实测 `7650bb1b...`（两者逐字节一致）；本地构建走 ohc E017 ghfast.top 镜像注入 |
| 2 | conan-init 生成 autotools 模板 | 工具按 URL 猜测构建系统，实际为 CMake | 重写 conanfile.py 为 CMake header-only（参照 variant-lite 同族配方），package_type=header-library |
| 3 | test_package generate() 冲突 | generators 同时声明 CMakeToolchain 又在 generate() 实例化 | generators 仅留 CMakeDeps，CMakeToolchain 在 generate() 中显式实例化（OHOS 映射需要） |
| 4 | 消费者测试 nonstd::ring<int> 编译失败 | ring 模板参数是容器类型而非元素类型 | 改为 `nonstd::ring<std::vector<int>>`（对齐上游测试用法） |

## 源码修改

无（无补丁，patches/ 为空）。

## 依赖版本

- 无第三方依赖（header-only，conan requires 空；L0i 检查对象为当前库自身）

## 验证结果

```bash
# 上游测试（4 标准 × 87 可见用例，详见 r01-upstream-test-ledger.md）
#   cpp98/cpp11/cpp14/cpp17 各 'All 87 selected tests passed.'
#   + 6 信息用例 + 3 assert 断言用例（按设计 abort）+ 1 applet，全量 97/97
# 消费者测试（HarmonyOS 专项）
clang++ -std=c++17 -I include test_ring_span_lite.cpp && ./test_ring_span_lite
#   ring-span-lite 0.7.0 consumer test: ALL PASSED
```

## 注意事项

- 本库为 nonstd-lite 家族（同 martinmoene/string-view-lite、variant-lite 等），
  OHOS 适配模式（E092 映射 + header-only）与家族一致，无平台专有代码需求。
---

**编译结束**: 2026-09-02 23:10
**最终状态**: built
