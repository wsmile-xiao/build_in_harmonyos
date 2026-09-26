# 测试报告 — ld2410-ble 0.2.0

> **项目**: ld2410-ble (HLK-LD2410B/LD2410C 24GHz mmWave presence-radar BLE client library)
> **测试日期**: 2026-09-25
> **测试环境**: HarmonyOS PC aarch64 (Python 3.12.8), Conan profile ohos-aarch64
> **测试类型**: 上游测试套件 (pytest) + 新增消费者测试 + 新增鸿蒙特有测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 64 | 100% |
| 通过 (PASS) | 64 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%** (64/64)

> 分层统计：上游 1 项 + 新增消费者 43 项 + 新增鸿蒙特有 20 项 = 64 项（详见 §三）。
> 本次为纯 Python 包，无 C/C++ 编译产物，故不存在编译期测试（如 make check）。

---

## 二、测试结论

### 2.1 总体评价

✅ **全部通过。** ld2410-ble 是纯 Python 库（poetry-core、src 布局、无 C 扩展），
上游 1 个用例与新增 63 项断言在 HarmonyOS PC 环境（Python 3.12.8）下 100% 通过，
未修改任何上游源码或测试文件，无崩溃点，无阻塞项。

上游测试套件仅 1 个用例（`tests/test_init.py::test_add`，只断言包可导入），
覆盖度不足以验证本库的实际功能，故按任务要求补足新增测试：消费者测试
覆盖真实 BLE 帧解析 API，鸿蒙特有测试覆盖 OHOS 运行时平台契约。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| bleak 默认 BLE 后端在 HarmonyOS 不可解析 | 真实 BLE 连接（需硬件） | 已知平台缺口，不影响本包安装与解码面 |

### 2.3 可用功能清单

```
✅ 包导入 + 版本元数据（ld2410_ble.__version__）
✅ 线序协议常量契约（CHARACTERISTIC_NOTIFY/WRITE UUID、CMD_* 命令字节）
✅ LD2410BLEState（frozen dataclass）默认值与不可变性
✅ 设备身份（address/name/rssi，含无 AdvertisementData 时 rssi=None）
✅ 普通帧解析：目标状态位（0/STATIC/MOVING/BOTH）、移动/静止距离与能量、探测距离
✅ 工程模式帧解析：max_motion_gates/max_static_gates、8 门能量数组、门访问器
✅ little-endian intify 字节序转换
✅ 回调注册/触发/注销；断开回调注册/注销
✅ 分包通知缓冲重组
✅ stop() 无活动客户端时的安全空操作
✅ OHOS 运行时契约：platform.system()==HarmonyOS、sys.platform 属 OHOS 族（设备/桌面构建 linux、CI worker 构建 ohos，双实测）、aarch64 little-endian
✅ 纯 Python 安装（包内无 .so/.pyd，免 OHOS 原生工具链）
✅ 运行期依赖导入完整性（bleak / bleak-retry-connector / async-timeout）
✅ bleak 后端平台缺口显式探测（BleakError: Unsupported platform: HarmonyOS）
```

### 2.4 已知限制

1. 上游测试套件规模极小（1 个用例），功能覆盖由本次新增测试补齐，故本包的测试
   充分性依赖新增测试而非上游套件。
2. bleak 在 HarmonyOS 上无法解析默认 BLE 后端（`platform.system()` 返回 `"HarmonyOS"`，
   而 bleak 仅接受 `"Linux"`）；真实 BLE 连接需硬件且需上游支持该平台。本包的数据
   解码面在 OHOS 完整可用，此缺口由鸿蒙特有测试显式探测记录，不做 stub 掩盖。
3. bleak 的 `dbus-fast` 依赖 wheel marker 为 `platform_system == "Linux"`，在 HarmonyOS
   下被 pip 跳过；镜像提供的 `dbus_fast-*-ohos_aarch64.whl` 与本机 pip tag
   （`harmonyos_aarch64`）不匹配，无法经 marker 路径安装。
4. 上游 `__version__` 上报 `"0.0.0"`（未与包版本联动），属上游行为，未改动。

---

## 三、测试详情

### 3.1 通过的测试（按来源分层）

| 测试来源 | 测试文件 | 功能 | 结果 |
|----------|----------|------|------|
| 上游 | tests/test_init.py | `import ld2410_ble` 并断言包可导入（`test_add`） | 1/1 ✅ PASS |
| 新增（消费者） | test_package/test_ld2410_ble.py | 帧解析 / 状态位 / 能量门 / 回调 / 缓冲重组 / 常量契约 / intify | 43/43 ✅ PASS |
| 新增（鸿蒙特有） | test_package/test_ld2410_ble_ohos.py | OHOS 运行时契约 / little-endian / 纯 Python 免工具链 / 依赖完整性 / backend 缺口 | 20/20 ✅ PASS |
| **合计** | | | **64/64 ✅** |

#### 3.1.1 上游测试逐项

| 测试项 | 结果 | 说明 |
|--------|------|------|
| tests/test_init.py::test_add | ✅ PASS | 上游唯一用例；源码逐字节未修改 |

#### 3.1.2 新增消费者测试逐项（test_ld2410_ble.py，43 项）

