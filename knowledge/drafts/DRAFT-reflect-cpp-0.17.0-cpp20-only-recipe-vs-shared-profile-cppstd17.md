# DRAFT-reflect-cpp-0.17.0-cpp20-only-recipe-vs-shared-profile-cppstd17：C++20-only 库配方与共享 profile cppstd=17 冲突，check_min_cppstd 硬拒绝导致 conan create 失败

> Contributor: tianyi_wang | Status: Draft | Updated: 2026-09-03
> Source: reflect-cpp 0.17.0 HarmonyOS PC 适配（archives/r/reflect-cpp/0.17.0/conanfile.py）
> 对应：knowledge/drafts/DRAFT-reflect-cpp-0.17.0-cpp20-only-recipe-vs-shared-profile-cppstd17.kv

## 现象

C++20-only 的 CMake 库（如 reflect-cpp，`project(... LANGUAGES CXX)` +
`set(CMAKE_CXX_STANDARD 20)`）在共享 `ohos-aarch64` profile
（`compiler.cppstd=17`）下做 `conan create` 时，配方若写了
`check_min_cppstd(self, 20)`，直接失败：

```text
ERROR: ...: Invalid 'compiler.cppstd' value: '17' is less than 20 required
ConanInvalidConfiguration: reflect-cpp/0.17.0: ...
```

更隐蔽的变体：build 上下文 profile 可能声明 `cppstd=gnu98`（conan profile
detect 默认值），`int(self.settings.get_safe("compiler.cppstd"))` 这类数值解析
直接抛 `ValueError`，validate() 异常同样中断 conan create。

即使库配方的 `generate()` 已通过 `CMakeToolchain.variables["CMAKE_CXX_STANDARD"]=20`
强制了 C++20（库本体因此能过），**test_package 用自己的 CMakeToolchain**，
仍继承 profile 的 `cppstd=17`，测试编译会以 C++17 报
`no template named 'remove_cvref_t'` / `consteval` 缺失等错误。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph（540 条 E*.kv）+ knowledge/drafts（163 对，快照
main@2f60a107，稀疏只读）。
检索词：check_min_cppstd / cppstd / CMAKE_CXX_STANDARD / compiler.cppstd /
C++20 / profile。
最接近者为正式条目 E096（abseil：CMake C++ 标准自动检测失败，
`Performing Test.*CXX17.*Failed` / `System is unknown to cmake`，解法
`-DCMAKE_CXX_STANDARD=17`）——**非等价命中**，逐字段比较：
- 错误签名不同：E096 是 CMake 特性探测失败/标准不足报错；本条是
  conan `validate()` 层 `ConanInvalidConfiguration`（profile cppstd < 配方要求）
  及 `int('gnu98')` 数值解析崩溃。
- 触发条件不同：E096 触发于 CMake configure 期标准探测；本条触发于
  conan create 的 validate() 与 test_package 编译期。
- 根因不同：E096 归因 CMake 对 OHOS 的编译器探测不完整；本条归因
  共享 profile 的 cppstd=17 与 C++20-only 库的配方级冲突，且 build/host
  双 profile、test_package 独立 toolchain 的三层 cppstd 传播问题。
- 解法不同：E096 用命令行 `-DCMAKE_CXX_STANDARD`；本条是配方 validate()
  策略（不按 profile cppstd 拒绝）+ generate() 注入 + test_package CMakeLists
  显式 `set(CMAKE_CXX_STANDARD 20)`。
其余条目（E293 C++17 动态异常规范 / E538 依赖图选项冲突）主题无关。无覆盖。

## 知识库沉淀价值

- 可复用问题类别：C++20（及以上）only 库接入统一 cppstd=17 的 OHOS 共享
  profile 时的配方级 cppstd 冲突与三层传播（host profile → 配方 generate()
  → test_package 独立 toolchain）。
- 适用对象：一切要求 C++20/23 的 CMake 库配方（现代 C++ 项目占比持续上升），
  以及任何复用共享 profile 的 conan 配方。
- 决策价值：一眼识别 `ConanInvalidConfiguration ... cppstd` 与 test_package
  的 `remove_cvref_t/consteval` 缺失错误；知道正确解法是"配方不拒绝 profile
  cppstd + 显式注入标准 + test_package 锁定标准"，而不是改共享 profile
  （会波及全部在途库）或把 cppstd 降到 17（改变 ABI/语义）。

## 方案

1. 配方 `validate()`：不要按 `self.settings.get_safe("compiler.cppstd")`
   做数值比较后拒绝（build 上下文可能是 `gnuXX`，`int()` 直接崩）；
   C++20-only 库直接不在 validate() 中拒绝 cppstd。
2. 配方 `generate()`：`tc.variables["CMAKE_CXX_STANDARD"] = 20`
   （+ 项目支持时 `CMAKE_CXX_STANDARD_REQUIRED=ON`），由配方锁定标准，
   工具链不支持时构建会真实失败（可接受，CI 可见）。
3. test_package：其 CMakeLists.txt 顶部显式
   `set(CMAKE_CXX_STANDARD 20)` + `set(CMAKE_CXX_STANDARD_REQUIRED ON)`，
   不依赖 conan toolchain 从 profile 传播（test_package 用独立 toolchain，
   会继承 profile cppstd=17）。
4. 不改共享 profile（ohos-aarch64 cppstd=17 是 217 个在途库的兼容基线）。

## 验证证据

- 修复前（check_min_cppstd 硬拒绝）：conan create 在 validate() 即失败
  （`ConanInvalidConfiguration`，reports/conan-create.log 多次复现）。
- 修复前变体（int('gnu98') 解析）：validate() 抛 ValueError 中断。
- 修复前 test_package：`no template named 'remove_cvref_t'`（C++17 编译）。
- 修复后：`conan create`（ohos-aarch64）exit 0；test_package 28 断言全过
  （13 + 15）；上游 ctest 193/193；W3 本地 CI exit_code=0。

## 禁止做法

- 修改共享 ohos-aarch64 profile 的 cppstd：波及全部在途库的 package ID
  与兼容性基线，属越界共享框架改动。
- 把 cppstd 降到 17 来"满足" profile：C++20-only 库无法编译，即使能编译
  也改变 ABI/语义并掩盖真实标准依赖。
- 在 validate() 里对 `compiler.cppstd` 做 `int()` 数值比较：build 上下文
  profile 可能是 `gnu98` 等非纯数字值，直接 ValueError。
