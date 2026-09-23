## 三方库信息

- **三方库名称**：platform_folders
- **上游版本**：4.2.0
- **上游仓库地址**：https://github.com/sago007/PlatformFolders
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 16 | 来源：上游 test/ 目录 16 个独立可执行测试程序（test/CMakeLists.txt `_def_test` 注册为 ctest 用例，含 integration.cpp 全量调用 20+ getter 与 internalTest.cpp 纯逻辑分词器） |
| 集成测试 | 0 | 无独立集成测试 |
| 其他测试 | 0 | |
| **合计** | **16** | 16 个 ctest 用例，全量编译并在 conanfile.py build() 内 `cmake.test()` 实跑 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 16 | 不变 | 上游 ctest 全量集成，16/16 通过 |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_platform_folders.cpp` 链接打包的 libplatform_folders.a，真实调用 XDG 目录 API 与 internal 分词器（20 checks） |
| **合计** | **17** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（16 个 ctest 全量集成于 build()）

## 验证结果

- 编译状态：通过（`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同`，L0/L1）
- 上游测试用例通过率：16/16（100%），`cmake.test()` 在 conan create 内实跑
- 新增测试用例通过率：1/1（100%），`test_package` 编译链接运行通过，输出 `platform_folders 4.2.0 consumer: ALL OK (20 checks)`

## 补充说明

- 本 PR 只新增 `archives/p/platform_folders/4.2.0/` 下的配方、元数据、notes 与 test_package，不修改其他目录。
- platform_folders 为特殊目录查询 C++11 库：单实现文件 `sago/platform_folders.cpp` + 单头 `sago/platform_folders.h`，零第三方依赖，CMake 构建（`PLATFORMFOLDERS_BUILD_TESTING` 开关注册 16 个 ctest）。
- OHOS 属非 Windows/非 Apple 平台，走 Linux/XDG 实现分支（HOME + XDG_* 环境变量与 `$XDG_CONFIG_HOME/user-dirs.dirs`），测试仅断言返回目录串非空，不要求目录真实存在。
- 上游 `cmake_minimum_required(VERSION 3.1)`，generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4。
- 静态库包（library）：`libplatform_folders.a` 装到 `lib/`，头文件到 `include/sago/`，并随包安装 `platform_foldersConfig.cmake`（导出 target `sago::platform_folders`）；`cpp_info.libs=["platform_folders"]`。
- 源码归档取自官方 GitHub tag 4.2.0，sha256 `31bb0f64...` 与 codeload/github.com 两路下载一致。
