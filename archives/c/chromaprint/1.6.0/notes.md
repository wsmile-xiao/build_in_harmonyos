# chromaprint 1.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 从 GitHub releases 下载源码 tarball
2. 解压并初始化编译环境
3. CMake 配置（使用内置 kissfft 和 avresample）:
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DFFT_LIB=kissfft \
         -DUSE_INTERNAL_AVRESAMPLE=ON \
         -DBUILD_SHARED_LIBS=ON \
         -DBUILD_TOOLS=OFF \
         -DBUILD_TESTS=OFF \
         ..
   ```
4. 编译: `make -j2`
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 预编译包制作: `ohc-run.py package chromaprint 1.6.0`
7. 本地安装验证: `make install`（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试程序链接失败 | 缺少 Google Test 符号 | 禁用测试（BUILD_TESTS=OFF）|
| 2 | SSL 下载失败 | 证书验证问题 | 使用 curl -k 手动下载 |
| 3 | manifest 缺少 build_system | 模板字段不完整 | 手动补充 build_system: cmake |

## 源码修改

无补丁，使用默认配置即可编译成功。

## 依赖版本

- 系统库: libc++_shared.so, libc.so
- 内置 KissFFT（无需外部依赖）
- 内置 avresample（无需外部 FFmpeg）

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion libchromaprint
1.6.0

# 库文件检查
ls -la ~/usr/local/lib/libchromaprint.so
-rwxrwx--- 1 20001006 file_manager 108992 2026-05-19 18:59 libchromaprint.so

# 动态链接依赖
NEEDED: libc++_shared.so, libc.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| chromaprint-1.6.0-ohos-aarch64.tar.gz | 137KB | 预编译包（ELF 签名）|
| chromaprint-1.6.0-ohos-aarch64-debug.tar.gz | 53KB | 调试符号包 |

## 注意事项

1. chromaprint 默认使用 FFmpeg 的 libswresample 进行音频格式转换，但我们使用内置 avresample 避免外部依赖
2. 如需构建 fpcalc 工具（BUILD_TOOLS=ON），需要安装 FFmpeg 预编译包
3. 测试套件依赖 Google Test，当前环境未安装，建议禁用测试
4. CMake 检测到"unknown system"（HarmonyOS），但不影响编译
---

**编译结束**: 2026-05-19 19:01
**最终状态**: built
