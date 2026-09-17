# lib60870

## 简介

lib60870 是 MZ Automation 开源的 IEC 60870-5-101/104 电力远动（telecontrol）协议栈的纯 C 实现，支持 CS 101（串行/平衡链路）与 CS 104（TCP）主站/子站双角色，广泛用于电力 SCADA 系统与工控网关。

## OHOS 适配
- CMake 构建（工程位于源码包 `lib60870-C/` 子目录），无任何 conan 依赖（TLS 支持需 vendored mbedtls，默认关闭）
- E092：OHOS conan CMakeToolchain 将 CMAKE_SYSTEM_NAME 映射为 HarmonyOS，CMake 4.x 视为未知平台 → `UNIX` 未定义 → 上游 HAL 源文件选择分支为空；配方显式覆盖 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`，linux HAL（socket/poll/termios/clock_gettime）在 OHOS musl 上全部可用
- CMake 4.x 兼容：`CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 3.0）
- musl 无独立 librt；上游无条件 `-lrt` 实测可链接，无需 patch
- 上游产物为 `liblib60870.so` / `liblib60870.a`（CMake target 名与 OUTPUT_NAME 均为 lib60870），`cpp_info.libs = ["60870"]`
- 上游 Unity 测试套件（90 个非 TLS 用例）在 conan create 时真实执行，本机全 PASS

## 依赖
- 无编译依赖（可选 TLS 未启用）

## 功能验证
```bash
conan create archives/l/lib60870/2.4.0 -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=同 --build=missing
```

上游测试 90/90 PASS（31 个 TLS 用例随无 TLS 配置不编译，与上游 CI 行为一致）。

## 参考
- 主页: https://lib60870.com/
- 源码: https://github.com/mz-automation/lib60870
