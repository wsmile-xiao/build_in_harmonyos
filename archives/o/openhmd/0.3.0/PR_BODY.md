## PR 信息
- **三方库名称**：openhmd
- **上游版本**：0.3.0
- **上游仓库地址**：https://github.com/OpenHMD/OpenHMD
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比
### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 11 | 来源：tests/unittests/（main.c 的 Test() 序列：vec3f×4 + quatf×5 + highlevel×2），上游由 autotools（make check）/meson 定义，CMake 构建不含 |
| 集成测试 | 0 | 上游无集成测试 |
| 其他测试 | 1 | examples/simple（示例程序，非断言型测试） |
| **合计** | **12** | |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 11 | 不变 | 上游 tests/unittests 全部 11 个测试移植到 test_package/test.c，测试数据与断言逐项对齐上游源码（vec.c/quat.c/highlevel.c） |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 2 | 新增 | test_public_api_version（版本号/字符串 API）、test_public_api_probe_enumeration（OHOS 上设备枚举 + 属性直读断言：dummy HMD 1280x800、控制器状态） |
| **合计** | **13** | **+2** | |

---

## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（逐条：修改的测试文件/修改原因/修改内容）

| 测试文件 | 修改原因 | 修改内容 |
|----------|----------|----------|
| tests/unittests/* → test_package/test.c | 上游单元测试仅由 autotools/meson 构建系统定义（tests/unittests/Makefile.am），上游 CMakeLists.txt 不含 tests/；本包采用上游 CMake 主路径构建，测试移植为 Conan test_package 消费者测试 | ① 内部头 openhmdi.h 的依赖改为手动复刻类型定义（vec3f/quatf）与数学函数原型（libopenhmd.a 导出的全局符号，nm 验证）；② 测试数据与断言逻辑逐项保留（5 组 normalize 数据、6 组 length、4 组 angle、3 组 dot、4 组 quat init_axis、5 组 get_rotated 等）；③ main() 的 Test() 序列与上游完全一致 |

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，补全（补全的测试范围/补全原因/新增测试文件清单）

| 补全范围 | 补全原因 | 新增文件 |
|----------|----------|----------|
| 公共 API 版本验证（ohmd_get_version/ohmd_require_version/ohmd_gets GLSL） | 上游测试只覆盖内部数学函数与高层开合，版本 API 无断言 | test_package/test.c（test_public_api_version） |
| OHOS 设备枚举 + 属性断言（probe 列表遍历 + OHMD_DEVICE_CLASS 读取 + dummy HMD 分辨率 1280x800 + 控制器状态 (0.1, 1.0)） | 上游 highlevel 测试只断言 open/close 返回值，未覆盖属性读取路径；同时作为 R40 深度适配验证（设备枚举非 stub 的实证） | test_package/test.c（test_public_api_probe_enumeration） |

---

## 验证结果
- 编译状态：通过（conan create 全绿，零源码补丁）
- 上游测试用例通过率：11/11（100%）
- 新增测试用例通过率：2/2（100%）

ctest 原始输出：`100% tests passed, 0 tests failed out of 1`；测试二进制输出上游标志性尾行 `all a-ok`。

本地 W3 CI 模拟（与远端 CI 同源脚本）：
```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
[ok] L1e: Negative test confirmed — test genuinely depends on openhmd
```

---

## 补充说明

1. **依赖**：hidapi/0.14.0（制品仓已发布，libusb 后端，传递依赖 libusb/1.0.27）。上游 configure.ac 声明 hidapi >= 0.0.5，0.14.0 满足。
2. **零源码补丁**：两处兼容性问题均以配方层解决——
   - 上游 `cmake_minimum_required(VERSION 3.1)` 与 CI 的 CMake 4.x 不兼容 → `-C` 初始 cache 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 官方兼容开关）；
   - conan toolchain 的 `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON` 令上游 `find_package(HIDAPI)`（module 模式）被 CMakeDeps config 抢占，上游 CMakeLists 消费的 `HIDAPI_INCLUDE_DIRS/HIDAPI_LIBRARIES` 未定义 → 初始 cache 预置全部四个变量（单数=Find 模块结果变量，复数=CMakeLists 消费变量）。
3. **驱动完整性（R40）**：上游默认驱动集全部保留编译（Oculus Rift/Deepoon/WMR/HTC Vive/NOLO/3Glasses/External/dummy，PSVR 上游默认 OFF 保持不变）；本机 OHOS PC 实测 `ohmd_ctx_probe` 枚举出 4 个设备（External + HMD Null + 左右 Controller Null），设备枚举链路真实工作、非 stub。
4. **平台限制（如实记录）**：本机无 VR 头显硬件，真实 HID 驱动 I/O 无法端到端验证（所有平台共同限制，dummy 驱动即为此设计）；OHOS 内核存在 /dev/hidraw0/1/2 与 /dev/bus/usb 节点（shell 用户无权限读取，节点存在），hidapi 走 libusb 后端的 /dev/bus/usb 枚举路径。
5. **已知 API 注意点**：上游 0.3.0 的 `ohmd_gets` 不支持版本字符串（OHMD_VERSION 枚举为后续版本引入），版本验证用 `ohmd_get_version`。
