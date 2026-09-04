# boolean-lite 0.1.0 适配笔记

## 编译环境
- 构建系统: cmake (INTERFACE header-only)
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 / clang++ (aarch64-linux-ohos)
- Conan: 2.29.1 (OHOS 适配版, profile: ci/conan/profiles/ohos-aarch64)

## 编译步骤

```bash
# 上游测试（原生 CMake 全量枚举并运行）
cmake -DBOOLEAN_LITE_OPT_BUILD_TESTS=ON -DBOOLEAN_LITE_OPT_BUILD_EXAMPLES=OFF ..
cmake --build . --parallel 4
ctest --output-on-failure            # 4 变体 x 17 用例全部通过

# Conan 配方生成与验证
python3 scripts/ohc-run.py conan-init boolean-lite 0.1.0       # 改写为 CMake header-only 配方
python3 scripts/ohc-run.py conan-verify boolean-lite 0.1.0     # G1-G4 全 PASS

# finish 收尾
python3 scripts/ohc-run.py finish boolean-lite 0.1.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 Autotools 模板 | init_build 按 URL 猜测构建系统为 autotools | 按同类 nonstd-lite 库（byte-lite/any-lite）改写为 CMake header-only 配方（package_type=header-library, CMakeToolchain, CMAKE_SYSTEM_NAME=Linux for OHOS） |
| 2 | conandata.yml sha256 为占位符 | 模板生成未回填 | 用官方 tarball 实测 sha256 回填: 30687455c55877464b61b87b66798af8bce45b6f90f1709c030f263fdcb5d97d |
| 3 | test_package 首轮编译报 `no member named 'boolean' in namespace 'nonstd'` | 头文件仅导出 `nonstd::boolean_`（`using boolean_lite::boolean_;`），无 `nonstd::boolean` 别名 | 消费者测试改用 `nonstd::boolean_` |
| 4 | 自写断言 `!!t` 失败 | 双重取反即原值，断言逻辑写反 | 改用 `boolean_ neg = !t; if (neg) ...` 验证取反 |
| 5 | W3 本地 CI 被 JC 拦截（3 个 junk） | junk_check 回退 full 模式扫描全仓，拦到 main 分支历史遗留的其他库 junk 文件 | 只提交本库归档后再跑 finish（incremental 模式仅扫本库 diff） |

## 源码修改

无。纯 header-only 库，无补丁（patches/ 为空）。

## 依赖版本

- 无第三方依赖（header-only，无 requires）。

## 验证结果

```bash
# 上游测试: 4 个 CTest 变体 (cpp98/cpp11/cpp14/cpp17) x 17 个 CASE 全部通过
ctest: 100% tests passed, 0 tests failed out of 4
# 消费者验证 (conan create test_package):
PASS: boolean-lite header-only 库链接和核心 API 验证通过
```

## 交付物

header-only 库无打包产物；交付 conanfile.py + conandata.yml + test_package/ 配方。

## 注意事项

- 该库导出类型名为 `boolean_`（命名空间 nonstd），不是 `boolean`。
- 上游 conanfile.py 仅为占位文件（内容 `# placeholder.`），配方由本仓库维护。

---

**编译结束**: 2026-09-02 22:30
**最终状态**: built