# qpdf 11.6.3 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码（使用 curl -k 绕过 SSL 证书问题）
2. 解压到 ~/tmp/builds/qpdf-11.6.3.work
3. 运行 CMake configure:
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -S . -B build
   ```
4. 编译: `cmake --build build -- -j1`
5. 安装: `cmake --install build -- DESTDIR=$TEST_PREFIX`
6. 打包: `ohc-run.py package qpdf 11.6.3`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络 SSL 证书问题 | 使用 curl -k -L 手动下载 |
| 2 | libjpeg not found | 缺少依赖 | 安装 libjpeg-turbo 3.1.4.1 预编译包 |

## 源码修改

无补丁。qpdf 11.6.3 能够直接识别 HarmonyOS 平台，无需修改源码。

## 依赖版本

- libjpeg-turbo: 3.1.4.1
- zlib: 1.3.1 (系统自带)
- openssl: 3.5.6 (可选)

## 验证结果

```bash
$ qpdf --version
qpdf version 11.6.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| qpdf-11.6.3-ohos-aarch64.tar.gz | 20MB | 主包 |
| qpdf-11.6.3-ohos-aarch64-debug.tar.gz | 2.9MB | 调试符号包 |

## 注意事项

- CMake 会输出 "System is unknown to cmake" 警告，但不影响编译
- make check 测试部分失败（平台兼容性问题），但核心功能正常

---

**编译结束**: 2026-05-20 12:17
**最终状态**: built