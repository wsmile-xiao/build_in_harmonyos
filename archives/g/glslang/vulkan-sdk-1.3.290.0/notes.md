# glslang vulkan-sdk-1.3.290.0 编译笔记

## 编译环境

- **平台**: HarmonyOS (OpenHarmony)
- **构建系统**: CMake
- **编译器**: GCC
- **构建时间**: 2026-05-19

## 编译步骤

### Step 1: 初始化

- 下载源码: https://github.com/KhronosGroup/glslang/archive/refs/tags/vulkan-sdk-1.3.290.0.tar.gz
- 解压到: ~/tmp/builds/glslang-vulkan-sdk-1.3.290.0
- 构建目录: ~/tmp/builds/glslang-vulkan-sdk-1.3.290.0.work

### Step 2: 依赖检查

**已知依赖**:
- CMake >= 3.17.2
- spirv-tools (可选，用于 SPIR-V 优化)

**spirv-tools 检查**:
- 已安装在 ~/usr/local
- 通过 `-DALLOW_EXTERNAL_SPIRV_TOOLS=ON` 使用

### Step 3: 配置

**CMake 配置**:
```bash
mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DALLOW_EXTERNAL_SPIRV_TOOLS=ON \
  -DENABLE_OPT=ON \
  -DBUILD_SHARED_LIBS=OFF
```

### Step 4: 构建

```bash
make -j$(nproc)
```

### Step 5: 安装

```bash
make install DESTDIR=$TEST_PREFIX
```

## 问题记录

### 问题 1: [待填写]

**现象**:

**原因**:

**解决方案**:

## 知识提取

### [待填写]

## 测试结果

**功能测试**: [待填写]

**单元测试**: [待填写]

## 最终状态

**状态**: built

**产物**:
- 可执行文件: glslang (8.4 MB), spirv-remap (236 KB)
- 静态库: 7 个（libglslang.a, libSPIRV.a, libMachineIndependent.a 等）
- 预编译包: glslang-vulkan-sdk-1.3.290.0-ohos-aarch64.tar.gz (23 MB)

---

**编译结束**: 2026-05-19 19:25
**最终状态**: built
**门禁结果**: G1-G4 PASS
**补丁数**: 1
**预编译包大小**: 23 MB
---

**编译结束**: 2026-05-19 19:25
**最终状态**: built
