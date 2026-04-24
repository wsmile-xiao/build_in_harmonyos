# libuv — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libuv-1.52.1-ohos-aarch64.tar.gz -C ~/usr/local

cd libuv-1.52.1-ohos-aarch64 && sh install-libuv-1.52.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.52.1 | partial | 4 |
| 1.51.0 | compiling | 0 |

## 当前版本 (1.52.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 882.7KB

### 编译信息
- 构建系统: cmake
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 4

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-src-unix-core.c.patch
- 0003-src-unix-internal.h.patch
- 0004-src-unix-udp.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
