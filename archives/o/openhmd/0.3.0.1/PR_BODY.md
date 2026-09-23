- **三方库名称**：OpenHMD（openhmd）
- **上游版本**：v0.3.0（适配版本号 `0.3.0.1`，源码 sha256 与 0.3.0 一致，零补丁）
- **上游仓库地址**：https://github.com/OpenHMD/OpenHMD
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（build_in_harmonyos 技能）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 9 | 来源：`tests/unittests/vec.c`（`ovec3f_*` 4 个）+ `tests/unittests/quat.c`（`oquatf_*` 5 个） |
| 集成测试 | 2 | 来源：`tests/unittests/highlevel.c`（打开/关闭单个设备与多个设备，跨 `ohmd_ctx → ohmd_list → ohmd_device → 驱动` 全链路） |
| 其他测试 | 0 | — |
| **合计** | **11** | 上游用 autotools 构建（`tests/Makefile.am: bin_PROGRAMS = unittests`），**不在上游 CMake 构建图内** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 10 | +1 | 9 个上游用例**原样执行**（源码零修改）+ 新增 1 个 `ohmd_gets` 着色器源码 API 用例 |
| 集成测试 | 8 | +6 | 2 个上游用例原样执行 + 新增 6 个消费者用例（消费打包产物：4 个真实打开 dummy 驱动 HMD，读写属性/控件/设置/姿态；2 个覆盖上下文生命周期/设备枚举与元数据） |
| 鸿蒙特有测试 | 1 | 新增 1 | `test_ohos_loader_dependency_contract`：OHOS 装载器按制品仓命名（无版本号 `.so`）解析 hidapi，13 个驱动实引入口符号 + `hid_init` 共 14 个全在位、`dladdr` 回报真实实现路径、`hid_init()` 可调用且返回受控值（0=libusb 可用 / -1=沙箱无 `/dev/bus/usb`，按值域断言，不绑定单一环境） |
| **合计** | **19** | **+8** | 上游 11/11 通过 + 新增 8/8 通过（消费者 7 = 1 单元 + 6 集成，另加鸿蒙特有 1） |

> 分类口径：按真实测试边界划分——上游 `vec.c`/`quat.c` 是库内数学 API 的直接单元测试；
> `highlevel.c` 两个用例打开真实设备、穿越完整调用链，属集成测试。新增用例中
> `shader_source_strings` 只调用库 API（不打开设备）计入单元测试；其余 6 个均消费打包产物
> 计入集成测试，其中 4 个真实打开 dummy 驱动 HMD（`open_hmd()` → `ohmd_list_open_device_s`），
> 另 2 个覆盖上下文生命周期/设备枚举与元数据。未把同一用例内的多条断言拆分成多个用例计数。
> 新增消费者用例合计 7 个 = 1 单元（`shader_source_strings`）+ 6 集成，与「合计」行的
> 「消费者 7」一致；`test_package/test.c` 内 89 处 `TAssert` 断言不重复计为用例。
> 鸿蒙专用用例 `test_ohos_loader_dependency_contract` 验证的是 OHOS 装载器 +
> 依赖闭包的运行期契约（非 OHOS aarch64 平台显式 SKIP，不误报失败），单列计入「鸿蒙特有测试」，
> 不再重复计入集成测试。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

上游 `tests/unittests/{main.c,vec.c,quat.c,highlevel.c}` 四个源文件**逐字节原样**编译执行
（配方内仅内联生成一个独立的小 `CMakeLists.txt` 复现上游 autotools 的编译关系：include
`include/` + `src/`，链接本次构建出的 `libopenhmd.a` + hidapi + m + pthread，静态目标一致地
定义 `OHMD_STATIC`）。测试源码哈希可在构建日志中校验。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游测试未被构建流程覆盖，适配后完成了接入与补全（说明如下）

