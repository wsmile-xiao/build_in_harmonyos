# STLink 1.8.0 package for HarmonyOS PC

Conan 配方（v3.0）：`archives/s/stlink/1.8.0/conanfile.py`

- 构建系统: CMake
- 依赖: libusb/1.0.27（Conan ohpcd 制品仓）
- 产物: libstlink.so / libstlink.a、bin/st-flash、st-info、st-util、st-trace
- 验证: `python3 scripts/ohc-run.py conan-verify stlink 1.8.0`（G0-G4 + L2/L4/L5 全过）
