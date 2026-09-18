# DRAFT: Python 级依赖未发布 conan 仓时的 pypi wheel vendor 闭包模式（BLE 解析库家族）

> 草稿条目 · 触发事件：kegtron-ble 1.0.2 适配 HarmonyOS PC（任务 #12803，2026-09-18）
> 关联 .kv：`knowledge/drafts/DRAFT-pypi-wheel-vendor-python-dep-closure.kv`

## 问题现象

适配 BLE 解析库家族包（Bluetooth-Devices/kegtron-ble 等 `*-ble` 系）时遇到三层连锁坑：

1. **依赖断链**：Python 级运行时依赖（sensor-state-data / bluetooth-data-tools /
   bluetooth-sensor-state-data / home-assistant-bluetooth）未发布到 ohpcd conan 仓
   ——主配方写 `requires` 会被 PF4 依赖闸拦截（R36 链断不连坐）
2. **最新版 .so 签名坑**：`pip install home-assistant-bluetooth` 解析到 2.0.0 →
   拖进 habluetooth>=4.0 → OHOS pypi 镜像只有 0.0.1/0.1.0/6.26.5 → 6.26.5 带
   `advertisement_tracker.cpython-312-aarch64-linux-ohos.so` **未签名不可
   dlopen**（`ImportError: Error loading shared library ... Permission denied`）
3. **HNP Python PYTHONPATH 怪癖**：设置 `PYTHONPATH` 后默认 sys.path[0]
   （`/data/storage/el2/base/files/interpreters/pip-global`）被移除——conan
   沙箱跑 pytest 时找到的 pytest 连带坏 hypothesis（`_native.abi3.so` 同样
   未签名）崩掉

## 根因

- OHOS conan 仓对 Python 生态覆盖不全；conan 与 pip 双包管理体系并存
- OHOS 平台 ELF 签名机制：pip 装的含 .so 包（habluetooth 6.x、hypothesis）
  未经 binary-sign-tool 签名，dlopen 被拒
- HNP Python 的 site 机制特殊：PYTHONPATH 覆盖而非追加默认 pip-global 路径

## 解决方案（可复用模式）

1. 主配方**不写 conan requires**——Python 级依赖在 notes.md/README 申报为
   pypi 依赖表
2. **版本组合以上游 lock 为准**（poetry.lock/uv.lock），不信 pip 最新解析：
   kegtron-ble 1.0.2 的 lock 组合 = sensor-state-data 2.19.0 /
   bluetooth-data-tools 0.3.1 / bluetooth-sensor-state-data 1.7.5 /
   home-assistant-bluetooth **1.4.0**（不依赖 habluetooth，纯 Python）
3. OHOS pypi 镜像直链 wheel URL 硬编码进配方 `_pypi_vendor()`
   （urllib 下载 + zipfile 解压），build() 上游测试与 test_package 消费
   验证共用同一 vendor 目录组装 PYTHONPATH
4. **pytest 五件套一并 vendor**（pytest/pluggy/iniconfig/packaging/pygments）
   ——干净环境绕开 pip-global 双坑
5. **bleak 边界实测**：解析层不依赖 bleak（移除后 import 链与 3 上游测试
   全过）——test_package 只验证解析路径即可，无需 BLE 硬件

## 上游测试实测（rule 4 申报）

- tests/test_parser.py：**3 用例，3/3 PASS（100%，0.09s）**——纯数据解析
  （构造 27 字节 manufacturer data 帧），无 BLE 硬件依赖

## 复用范围

- 所有 `*-ble` 解析库家族包（bthome-ble / qingping-ble / thermoplus-ble 等几十个同构包）
- 所有 Python 级依赖未发布 conan 仓的纯 Python 包
- 所有需要在 conan 沙箱里跑 pytest 的 Python 配方

## 验证命令

```bash
conan download sensor-state-data/2.19.0 -r=ohpcd --only-recipe  # 404 → 依赖未发布
grep -A2 'name = "home-assistant-bluetooth"' poetry.lock | head -4  # lock 锁定版本
PYTHONPATH=/path/to/vendor python3 -c "import home_assistant_bluetooth"  # vendor 闭包验证
conan create archives/k/kegtron-ble/1.0.2 --build=missing  # 全绿 + 3 passed
```
