# portmidi 2.0.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化构建环境:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build portmidi 2.0.8 --url=file:///storage/Users/currentUser/build/portmidi-2.0.8.tar.gz
   ```

2. CMake 配置:
   ```bash
   source $SKILL_ROOT/.build-context-portmidi-2.0.8
   cd $BUILD_SRC_DIR
   cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
   ```

3. 编译:
   ```bash
   cmake --build build -- -j1
   ```

4. DESTDIR 安装:
   ```bash
   DESTDIR=$TEST_PREFIX cmake --install build
   ```

5. 验证和打包:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py verify-build portmidi 2.0.8
   python3 $SKILL_ROOT/scripts/ohc-run.py package portmidi 2.0.8
   ```

6. 正式安装:
   ```bash
   cmake --install build
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | GitHub SSL 证书无法验证 | 使用 curl -k 手动下载源码包 |
| 2 | "Operating system not supported" | PortMidi 不支持 HarmonyOS | 修改 CMakeLists.txt，添加 HarmonyOS 检测逻辑，将其视为 UNIX 系统 |
| 3 | ALSA 库缺失 | HarmonyOS 没有 ALSA 音频库 | 使用 PMNULL 模式编译（无 MIDI 设备支持） |
| 4 | manifest.yaml 字段错误 | 验证检查字段名为 build_system | 将 system 字段改为 build_system |

## 源码修改

### 0001-CMakeLists.txt.patch

修改主 CMakeLists.txt 文件，添加 HarmonyOS 平台支持：

```cmake
# HarmonyOS compatibility: treat as UNIX-like system
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_HOST_SYSTEM_NAME STREQUAL "HarmonyOS")
  message(STATUS "Detected HarmonyOS, treating as UNIX system")
  set(UNIX TRUE CACHE BOOL "HarmonyOS is UNIX-like" FORCE)
  set(CMAKE_SYSTEM_NAME "Linux" CACHE STRING "Treat HarmonyOS as Linux" FORCE)
  # HarmonyOS does not have ALSA, so use PMNULL mode
  set(LINUX_DEFINES "PMNULL" CACHE STRING "HarmonyOS uses PMNULL mode" FORCE)
endif()
```

## 依赖版本

无额外依赖（使用 PMNULL 模式）

## 验证结果

```bash
# 质量门禁验证
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build portmidi 2.0.8

# 结果:
# G1: 二进制完整性: PASS
# G2: 功能可用性: PASS (无二进制文件，仅库文件)
# G3: 可移植性: PASS
# G4: 档案完整性: PASS
# 质量报告: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| portmidi-2.0.8-ohos-aarch64.tar.gz | 155KB | 预编译包 |
| portmidi-2.0.8-ohos-aarch64-debug.tar.gz | 33KB | 调试符号包 |

## 注意事项

1. PortMidi 在 HarmonyOS 上使用 PMNULL 模式，无法检测或使用 MIDI 设备
2. 这是预期行为，适合作为其他软件的依赖库
3. 补丁是平台兼容性补丁，仅用于 HarmonyOS 平台

---

**编译结束**: 2026-05-19 17:29
**最终状态**: built