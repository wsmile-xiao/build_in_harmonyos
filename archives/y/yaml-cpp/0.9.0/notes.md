# yaml-cpp 0.9.0 — OHOS PC (aarch64) adaptation notes

> Archive created: 2026-08-14
> Last updated: 2026-08-14

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | yaml-cpp |
| 版本 | 0.9.0 |
| 状态 | 🔵 built (recipe complete, pending device validation) |
| 构建系统 | cmake |
| 源码路径 | https://github.com/jbeder/yaml-cpp/archive/refs/tags/yaml-cpp-0.9.0.tar.gz |
| SHA256 | 25cb043240f828a8c51beb830569634bc7ac603978e0f69d6b63558dadefd49a |

## 二、源码与标签
- 上游 GitHub tag 为 `yaml-cpp-0.9.0`（带 `yaml-cpp-` 前缀，不是 `0.9.0`）。
- 归档 URL 因此使用 `refs/tags/yaml-cpp-0.9.0`。
- 解压后根目录为 `yaml-cpp-yaml-cpp-0.9.0/`，`source()` 用 `strip_root=True` 折叠。

## 三、Conan 配方要点
- `package_type = "library"`，`options = {shared, fPIC}`，默认 `shared=False, fPIC=True`。
- `config_options()`: Windows 下移除 fPIC。
- `validate()`: R32 — `settings.os in ("Linux", "OHOS")`，不用 `== "Linux"`。
- `generate()` 设置的 CMake 变量：
  - `YAML_CPP_BUILD_TESTS = False`
  - `YAML_CPP_BUILD_TOOLS = False`
  - `YAML_CPP_BUILD_CONTRIB = False`
  - `YAML_CPP_FORMAT_SOURCE = False`
  - `YAML_CPP_INSTALL = True`
  - `YAML_CPP_MAIN_INCLUDE = False`
  - `BUILD_SHARED_LIBS = options.shared`（跟随选项，禁止写死）
  - 静态构建时 `CMAKE_POSITION_INDEPENDENT_CODE = fPIC`
- OHOS 守卫块（R26/平台陷阱）：
  - `tc.blocks["generic_system"]` 把 `cmake_system_name` 设为 `"OHOS"`、`cmake_system_processor` 设为 `"aarch64"`，修复 CMake 找不到 `Platform/HarmonyOS.cmake` 导致 SONAME 缺失的问题。
  - `CMAKE_INSTALL_LIBDIR = "lib"`（避免装到 lib64/）。
- `package()` 复制 LICENSE 到 `licenses/`；OHOS + shared 时对 `lib/**/*.so` 做代码签名（原子替换）。

## 四、test_package
- `test.cpp` 实质调用 yaml-cpp API（R34）：Load、scalar/sequence/map 节点遍历、bool 转换、emit 往返、从零构建 Emitter、版本宏检查。
- CMakeLists 用 `find_package(yaml-cpp CONFIG REQUIRED)` + `yaml-cpp::yaml-cpp`。
- OHOS 上执行前对 test 二进制做代码签名。

## 五、依赖
- 无外部依赖（仅需 C++11 编译器）。

## 六、对话记录
### 对话 #1 — 2026-08-14
**操作**: 编写 conanfile.py + conandata.yml + test_package/
**结果**: 配方完成，待 conan create / 设备验证
**发现的问题**: GitHub tag 前缀为 `yaml-cpp-`，URL 必须用 `yaml-cpp-0.9.0`
**当前状态**: recipe ready
**遗留问题**: 真机验证、CI 上传
---

**编译结束**: 2026-08-14 15:11
**最终状态**: built
