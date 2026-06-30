# OpenH264 2.4.1 编译笔记

## 编译时间
- 开始：2026-05-22 18:05
- 结束：2026-05-22 18:20

## 编译状态
✅ 成功

## 编译系统
- 构建系统：meson + ninja
- 编译器：clang 15.0.4
- 平台：HarmonyOS (aarch64)

## 遇到的问题和解决方案

### 问题 1：Meson 不识别 harmonyos 系统
**现象**：
```
meson.build:134:2: ERROR: Problem encountered: FIXME: Unhandled system harmonyos
```

**解决方案**：
修改 `meson.build` 文件，将 `harmonyos` 添加到支持的系统列表中：
```python
# 原代码
if ['linux', 'android', 'ios', 'darwin'].contains(system)

# 修改后
if ['linux', 'android', 'ios', 'darwin', 'harmonyos'].contains(system)
```

**原因**：
HarmonyOS 基于 Linux 内核，与 Linux 系统兼容，因此可以直接使用相同的配置。

### 问题 2：缺少 platform-harmonyos.mk 文件
**现象**：
```
Makefile:94: build/platform-harmonyos.mk: No such file or directory
```

**解决方案**：
创建 `build/platform-harmonyos.mk` 文件，使用 Linux 的 GNU-chain 配置：
```makefile
include $(SRC_PATH)build/arch.mk
include $(SRC_PATH)build/platform-gnu-chain.mk
```

## 编译产物

### 动态库
- `libopenh264.so.2.4.1` (3.3 MB)
- `libopenh264.so.7` (软链接)
- `libopenh264.so` (软链接)

### 头文件
- `codec_api.h`
- `codec_app_def.h`
- `codec_def.h`
- `codec_ver.h`

### 可执行文件
- `h264dec` (解码器)
- `h264enc` (编码器)

### pkg-config 文件
- `openh264.pc`

## 编译参数
```bash
meson setup builddir --prefix=/storage/Users/currentUser/usr/local
ninja -j2
ninja install
```

## 编译警告
编译过程中有多个 `-Wunused-but-set-variable` 警告，但不影响编译结果。

## 知识沉淀
- L1 平台真理：HarmonyOS 需要在 meson.build 中添加到支持的系统列表
- L2 模式经验：基于 Linux 的系统可以直接使用 platform-gnu-chain.mk 配置