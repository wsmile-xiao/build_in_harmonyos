# vulkan-validationlayers vulkan-sdk-1.4.350.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build vulkan-validationlayers vulkan-sdk-1.4.350.0 --url=https://github.com/KhronosGroup/Vulkan-ValidationLayers/archive/refs/tags/vulkan-sdk-1.4.350.0.tar.gz`
2. 安装依赖到 $DEFAULT_PREFIX:
   - Vulkan-Headers v1.4.350 (cmake, 从源码编译安装)
   - SPIRV-Headers (commit ad9184e, 从源码编译安装)
   - Vulkan-Utility-Libraries (commit a96bd493, 从源码编译安装)
   - SPIRV-Tools-opt (已预装 v2026.2.1)
3. cmake 配置:
   ```bash
   cd $BUILD_SRC_DIR/build && cmake \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_SYSTEM_NAME=Linux \
     -DBUILD_WSI_XCB_SUPPORT=OFF \
     -DBUILD_WSI_XLIB_SUPPORT=OFF \
     -DBUILD_WSI_WAYLAND_SUPPORT=OFF \
     -DBUILD_TESTS=OFF \
     -DBUILD_WERROR=OFF \
     -DUPDATE_DEPS=OFF \
     ..
   ```
4. 编译: `make -j2`
5. 安装 staging: `make install DESTDIR=$TEST_PREFIX`
6. 安装本地: `make install` (到 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | UPDATE_DEPS 自动构建耗时过长 | update_deps.py 会从源码构建所有依赖 | 手动先编译安装所需依赖(Vulkan-Headers, SPIRV-Headers, Vulkan-Utility-Libraries)，然后设置 UPDATE_DEPS=OFF |
| 2 | Vulkan-Headers 版本不匹配 | 已安装版本为 v1.3.295，VVL 需要 v1.4.350 | 手动编译安装 Vulkan-Headers v1.4.350 |
| 3 | SPIRV-Headers 未安装 | 系统中缺少 SPIRV-Headers cmake config | 从 known_good.json 指定的 commit 编译安装 |
| 4 | 平台检测问题 | cmake 检测 OpenHarmony 平台无法识别 WSI 依赖 | 设置 CMAKE_SYSTEM_NAME=Linux 并禁用所有 WSI 支持 |
| 5 | 编译警告 -Werror | 默认启用 BUILD_WERROR 导致编译失败 | 设置 BUILD_WERROR=OFF |

## 源码修改

无源码修改。所有适配通过 cmake 参数完成。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Vulkan-Headers | v1.4.350 | 手动编译安装 |
| SPIRV-Headers | commit ad9184e | 手动编译安装 |
| Vulkan-Utility-Libraries | commit a96bd493 | 手动编译安装 |
| SPIRV-Tools-opt | 2026.2.1 | 预装 |
| SPIRV-Tools | 2026.2.1 | 预装 |

## 验证结果

```bash
# 检查编译产物
ls $DEFAULT_PREFIX/lib/libVkLayer_khronos_validation.so
# 输出: libVkLayer_khronos_validation.so (38MB)

# 检查 layer JSON
ls $DEFAULT_PREFIX/share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json
# 输出: VkLayer_khronos_validation.json
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libVkLayer_khronos_validation.so | ~38MB | Vulkan 验证层共享库 |
| VkLayer_khronos_validation.json | ~101KB | Layer manifest JSON |

## 注意事项

- VVL 需要与 Vulkan-Headers 版本严格匹配
- CMAKE_SYSTEM_NAME=Linux 是 OpenHarmony 上 cmake 项目平台检测的关键设置
- 禁用 WSI 支持是必要的，因为 OpenHarmony 不提供 XCB/Xlib/Wayland
- UPDATE_DEPS=OFF 模式需要所有依赖已预装到 $DEFAULT_PREFIX
- phmap (parallel hash map) 缺失是可选依赖，不影响编译
---

**编译结束**: 2026-05-28 12:21
**最终状态**: published
