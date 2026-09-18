# kegtron-ble

## 软件描述
kegtron-ble 是 Kegtron 啤酒桶流量计（KT-100 单口 / KT-200 双口设备）的 BLE 广告解析库（纯 Python）。它将 27 字节的 manufacturer data 帧解析为结构化的传感器状态数据：设备型号、桶型（Corny/1/6 Barrel 等 12 种规格表）、桶容积、起始容积、已出酒量、端口状态、端口名称。属于 Home Assistant 生态的 Bluetooth-Devices 系列解析库。

## 功能概述
- **设备识别**：KT-100（单口）/ KT-200（双口，port 1/port 2）型号判定
- **桶型解析**：KEGTRON_SIZE_DICT 12 种标准桶型（Half Corny 2.5gal ~ 1/2 Barrel 15.5gal）+ 非标桶回退（`Other (N L)`）
- **容积换算**：keg_size / volume_start / volume_dispensed 千分位整数 → 升（float）
- **端口信息**：port_state（Configured/Unconfigured）、port_name（设备配置的字符串名）
- **信号透传**：RSSI signal_strength
- **输出模型**：sensor-state-data 的 SensorUpdate/SensorValue 结构化对象

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无 C/C++ 编译
- 直接拷贝源码 `kegtron_ble/` 模块（`__init__.py` + `parser.py` + `py.typed`）到 `lib/pythonX.Y/site-packages`——绕过 pip 构建（同 rich/python-magic 模式：环境 setuptools egg_info 加载 entry point 报 pbr 缺失实测）

### 关键攻坚点
1. **Python 级依赖未发布**：`sensor-state-data`（>=2.19.0）/ `bluetooth-data-tools`（>=0.1.2）/ `bluetooth-sensor-state-data`（>=1.6.1）及其传递依赖 `home-assistant-bluetooth` 均未发布到 ohpcd conan 仓（R36 断链）——主配方不写 conan requires（PF4 依赖闸禁止），build() 上游测试与 test_package 消费验证均从 OHOS pypi 镜像 vendor 上游 poetry.lock 锁定版本的纯 wheel（py3-none-any）组装 PYTHONPATH
2. **版本组合以 lock 为准**：home-assistant-bluetooth 若用最新 2.0.0 会拖进 habluetooth 6.26.5（带 aarch64-linux-ohos .so 未签名不可 dlopen）；回退 lock 锁定的 1.4.0 纯 Python 版本即全通过
3. **bleak 边界实测**：上游 lock 中 bleak 0.17.0 只是 home-assistant-bluetooth 的传递依赖——实测从 PYTHONPATH 移除 bleak 后 import 链与全部 3 个上游测试通过（解析只消费 BluetoothServiceInfo 数据类，不触碰 BLE 扫描后端）
4. **PYTHONPATH 注入**：`package_info()` 把 site-packages 注入 `env_info.PYTHONPATH`——消费者 `import kegtron_ble` 可用

### 与 Linux 的差异
- 无差异——纯数据解析库，无平台相关代码

## 依赖关系
| 依赖 | 版本 | 用途 |
|------|------|------|
| sensor-state-data | 2.19.0（lock） | 传感器状态数据模型（SensorUpdate/SensorValue） |
| bluetooth-data-tools | 0.3.1（lock） | short_address 等蓝牙数据工具 |
| bluetooth-sensor-state-data | 1.7.5（lock） | BluetoothServiceInfo 载荷模型 |
| home-assistant-bluetooth | 1.4.0（lock） | BluetoothServiceInfo 数据类（bluetooth-sensor-state-data 传递依赖） |

> 以上均为 Python 级运行时依赖（pypi），未发布到 ohpcd conan 仓——消费时按 lock 组合自行 pip 安装或 vendor。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.0.2 | built | 2026-09-18 | 纯 Python noarch 适配，上游测试 3/3 PASS |

## 参考资料
- 上游仓库: https://github.com/Bluetooth-Devices/kegtron-ble
- PyPI: https://pypi.org/project/kegtron-ble/1.0.2/
