# ld2410-ble 0.2.0 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，poetry-core，`pip install . --prefix=<stage>` 安装到 site-packages）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（纯 Python 无 C 编译步骤；随 OHOS profile 填充以过 L0 settings 完整性门禁）
- 语言: python（lang-preflight 实测 detected=python，主体占比 91%）
- 状态: built

## 编译步骤

```bash
# conan create 由真机预检执行；配方内 build() 完成：
python3 -m pip install . --prefix=<stage>          # poetry-core + 运行时依赖由 pypi.cnb.cool 镜像解析
# 三层测试由 test_package 的 test() 执行：
python3 test_package/test_ld2410_ble.py      <site-packages>   # 消费者测试  → HMBS_TEST_PACKAGE_RESULT
python3 test_package/test_ld2410_ble_ohos.py <site-packages>   # 鸿蒙特有测试 → HMBS_OHOS_TEST_RESULT
python3 -m pytest test_package/tests/ -q --no-header -o addopts= -p no:cacheprovider  # 上游套件 → HMBS_UPSTREAM_TEST_RESULT
```

## 软件说明

ld2410-ble 是 HLK-LD2410B/LD2410C 24GHz 毫米波存在雷达的 BLE 客户端库（纯 Python、async）。
它通过 BLE 通知帧解析目标存在状态、移动/静止目标距离与能量、工程模式 8 个能量门，
不涉及任何 C/C++ 编译产物。上游仓库 `930913/ld2410-ble`，Apache-2.0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PyPI 官方 sdist 不含 tests/ 目录 | 官方发布物只打包 src/ld2410_ble/ 与元数据，无测试 | 源码改用 GitHub 官方 tag archive v0.2.0（含完整 tests/）；两个归档 sha256 分别实测核验，GitHub 版 `9ce3258…` 采用、PyPI 版 `25046e1…` 记录备查（见 conandata.yml） |
| 2 | 运行时依赖 bleak / bleak-retry-connector 未发布为 conan 配方 | 制品仓无这两个包配方（`async-timeout/5.0.1` 已发布，但同组依赖不齐会拆成 conan+pip 两条解析路径） | 遵循 airthings-ble / aiven-client 先例：统一 `pip install .` 由 pip 从 pypi.cnb.cool 镜像解析全部三个运行时依赖，装进同一 site-packages，配方不引入任何 C/C++ 编译依赖 |
| 3 | `platform.system()` 返回 `"HarmonyOS"`，bleak 只认 `"Linux"` | bleak 的 `get_default_backend()` 按 `platform.system() == "Linux"` 选择后端；OHOS 报 `BleakError: Unsupported platform: HarmonyOS` | 属平台缺口，不在配方内规避（不改上游、不 stub）：数据解码面在 OHOS 完整可用；由鸿蒙特有测试把该缺口显式探测并记录（`ohos_bleak_backend_probe` 断言平台名出现在报错中，Linux/OHOS 双结果均接受，保证 CI 主机亦绿） |
| 4 | bleak 的 `dbus-fast` 依赖在 HarmonyOS 上被 pip 跳过 | `dbus-fast` 的 wheel marker 为 `platform_system == "Linux"`，OHOS 下为 false | 属上游打包与平台标记问题；镜像虽提供 `dbus_fast-*-ohos_aarch64.whl`，但其 wheel tag（`ohos_aarch64`）与本机 pip 支持的 tag（`harmonyos_aarch64`）不匹配，无法经 marker 路径安装。不影响本次适配目标（纯 Python 安装 + 解码面） |
| 5 | 上游 pyproject `addopts` 带 coverage 相关项 | 上游配置了 pytest-cov | 运行测试时以 `-o addopts=` 覆盖，避免依赖未安装插件；并加 `-p no:cacheprovider` 规避只读/受限缓存目录 |

## 源码修改
无。上游源码零修改，`patches_applied: []`，上游 tests/ 原样复制进 test_package/tests/（逐字节一致）。

