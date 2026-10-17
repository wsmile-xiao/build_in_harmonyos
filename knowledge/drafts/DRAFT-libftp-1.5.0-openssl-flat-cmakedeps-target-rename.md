# Flat openssl 包在 CMakeDeps 下只暴露 openssl::openssl，上游 find_package(OpenSSL) + OpenSSL::SSL 目标名重映射

**草稿条目**（`DRAFT-libftp-1.5.0-openssl-flat-cmakedeps-target-rename`，配对 `.kv` 同 stem）
来源：libftp 1.5.0 HarmonyOS PC 适配（2026-09-23）。

## 现象

`conan create` 配置期失败：

```console
CMake Error at CMakeLists.txt:101 (target_link_libraries):
  Target "ftp" links to:
    OpenSSL::SSL
  but the target was not found.
```

随后 test_package 编译消费者测试时：

```console
fatal error: 'openssl/conf.h' file not found
  (来自 boost/asio/ssl/detail/openssl_types.hpp:23)
```

## 根因

1. 制品仓 `openssl/3.5.6.1.1` 是 **flat 包**：`package_info()` 仅声明
   `cpp_info.libs = ["ssl", "crypto"]`，没有 components，也没有
   `cmake_file_name` / `cmake_target_name` 导出属性。Conan 2 `CMakeDeps`
   对无导出属性的包按包名生成默认目标 `openssl::openssl`。
2. libftp 上游 `CMakeLists.txt` 使用 `find_package(OpenSSL REQUIRED)` +
   `target_link_libraries(ftp PUBLIC OpenSSL::SSL)` —— 期望 CMake 生态标准的
   `OpenSSL::SSL` 目标名，与 CMakeDeps 默认名不一致 → 配置期目标找不到。
3. libftp 公共头链（`client.hpp` → Boost.Asio.SSL）编译期 `#include <openssl/conf.h>`，
   openssl 头文件路径不会自动传到下游；只有对 requires 声明
   `transitive_headers=True` 才能把 include 目录沿依赖链传递给 test_package /
   下游消费者。

## 方案（实际验证通过）

消费方 conanfile.py，无需改动 openssl 配方、不改上游源码：

```python
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout

def requirements(self):
    self.requires("boost/1.90.0", transitive_headers=True)
    self.requires("openssl/3.5.6.1.1", transitive_headers=True)

def generate(self):
    deps = CMakeDeps(self)
    deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")
    deps.generate()
    tc = CMakeToolchain(self)
    # ...
    tc.generate()
```

关键点：
- `deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")` 让
  CMakeDeps 直接生成名为 `OpenSSL::SSL` 的目标。CMake 配置期
  find_package(OpenSSL) 命中 CMakeDeps config（`CMAKE_FIND_PACKAGE_PREFER_CONFIG`
  默认开启），config 模式先于内置 FindOpenSSL 模块执行，因此
  `OPENSSL_ROOT_DIR` 等缓存变量对目标名问题无效——直接重映射目标名是正解。
- `transitive_headers=True` 传递 openssl 头文件路径，解决下游
  `openssl/conf.h file not found`。

## 验证

`python3 scripts/ohc-run.py conan-verify libftp 1.5.0`：G2 conan create 全通过，
test_package 实际编译运行真实 API 测试（`1/1 Test #1: test_libftp Passed`）。

## 适用边界与反例

- 适用于消费 flat openssl（无 CMake 导出属性）且上游用 `OpenSSL::SSL` 目标名的项目。
- 与 E473（WebP::webpdemux 缺失）同属"CMakeDeps 目标名与上游期望不符"类的不同子问题：
  - E473：目标**缺失**（配方未暴露组件）→ 需 build-module 注入 IMPORTED target；
  - 本条：目标**存在但名字不符**（flat 包默认名）→ 优先 `set_property` 重映射，更简洁。
- 反例：openssl 配方若后续声明了完整的 components/cmake 属性，此方案可简化或去除；
  仅自身构建阶段需要额外系统头时，可用 cpr 先例的 OPENSSL_* 缓存变量兜底（见 .kv fallback）。