#!/usr/bin/env python3
"""verify_rom.py — VGA Option ROM 结构校验器（vgabios test_package 断言助手）。

对 vgabios 产出的 8086 Option ROM 镜像做离线结构校验，全部依据公开的
PCI Firmware Spec（PCIR 结构）与 x86 Option ROM 约定：

  * 0x55 0xAA                    —— x86 Option ROM 签名字节
  * data[2]                      —— ROM 长度（单位 512 字节）
  * data[2]*512 字节求和 ≡ 0 mod 256 —— ROM 校验和（biossums 写入）
  * data[0x18..0x19]             —— PCIR 结构指针（小端，PCI BIOS 镜像）
  * "PCIR" @ 指针                —— PCI 数据结构的 magic
  * PCIR +0x04                   —— Vendor ID / Device ID（小端）
  * PCIR +0x10                   —— Image Length（单位 512 字节）

用法（退出码 0 = 断言成立；1 = 断言失败；2 = 用法错误）：
    verify_rom.py signature  <rom>
    verify_rom.py checksum   <rom>
    verify_rom.py sizefield  <rom>
    verify_rom.py pcir       <rom> <vendor_hex> <device_hex>
    verify_rom.py contains   <rom> <ascii>
    verify_rom.py not-contains <rom> <ascii>
    verify_rom.py bytes-at   <rom> <offset_hex> <hexbytes>
    verify_rom.py psig       <rom>          # 打印 PCIR 摘要（调试）
    verify_rom.py elf-ohos   <bin>          # ELF64 / 小端 / AArch64（鸿蒙原生产物）
"""
from __future__ import annotations

import struct
import sys

ROM_SIG = b"\x55\xaa"


def _load(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _fail(msg: str) -> int:
    print(f"   ! {msg}")
    return 1


def cmd_signature(path: str) -> int:
    data = _load(path)
    if len(data) < 4:
        return _fail(f"{path}: 文件过短（{len(data)} 字节）")
    if data[:2] != ROM_SIG:
        return _fail(f"{path}: 缺少 0x55AA Option ROM 签名（实际 {data[:2].hex()}）")
    print(f"   0x55AA 签名 OK（off=0），ROM 长度字节 data[2]={data[2]} → {data[2] * 512} 字节")
    return 0


def cmd_checksum(path: str) -> int:
    data = _load(path)
    size = data[2] * 512
    if size == 0 or size > len(data):
        return _fail(f"{path}: data[2]={data[2]} 给出的 ROM 长度 {size} 超出文件（{len(data)}）")
    total = sum(data[:size]) & 0xFF
    if total != 0:
        return _fail(f"{path}: ROM 校验和不为 0（前 {size} 字节求和 = 0x{total:02X}）")
    print(f"   checksum OK：前 {size} 字节求和 mod 256 = 0")
    return 0


def cmd_sizefield(path: str) -> int:
    data = _load(path)
    declared = data[2] * 512
    if declared != len(data):
        return _fail(f"{path}: data[2]*512={declared} 与文件大小 {len(data)} 不一致")
    print(f"   长度字段 OK：data[2]={data[2]} → {declared} 字节 == 文件大小")
    return 0


def _pcir_offset(data: bytes) -> int | None:
    if len(data) < 0x1A:
        return None
    off = struct.unpack_from("<H", data, 0x18)[0]
    if off + 24 > len(data):
        return None
    return off if data[off:off + 4] == b"PCIR" else None


def cmd_pcir(path: str, vendor_hex: str, device_hex: str) -> int:
    data = _load(path)
    off = _pcir_offset(data)
    if off is None:
        return _fail(f"{path}: 未找到合法的 PCIR 数据结构（指针 @0x18 或 magic 不符）")
    vendor, device = struct.unpack_from("<HH", data, off + 4)
    imagelen = struct.unpack_from("<H", data, off + 0x10)[0]
    if vendor != int(vendor_hex, 16):
        return _fail(f"{path}: PCIR Vendor ID=0x{vendor:04X} != 期望 0x{int(vendor_hex, 16):04X}")
    if device != int(device_hex, 16):
        return _fail(f"{path}: PCIR Device ID=0x{device:04X} != 期望 0x{int(device_hex, 16):04X}")
    if imagelen * 512 != len(data):
        return _fail(f"{path}: PCIR Image Length={imagelen} → {imagelen * 512} != 文件大小 {len(data)}")
    print(f"   PCIR@{off} OK：Vendor=0x{vendor:04X} Device=0x{device:04X} ImageLen={imagelen}")
    return 0


def cmd_psig(path: str) -> int:
    data = _load(path)
    off = _pcir_offset(data)
    if off is None:
        return _fail(f"{path}: 无 PCIR")
    vendor, device = struct.unpack_from("<HH", data, off + 4)
    cls = data[off + 0x0D:off + 0x10].hex()
    imagelen = struct.unpack_from("<H", data, off + 0x10)[0]
    print(f"   PCIR@{off} vendor=0x{vendor:04X} device=0x{device:04X} class=0x{cls} imagelen={imagelen}")
    return 0


def cmd_contains(path: str, needle: str) -> int:
    data = _load(path)
    if needle.encode("latin1") not in data:
        return _fail(f"{path}: 未包含字符串 {needle!r}")
    print(f"   包含 {needle!r} OK")
    return 0


def cmd_not_contains(path: str, needle: str) -> int:
    data = _load(path)
    if needle.encode("latin1") in data:
        return _fail(f"{path}: 不应包含字符串 {needle!r}，但出现了")
    print(f"   不含 {needle!r} OK")
    return 0


def cmd_bytes_at(path: str, offset_hex: str, hexbytes: str) -> int:
    data = _load(path)
    off = int(offset_hex, 16)
    want = bytes.fromhex(hexbytes)
    got = data[off:off + len(want)]
    if got != want:
        return _fail(f"{path}: off 0x{off:X} 期望 {want.hex()}，实际 {got.hex()}")
    print(f"   off 0x{off:X} == {want.hex()} OK")
    return 0


def cmd_elf_ohos(path: str) -> int:
    """产物必须为 ELF64、小端、AArch64（HarmonyOS PC 目标架构）。"""
    data = _load(path)
    if data[:4] != b"\x7fELF":
        return _fail(f"{path}: 不是 ELF（magic {data[:4].hex()}）")
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 0x12)[0]
    if ei_class != 2:
        return _fail(f"{path}: 非 ELF64（EI_CLASS={ei_class}）")
    if ei_data != 1:
        return _fail(f"{path}: 非小端（EI_DATA={ei_data}）")
    if e_machine != 0xB7:
        return _fail(f"{path}: 非 AArch64（e_machine={e_machine:#x}）")
    print("   ELF64 / little-endian / AArch64 OK")
    return 0


_DISPATCH = {
    "signature": (1, cmd_signature),
    "checksum": (1, cmd_checksum),
    "sizefield": (1, cmd_sizefield),
    "pcir": (3, cmd_pcir),
    "psig": (1, cmd_psig),
    "contains": (2, cmd_contains),
    "not-contains": (2, cmd_not_contains),
    "bytes-at": (3, cmd_bytes_at),
    "elf-ohos": (1, cmd_elf_ohos),
}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in _DISPATCH:
        print(__doc__)
        return 2
    argc, func = _DISPATCH[argv[1]]
    args = argv[2:]
    if len(args) != argc:
        print(f"usage: verify_rom.py {argv[1]} " + "<rom> " * argc, file=sys.stderr)
        return 2
    return func(*args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