| 分组 | 断言项 | 结果 |
|------|--------|------|
| 导入面 | import_package, version_metadata | 2/2 ✅ |
| 常量契约 | characteristic_notify_uuid, characteristic_write_uuid, bt_password_default, cmd_enable_config, cmd_enable_engineering_mode | 5/5 ✅ |
| 状态容器 | state_defaults_flags, state_defaults_gates, state_defaults_energy_gates, state_dataclass_frozen | 4/4 ✅ |
| 设备身份 | device_address, device_name, rssi_from_advertisement, rssi_without_advertisement | 4/4 ✅ |
| 普通帧解析 | plain_frame_moving_flag, plain_frame_static_flag, plain_frame_moving_distance_energy, plain_frame_static_distance_energy, plain_frame_detection_distance, is_moving_property, moving_target_distance_property, plain_frame_no_engineering_gates | 8/8 ✅ |
| 目标状态位 | target_state_idle, target_state_static_only, target_state_both | 3/3 ✅ |
| 工程模式帧 | engineering_frame_max_gates, engineering_frame_motion_energy_gates, engineering_frame_static_energy_gates, motion_energy_gate_accessors, static_energy_gate_accessors, max_gates_properties, energy_gate_list_length | 7/7 ✅ |
| 字节序 | intify_little_endian, intify_high_byte | 2/2 ✅ |
| 回调 | callback_fires_per_notification, callback_registered, callback_unregister, disconnected_callback_register, disconnected_callback_unregister | 5/5 ✅ |
| 分包缓冲 | split_frame_buffered, split_frame_completed | 2/2 ✅ |
| 生命周期 | stop_without_client_safe | 1/1 ✅ |

#### 3.1.3 新增鸿蒙特有测试逐项（test_ld2410_ble_ohos.py，20 项）

| 分组 | 断言项 | 结果 |
|------|--------|------|
| 运行时身份 | ohos_platform_is_ohos_family, ohos_platform_machine_aarch64, ohos_sys_platform_is_ohos_family, ohos_runtime_little_endian, ohos_python_version_supported | 5/5 ✅ |
| 纯 Python 安装 | ohos_package_has_no_native_extension, ohos_package_python_modules_present | 2/2 ✅ |
| 依赖完整性 | ohos_dep_bleak_importable, ohos_dep_bleak_retry_connector_importable, ohos_dep_async_timeout_importable | 3/3 ✅ |
| 平台缺口探测 | ohos_bleak_backend_probe | 1/1 ✅ |
| OHOS 运行时解码 | ohos_client_constructs_on_loop, ohos_rssi_on_ohos_runtime, ohos_little_endian_decode_correct, ohos_plain_frame_flags, ohos_plain_frame_values, ohos_engineering_gates, ohos_engineering_energy_gates, ohos_callback_dispatch_on_loop, ohos_no_device_raises_bleak_error | 9/9 ✅ |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | — |

---

## 四、关键问题分析

无失败/阻塞测试。全部测试离线运行，不连接真实 BLE 设备：帧解析断言通过直接投喂
构造的真实线序字节（`F4F3F2F1 | len | eng | AA | state | moving-dist/energy |
static-dist/energy | detection | [eng-data] | 55 00 F8F7F6F5`）到
`LD2410BLE._notification_handler` 完成，因此无蓝牙硬件亦可完整执行。

本次实测命令：

```bash
# 1. 上游 pytest 套件（1 用例）
PYTHONPATH=<site-packages> python3 -m pytest test_package/tests -q --no-header -o addopts= -p no:cacheprovider
# → 1 passed in 0.02s

# 2. 新增消费者测试（43 断言）
python3 test_package/test_ld2410_ble.py <site-packages>
# → HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 43, "passedCount": 43}

# 3. 新增鸿蒙特有测试（20 断言）
python3 test_package/test_ld2410_ble_ohos.py <site-packages>
# → platform facts: system=HarmonyOS machine=aarch64 sys.platform=linux byteorder=little python=3.12.8
#   CI worker 对同一契约实测: sys.platform=ohos, python=3.12.9 —— 故套件按 OHOS 族 linux|ohos 断言
# → bleak backend probe: BleakError: Unsupported platform: HarmonyOS
# → HMBS_OHOS_TEST_RESULT={"executed": true, "passed": true, "platform": "HarmonyOS", "machine": "aarch64", "discovered": 20, "passedCount": 20}
```

三层测试均由 `test_package/conanfile.py` 的 `test()` 在 `conan create` 时真实执行，
并分别输出 `HMBS_UPSTREAM_TEST_RESULT` / `HMBS_TEST_PACKAGE_RESULT` / `HMBS_OHOS_TEST_RESULT` 标记。

---

## 五、测试环境

```
Python: 3.12.8
平台: HarmonyOS aarch64 (platform.system()=HarmonyOS, sys.platform=linux (CI worker: ohos), byteorder=little)
Conan profile: ohos-aarch64 (os=OHOS, arch=aarch64, clang, Release)
构建方式: pip install . --prefix=<stage> (poetry-core + build isolation)
运行期依赖: bleak 3.0.1 / bleak-retry-connector 4.6.1 / async-timeout 5.0.1
测试依赖: pytest
配方: package_type=python-require，settings=os,arch,compiler,build_type
源码: GitHub 官方 tag archive v0.2.0 (sha256=9ce32580ee9ecfec65f644e879d73eca045b2c667182c54f7286573673990e73)
```

---

*报告生成时间: 2026-09-25*
