# cpp-hocon 0.3.0 适配笔记

**日期**: 2026-09-09
**状态**: ✅ 编译 + 上游测试全量通过
**任务**: 平台任务 #6867（开源鸿蒙PC专项积分赛，认领人 calbee21）

## 软件概况

cpp-hocon 是 Puppet Labs 的 HOCON 配置文件格式 C++ 解析库（TypesafeConfig
移植版），facter 等工具的核心配置依赖。上游：https://github.com/puppetlabs/cpp-hocon

## 依赖分析（W0 核验）

| 依赖 | 上游声明 | 实际使用 | 制品仓状态 | 处置 |
|------|---------|---------|-----------|------|
| libuv | 任务背景提及 | **零使用**（源码 grep 无命中） | libuv/1.52.1 在仓 | 无需引入——libuv 是 leatherman 体系依赖，非 cpp-hocon 的 |
| leatherman | CMakeLists REQUIRED | 3 个 API（locale::_/format/translate、util::environment::each、util::scope_exit） | **不在仓** | patch 0001 提供 170 行 header shim（boost::format 实现） |
| Boost >= 1.54 | CMakeLists REQUIRED | filesystem/program_options/thread（tss）/regex（header）+ variant/optional/algorithm/format/nowide（header） | boost1.84/1.84.0 + boost1.84-thread/1.84.0 在仓 | 直接引用 |
| Catch（测试） | leatherman catch 组件 | lib/tests 测试框架（Catch v1） | catch/1.12.2 在仓 | 直接引用 |

## 适配方案（两个补丁）

### 0001 leatherman compat shim
- `lib/compat/leatherman/locale/locale.hpp`：`_()`/`format()` 用 boost::format
  实现 leatherman 的 `{N}` 位置占位符语义（{1}→%1%，裸 % 转义），
  `translate()` 返回原文（无 gettext 目录）
- `lib/compat/leatherman/util/environment.hpp`：`each()` 遍历 POSIX environ
- `lib/compat/leatherman/util/scope_exit.hpp`：RAII 实现
- `lib/export.h.in`：静态库下 LIBCPP_HOCON_EXPORT 为空（上游由 leatherman
  symbol_exports 宏生成）

### 0002 CMake 构建体系移植
- 重写顶层/lib/lib-tests 三级 CMakeLists：去除 leatherman 宏
  （include(options)/cflags/leatherman、gettext、cpplint/cppcheck）
- 保留上游源文件列表（59 个 .cc）与 unit_tests 测试目标（Catch v1）
- Boost 查找用 CONFIG 模式（CMake 4.x 移除了 FindBoost，CMP0167）
- 测试目标显式补 inc/compat include（OBJECT 库 usage requirements 不随
  $<TARGET_OBJECTS:> 传播）

## 关键坑与解法

1. **boost1.84 与 boost1.84-thread 的 cmake_file_name 冲突**：两个包都注册
   "Boost"，CMakeDeps 同一 generator 目录生成时后者覆盖前者，主包组件
   （Boost::filesystem 等）丢失。解法：配方 generate() 里
   `deps.set_property("boost1.84-thread", "cmake_file_name", "hocon-boost-thread")`
   改名 thread 包，主包独占 Boost 名。
2. **OHOS toolchain 的 find_package 限制**：CMAKE_FIND_ROOT_PATH_MODE_PACKAGE
   ONLY 导致 CMAKE_PREFIX_PATH 里的 conan deps 目录被忽略。conan 的
   CMakeToolchain 自动把 deps 目录加进 CMAKE_FIND_ROOT_PATH，手动 cmake 验证
   时需显式传。
3. **测试二进制运行缺 libc++_shared.so**：设备运行需
   LD_LIBRARY_PATH 含 SDK aarch64-linux-ohos/lib（conanrun env 自动处理，
   手动跑时显式设置）。

## 上游测试结果（rule4 口径）

上游构建系统（CMake）注册的测试目标：**1 个 ctest 目标（unit_tests）**，
内含 **114 个 TEST_CASE**（grep -c TEST_CASE lib/tests/*.cc 合计）。

设备实测（2026-09-09，libcpp-hocon_test 直接运行）：

```
test cases:  114 | 105 passed |  9 failed as expected
assertions: 3229 | 3217 passed | 12 failed as expected
```

- **0 个意外失败**，套件整体 PASS（Catch v1 的 "failed as expected" 是
  预期异常断言语义，不是失败）
- 9 个 failed-as-expected 的 TEST_CASE 全部属于上游标注 pending 的
  '+=' 拼接功能（"Concatenation pending '+=' implementation" 等章节），
  上游在该版本同样未实现

## 验证记录

| 步骤 | 结果 |
|------|------|
| 源码下载（GitHub tag tarball） | ✅ sha256 dab02354...4c3dd |
| 补丁应用（patch -p1） | ✅ 两个补丁干净应用 |
| cmake configure（OHOS arm64-v8a） | ✅ Boost/Threads/Catch 全部找到 |
| 编译（clang 15.0.4, -j4） | ✅ 59 源文件 + 测试全过（仅警告） |
| 上游测试（设备运行） | ✅ 114 cases / 3229 assertions 零意外失败 |
| conan create | ✅（见 .ci-result.json） |
| test_package | ✅ 消费者 API 断言全过 |
