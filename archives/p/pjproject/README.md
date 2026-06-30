# pjproject

## 软件简介

PJSIP是一个免费开源的多媒体通信库，使用C语言编写，实现了基于标准的协议，如SIP、SDP、RTP、STUN、TURN和ICE。它将信令协议（SIP）与丰富的多媒体框架和NAT穿越功能结合到高级API中，可移植并适用于从桌面、嵌入式系统到移动手机的几乎所有类型的系统。

## 功能特性

- **SIP协议栈**: 完整的SIP协议实现，包括SIP信令、SDP协商、事件订阅等
- **多媒体框架**: 音频/视频编解码、设备抽象、媒体传输
- **NAT穿越**: ICE、STUN、TURN协议实现
- **高级API**: PJSUA（C API）、PJSUA2（C++ API）简化应用开发
- **跨平台**: 支持 Linux、macOS、Windows、Android、iOS 等

## 编译版本

### 2.17 (2026-05-22)

**编译状态**: built  
**构建系统**: CMake  
**编译器**: Clang 15.0.4  

**功能限制**:
- ❌ SSL/TLS不可用（未安装OpenSSL）
- ❌ 音频设备受限（仅null audio）
- ❌ 视频设备受限（未安装SDL2/FFMPEG）
- ✅ 基础SIP通信可用
- ✅ 内置编解码器可用（G.711、G.722、Speex、iLBC）

**产物列表**:
- 13个静态库（libpjlib、libpjmedia、libpjsip等）
- pjsua-2.17可执行文件（命令行SIP客户端）
- CMake配置文件和pkg-config文件

## 使用说明

### 安装

从预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- pjproject 2.17
```

### 使用示例

```c
#include <pjsua-lib/pjsua.h>

int main() {
    pjsua_config ua_cfg;
    pjsua_acc_config acc_cfg;
    
    // 初始化PJSUA
    pjsua_create();
    pjsua_init(&ua_cfg, NULL, NULL);
    
    // 添加SIP账号
    pjsua_acc_add(&acc_cfg, PJ_TRUE, NULL);
    
    // 运行
    pjsua_start();
    
    return 0;
}
```

## 依赖关系

### 编译时依赖（可选）

| 依赖 | 版本 | 功能 | 状态 |
|------|------|------|------|
| openssl | 1.1+ | TLS/SSL支持 | ❌ 未安装 |
| alsa-lib | 1.0+ | 音频设备 | ❌ 未安装 |
| SDL2 | 2.0+ | 视频设备 | ❌ 未安装 |
| FFMPEG | 4.0+ | 视频编解码 | ❌ 未安装 |
| opus | 1.0+ | Opus编解码器 | ❌ 未安装 |

### 运行时依赖

- pthread（系统自带）
- librt（系统自带）
- libm（系统自带）

## 技术细节

### 构建系统

pjproject支持多种构建系统：
- **Autotools**: 传统构建系统（configure/make）
- **CMake**: 现代构建系统（推荐）
- **Makefile**: 简化构建（适用于快速开发）

### 平台适配

- ✅ 平台识别：aarch64-unknown-linux-ohos
- ✅ 编译器支持：Clang 15.0.4
- ⚠️ WebRTC模块：部分平台兼容性问题（已禁用）

## 许可证

GPL-2.0-or-later

## 参考资料

- [官方文档](https://docs.pjsip.org)
- [GitHub仓库](https://github.com/pjsip/pjproject)
- [编译指南](archives/p/pjproject/2.17/notes.md)

---

**维护者**: OpenHarmony Compile Agent  
**最后更新**: 2026-05-22