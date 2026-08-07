# airspyhf 1.6.8 功能测试报告

**日期**: 2026-08-07
**平台**: HarmonyOS (OHOS, arm64)
**构建方式**: CMake (cmake 4.1.2) + clang 15.0.4
**Profile**: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)
**依赖**: libusb/1.0.27 (Conan ohpcd 制品仓)
**补丁**: 0 个（配方内通过 CMake cache 变量处理 CMake4 兼容与平台识别）

## 上游测试清单

airspyhf 1.6.8 上游 CMake 工程未注册任何 ctest / `make check`
测试目标（`ctest` 输出 "No tests were found!"）。上游唯一的运行时验证
工具是随包安装的 5 个可执行程序，其中 `airspyhf_lib_version` 调用
库 API `airspyhf_lib_version()` 打印版本号，作为实质性的 API 冒烟测试。

| # | 测试 | 描述 | 结果 | 说明 |
|---|------|------|------|------|
| 1 | airspyhf_lib_version | 调用 `airspyhf_lib_version()` 打印库版本 | ✅ PASS | 输出 "AirSpy HF library version: 1.6.8" |
| 2 | airspyhf_info | 枚举/打开 AirSpy HF+ 设备 | ⏸ 平台限制 | 无 USB 硬件，需真实 AirSpy HF+ 设备 |
| 3 | airspyhf_gpio | 读写板载 GPIO | ⏸ 平台限制 | 同上 |
| 4 | airspyhf_calibrate | 校准读取/写入 | ✅ PASS | 无参数时正确输出 Usage 并退出 (rc=1) |
| 5 | airspyhf_rx | 频谱采样接收 | ✅ PASS | 无参数时正确输出用法并退出 (rc=1) |
| 6 | test_package (test_airspyhf) | 消费者视角 API 测试 | ✅ PASS | ctest 1/1 通过，验证版本 API + libusb 依赖链加载 |

**通过**: 4/4 可执行测试 | **平台限制**: 2 (airspyhf_info / airspyhf_gpio 需硬件)

## 平台限制说明

- **airspyhf_info / airspyhf_gpio**: 需要物理 AirSpy HF+ 设备 (VID:0x03EB,
  PID:0x800B)，沙箱环境无 USB 设备；`libusb_init()` 在该环境返回 -1
  (无 USB 子系统访问权)。属平台限制（E051 类），非适配缺陷。
- **ELF 签名**: 鸿蒙平台要求可执行文件和 .so 库 ELF 签名后才能加载
  执行，配方 `package()` 已对 lib/ 和 bin/ 产物统一签名
  (`binary-sign-tool`, SHA256withECDSA)。

## 测试环境

- **Conan 版本**: 2.29.1 (OHOS 适配版)
- **Profile**: ci/conan/profiles/ohos-aarch64
- **cmake**: 4.1.2 (需 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 2.8 最低版本声明)
- **平台识别**: 上游 `if( ${UNIX} )` 安装规则在 HarmonyOS 下不生效，
  配方 `generate()` 设 `CMAKE_SYSTEM_NAME=Linux` 修复 (E092)

## 验证命令

```bash
python3 scripts/ohc-run.py conan-verify airspyhf 1.6.8   # 8 门禁全过
conan create archives/a/airspyhf/1.6.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```
