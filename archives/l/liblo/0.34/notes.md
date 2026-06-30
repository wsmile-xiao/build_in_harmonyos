# liblo 0.34 编译笔记

## 编译日期
2026-05-20

## 构建系统选择

### autotools 构建失败
- **问题**: configure 脚本在 HMDFS 文件系统上无法创建临时文件
- **错误信息**: `config.status: error: could not setup config files machinery`
- **根因**: HMDFS 文件系统上 `cat -` 命令输出到 stdout 时权限被拒绝
- **解决方案**: 切换到 cmake 构建系统

### cmake 构建成功
- cmake 4.1.2 在 HarmonyOS 上正常工作
- 仅出现警告 "System is unknown to cmake"，不影响编译
- 配置参数: `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`

---

## 关键问题及解决

### 问题 1: config.guess 不识别 HarmonyOS
- **现象**: `./config.guess: unable to guess system type`
- **解决**: 使用 `patch-autotools-ohos.pl` 补丁 config.guess 和 config.sub
- **知识图谱**: E007 (已有条目)

### 问题 2: config.sub 内核-操作系统组合验证失败
- **现象**: `Invalid configuration: Kernel 'linux' not known to work with OS 'ohos'`
- **解决**: 在 config.sub 的 kernel-os 组合列表中添加 `linux-ohos*`
- **修改位置**: 第 1781 行

### 问题 3: doxygen 缺失
- **现象**: `configure: error: doxygen not found`
- **解决**: 添加 `-DENABLE_DOXYGEN=OFF` 参数跳过文档生成

### 问题 4: 测试需要 LD_LIBRARY_PATH
- **现象**: 测试可执行文件找不到 liblo.so
- **解决**: 设置 `LD_LIBRARY_PATH=$STAGING_PREFIX/lib`
- **影响**: RPATH 问题，预编译包部署时需处理

---

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | 未修改源码 | 仅切换构建系统 | - |

说明：本次编译未修改任何源码文件，仅使用了 cmake 构建系统替代 autotools。

---

## 产物清单

### 可执行文件
- `oscdump` - OSC 消息 dump 工具 (27KB)
- `oscsend` - OSC 消息发送工具 (27KB)
- `oscsendfile` - OSC 文件发送工具 (31KB)

### 库文件
- `liblo.so` - OSC 共享库 (113KB)

### 头文件
- `lo/*.h` - 共 10 个头文件

### 配置文件
- `liblo.pc` - pkg-config 配置文件
- `libloConfig.cmake` - cmake 配置文件

---

## 质量门禁结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 干净构建 | ✓ 通过 | cmake 重新构建验证 |
| G1 二进制完整性 | ✓ 通过 | 所有二进制可执行 |
| G2 功能可用性 | ✓ 通过 | 测试 100% 通过 (9项) |
| G3 可移植性 | ✓ 通过 | 库符号完整 |
| G4 档案完整性 | ✓ 通过 | 必需文件齐全 |

---

## 知识提取

### 已复用知识
- E007: config.guess/config.sub HarmonyOS 支持

### 新发现（待评估）
- HMDFS 文件系统上 autotools 的 `cat -` 权限问题
- 建议：遇到 autotools configure 失败时优先尝试 cmake

---

---
**编译结束**: 2026-05-20 22:50
**最终状态**: 已编译 (built)
