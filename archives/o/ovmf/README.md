# ovmf — Open Virtual Machine Firmware（EDK II UEFI 固件）

OVMF 是 tianocore/edk2 提供的 UEFI 固件实现，用于 QEMU/KVM 等虚拟机启动。

- **上游**：https://github.com/tianocore/edk2
- **版本**：`0.0.202605`（对应 `edk2-stable202605` tag，commit `b03a21a63e3bd001f52c527e5a57feddb53a690b`）
- **许可证**：BSD-2-Clause-Patent
- **目标**：HarmonyOS PC（aarch64）的 QEMU UEFI 固件 `QEMU_EFI.fd`
  （`ArmVirtPkg/ArmVirtQemu.dsc`，工具链 `CLANGDWARF`）

## 产物
- `res/firmware/QEMU_EFI.fd` — AArch64 UEFI 固件映像（bare-metal，非宿主 ELF）

## 说明
OVMF 传统上指 `OvmfPkg`（X64/IA32）；本包因 HarmonyOS PC 为 aarch64，
构建其等价产物（`ArmVirtQemu` → `QEMU_EFI.fd`）。详见 `0.0.202605/notes.md`。

## 状态
`built` — 真机 shadow CI 100% 通过（2026-09-17）。
