# DRAFT-sophus-1.22.10-fmt-basic-logging-macro：header-only 库 basic logging 宏的 Conan 消费者传播

## 现象

在 OHOS 环境为 header-only 库 sophus 1.22.10 运行 `conan-verify`（G2 门禁）时，
主包 `conan create` 构建成功并打包，但 `test_package` 消费者编译失败：

```text
/storage/.../p/include/sophus/common.hpp:36:10: fatal error: 'fmt/format.h' file not found
#include <fmt/format.h>
```

主包（`sophus` target）自身编译却不受影响。

## 根因

上游 Sophus 的 CMakeLists 在配置期找不到 fmt target 时自动开启 basic logging，并把
`SOPHUS_USE_BASIC_LOGGING=1` 作为 `INTERFACE_COMPILE_DEFINITIONS` 写入其导出的
`SophusTargets.cmake`（第 62 行）。`common.hpp` 通过该宏选择不走
`#include <fmt/format.h>` 的分支。

但 Conan 消费者的 `CMakeDeps` 生成 target 只从配方 `package_info()` 读取编译定义，
并不会继承上游 CMake 导出的 INTERFACE 编译定义。因此消费者（test_package / 下游）
编译时宏未定义，`common.hpp` 回落进 fmt 头文件分支而找不到 fmt/format.h。

## 可复用修复模式

带可选 fmt（或类似可选依赖）且无 fmt 时降级到自带 basic logging 宏的 C/C++
header-only 库，Conan 配方必须在 `package_info()` 中显式传播降级宏：

```python
def package_info(self):
    self.cpp_info.libs = []
    self.cpp_info.defines = ["SOPHUS_USE_BASIC_LOGGING=1"]
    ...
```

## 验证方法

```bash
conan create archives/s/sophus/1.22.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

G2 通过、`test_package` 中实际运行消费者二进制（SO3/SE3 exp-log roundtrip），
且 W3 的 L1e 破坏性负测（把 include/ 移走）确认测试真实依赖被测包。

## 适用边界与反例

- 仅适用于"上游无 fmt 时自动降级 basic logging 宏"的 header-only 库；若上游始终强制
  fmt 头文件（无降级分支），本模式不适用，需另配 fmt 依赖。
- 若生态已发布 fmt 且上游希望走完整 fmt 格式化路径，可 `requires("fmt/<版本>")` 走
  fmt::fmt 分支（本任务环境 fmt 未发布，不可用）。
- 禁止用空壳 test_package、删除 fmt include 或关闭上游测试来掩盖消费者编译失败。

## 关联条目

- E103：CMake 4.x 拒绝 `cmake_minimum_required < 3.5`（本任务另一候选，等价命中，走路径 A）
- E307：header-only 库 test_package 的 CMake 前置问题（相似但不相同）