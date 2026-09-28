# DRAFT-librecast-0.11.2-conan2-package-info-manual-transitive-include-propagation — Conan 2 生产者侧 package_info 手动注入传递依赖 include/lib 路径，修复 CMakeDeps 对 autotools 纯 C 库传递依赖 include 置空

> **Contributor**: gcw_6YxinkyD | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: blocking (2) | **Category**: conan / cmake / packaging / c-libraries
> **Audience**: 所有公共头传递 #include 第三方库头文件的 Conan 2 纯 C autotools 库配方作者

## 触发（trigger）

librecast/0.11.2 OHOS PC aarch64 适配：公共头 `include/librecast/types.h:16` 无条件
`#include <lcrq.h>`，lcrq/0.4.1 为独立 Conan 包（纯 C autotools 构建，无 CMake target
导出，package_info 仅设 `libs = ["lcrq"]`）。test_package 走 CMakeDeps 流：
`find_package(librecast REQUIRED)` + `target_link_libraries(test librecast::librecast)`。

## 症状（symptom）

主包 librecast 构建打包全部成功（configure/make/package 均通过），test_package 编译却报：

```
In file included from .../include/librecast/types.h:16:
fatal error: 'lcrq.h' file not found
```

test_package CMakeDeps 生成的 `lcrq-release-armv8-data.cmake` 中：

```
set(lcrq_INCLUDE_DIRS_RELEASE )    # 空！
```

即使 lcrq 的 package_info 已显式设置 `self.cpp_info.includedirs = ["include"]`，
CMakeDeps 仍未将其序列化到传递依赖的数据文件中。

## 机制（root cause）

Conan 2.29.1 CMakeDeps 对**非 CMake 导出型依赖**（纯 autotools 库，无 .cmake target
文件）的传递依赖处理存在以下行为：

1. lcrq 作为 librecast 的直接依赖参与 librecast 构建时，AutotoolsToolchain 通过
   `conandepsenv` 注入 `-I<lcrq-prefix>/include`，主包编译不报错。
2. test_package 侧，lcrq 是通过 librecast 传递引入的。CMakeDeps 为 lcrq 生成的
   data.cmake 中 `INCLUDE_DIRS` 变量为空，即使 lcrq package_info 显式声明了
   `includedirs = ["include"]`。
3. `self.cpp_info.requires = ["lcrq::lcrq"]` 在 librecast package_info 中声明后，
   CMakeDeps 确实生成了 `lcrq::lcrq` target，但该 target 的
   `INTERFACE_INCLUDE_DIRECTORIES` 绑定到空变量 `lcrq_INCLUDE_DIRS_RELEASE`。
4. **与已有 draft（DRAFT-conan2-cmakedeps-transitive-include-strip）的区别**：
   该 draft 描述的是"消费者端显式 requires 传递依赖即可修复"（boost 案例，boost
   有显式 CMake 组件 target）；本案例中 lcrq 是纯 autotools 库，即使 test_package
   CMakeLists 中 `find_package(lcrq REQUIRED)` 并直接 link `lcrq::lcrq`，
   include 路径仍为空——因为 lcrq 本身不导出任何 CMake target 文件，CMakeDeps
   无法从 .cmake 文件中恢复 include 路径。

## 修复（resolution）

在 librecast 的 `package_info` 中，手动遍历 host 依赖并将传递依赖的 include/lib
路径聚合到自身 cpp_info：

```python
def package_info(self):
    self.cpp_info.libs = ["librecast"]
    self.cpp_info.requires = ["lcrq::lcrq"]
    self.cpp_info.ignored_requires = ["libsodium"]
    for dep in self.dependencies.values():
        if dep.ref.name in ("libsodium", "lcrq"):
            comp = dep.cpp_info.aggregated_components()
            for d in comp.includedirs:
                self.cpp_info.includedirs.append(d)
            for d in comp.libdirs:
                self.cpp_info.libdirs.append(d)
            for lib in comp.libs:
                self.cpp_info.libs.append(lib)
```

这使得 librecast 自身的 `lcrq_INCLUDE_DIRS_RELEASE`（即 librecast 包的 data.cmake）
携带了 lcrq 的绝对 include 路径，下游消费者只需 `find_package(librecast REQUIRED)`
即可编译通过。

验证：
```
-- Conan: Target declared 'lcrq::lcrq'
[100%] Built target test_librecast
```

## 反模式（anti-patterns）

- ❌ 只在下游 test_package 中 `find_package(lcrq REQUIRED)` 而不在 producer
  package_info 中传播 include——纯 autotools 库无 CMake target 文件，CMakeDeps
  无法从包中恢复 include 路径。
- ❌ 在 test_package 中设 `CPATH`/`CMAKE_INCLUDE_PATH` 环境变量兜底——破坏声明式
  依赖语义，干净 CI 复现失败。
- ❌ 把 lcrq.h copy 进 librecast 包的 include/——制品膨胀且版本漂移。

## 关联

- similar_to: DRAFT-conan2-cmakedeps-transitive-include-strip（消费者侧修复策略），
  本 draft 是其生产者侧补充：当传递依赖是纯 autotools 库（无 CMake target 导出）时，
  消费者侧 requires 不足以修复，必须由生产者在 package_info 中手动聚合 include/lib。
- 姊妹问题：DRAFT-conan-shared-pkgconfig-requires-drop（PkgConfigDeps 流）
