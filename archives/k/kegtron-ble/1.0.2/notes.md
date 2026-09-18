# kegtron-ble 1.0.2 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无 C/C++ 编译）
- **编译日期**: 2026-09-18
- **平台**: OHOS PC（arm64）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/k/kegtron-ble/1.0.2 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 PyPI sdist（kegtron_ble-1.0.2.tar.gz，5.6KB，sha256=8f52ff...），
`strip_root=True` 解压。sdist 只含 LICENSE/PKG-INFO/README/pyproject.toml/src/。

### 2. 上游测试（build()——rule 4 实测回填）
- **sdist 不含 tests/**——从 GitHub v1.0.2 tag tarball 提取 tests/（test_parser.py）
- Python 级依赖 vendor：上游 poetry.lock 锁定组合的 4 个纯 wheel 从 OHOS pypi
  镜像下载解压（sensor_state_data-2.19.0 / bluetooth_data_tools-0.3.1 /
  bluetooth_sensor_state_data-1.7.5 / home_assistant_bluetooth-1.4.0，
  全部 py3-none-any）
- pytest 实跑：**3 passed / 0 failed / 0 skipped（3/3 = 100%，0.04s）**
  - test_can_create：实例化 KegtronBluetoothDeviceData
  - test_kegtron_kt100：KT-100 单口帧完整解析断言（含 SensorUpdate 全结构比对）
  - test_kegtron_kt200：KT-200 双口 port 2 帧完整解析断言
- 本地预验证同款环境实测同结果（/data/app/bin/python3 3.12.9 + pytest 9.1.1）

### 3. 打包（package()）
`shutil.copytree` 拷贝 `src/kegtron_ble/` 模块（__init__.py + parser.py +
py.typed）到 `lib/pythonX.Y/site-packages/kegtron_ble`。

### 4. package_info()
`env_info.PYTHONPATH` 注入 site-packages——消费者 `import kegtron_ble` 可用。

## 依赖处理

kegtron-ble 1.0.2 的 pyproject.toml 声明三个直接依赖：
- `bluetooth-sensor-state-data >= 1.6.1`
- `sensor-state-data >= 2.19.0`
- `bluetooth-data-tools >= 0.1.2`
- 传递：`home-assistant-bluetooth`（bluetooth-sensor-state-data 依赖它提供
  BluetoothServiceInfo 数据类）

**全部未发布到 ohpcd conan 仓**（`conan download <pkg> -r=ohpcd --only-recipe`
实测 404/空）——不写 conan requires（PF4 依赖闸禁止引用未发布依赖，
R36 链断不连坐）。上游测试与 test_package 消费验证均 vendor pypi wheel。

### 版本组合踩坑记录（重要）
- **home-assistant-bluetooth 必须用 1.4.0（lock 锁定）**：最新 2.0.0 声明
  `habluetooth >= 4.0`，OHOS pypi 镜像只有 habluetooth 0.0.1/0.1.0/6.26.5；
  6.26.5 带 `advertisement_tracker.cpython-312-aarch64-linux-ohos.so`
  未签名不可 dlopen（ImportError: Permission denied）
- **bleak 无关紧要**：上游 lock 中 bleak 0.17.0 只是 home-assistant-bluetooth
  1.4.0 的声明依赖；实测从 PYTHONPATH 移除 bleak 后 import 链与 3 个上游
  测试全部通过——解析只消费数据类，不触碰扫描后端
- **HNP Python PYTHONPATH 怪癖**：设置 PYTHONPATH 后默认 sys.path[0]
  （/data/storage/el2/base/files/interpreters/pip-global）被移除——pytest
  等工具必须一并装进 PYTHONPATH 指向目录

## 上游测试申报（rule 4）

| 项 | 值 |
|---|---|
| 上游注册测试数 N | 3（tests/test_parser.py，pytest） |
| 本地实测 | 3/3 PASS（100%） |
| 跳过/失败 | 0 / 0 |
| 环境组合 | lock 锁定 4 wheel vendor + OHOS Python 3.12.9 + pytest 9.1.1 |
| 硬件依赖 | 无（纯数据解析——构造字节数组帧，无 BLE 硬件调用） |

## test_package（R34 消费验证）

`test_kegtron_ble.py`：
1. HARD 断言：包文件存在（__init__.py / parser.py / py.typed）
2. KT-100 真实广告帧解析（与上游测试同形状的 27 字节载荷）：
   - 设备识别：name="Kegtron KT-100 9B75"、model=KT-100、manufacturer=Kegtron
   - keg_size=18.927、keg_type="Corny (5.0 gal)"
   - volume_start=5.0、volume_dispensed=0.738
   - port_state="Configured"、port_name="Single Port"、port_count
   - signal_strength=-82、entity_descriptions=8 项完整
3. 依赖 vendor（同 build() 的 4 wheel）组装 PYTHONPATH 后子进程跑 smoke

## 知识沉淀
- L2：Python 级依赖未发布时的 vendor 模式（lock 锁定 + 纯 wheel 筛选）
- L2：habluetooth 新版 .so 未签名坑 + HNP Python PYTHONPATH 怪癖
- L3：bleak 依赖边界实测（本版本解析层无需 bleak）
