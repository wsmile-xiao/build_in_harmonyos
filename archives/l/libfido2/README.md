# libfido2

## 简介

libfido2 是 Yubico 开源的 FIDO2/WebAuthn 客户端库，提供与 FIDO 认证器
（YubiKey 等）通过 USB HID/NFC 通信的功能，以及 attestation/assertion
签名验证。附带 fido2-token、fido2-assert、fido2-cred 三个命令行工具。

- 上游：https://github.com/Yubico/libfido2
- 许可证：BSD-2-Clause
- 语言：C（CMake 构建）

## OHOS 适配要点

- **libudev 缺失**：OHOS 无 libudev，patch 0004 提供 static-inline stub
  （全部函数返回 NULL/-1，禁用 udev 枚举路径）；HID 后端走 hid_linux.c
  （patch 0001/0002 将 HarmonyOS 路由到 Linux HID 后端）
- **ppoll**：OHOS musl 的 poll.h 有 ppoll 声明但需 `_GNU_SOURCE`
  （历史记录"ppoll 不可用"实为宏未定义所致）；patch 0003 保守保留
  `__OHOS__` 下 poll() 回退；配方 toolchain 补 `-D_GNU_SOURCE -D_DEFAULT_SOURCE`
- **SONAME**：上游 SOVERSION 属性在 conan CMakeToolchain 布局下不传
  `-Wl,-soname`，导致 tools 的 NEEDED 记为构建目录相对路径；配方注入
  `CMAKE_SHARED_LINKER_FLAGS="-Wl,-soname,libfido2.so"` 修复（详见 1.15.0/notes.md）
- **依赖**：libcbor/0.10.2、openssl/3.5.6（transitive_headers，fido.h 公开
  include openssl 头）、zlib/1.3.1——均来自制品仓 ohpcd

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.15.0 | built | W3 conan create 通过（7/7 上游 regress + consumer 测试） |
