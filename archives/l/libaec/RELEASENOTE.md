# libaec — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libaec-1.1.6-ohos-aarch64.tar.gz

cd libaec-1.1.6-ohos-aarch64 && sh install-libaec-1.1.6.sh
```

或使用软件级安装脚本：
```bash
sh install.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.1.6 | ✅ success | 0 |

## 当前版本 (1.1.6) 详情

### 包内容
- 库文件: libaec.so, libaec.a, libsz.so, libsz.a
- 头文件: libaec.h, szlib.h
- CMake 配置: libaec-config.cmake
- 包大小: 305KB (main) + 56KB (debug symbols)

### 编译信息
- 构建系统: CMake
- 编译器: Clang 15.0.4
- 目标: ohos-aarch64
- 质量门禁: PASS (G1-G4)
- 测试结果: 6/6 通过 (100%)
- 补丁数: 0

### 配置选项
```
-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
-DBUILD_SHARED_LIBS=ON
-DBUILD_STATIC_LIBS=ON
```

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 无外部依赖

## 使用说明
libaec 提供自适应熵编码功能（Golomb-Rice 算法），主要用于科学数据压缩。

- libaec: 主库，提供 aec_* API
- libsz: SZ 兼容库，提供 SZ 库兼容接口