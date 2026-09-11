# ktx-software 4.4.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (Clang 15.0.4)
- 平台: HarmonyOS (OHOS) aarch64
- 状态: built

## 编译步骤

```bash
cmake . -B build-ohos \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DKTX_FEATURE_TESTS=OFF \
  -DKTX_FEATURE_LOADTEST_APPS=OFF \
  -DKTX_FEATURE_DOC=OFF \
  -DKTX_FEATURE_JNI=OFF \
  -DKTX_FEATURE_PY=OFF \
  -DKTX_FEATURE_TOOLS=ON \
  -DKTX_FEATURE_GL_UPLOAD=OFF \
  -DKTX_FEATURE_VK_UPLOAD=OFF \
  -DKTX_GIT_VERSION_FULL=v4.4.2
cmake --build build-ohos -j$(nproc)
cmake --install build-ohos --prefix $TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 提示 "System is unknown" | CMake 无 OHOS 平台定义 | 非致命警告，不影响编译 |
| 2 | test_package 链接失败 (operator new/delete undefined) | C 程序链接含 C++ 的 libktx.a 缺少 libc++ | package_info 添加 system_libs=[c++, dl, pthread, m] |
| 3 | CI L0d: test() 无 self.run() | cmake.test() 不被识别 | 改用 self.run() 直接执行测试二进制 |
| 4 | 版本字符串显示 exitcode-128-NOTFOUND | mkversion 脚本在 Conan 环境中 git describe 失败 | 非致命，不影响库功能 |

## 源码修改

无补丁。ktx-software 在 OHOS 上原生兼容：
- OHOS clang 定义 `__linux__` → Linux 代码路径（dlopen/dlsym）自动生效
- OHOS clang 定义 `__aarch64__` → ASTC 编码器 NEON 后端自动启用
- 所有依赖内置（basisu/astc-encoder/zstd/miniz），无外部依赖

## 依赖版本

无外部依赖。所有第三方库已内置在源码中。

## 验证结果

```bash
$ ktx --version
ktx version: exitcode-128-NOTFOUND   # 版本字符串问题，非致命

$ file bin/ktx
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ readelf -d bin/ktx | grep FLAGS
BIND_NOW / NOW PIE  # Full RELRO + PIE

$ llvm-nm lib/libktx.a | grep ' T ' | wc -l
982   # 982 个公开符号

# Conan verify: G0-G4 + L2/L4/L5 全部 PASS
# W3 本地 CI 模拟: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libktx.a | 2.7MB | 主库（静态），含 KTX 读写、BasisU 转码、ASTC 编码 |
| lib/libastcenc-neon-static.a | 227KB | ASTC 编码器（NEON 加速） |
| bin/ktx | — | 通用 KTX2 管理工具 |
| bin/toktx | — | 从 PNG/JPEG 创建 KTX 文件 |
| bin/ktxinfo | — | 显示 KTX 文件信息 |
| bin/ktxsc | — | KTX2 超压缩工具 |
| bin/ktx2check | — | KTX2 格式验证 |
| bin/ktx2ktx2 | — | KTX1 转 KTX2 转换器 |
| include/ktx.h | — | 主头文件 |
| include/ktxvulkan.h | — | Vulkan 纹理上传接口 |
| include/KHR/khr_df.h | — | Khronos 数据格式头文件 |

## 注意事项

- KTX_FEATURE_GL_UPLOAD 和 KTX_FEATURE_VK_UPLOAD 默认关闭，因为 OHOS 可能无 OpenGL/Vulkan 运行时。如需启用，使用动态加载（dlopen），不会导致链接错误
- 版本字符串 "exitcode-128-NOTFOUND" 是 mkversion 脚本在非 git 环境下的已知行为，不影响库功能
- R40 适配完整性：KTX-Software 是纹理格式库（非图形渲染/UI 框架），核心功能（KTX 读写、BasisU 转码、ASTC 编码）不依赖特定 GPU API。GL/VK 上传功能通过 dlopen 动态加载，按需启用

---

**编译结束**: 2026-09-01 20:30
**最终状态**: built
