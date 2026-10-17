# DRAFT-imx-code-signing-tool-4.0.1: OHOS 上为 find_package(OpenSSL) 消费者重映射 Conan openssl 组件

> 草稿（路径 B 知识库贡献候选，随 imx-code-signing-tool 4.0.1 归档 PR 提交）。
> 来源事件：imx-code-signing-tool 4.0.1（NXP CST）HarmonyOS PC 适配。

## 错误现场

上游 CMakeLists 使用 `find_package(OpenSSL 3.0.0 REQUIRED)` 并链接
`OpenSSL::Crypto` / `OpenSSL::SSL` 目标：

```
CMake Error at lib/back_end/CMakeLists.txt:19 (target_link_libraries):
  Target "back_end" links to:
    OpenSSL::Crypto
  but the target was not found.
```

同款报错变体：`OpenSSL::SSL`、`FATAL Cannot find OpenSSL`（find_package 阶段）。

## 根因

ohpcd 制品仓的 openssl 配方 `package_info()` 只声明包级目标
`openssl::openssl`（cmake_file_name `openssl`），并不导出 CMake 官方
`FindOpenSSL` 风格的 `OpenSSL::Crypto` / `OpenSSL::SSL` 组件目标。上游
项目若直接 `find_package(OpenSSL)` + `OpenSSL::Crypto` 链接，CMakeDeps
生成的 `openssl-config.cmake` 无法满足该目标名，配置期即失败。

Conan 2 的 CMakeDeps 是**惰性读取** cpp_info 的：组件属性和
`cmake_target_name` 必须在 `CMakeDeps.generate()` **之前**写入
`self.dependencies["openssl"].cpp_info`，否则生成的 config 文件不含
重映射后的目标名（实测 generate() 内先 deps.generate() 再改组件 → 目标
仍然 not found）。

## 解法

在 conanfile.py `generate()` 中，先重映射 openssl 组件，再生成 CMakeDeps：

```python
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

def generate(self):
    # 1) 先重映射（必须在 CMakeDeps.generate() 之前）
    openssl = self.dependencies["openssl"].cpp_info
    openssl.set_property("cmake_file_name", "OpenSSL")
    openssl.set_property("cmake_additional_variables_prefixes", ["OPENSSL"])
    package_folder = self.dependencies["openssl"].package_folder
    include_dirs = [os.path.join(package_folder, p) for p in openssl.includedirs]
    lib_dirs = [os.path.join(package_folder, p) for p in openssl.libdirs]
    system_libs = list(openssl.system_libs)
    openssl.libs = []
    openssl.system_libs = []

    crypto = openssl.components["Crypto"]
    crypto.libs = ["crypto"]
    crypto.system_libs = system_libs
    crypto.includedirs = include_dirs
    crypto.libdirs = lib_dirs
    crypto.set_property("cmake_target_name", "OpenSSL::Crypto")

    ssl = openssl.components["SSL"]
    ssl.libs = ["ssl"]
    ssl.includedirs = include_dirs
    ssl.libdirs = lib_dirs
    ssl.requires = ["Crypto"]
    ssl.set_property("cmake_target_name", "OpenSSL::SSL")

    # 2) 再生成（此时 config 已带 OpenSSL::Crypto/OpenSSL::SSL 目标）
    deps = CMakeDeps(self)
    deps.generate()

    tc = CMakeToolchain(self)
    tc.generate()
```

## 适用边界

- 适用：上游 CMake 工程用官方 `find_package(OpenSSL)` +
  `OpenSSL::Crypto` / `OpenSSL::SSL` 目标链接，且依赖 ohpcd openssl 配方。
- 不适用：上游自带 `cmake/modules/FindOpenSSL.cmake` 或期望 MODULE 模式
  查找的项目（应改用 `OPENSSL_ROOT_DIR` + `CMAKE_PROJECT_INCLUDE` 禁用
  PREFER_CONFIG，见 getdns 草稿）；上游直接用 `openssl::openssl` 的
  Conan 风格项目无需重映射。
- 组件键名以 ohpcd openssl 配方 `components` 为准（Crypto/SSL）。

## 验证

`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
配置阶段不再报 `OpenSSL::Crypto ... target was not found`，链接产物
`readelf -d` 无未解析符号。

## 反例与限制

- 先 `deps.generate()` 再改组件 → 目标仍 not found（顺序敏感）。
- 只改 `set_property("cmake_target_name", ...)` 但不清空 `openssl.libs` →
  包级默认 libs 与组件 libs 重复，链接行出现两次 -lcrypto。
- `system_libs`（如 dl、pthread）必须复制到组件上，否则静态链接
  OpenSSL 时缺系统库。
