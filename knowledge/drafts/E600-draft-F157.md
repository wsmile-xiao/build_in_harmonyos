# E600：Conan CMakeToolchain 中 CMAKE_POLICY_VERSION_MINIMUM 必须走 cache_variables

## 一句话

老项目（`cmake_minimum_required < 3.5`）在 Conan 配方中用 CMake 4.x 构建时，
`tc.variables` 写法**不生效**（policy 检查早于 toolchain 文件执行），必须用
`tc.cache_variables`（`-D` 命令行注入）。

## 现象

`conan create` 失败：

```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
  ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
ERROR: jansson/2.14@ohpcd/stable: Error in build() method, line 58
	cmake.configure()
```

而本地裸 `cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..` 测试通过——错误提示
里的答案在 Conan 集成场景"看得见用不上"，极易卡住。

## 根因

CMake 的 policy 版本兼容检查发生在 `project()` 命令处理 **toolchain 文件之前**：

- `tc.variables["X"]` → 生成 toolchain 文件里的 `set(X VAL)`——执行时 policy 检查**已失败**
- `tc.cache_variables["X"]` → 生成 `cmake -DX=VAL` 命令行参数——配置启动即注入，**早于检查**

与 E103/E187（裸 cmake 命令行解法）同族，但 E187 的 `rec_command`
（`cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5`）在 Conan 配方中不可直接使用——
配方通过 CMakeToolchain 驱动 cmake，不手拼命令行。

## 处方

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["JANSSON_BUILD_SHARED_LIBS"] = self.options.shared
    # CMake 4.x 移除 <3.5 兼容；必须 cache_variables（-D 命令行），
    # tc.variables（toolchain set()）在 project() 检查之后才执行，无效
    tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    tc.generate()
```

## 证据

jansson 2.14（PR #8050，2026-09-04，jansson 上游声明 `cmake_minimum_required(VERSION 2.8)`）：

1. 初版配方用 `tc.variables` → conan-verify **G2 FAIL**（"Compatibility with CMake < 3.5 has been removed"）
2. 仅改为 `tc.cache_variables` → G2 PASS，conan create 全绿：
   - 上游 ctest 213/213（100%）
   - test_package 实际运行通过
3. 本地裸 cmake 加 `-D` 参数可过（与 E187 一致），确认差异只在 Conan 集成层

## 推广范围

所有 `cmake_minimum_required(VERSION 2.x / 3.0-3.4)` 且走 Conan CMakeToolchain
构建的库：woff2、brotli 早期版本、olm 3.2.16、jansson ≤2.14 等。上游 3.15.1
起已自行提升最低版本，属过渡期通用坑。

## 关联

- E103：CMake 4.x 移除 <3.5 兼容（错误面）
- E187：裸 cmake 命令行解法（本条目的 Conan 集成补全）
