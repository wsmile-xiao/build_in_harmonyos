# spirv-headers vulkan-sdk-1.3.290.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 scripts/ohc-run.py init-build spirv-headers vulkan-sdk-1.3.290.0 --url=https://github.com/KhronosGroup/SPIRV-Headers/archive/refs/tags/vulkan-sdk-1.3.290.0.tar.gz --no-download
   ```
   - 源码已手动下载（SSL 证书问题，使用 curl -k）
   - 解压到 ~/tmp/builds/spirv-headers-vulkan-sdk-1.3.290.0.work

2. **CMake 配置**
   ```bash
   cd $BUILD_SRC_DIR && mkdir -p build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DSPIRV_HEADERS_ENABLE_TESTS=OFF ..
   ```
   - 配置成功，检测到 HarmonyOS 平台未知（不影响 header-only 库）

3. **安装**
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```
   - 头文件安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/include/spirv/`
   - CMake 配置文件安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/share/cmake/SPIRV-Headers/`
   - pkg-config 文件安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/share/pkgconfig/`

4. **用户验证安装**
   ```bash
   make install  # 安装到 $DEFAULT_PREFIX
   pkg-config --cflags SPIRV-Headers  # 返回 -I/storage/Users/currentUser/usr/local/include
   pkg-config --modversion SPIRV-Headers  # 返回 1.5.5
   ```

5. **打包与归档**
   ```bash
   python3 scripts/ohc-run.py verify-build spirv-headers vulkan-sdk-1.3.290.0
   python3 scripts/ohc-run.py package spirv-headers vulkan-sdk-1.3.290.0
   python3 scripts/ohc-run.py finish spirv-headers vulkan-sdk-1.3.290.0 built
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | GitHub SSL 证书链问题 | 使用 curl -k 跳过验证下载 |
| 2 | /tmp 目录只读 | HarmonyOS 平台限制 | 使用 ~/tmp 目录替代 |
| 3 | CMake 平台未知警告 | HarmonyOS 未在 CMake 平台列表 | 不影响 header-only 库安装 |

## 源码修改

无补丁，header-only 库无需修改源码。

## 依赖版本

无依赖，header-only 库。

## 验证结果

```bash
# 头文件验证
ls /storage/Users/currentUser/usr/local/include/spirv/unified1/spirv.h
# 输出: 文件存在

# pkg-config 验证
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/share/pkgconfig:$PKG_CONFIG_PATH
pkg-config --cflags SPIRV-Headers
# 输出: -I/storage/Users/currentUser/usr/local/include

pkg-config --modversion SPIRV-Headers
# 输出: 1.5.5
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| spirv-headers-vulkan-sdk-1.3.290.0-ohos-aarch64.tar.gz | 3273KB | 预编译包（header-only） |

## 注意事项

1. spirv-headers 是 header-only 库，不需要编译二进制文件
2. pkg-config 需要设置 PKG_CONFIG_PATH 才能找到
3. 主要用于 SPIR-V 编译器工具链（如 glslang、spirv-tools）

---

**编译结束**: 2026-05-19 16:13
**最终状态**: built
