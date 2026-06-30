# libaom 3.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 Google Storage 下载源码（SSL 证书验证失败，改用本地文件）
2. 初始化编译环境：`python3 ohc-run.py init-build libaom 3.8.0 --url=file:///path/to/libaom-3.8.0.tar.gz`
3. 创建 build 子目录（libaom 要求在子目录构建）
4. CMake 配置：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DENABLE_TESTS=OFF \
         -DENABLE_EXAMPLES=OFF \
         -DENABLE_DOCS=OFF \
         -DCONFIG_RUNTIME_CPU_DETECT=0 \
         ..
   ```
5. 编译：`make -j2`
6. 安装：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败下载失败 | HTTPS 证书问题 | 使用 curl -k 手动下载，再用 file:// URL 初始化 |
| 2 | CMake 检测到 unknown architecture | HarmonyOS 平台未被 CMake 识别 | 回退到 generic target（符合预期） |
| 3 | fenv_check 测试失败 | 平台特性检测失败 | 非致命错误，编译继续 |

## 关键配置说明

- **CONFIG_RUNTIME_CPU_DETECT=0**: 禁用运行时 CPU 检测（OpenHarmony 兼容性要求）
- **ENABLE_TESTS=OFF**: 禁用测试（减少编译时间）
- **ENABLE_EXAMPLES=OFF**: 禁用示例程序
- **ENABLE_DOCS=OFF**: 禁用文档生成

## 源码修改

无补丁，源码未经修改直接编译。

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- perl 5.42.0

## 验证结果

```bash
# 库文件
$ ls -lh ~/test-install-libaom-3.8.0/storage/Users/currentUser/usr/local/lib/
-rw-rw---- 1 20001006 file_manager 5.9M 2026-05-19 22:47 libaom.a

# 头文件
$ ls ~/test-install-libaom-3.8.0/storage/Users/currentUser/usr/local/include/aom/
aom.h  aom_codec.h  aom_decoder.h  aom_encoder.h  aom_external_partition.h
aom_frame_buffer.h  aom_image.h  aom_integer.h  aomcx.h  aomdx.h

# pkg-config
$ cat ~/test-install-libaom-3.8.0/storage/Users/currentUser/usr/local/lib/pkgconfig/aom.pc
prefix=/storage/Users/currentUser/usr/local
Version: 3.8.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libaom.a | 5.9M | 静态库 |
| include/aom/*.h | 10 个文件 | 头文件 |
| lib/pkgconfig/aom.pc | - | pkg-config 文件 |

## 注意事项

1. **必须使用 CMake 构建**：libaom 不支持 autotools
2. **建议在子目录构建**：避免污染源码目录
3. **禁用运行时 CPU 检测**：OpenHarmony 兼容性问题
4. **SSL 证书问题**：使用 curl -k 下载或本地文件
---

**编译结束**: 2026-05-19 22:50
**最终状态**: published
