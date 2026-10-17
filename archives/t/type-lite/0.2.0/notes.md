# type-lite 0.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ (15.0.4, aarch64-linux-ohos)
- 状态: published

## 最终状态
- 适配完成：conan-verify 8 门禁 PASS，W3 本地 CI 100% (1/1)，W4 审计 PASS（P0/P1=0）
- 上游测试 121/121 通过，鸿蒙专项测试与消费者 test_package 均通过
- 路径判断：A（【依赖项】），无新增知识草稿
- COMPLETED

## 编译步骤

```bash
# header-only CMake 库，无 configure/make 步骤，使用 Conan create 验证：
conan create archives/t/type-lite/0.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

上游测试（在配方 build() 阶段执行）：
```bash
cmake -DTYPE_LITE_OPT_BUILD_TESTS=ON -DTYPE_LITE_OPT_BUILD_EXAMPLES=OFF ..
cmake --build . -j4
ctest --output-on-failure   # 4/4 (cpp98/11/14/17)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 下 CMake 平台识别 | CMake 不识别 OHOS 为平台 | 复用 E092/E321 模式：generate() 中 settings.os in ("Linux","OHOS") 时设 CMAKE_SYSTEM_NAME=Linux、CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 2 | 上游自带 Conan 1.x 配方 | 本项目基线 Conan 2.29.1 不支持 conans API | 复用 E321（nonstd-lite 系）：重写为 Conan 2 header-library 配方 |

## 源码修改

无（patches=0，纯头文件库零改动）。

## 依赖版本

无第三方依赖（header-only）。

## 验证结果

```bash
# 上游 121 独立用例全过（115 + 6 信息用例），4 个标准目标 ctest 4/4
./type-lite-cpp98.t --pass  # All 113 selected tests passed (exit 0)
# 鸿蒙专项测试（OHOS 工具链 clang 15 编译运行）
#   type-lite HarmonyOS test: ALL PASSED (exit 0)
# 消费者 test_package: 通过 conan create 内 L1 执行
```