# ipsumdump 1.86 — 适配记录

## 编译过程

### 编译系统
- 构建系统: Autotools (configure + make)
- 编译器: clang 15.0.4
- 依赖: libpcap/1.10.6 (published)

### 补丁列表（全部由 conanfile.py build() 内联应用，无独立 .patch 文件）
- config.guess HarmonyOS 识别 (E007/E072)
- config.sub OHOS 三元组 + aarch64 机器类型 (E007/E072)
- SIOCGSTAMP 回退定义 (0x80108906)
- umask 077→022 (E002/E011, HMDFS)
- _IOC_DIRSHIFT 回退定义 (llrpc.h)
- install-man 禁用 (HMDFS 路径权限)

### 测试结果
- test_package: 1/1 通过 (100%)
- 上游测试: 0/0 (N/A)
- W3本地CI: 通过

## 最终状态
status: closed
---

**编译结束**: 2026-07-28 15:33
**最终状态**: built
