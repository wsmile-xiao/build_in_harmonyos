# zint 2.16.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码：`https://github.com/zint/zint/archive/refs/heads/master.tar.gz`
2. 解压源码到构建目录
3. 使用 CMake 配置：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DZINT_USE_PNG=OFF \
         -DZINT_USE_QT=OFF \
         ..
   ```
4. 编译：`make -j4`
5. 安装：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | RPATH 使用相对路径 ../backend/libzint.so | CMake 构建树链接行为 | 需要在打包时使用 patchelf 修复 |
| 2 | manifest.yaml build_system 错误 | init-build 自动检测为 autotools | 手动修正为 cmake |
| 3 | 缺少 PNG 和 Qt 支持 | 未安装相关依赖 | 禁用 PNG 和 Qt 支持 |

## 源码修改

### 0001-frontend-CMakeLists.txt.patch
修改 frontend/CMakeLists.txt，尝试设置 RPATH（但 CMake 的 NEEDED 字段仍使用相对路径）：
- 将 RPATH 设置从仅 Apple 平台扩展到所有非 Windows 平台
- 使用 BUILD_WITH_INSTALL_RPATH TRUE

## 依赖版本

- 无额外依赖（禁用了 PNG 和 Qt 支持）

## 验证结果

```bash
# 需要设置 LD_LIBRARY_PATH 才能运行
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
/storage/Users/currentUser/usr/local/bin/zint --version
# 或使用 patchelf 修复
patchelf --set-rpath /storage/Users/currentUser/usr/local/lib zint
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| zint-2.16.0-ohos-aarch64.tar.gz | 948KB | 预编译包（库 + 头文件） |
| zint-2.16.0-ohos-aarch64-debug.tar.gz | 69KB | Debug 符号包 |
| lib/libzint.so | 858KB | 共享库 |
| bin/zint | 80KB | CLI 工具（需修复 RPATH） |

## 注意事项

1. RPATH 问题：bin/zint 需要使用 patchelf 设置正确的 RPATH
2. 可选功能：如需 PNG 支持，需安装 libpng 并启用 -DZINT_USE_PNG=ON
3. CMake 平台警告：System unknown to cmake，建议创建 HarmonyOS 平台配置

---

**编译结束**: 2026-05-25 18:05
**最终状态**: built
