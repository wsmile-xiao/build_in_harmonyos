# pixman: `include/pixman-1` 是消费者头文件契约的一部分

## 触发场景

pixman 安装头文件到：

```text
include/pixman-1/pixman.h
include/pixman-1/pixman-version.h
```

`pixman.h` 内部再用 angle include 引用 `pixman-version.h`。如果 Conan 只暴露顶层 `include`，消费者编译会报 `pixman-version.h` 找不到。

## 修法

在 `package_info()` 中明确：

```python
self.cpp_info.includedirs = ["include/pixman-1", "include"]
self.cpp_info.set_property("pkg_config_name", "pixman-1")
```

## 测试要求

`test_package` 应从消费者视角写：

```c
#include <pixman.h>
```

而不是只写 `#include <pixman-1/pixman.h>`。这样才能验证 Conan 提供的 include dirs 是否足够。

## pixman 0.46.4 验证

真机 shadow CI 中，test_package 用 Conan include dirs 编译 `<pixman.h>`，并调用 `pixman_version_string()` 与 `pixman_region32_*` API，通过运行期 smoke。
