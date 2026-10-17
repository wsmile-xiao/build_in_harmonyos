# rttr 0.9.6 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMake，`loadFolder` + `unit_tests.cmake` 显式清单）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，OHOS SDK）
- 状态: built

## 上游软件
- RTTR (Run Time Type Reflection)，https://www.rttr.org，GitHub rttrorg/rttr 标签 v0.9.6
- 纯 C++11 反射库，无第三方依赖（3rd_party 内置 Catch 1.12/Nonius/RapidJSON 仅测试与基准使用；Boost 仅 BUILD_BENCHMARKS 需要）
- 语言预检 R47：cpp（lang_checked）

## 编译步骤

原生探索（同一源码树，先于配方）：

```bash
# 共享库 + 上游单元测试
cmake -S $SRC -B $NB -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DBUILD_EXAMPLES=OFF -DBUILD_DOCUMENTATION=OFF -DBUILD_INSTALLER=ON -DBUILD_PACKAGE=OFF \
  -DBUILD_BENCHMARKS=OFF -DUSE_PCH=OFF -DBUILD_UNIT_TESTS=ON
ninja -C $NB -j2
LD_LIBRARY_PATH=$NB/lib $NB/bin/unit_tests
# → All tests passed (4891 assertions in 531 test cases)

# 静态库（conan 默认 shared=False 形态的等价验证）
cmake -S $SRC -B $SB ... -DBUILD_RTTR_DYNAMIC=OFF -DBUILD_STATIC=ON -DBUILD_UNIT_TESTS=OFF
ninja -C $SB -j2   # → lib/librttr_core.a 安装干净
```

W3 正式验证经 `finish`（私有 CONAN_HOME，见 reports/）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `System is unknown to cmake` + `Could not set install folders for this platform!` | conan 在 os=OHOS 下把 CMAKE_SYSTEM_NAME 映射为 HarmonyOS，cmake 无该平台模块，UNIX 变量未定义；上游 config.cmake `if(UNIX)` 直落 fatal（设备最小工程实证 `UNIX=` 为空） | 配方 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`（仓库既有 CMake 配方同口径） |
| 2 | CMake 4.1 拒绝配置 | 上游 `cmake_minimum_required(VERSION 3.0)` 低于 CMake 4 下限 | 工具链变量 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（不改源码） |
| 3 | clang 15 `-Werror` 下 9 处 `-Wimplicit-const-int-float-conversion` | number_conversion.h 浮点→整型边界比较中 `std::numeric_limits<T>::max()` 隐式转浮点丢精度（int/long/unsigned 与 float/double 组合） | 显式 `static_cast<F>`（补丁 0003），运行时语义与原隐式转换逐位一致 |
| 4 | `-Wordered-compare-function-pointers`（compare_less_impl.h:46、misc_type_traits.h:621 实例化） | 对函数指针做 `<` 有序比较（合法 C++，仅次序未指定）；trait 的未求值探针同样命中 | clang 守卫的局部 pragma 抑制（补丁 0002/0004），比较语义不变 |
| 5 | `type::get_sizeof<int*>()==4` 单测失败（8!=4） | `RTTR_ARCH_TYPE` 64 位探测列表缺 `__aarch64__`，aarch64 全按 32 位走 `#else` 分支 | 探测列表补 `__aarch64__/_M_ARM64`（补丁 0001），修正后 531 用例全过 |
| 6 | 单测约 20 个 TU 编译失败：`reference to 'variant' is ambiguous` | 上游自选 `-std=c++17`（clang 分支），C++17 头透传引入 `std::variant`，与测试文件 `using namespace rttr; using namespace std;` 下的裸 `variant` 二义 | 各失败文件将裸 `variant` 机械限定为 `rttr::variant`（补丁 0005/0007-0014/0017-0024，共 17 文件，不动断言） |
| 7 | `-Wdelete-non-abstract-non-virtual-dtor` | 测试夹具 `CLASS` 宏类与 `instance_base` 有虚函数（RTTR_ENABLE）但无虚析构，经基类智能指针删除 | 补 `virtual ~...() = default`，且必须放在 `RTTR_ENABLE()` 之前（宏以 `private:` 结尾，放后面会连带删除派生类构造/析构——首轮即踩，补丁 0006/0015） |
| 8 | `-Wdeprecated-builtins`（variant_ctor_test） | clang 定义 `__GNUG__` 且 `__GNUC__=4.2.1`，上游 `#if __GNUG__ && __GNUC__ < 5` 误入废弃内建 `__has_trivial_copy` 分支 | 分支条件补 `!defined(__clang__)`（补丁 0021），clang 走上游本意的 `std::is_trivially_copyable` 断言 |
| 9 | `-Wself-assign-overloaded`（variant_assign_test） | 自赋值用例 `a = a` 为测试意图（验证 operator= 自赋值安全），clang 判错 | 经引用别名 `a = self_ref` 完成同一对象赋值（补丁 0016），断言语义不变 |
| 10 | `cmake --install` 静默零安装 | 安装规则门在 `BUILD_INSTALLER` 之后，OFF 时仅打印 "Install configuration" | 配方保持 `BUILD_INSTALLER=ON`（`BUILD_PACKAGE` 关） |

