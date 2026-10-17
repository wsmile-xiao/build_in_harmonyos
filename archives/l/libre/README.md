# libre

`libre`（上游项目 baresip/re，库名 `-lre`）是 baresip/rem 生态的实时通信基础库：
RTP/RTCP、SIP/SIPS、SDP、STUN/TURN/ICE、DNS-SD、定时器、内存池与线程抽象。

- 上游仓库：https://github.com/baresip/re
- 源码包：`v3.21.0.tar.gz`
  sha256 `ef4327eb46167bf91e91d2cf56214244d7c57b401f0f170a7cef7c1d65b48228`
- 许可证：BSD-3-Clause
- 构建系统：CMake（`cmake/re-config.cmake` 会无条件 `find_package(OpenSSL)`）
- 类型：共享库（`libre.so.31`，CMake 目标 `libre::libre`，pkg-config `libre`）
- 上游测试：`test/test.c` 两张注册表 —— `tests[]` 单元 197 项 + `tests_integration[]` 集成 15 项 = 212 项；
  `retest`（上游 `make test` 口径）执行单元表
- 依赖：`openssl/3.5.8.1`

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.21.0 | built | 首次适配 HarmonyOS PC (aarch64) |

## 适配要点

- `-D__MUSL__`：`src/net/linux/*.c` 经 `<linux/netlink.h>` 与 OHOS sysroot 的 `<sys/socket.h>` 争用
  `struct sockaddr_storage`（E091）。
- 平台源文件选择：conan 把 OHOS 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 既无对应 Platform 模块也不 set
  `UNIX`，上游 `elseif(UNIX)` / `MATCHES "Linux"` 分支被静默跳过，缺陷潜伏到链接期（`net_if_list` /
  `net_rt_list` undefined）。配方改走 Linux 分支并显式补 `UNIX`（E092 家族）。
- ELF 签名：OHOS 动态链接器要求 `.so` 已签名（E135），`package()` 内做 `llvm-objcopy --remove-section
  .codesign` + `binary-sign-tool -selfSign 1`。
- 补丁 `0001-test-unixsock-skip-ephemeral-EPERM.patch`：HMDFS 拒绝 `AF_UNIX bind()`（EPERM），
  `test_unixsock` 按上游 `ESKIPPED` 机制逐项申报跳过。

## 已知限制

- 15 项 `tests_integration[]` 网络集成用例不在 `make test` 默认口径内（需集成模式），已逐项列出、不从分母删除。
- `test_unixsock` 因 HMDFS 平台限制跳过（EPERM，非配方问题）。
