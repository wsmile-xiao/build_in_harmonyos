# DRAFT — pybind11 header-only 配方：PYBIND11_NOPYTHON 零依赖构建 + test_package 宿主 Python include 注入

> 状态: 草稿（基于 pybind11 2.10.1 R01 真实证据，待查重/提升）。
> 来源: pybind11 2.10.1 全量适配（pc1-13, 2026-09-05），G2/G3/G4 + W3 L0/L1 全程实证。

## 真实问题（场景）

pybind11 是 CMake 头文件型绑定库，但有两个 OHOS/Conan 配方落地陷阱：

1. **detail/common.h 无条件 `#include <Python.h>`**（约 L208），任何消费者 TU 包含
   pybind11 头文件都需要 Python 开发头。OHOS 工具链 sysroot（/data/service/hnp）
   无 Python.h，若配方 build() 阶段让 cmake 搜索 Python（PYBIND11_TEST 默认随
   master project 为 ON、tools/pybind11Tools.cmake 会 `find_package(PythonLibsNew
   REQUIRED)`），会直接失败或把宿主 Python 头引入交叉编译。

2. test_package 消费者编译同样需要 Python.h；且 conanfile.py 若手写
   `export_sources()` 却漏 import `export_conandata_patches`，conan create 在
   export 阶段抛 `NameError: name 'export_conandata_patches' is not defined`。

## 根因

- pybind11 本体构建（仅安装头文件 + cmake 配置）不需要 Python，但 CMake 默认行为
  会搜索 Python；必须显式 `PYBIND11_NOPYTHON=ON` 关闭搜索。
- 头文件硬依赖 Python.h 是消费者侧约束：test_package 用宿主 Python 的
  sysconfig include 注入 `PYTHON_INCLUDE_DIR` 即可编译探测程序，不产生包级依赖。
- export_sources() 与导入缺失是通用 Conan 2 配方坑：定义方法就必须 import 对应
  helper。

## 修复/方案

conanfile.py（package_type="header-library"）：

```python
def generate(self):
    tc = CMakeToolchain(self)
    if self.settings.os == "OHOS":
        tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
        tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
    tc.variables["PYBIND11_TEST"] = "OFF"
    tc.variables["PYBIND11_INSTALL"] = "ON"
    tc.variables["PYBIND11_NOPYTHON"] = "ON"   # ★ 构建期零 Python 依赖
    tc.generate()
```

test_package 侧：generate() 中 `sysconfig.get_paths()["include"]` 注入
`PYTHON_INCLUDE_DIR`（CMakeLists 条件 include），test() 用 self.run 实跑二进制。

## 验证

- conan-verify：G1/G0/G2/G3/G4 全 PASS；G2 conan create 全程无 Python 头依赖拉取。
- W3 build_and_test.sh：L0 全检 pass、L1 test_package executed、Success: 1。
- test_package 探测程序在真实 OHOS aarch64 设备运行：
  `pybind11 2.10.1 (hex 0x020A0100) CXX17=yes`，exit 0。
- 修复前证据：G1 报缺 export_sources()、G2 NameError export_conandata_patches、
  test_package generators 双重声明 ConanException（后两者见 DRAFT-ctre 等价条目）。

## 适用边界 / 反例 / 限制

- 适用：一切 pybind11 类 header-only 绑定库（nanobind、boost::python 包装库）在
  OHOS/arm64 的 Conan 2.x 配方；以及任何头文件硬依赖第三方开发头的库。
- 反例：需要真实构建 Python 扩展模块（PYBIND11_TEST 构建上游测试套件）的配方
  不应开 NOPYTHON；纯 python 交付项目不适用。
- 限制：宿主 Python include 仅用于 test_package 编译期；CI 与本地须为同一
  Python 3.12（本仓 ci/setup.sh 保证）。设备 python3 为静态构建，跑上游 pytest
  需 LD_PRELOAD libpython + 签名后 dlopen，属平台限制不阻塞交付。