> - **补全的测试范围**：
>   1. 将上游 11 个测试用例接入 `conanfile.py` 的 `build()`，在每次构建时**原样编译执行**，
>      结果以 `HMBS_UPSTREAM_TEST_RESULT=<json>` 上报，任一用例失败即构建失败；
>      （此前 0.3.0 的 `test_package` 只是手工重声明内部符号并复刻内部断言，
>      既不编译也不运行上游测试源）
>   2. 新增 7 个消费者测试用例，全部只使用公共头文件 `<openhmd.h>`，消费打包产物；
>   3. 新增 1 个鸿蒙特有用例 `test_ohos_loader_dependency_contract`（`test_package/test.c`），
>      验证 OHOS 运行时装载器与 hidapi 依赖闭包契约（4 组断言，实测数据见「验证结果」）。
> - **补全原因**：上游测试仅由 autotools 目标构建（`make check`），不在 CMake 构建图中，
>   交叉编译场景下不会被自动执行；同时公共 API（设备枚举/属性/控件元数据/设置/姿态回环/
>   着色器源码）缺少消费者视角的验证。
> - **新增测试文件清单**：
>   1. `test_package/test.c` — 7 个消费者用例（`ctx_create_probe_destroy`、`device_list_metadata`、
>      `device_open_close`、`device_properties`、`device_control_metadata`、`shader_source_strings`、
>      `device_settings_and_pose_roundtrip`、`ohos_loader_dependency_contract`（鸿蒙特有））
>   2. `test_package/conanfile.py` + `test_package/CMakeLists.txt` — 消费者测试构建/执行入口
>   3. `conanfile.py`（`build()` 末尾）— 上游测试原样编译执行与结果上报

## 验证结果

- 编译状态：通过（`conan create`，profile `ci/conan/profiles/ohos-aarch64`，鸿蒙 PC aarch64 原生验证）
- 上游测试用例通过率：11/11（100%）
- 新增测试用例通过率：8/8（100%）——消费者 7 例 + 鸿蒙特有 1 例
- 鸿蒙特有测试实测（`test_ohos_loader_dependency_contract`）：
  `dlopen("libhidapi-libusb.so", RTLD_NOW)` → ok；hidapi 入口符号 **14/14** 可解析；
  `dladdr(hid_enumerate)` → 制品仓发布的 `libhidapi-libusb.so` 真实路径；`hid_init()` → 受控值
（**0**=libusb 后端可用 / **-1**=环境无 `/dev/bus/usb` 访问，CI 沙箱常见；两者均属正常，
断言按值域接受而非绑定单一环境）
- 依赖：`hidapi/0.14.0`（制品仓已发布的 OHOS 预编译包）

## 补充说明

1. **版本号说明**：`0.3.0` 已合入 main 且制品仓已发布，按仓库规则（同版本不可重复发布，
   CI L0j 门禁）本次改进以 `0.3.0.1` 发布；源码仍取上游 tag `0.3.0`，**无任何补丁**。
2. **零补丁实现方式**：上游 `cmake/FindHIDAPI.cmake` 为 module 模式（`find_path`/`find_library`），
   与 conan `CMakeDeps` 的 config 模式包不互通；配方在 `configure` 时注入
   `HIDAPI_LIBRARY`/`HIDAPI_LIBRARIES`/`HIDAPI_INCLUDE_DIR`/`HIDAPI_INCLUDE_DIRS` 四个 cache
   变量（实测真正被上游 `CMakeLists.txt` 消费的是复数变量 `HIDAPI_LIBRARIES`/`HIDAPI_INCLUDE_DIRS`，
   单数变量为兼容兜底、CMake 会提示未被使用且无副作用），从而零补丁消费 conan hidapi 包。
   另：上游 `cmake_minimum_required(VERSION 3.1)` 与 CMake 4.x 不兼容，通过
   `CMAKE_POLICY_VERSION_MINIMUM=3.5` 传参解决。
3. **已知限制**：运行时验证基于 dummy 驱动（无需真实 HMD 硬件）；真实驱动
   （Rift/Deepoon/WMR/Vive/NOLO/3Glasses/External）与 hidapi 后端的代码路径在编译期全部参与构建。
4. **产物**：`libopenhmd.a`（静态，非系统同名库，保持上游默认）+ `include/openhmd.h`，
   不包含可执行文件，故无需 `commands.json`。
5. **适配完整性（R40 自查）**：本库属 VR HMD/外设领域，但上游为平台无关的纯 C 实现
   （`platform-posix.c` 在 OHOS 上直接可用），本次适配为**零补丁**，不存在 stub/`return 0`
   式占位适配代码；平台相关面（动态库装载约定、hidapi → libusb-1.0 依赖闭包解析）
   由「鸿蒙特有测试」`test_ohos_loader_dependency_contract` 实测守住。
