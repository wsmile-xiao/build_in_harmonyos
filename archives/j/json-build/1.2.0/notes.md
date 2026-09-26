# json-build 1.2.0 适配笔记

## 编译环境
- 构建系统: headeronly（单头文件 C89 库，无编译阶段；上游测试为 test/Makefile）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，ohos-aarch64 profile）
- 状态: built

## 编译步骤

json-build 是零动态分配、零依赖的 ANSI C（C89）JSON 序列化头文件库
（json-build.h 单头文件）。无需 configure/make 库阶段；配方为 header-only
变体（conanfile-headeronly 模式，参照本仓 args-parser 等成熟写法）：

1. `ohc-run.py init-build json-build 1.2.0 --url=...v1.2.0.tar.gz`
   （官方 GitHub archive，SHA-256 b20132f0...44a25f，与 codeload 官方端点一致）
2. 修正 manifest.yaml 构建系统为 headeronly；`ohc-run.py conan-init` 生成配方
3. 重写 conanfile.py 为 header-only 形态（cmake_layout src_folder="."，
   copy *.h 到包根，includedirs=["."]，package_id clear）
4. `ohc-run.py conan-verify` → G1-G4 全 PASS（ohos-aarch64 clean build）
5. 上游测试：`make -C test CC=clang` 编译 test/test_auto/fuzz，
   `./test`（15 用例）、`./test_auto`（6 用例）全部通过
6. 新增 test_ohos 鸿蒙专项验证（run_ohos_test.py，T1-T5 全 PASS）
7. test_package 消费者测试（test.c 仅经 json-build.h 公开 API 构造 JSON
   并校验输出 `{"foo":[1,"hi",false,null]}`）在 conan create 内 1/1 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build "嵌套源码提升"误将 test/ 提升为源码根 | 检测逻辑把单目录 tar 内的 test/ 子目录当作唯一源码 | 重新解包保持真实结构（json-build.h 在根，test/ 为子目录），重新生成基线指纹 |
| 2 | G2 conan create 报 "No files in this package!" | header-only 模板 basic_layout 下 source_folder 指向不当，package() 拷贝为空 | 按本仓 args-parser 成熟模式改为 cmake_layout(src_folder=".") + copy 到 package_folder + includedirs=["."] |
| 3 | conan create 时 E225 CMakeUserPresets.json 落盘 test_package 源码目录 | CMakeToolchain 默认写 user_presets | 清理构建残留，保持配方无污染；CI 干净环境不受影响 |
| 4 | test_ohos 运行期工具探测失败 | HMDFS 上 os.access(X_OK) 恒 False（E046/R49）；env CC=clang 裸名 posix_spawn 失败 | _which 优先绝对路径候选（/data/service/hnp/bin/*），isfile 判断不判 X_OK |

## 源码修改

无补丁（patches/ 为空）。配方与测试为新增交付物。

## 依赖版本

无运行时依赖（header-only，C89，零动态分配）。构建仅需 clang + make + cmake。

## 验证结果

```bash
# 上游测试
make -C test CC=clang
./test          # Total: 15 tests, 7802 assertions, Pass: 15, fail: 0
./test_auto     # Total: 6 tests, 75 assertions, Pass: 6, fail: 0
# OHOS 专项
python3 test_ohos/run_ohos_test.py <package_folder>   # T1-T5 ALL PASS
# 消费者（test_package）
conan create ... test_package  # 1/1 tests passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方 GitHub tag 源码 + SHA-256 |
| test_package/ | 真实消费者测试（json-build.h 公开 API） |
| test_ohos/ | HarmonyOS PC 专项验证（T1-T5） |
| reports/upstream-test-report.md | 上游测试双口径台账 |

## 注意事项

- 本库为 header-only，无 commands.json（无 CLI 产物，R38 不适用）
- 上游测试 greatest 框架：test.c 15 个 TEST、test_auto.c 6 个 TEST 为独立用户用例；
  fuzz.c 为 afl 风格模糊器入口（无断言，不计入通过率分母）
---

**编译结束**: 2026-09-26 01:02
**最终状态**: built