## 依赖版本

- 运行时 Python 依赖（配方不声明 conan requires，由 pip 从 pypi.cnb.cool 镜像解析）：
  - bleak >= 0.19.0（实测解析到 3.0.1）
  - bleak-retry-connector >= 2.3.0（实测解析到 4.6.1）
  - async-timeout >= 4.0.1（实测解析到 5.0.1；该包制品仓已有配方，但为保持解析路径单一仍走 pip）
- 测试依赖：pytest（CI 镜像若缺失则由 test_package 从镜像安装）

> 配方刻意不引入任何 C/C++ 编译依赖（任务要求）：纯 Python 库的安装不经过 C/C++ 工具链，
> 写入 settings 的 compiler/build_type 仅用于满足 CI L0 settings 完整性门禁，对 pip 安装为惰性字段。

## 验证结果

- 上游测试：1 个测试文件（tests/test_init.py）、1 个用例（`test_add`：`import ld2410_ble` 并断言包可导入）。上游套件规模极小，故本轮按任务要求补足新增测试。
- 新增消费者测试 test_ld2410_ble.py：43 项断言全部通过，覆盖真实 API（LD2410B/C 帧解析、目标状态位、移动/静止距离与能量、探测距离、工程模式 8 能量门 + 门访问器、回调注册/触发/注销、断开回调、分包缓冲重组、little-endian intify、常量线序契约、stop() 无客户端安全）。无需 BLE 硬件。
- 新增鸿蒙特有测试 test_ld2410_ble_ohos.py：20 项断言全部通过，覆盖 OHOS 运行时契约（`platform.system()==HarmonyOS`、`sys.platform` 属 OHOS 族 `linux|ohos`、aarch64 little-endian、包内无原生扩展、三依赖导入完整性、bleak backend 平台缺口探测、无硬件时 initialise 抛 bleak 错误而非崩溃）。
- 实测命令与数字见 `reports/test-report.md`。

## R40 适配完整性人工确认

本包属 R40 覆盖的外设/蓝牙域，需人工确认适配完整性口径：

- **已确认可用的适配面**：纯 Python 安装（无原生扩展，免 OHOS 原生工具链）+ LD2410B/C
  线序协议完整解码面（帧解析、目标状态位、移动/静止距离与能量、工程模式 8 能量门、
  回调机制），由 63 项新增断言在 OHOS 运行时实测通过。
- **已确认的平台缺口（非 stub 掩盖）**：OHOS 上 bleak 默认 BLE 传输后端不可解析
  （`get_default_backend()` 抛 `BleakError: Unsupported platform: HarmonyOS`，因 bleak
  只接受 `platform.system() == "Linux"`）。本仓库**不修改上游**、不写空壳 stub、不
  `return 0`/假成功；该缺口由鸿蒙特有测试 `ohos_bleak_backend_probe` 显式探测并在
  notes #3/#4 与 manifest `knowledge_gained` 中如实记录。
- **同类先例**：`archives/a/airthings-ble/1.2.0`（同为 BLE 纯 Python 库、同为该平台
  缺口，已合入 main）采用相同处置口径。
- **口径**：数据解码面适配完整；真实 BLE 连接需上游支持 HarmonyOS 平台，属上游/平台
  层面待办，不属本包适配缺陷。

## 注意事项

- 上游自述 `__version__` 为 `"0.0.0"`（未与包版本联动），属上游行为，未改动；测试只断言其为非空字符串。
- 全部测试离线运行，不连接真实 BLE 设备，可在无蓝牙环境完整执行。
- 包类型 `python-require`；`package_info()` 经 `runenv_info.append_path` 将 site-packages 暴露到 PYTHONPATH（libdirs/libs/includedirs 置空，因纯 Python 无 C 产物）。
---

**编译结束**: 2026-09-25 01:41
**最终状态**: built
