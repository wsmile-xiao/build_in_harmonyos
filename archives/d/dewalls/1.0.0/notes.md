# dewalls 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 QBS → 适配为 CMake 改写）
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

```bash
# 上游仅提供 dewalls.qbs（Qt Build Suite），CI 无 QBS 工具链。
# 适配方案：新增 CMakeLists.txt（patches/0001-CMakeLists.txt.patch），
# 声明与 dewalls.qbs 等价的两个目标：
#   libdewalls    — 动态库（src/*.cpp，依赖 Qt5::Core，AUTOMOC）
#   dewalls-test  — Catch v1.2.1 测试程序（test/*.cpp + test/dewalls-test.qrc）

export QT_PREFIX=<qt/5.15.19 conan package_folder>
cmake -S . -B build -DCMAKE_PREFIX_PATH=$QT_PREFIX \
      -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 1
ctest --test-dir build --output-on-failure
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游构建系统是 QBS（dewalls.qbs），CI 无 QBS 工具链 | 上游 2015 年项目仅用 Qt Creator + QBS 构建 | 改写为 CMakeLists.txt 补丁，声明等价目标（库+测试），与 posixsignalmanager/qxlsx 等 Qt5 库先例一致 |
| 2 | moc 执行报 `Error relocating: __cxa_pure_virtual symbol not found` | qt/5.15.19 包内 moc 依赖 libc++_shared.so，运行 LD_LIBRARY_PATH 未包含 OHOS SDK llvm lib 目录 | 编译/测试时 LD_LIBRARY_PATH 追加 `$OHOS_SDK/native/llvm/lib/aarch64-linux-ohos` |
| 3 | dewalls-test 运行报 `Error relocating ... symbol not found` | 运行 LD_LIBRARY_PATH 未包含 build 目录（libdewalls.so） | 运行测试时将 build 目录加入 LD_LIBRARY_PATH |
| 4 | CMake 不识别 OHOS（System is unknown to cmake） | CMake < 平台配置 | conan 的 CMakeToolchain 自动处理（profile 注释说明已适配）；offline 探索编译不影响 |
| 5 | main.cpp 引用不存在的头文件（unit.h/unittype.h/wallsvisitor.h） | 上游孤儿文件，不在 dewalls.qbs 构建集内 | 不参与构建，CMakeLists.txt 只收录 src/*.cpp 与 test/*.cpp |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| CMakeLists.txt（新增，patch 生成） | QBS→CMake 改写，构建 libdewalls + dewalls-test |

> 上游源码文件本身零改动；唯一补丁是新增 CMakeLists.txt。

## 依赖版本

- qt/5.15.19（Qt5 Core；制品仓发布，含 OHOS armv8 binary）

## 上游测试清点（R51 三步法第 1 步）

| 测试目录/文件 | 测试框架 | 注册用例数 | 说明 |
|---|---|---|---|
| test/dewallstests.cpp | Catch v1.2.1 | 0（main+异常翻译） | CATCH_CONFIG_MAIN 入口 |
| test/generaltests.cpp | Catch | 2 TEST_CASE | 单位/向量/解析通用测试 |
| test/azimuthparsingtests.cpp | Catch | 1 TEST_CASE | 方位角解析 |
| test/inclinationparsingtests.cpp | Catch | 1 TEST_CASE | 倾角解析 |
| test/lengthparsingtests.cpp | Catch | 1 TEST_CASE | 长度解析 |
| test/applyheightcorrectionstest.cpp | Catch | 1 TEST_CASE | 高程修正 |
| test/wallsprojectparsertests.cpp | Catch | 2 TEST_CASE | .wpj 工程解析 |
| test/tostrings.cpp | Catch | 0（辅助） | toString 辅助 |
| **合计** | | **8 TEST_CASE** | 2729 断言 |

> 上游测试程序 dewalls-test 由 dewalls.qbs 的 CppApplication 目标定义；适配后
> 在 conanfile.py build() 内以 ctest 运行（见验证结果）。

## 验证结果

```bash
# 探索编译（本机 OHOS 环境，qt binary 从制品仓 conan install 注入）
cmake --build . --parallel 1        # ✅ 构建成功（libdewalls.so + dewalls-test）
./dewalls-test                      # ✅ All tests passed (2729 assertions in 8 test cases)
test_package/test_dewalls           # ✅ WallsSurveyParser 解析 .srv 数据行成功
```

| 项目 | 结果 |
|------|------|
| 上游测试用例 | 8 个 TEST_CASE（Catch v1.2.1），2729 断言全过 |
| test_package 自研断言 | 4 项（默认单位、解析信号、向量长度） |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方（cmake，requires qt/5.15.19） |
| conandata.yml | 源码 URL + sha256 + 补丁声明 |
| patches/0001-CMakeLists.txt.patch | QBS→CMake 改写补丁 |
| test_package/ | 消费者验证（cpp_info 链接 + WallsSurveyParser API 实测） |

## 注意事项

- Qt5 conan 包（qt/5.15.19）`cmake_find_mode=none`：CMakeDeps 不会生成 qt 目标文件，下游须在 generate() 将 qt package_folder 注入 `CMAKE_PREFIX_PATH` 后自行 `find_package(Qt5)`。
- AUTOMOC/AUTORCC 需要在构建环境能找到 libc++_shared.so（OHOS SDK llvm lib 目录入 LD_LIBRARY_PATH）。CI 的 ohos-aarch64 profile [buildenv] 已含该路径。
- 本包为纯库（libdewalls），产出动态库，无 CLI 可执行文件安装 → 无需 commands.json（R38 仅 tool 类型需要）。
---

**编译结束**: 2026-09-15 04:39
**最终状态**: published
