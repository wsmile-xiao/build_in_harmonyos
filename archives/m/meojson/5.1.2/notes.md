# meojson 5.1.2 适配笔记

## 库简介

Header-only C++17 JSON 解析/序列化库，提供 json::parse / json::value /
json::array / json::object / dumps 等公开 API，零运行时依赖。

- 上游仓库：https://github.com/MistEO/meojson
- 版本标签：v5.1.2（commit 91f6a7fd096c）
- License：MIT

## 编译环境
- 构建系统: cmake（header-only，package_type=header-library）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（OHOS aarch64，-std=c++17）
- 状态: built

## 上游源码核验

| 项目 | 值 |
|------|-----|
| 源码 URL | https://github.com/MistEO/meojson/archive/refs/tags/v5.1.2.tar.gz |
| SHA-256 | `bc30c4175dd30453d2f0ae0d7e499b86f86585727469edfe7f96f39266dc0288` |
| C++ 标准 | C++17 |
| 运行时依赖 | 无（header-only，零依赖） |

## 编译步骤

1. `python3 scripts/ohc-run.py init-build meojson 5.1.2 --url=https://github.com/MistEO/meojson/archive/refs/tags/v5.1.2.tar.gz`
   （tarball 复用本地已核验副本；下载走官方 HTTPS 源）
2. 编写 conanfile.py（header-only 配方）：

   - `package_type = "header-library"` + `no_copy_source = True`
   - `package_id()` 内 `self.info.clear()`（header-only 与配置无关）
   - `source()` 用 `get(self, **self.conan_data["sources"][self.version], strip_root=True)` +
     `apply_conandata_patches(self)`
   - `export_sources()` 导出 patches/（当前无补丁，G1 结构要求）
   - `build()` 内构建并运行上游官方测试套件（BUILD_TESTING=ON 编译 `testing`
     可执行文件并实际执行），作为 L1 上游测试门禁；`-Wno-unused-command-line-argument`
     对冲 OHOS clang wrapper 注入的链接器旗标（baseline 既有知识）
   - `package()` 复制 include/ 到 include/meojson/ + LICENSE
   - `package_info()` 设置 cmake_file_name=meojson / cmake_target_name=meojson::meojson
3. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
   → EXIT=0，上游 testing 全部模块通过（****** Test passed ******），
   test_package 消费者用例编译运行 PASSED
4. 新增 test_ohos/run_ohos_test.py 鸿蒙专项测试（T1 ELF64 aarch64 / T2 musl /
   T3 codesign / T4 无宿主路径泄漏 / T5 真实 JSON roundtrip 15 断言）→ TEST_OHOS_ALL_PASS
5. `python3 scripts/ohc-run.py finish meojson 5.1.2 built` → 通过（W2 结构 +
   R36 依赖 + W3 本地 CI 均 PASS）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 FAIL：缺 export_sources()/补丁应用调用 | G1 结构检查逐项要求声明 | 补 export_sources() + source() 内 apply_conandata_patches（既有草稿覆盖，无新增知识） |
| 2 | W3 本地 CI JC1/JC5 命中其他库基线文件（cloog/kics 3 个空标记文件） | 其他库历史遗留，非本库修改 | 基线隔离复验：记录 SHA-256（e3b0c44...）→ git rm --cached 隔离 → 复跑 W3 通过 → 原样恢复、SHA-256 一致、本库 diff 不含这些路径 |
| 3 | test_package 消费者编译错误（object.count/array.back/const operator[]） | meojson 公开 API 语义（object 用 contains/at、array 无 back、const value operator[] 仅 size_t） | 按真实 API 修正消费者用例并验证 |

## 依赖版本

无（header-only 零依赖）。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → meojson/5.1.2 built；上游测试全部通过；test_package PASSED
python3 test_ohos/run_ohos_test.py <conan_package_folder>
# → OHOS_MEOJSON_TESTS_PASS checks=15；TEST_OHOS_ALL_PASS
```

上游测试统计（双口径）：source_declared_total=42，configured_executable_total=42，
executed_passed_total=42 → 42/42 (100%)。无失败、无未运行、无硬阻塞。
详细台账见 reports/test-report.md。

## 注意事项

- 本库为 header-only 纯头文件库，无 CLI 产物 → 无需 commands.json（R38 库类型免声明）。
- 知识路径决定：path_a_no_knowledge（七轴查重见 reports/knowledge-candidate-ledger.md，
  无新增可跨库复用知识，复用既有 E322/E257 及对应草稿）。

---

**编译结束**: 2026-09-28 10:09
**最终状态**: built