## 源码修改

补丁 24 个（refresh-patch --auto 生成，详见 conandata.yml patches 段与 manifest.yaml patches_applied）：
- 库头文件 4 个（0001-0004）：编译所必需的平台/编译器移植修复，进 conan create 路径。
- 单元测试源 20 个（0005-0024）：仅上游测试目标（BUILD_UNIT_TESTS=ON，conan create 不编），为在设备实跑上游套件而修，PR 正文"上游测试用例修改说明"逐条申报。

## 上游测试清点与实跑（R51）

- 单位：Catch TEST_CASE（case 级）。
- N = 546（`grep -rc "^TEST_CASE" src/unit_tests --include=*.cpp` 合计，65 个 .cpp）。
- N′ = 531（`unit_tests --list-test-names-only | wc -l`；`All tests passed (4891 assertions in 531 test cases)`）。
- NOT_RUN = 15：全部位于 variant_array_view/variant_array_view_test.cpp——上游 `unit_tests.cmake` 显式清单未纳入该文件，且所测 `variant_array_view` API 在 0.9.6 不存在（源内仅 `variant_array`；单文件编译实证 `unknown type name 'variant_array_view'`）。属上游清单排除，非本次适配裁剪。
- 上游测试用例修改：见上表 #6-#9（24 个补丁中的 20 个测试源补丁）；修改均为编译必需，无断言值改动。

## 依赖版本

无（零依赖包，W0 版本占用检查确认制品仓无 rttr/0.9.6 同版配方）。

## 验证结果

```bash
# 原生探索（共享库）
LD_LIBRARY_PATH=$NB/lib $NB/bin/unit_tests
# → All tests passed (4891 assertions in 531 test cases)
# 静态库形态
ninja -C $SB   # → lib/librttr_core.a，安装树干净（include/ lib/ share/rttr/cmake/）
```

W3（conan create + test_package 消费者）与 L2/L4/L5 证据见 reports/。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/librttr_core.so.0.9.6 | ~1.0 MB | shared 形态（conan shared=True） |
| lib/librttr_core.a | ~1.6 MB | static 形态（conan 默认） |
| include/rttr/** | — | 公共头 + detail 头（上游布局原样） |
| share/rttr/cmake/rttr-config.cmake | — | 上游导出配置（包内已移除，CMakeDeps 重新生成） |

## 注意事项

- 消费者链接 shared 形态需 `RTTR_DLL` 定义（包的 cpp_info.defines 已声明；static 无需定义，RTTR_API 为空）。
- 上游导出配置为小写 `rttr-config.cmake`，与 CMakeDeps 生成的 `RTTRConfig.cmake` 可能互相遮蔽，包内已移除上游配置目录（recipe package() 内说明）。
- RTTR 上游（master）至 2026-09 未修 #3/#4/#5（对照过 master 的 compare_less_impl.h 仍为裸 `<`）。
