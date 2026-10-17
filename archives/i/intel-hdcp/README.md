# intel-hdcp — Intel Unified HDCP SDK

## 简介
intel-hdcp 是 Intel 发布的 HDCP（High-bandwidth Digital Content Protection，高带宽数字内容保护）SDK。
本仓库适配交付其 SDK 库形态：`libhdcpsdk.so` 共享库、`hdcpapi.h` 头文件与 `libhdcpsdk.pc`
pkg-config 文件，供上层应用管理 HDMI/DP 输出链路的 HDCP 认证与内容保护级别（HDCP_TYPES0/1、HDCP 2.2）。

## 版本
| 版本 | 上游 release | 上游 commit | 状态 |
|------|-------------|-------------|------|
| 21.2.0 | [intel-HDCP-21.2.0](https://github.com/intel/hdcp/releases/tag/intel-HDCP-21.2.0) | `cacc352159c5bdaf1c21846cecdd1eb7b031e1d3` | built |

## 适配说明
- 构建系统：CMake（强制 out-of-tree）。三个子工程：
  - `common/` — 静态库（socket 辅助层），配置期依赖 OpenSSL/Threads
  - `sdk/` — `libhdcpsdk.so` 共享库（API：HDCPCreate/HDCPDestroy/HDCPSetProtectionLevel/HDCPGetStatus 等）
  - `daemon/` — `hdcpd` 守护进程，依赖 Wayland/EGL 客户端头文件与 systemd，HarmonyOS 环境不可用，
    由补丁 `0001-optional-daemon.patch` 以 `HDCP_BUILD_DAEMON=OFF` 门控排除（SDK 库为交付物）
- 依赖：openssl/3.5.6（CMake 配置期 find_package(OpenSSL REQUIRED)）

## 使用知识库
- 参照库型 CMake 配方模板（conanfile-cmake）与 E416（conan slug 全小写）等既有知识