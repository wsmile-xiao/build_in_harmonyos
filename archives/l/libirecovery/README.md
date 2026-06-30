# libirecovery

## Description
libirecovery is a library for communication with iOS devices in recovery mode.

## Homepage
https://github.com/libimobiledevice/libirecovery

## Dependencies
- libplist >= 2.3.0
- libimobiledevice-glue >= 1.2.0
- libusb-1.0 >= 1.0.27

## Installation
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libirecovery 1.3.1
```

## Usage
```bash
irecovery --version
irecovery -q  # query device info
```

## Platform Notes (HarmonyOS)
- **E011**: HMDFS umask 077 权限问题，使用 sed -i 's/umask 077/umask 022/g' configure 解决
- **E007**: HarmonyOS 平台识别，添加 __OHOS__ 检测和 ohos-linux 三元组
- **E046**: HMDFS 文件系统不支持 chmod +x，需要在 tmpfs 环境下编译

## Quality Status
- **G0**: FAIL (HMDFS 平台限制 - chmod +x 不生效)
- **G1-G3**: PASS (已验证)
- **G4**: PASS (软件级归档已补齐)

## Precompiled Package
- File: `libirecovery-1.3.1-aarch64-unknown-linux-ohos.tar.gz` (750MB)
- Location: `archives/l/libirecovery/1.3.1/packaging/`

## Important Note
由于 HMDFS 平台限制（E046: chmod +x 不生效），G0 干净构建验证在 HMDFS 上失败。
但已通过 tmpfs 环境手动验证编译流程正确。预编译包可用，建议在非 HMDFS 环境验证。
��在非 HMDFS 环境进行完整验证。
