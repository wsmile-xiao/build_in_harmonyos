# libxmp 4.6.0 编译记录

## 编译信息
- **软件**: libxmp
- **版本**: 4.6.0
- **日期**: 2026-05-22
- **编译者**: openharmony-compile-agent

## 编译过程

### 1. 源码下载
- URL: https://github.com/libxmp/libxmp/releases/download/libxmp-4.6.0/libxmp-4.6.0.tar.gz
- 使用 curl 手动下载（自动下载超时）

### 2. 构建系统选择
- 原计划使用 autotools (configure)
- 遇到问题：
  - E007: config.guess 无法识别 HarmonyOS 系统
  - configure 执行时权限问题（HMDFS 限制）
- 改用 CMake 构建（libxmp 支持 CMake）

### 3. 补丁应用
- 使用 patch-autotools-ohos.pl 补丁 config.guess 和 config.sub
- 手动修改 config.sub 内核验证部分添加 linux-ohos*

### 4. CMake 构建
```bash
cmake ../libxmp-4.6.0.work \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j4
```

### 5. 安装
- 静态库: libxmp.a
- 动态库: libxmp.so (已签名)
- 头文件: xmp.h

## 遇到的问题

### E007: config.guess 无法识别 HarmonyOS
- **触发**: configure 阶段
- **错误**: `cannot guess build type; you must specify one`
- **解决**: 使用 patch-autotools-ohos.pl 补丁脚本
- **验证**: config.guess 输出 `aarch64-unknown-linux-ohos`

### 内核验证错误
- **触发**: configure 阶段
- **错误**: `Kernel 'linux' not known to work with OS 'ohos'`
- **解决**: 修改 config.sub 第 1780-1782 行添加 linux-ohos*

### configure 权限问题
- **触发**: config.status 执行
- **错误**: `can't create ./confjmVgkg/subs1.awk: Permission denied`
- **原因**: HMDFS 文件系统限制
- **解决**: 改用 CMake 构建

## 知识沉淀

### L1 平台真理
- libxmp 支持 CMake 构建
- CMake 在 HarmonyOS 上需要 CMAKE_POLICY_VERSION_MINIMUM 参数处理版本兼容性

### L2 模式经验
- autotools 项目遇到 HMDFS 权限问题可考虑 CMake 替代方案
- 补丁脚本已处理大部分 autotools 适配问题

## 编译状态
- **最终状态**: 成功
- **产物**: libxmp.so, libxmp.a, xmp.h
- **质量门禁**: 全部通过