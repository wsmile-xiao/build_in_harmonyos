# nlohmann_json 3.1.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态库供链接与 dlopen（具体库名由 collect_libs 自动收集）。

## 关键适配
- 无特殊适配：上游源码直接可用鸿蒙 PC 原生工具链构建。

## 为什么要有 3.1.1（而不是只留 3.12.0）

**qiskit-aer 在两条路径上都钉 3.1.1**：`cmake/conan_utils.cmake` 的
`REQUIREMENTS nlohmann_json/3.1.1`、`cmake/dependency_utils.cmake` 的
`find_package(nlohmann_json 3.1.1 EXACT)`。

用 3.12.0 编出来的 aer **能构建、能 import、能跑 Bell 线路并给出正确分布**，
但自带测试套件里 **196 个**噪声模型用例全报
`ValueError: Invalid noise_params JSON: not an object.` ——
aer 把自定义的 pybind11 caster 塞在 `namespace std` 里，而 nlohmann_json 在
3.2/3.9/3.11 改过 ADL 与序列化器的解析规则，跨 11 个小版本后那个 caster 不再被找到。
上游 CMake 当场就警告过 `WARNING: This version may not work!!!`。

改用 3.1.1 后这 196 条全部消失。**两个版本必须并存**：新项目用 3.12.0，
钉旧版的消费方用 3.1.1。

## 关键适配
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`：3.1.1 声明的是
  `cmake_minimum_required(VERSION 3.0.0)`，而 **CMake 4.x 起拒绝 < 3.5 的声明**。
  2018 年前后的项目都会撞这一条。
- `--header-only`：package_id 恒定（`da39a3ee…` 空哈希）。
- 布局差异：3.1.1 的 CMake config 装在 **`lib/cmake/`**，3.12 装在 `share/cmake/`。

## 状态
built —— 真机 `conan create -pr ohos-native --update` rc=0（2026-08-11）。

### 真机证据
test_package **22 条真实断言全通过**（与 3.12.0 同一套，按 3.1.1 的 API 收敛：
`contains()` 是 3.6.0 才有的，这里改用 `count()`）。

下游实证：aer 用本包重编后，测试套件从 `errors=210` 降到 `errors=14`，
196 个 JSON 相关错误全部消失。
