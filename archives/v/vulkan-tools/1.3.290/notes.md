# vulkan-tools 1.3.290 编译笔记

## 编译环境
- **日期**: 2026-08-23
- **平台**: HarmonyOS (HongMeng Kernel 1.12.0)
- **编译器**: Clang 15.0.4
- **构建系统**: CMake 4.1.2

## 源码
- **下载 URL**: https://github.com/KhronosGroup/Vulkan-Tools/archive/refs/tags/vulkan-sdk-1.3.290.0.tar.gz
- **版本**: 1.3.290
- **SHA256**: 9d8a941f3cedd904774e888871840dd9b5df4de7682d741181b5c9af58a46420

## Conan 适配

### 依赖处理
vulkan-headers 和 volk 未发布到 Conan 制品仓，在 conanfile.py 内从源码构建：
- vulkan-headers: header-only, CMake install 生成 VulkanHeadersConfig.cmake
- volk: 静态 C 库 (volk.h + volk.c), CMake build + install 生成 volkConfig.cmake

### Conan 配方 (conanfile.py)
- package_type: application (包含可执行文件 vulkaninfo)
- 无 self.requires() — 依赖从源码构建
- R33: 编译器路径从 self.conf.get("tools.build:compiler_executables") 获取
- R39: 所有源码 URL 来自官方 GitHub 仓库

### test_package
- 执行 vulkaninfo --summary 验证二进制可运行
- 验证 Mock ICD 库 (libVkICD_mock_icd.so) 和 JSON 清单存在

## 编译步骤

### 1. 配置
```bash
cmake -B build -S . \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=<deps_install_dir> \
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
make install DESTDIR=<staging_dir>
```

## 问题与方案

### 问题1: CMake 平台识别失败
**解决方案**: 设置 `CMAKE_SYSTEM_NAME=Linux`

### 问题2: 缺少 xcb 依赖
**解决方案**: 禁用所有 WSI 支持 (HarmonyOS 无 X11/Wayland)

### 问题3: Mock ICD 未安装
**解决方案**: 启用 `INSTALL_ICD=ON`

### 问题4: vulkan-headers/volk 未发布到 Conan 制品仓
**解决方案**: 在 conanfile.py build() 内从源码构建并安装到临时前缀

## 编译产物
1. **vulkaninfo** (0.9M) — Vulkan 设备信息查询工具
2. **libVkICD_mock_icd.so** (306K) — Mock ICD 共享库
3. **VkICD_mock_icd.json** — Mock ICD 清单文件

## 运行验证
vulkaninfo --summary 在 HarmonyOS 设备上成功执行，
检测到 Vulkan 1.3 硬件 (VK_OHOS_surface 扩展)。

## 备注
- 未修改源码，仅使用 CMake 参数配置
- WSI 和 BUILD_CUBE 禁用是平台限制 (HarmonyOS 无 X11/Wayland)

---

**编译结束**: 2026-08-24 00:29
**最终状态**: built
