- **三方库名称**：libfishcamp
- **上游版本**：v2.2.4（indi-3rdparty 单体仓库内 libfishcamp 子项目，版本 1.2）
- **上游仓库地址**：https://github.com/indilib/indi-3rdparty
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游为硬件相机驱动库，无单元测试 |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | 上游无正式测试框架 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 1 | 新增 | test_package 一个**完整消费者端到端用例**（init→枚举→开相机→读设备信息→配置曝光→取帧→关闭），内部含 20+ 项真实产出校验 |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：编写了一个**完整的下游消费者端到端用例** `test_fishcamp.c`，模拟 INDI 驱动使用本库的真实方式，跑通一整条捕获会话并对**真实产出**做校验，而非仅断言函数可调用：
>   `fcUsb_init()` → `fcUsb_setSimulation(1)` → `fcUsb_FindCameras()`（仿真模式枚举出 1 台虚拟 Starfish 相机）→ `fcUsb_GetNumCameras()` → `fcUsb_OpenCamera(1)` → 读取相机身份（`GetCameraVendorID==0x1887` / `GetCameraProductID==0x0003` / `GetCameraSerialNum==12345`）→ `fcUsb_cmd_getinfo()`（仿真模式真实填充 `fc_camInfo`：1280×1024、"Starfish Mono"、序列号串）→ 配置曝光（`setIntegrationTime`/`setRoi`/`setBin`）→ `startExposure` → `getState` → `getRawFrame` → `CloseCamera` → `fcUsb_close()`。
>   用例内部对每一步的真实返回值/结构体内容做 20+ 项 CHECK 校验（相机枚举数、相机身份、设备信息尺寸与名称、各命令返回码均为 0），全部通过即判定端到端用例成功。
> - **补全原因**：上游 libfishcamp 为 Fishcamp CCD 相机驱动，仅随驱动发布，无正式测试框架；本库的控制流在仿真模式下为官方一等支持路径，可无需硬件跑通真实流程并产出可校验状态。
> - **新增测试文件清单**：
>   1. `archives/l/libfishcamp/1.2/test_package/src/test_fishcamp.c` — 自定义 CHECK 宏（不使用 `<cassert>`，避免 Release `-DNDEBUG` 剔除 assert 使测试退化为空壳）。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（上游无测试用例）
- 新增测试用例通过率：1/1（100%）—— 1 个完整端到端消费者用例，内部 20+ 项子校验全部通过

## 补充说明

- 构建系统：CMake + Conan 2.29；OHOS aarch64 / clang 15 / cppstd 17。
- 仅依赖 libusb-1.0（公有依赖，`fishcamp_common.h` 包含 `<libusb.h>`），已通过 patch 去掉唯一 INDI 耦合（`INDI_UNUSED` 宏本地定义，无需 libindi）。
- 上游 CMakeLists 依赖 INDI 框架，本适配以精简 CMakeLists 替代。
- 源码直接从官方 v2.2.4 tag 抓取 4 个文件（3 源 + LGPL 许可），SHA256 校验见 conandata.yml。
- 运行时说明：本库为硬件相机驱动，需真实 Fishcamp CCD 相机 + 固件；OHOS PC 无该硬件，故测试使用库内置的**仿真模式**（官方一等支持路径）跑通完整控制流并校验真实产出，符合本仓「可编译但无硬件运行时」类适配。
