# vulkan-tools 1.3.290 编译笔记

## 编译环境
- **日期**: 2026-05-21
- **平台**: HarmonyOS (HongMeng Kernel 1.12.0)
- **编译器**: Clang 15.0.4
- **构建系统**: CMake 4.1.2

## 源码
- **下载 URL**: https://github.com/KhronosGroup/Vulkan-Tools/archive/refs/tags/vulkan-sdk-1.3.290.0.tar.gz
- **版本**: 1.3.290

## 编译步骤

### 1. 配置
```bash
cmake -B build -S . \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DBUILD_CUBE=OFF \
  -DBUILD_WSI_XCB_SUPPORT=OFF \
  -DBUILD_WSI_XLIB_SUPPORT=OFF \
  -DBUILD_WSI_WAYLAND_SUPPORT=OFF \
  -DBUILD_WSI_DIRECTFB_SUPPORT=OFF \
  -DINSTALL_ICD=ON
```

### 2. 编译
```bash
cd build && make -j2
```

### 3. 安装
```bash
make install DESTDIR=/storage/Users/currentUser/tmpexport/test-install-vulkan-tools-1.3.290
```

## 问题与方案

### 问题1: CMake 平台识别失败
**解决方案**: 设置 `CMAKE_SYSTEM_NAME=Linux`

### 问题2: 缺少 xcb 依赖
**解决方案**: 禁用所有 WSI 支持

### 问题3: Mock ICD 未安装
**解决方案**: 启用 `INSTALL_ICD=ON`

## 编译产物
1. **vulkaninfo** (0.9M)
2. **libVkICD_mock_icd.so** (306K)
3. **VkICD_mock_icd.json**

## 备注
- 未修改源码，仅使用 CMake 参数配置