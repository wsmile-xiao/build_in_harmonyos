# wavpack — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf wavpack-5.8.1-ohos-aarch64.tar.gz -C ~/usr/local

cd wavpack-5.8.1-ohos-aarch64 && sh install-wavpack-5.8.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 5.8.1 | partial | 8 |

## 当前版本 (5.8.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 731.2KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 8

### 补丁列表
- 0001-CMakeCache.txt.patch
- 0002-CPackConfig.cmake.patch
- 0003-CPackSourceConfig.cmake.patch
- 0004-cmake_install.cmake.patch
- 0005-wavpack-config-version.cmake.patch
- 0006-wavpack-config.cmake.patch
- 0007-libwavpack.map.patch
- 0008-config.guess.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
