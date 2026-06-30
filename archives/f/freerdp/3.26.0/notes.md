# freerdp 3.26.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

### 1. CMake 配置
```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DZLIB_LIBRARY=/storage/Users/currentUser/usr/local/lib/libz.a \
  -DZLIB_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include \
  -DOPENSSL_ROOT_DIR=/storage/Users/currentUser/usr/local \
  -DOPENSSL_CRYPTO_LIBRARY=/storage/Users/currentUser/usr/local/lib/libcrypto.so \
  -DOPENSSL_SSL_LIBRARY=/storage/Users/currentUser/usr/local/lib/libssl.so \
  -DOPENSSL_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include \
  -DWITH_FFMPEG=OFF \
  -DWITH_PCSC=OFF \
  -DWITH_CAIRO=OFF \
  -DWITH_SWSCALE=OFF \
  -DWITH_OPUS=OFF \
  -DWITH_WAYLAND=OFF \
  -DWITH_X11=OFF \
  -DWITH_KRB5=OFF \
  -DWITH_GSSAPI=OFF \
  -DWITH_UNICODE_BUILTIN=ON \
  -DWITH_CUPS=OFF \
  -DWITH_CHANNELS=OFF \
  -DWITH_FUSE=OFF \
  -DWITH_SERVER=OFF \
  -DWITH_SAMPLE=OFF \
  -DWITH_SHADOW=OFF \
  -DWITH_PROXY=OFF \
  -DWITH_PLATFORM_SERVER=OFF
```

### 2. 编译
```bash
cmake --build build -j2
```

### 3. Staging 安装 (DESTDIR 模式)
```bash
DESTDIR=/storage/Users/currentUser/tmp/test-install-freerdp-3.26.0 cmake --install build --prefix /storage/Users/currentUser/usr/local
```

### 4. 预编译包制作
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package freerdp 3.26.0 --prefix=$TEST_PREFIX/$DEFAULT_PREFIX
```

### 5. 本地安装
```bash
cmake --install build --prefix /storage/Users/currentUser/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 找不到 ZLIB | 预编译 zlib 未注册 pkg-config | 手动指定 `-DZLIB_LIBRARY` 和 `-DZLIB_INCLUDE_DIR` |
| 2 | CMake 找不到 OpenSSL | 预编译 openssl 未注册 pkg-config | 手动指定 `-DOPENSSL_ROOT_DIR` 等参数 |
| 3 | 缺少 FFmpeg | FFmpeg 是可选依赖 | 设置 `-DWITH_FFMPEG=OFF` |
| 4 | 缺少 Kerberos | krb5 库未安装 | 设置 `-DWITH_KRB5=OFF` |
| 5 | 缺少 ICU (CMake 错误) | ICU 是必需依赖（除非使用 builtin unicode） | 设置 `-DWITH_UNICODE_BUILTIN=ON` |
| 6 | 缺少 CUPS | CUPS 是可选依赖（打印机支持） | 设置 `-DWITH_CUPS=OFF` |
| 7 | 缺少 fuse3 | fuse3 是可选依赖（剪贴板 FUSE 文件复制） | 设置 `-DWITH_FUSE=OFF` |
| 8 | 缺少 libusb | urbdrc channel 需要 libusb | 设置 `-DWITH_CHANNELS=OFF` |
| 9 | server/Sample 链接失败 | channels 已禁用但 server 仍需要相关符号 | 设置 `-DWITH_SERVER=OFF` 禁用所有服务器功能 |
| 10 | 可执行文件 RPATH 问题 | CMake 生成的 RPATH 不正确 | 设置 LD_LIBRARY_PATH 后可运行，待修复 |

## 源码修改

无补丁，所有适配通过 CMake 参数完成。

## 依赖版本

- zlib: 1.3.1 (预编译包)
- openssl: 3.5.6 (预编译包)
- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

### 二进制文件验证
```bash
# 设置 LD_LIBRARY_PATH 后验证
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH

# winpr-makecert 验证
/storage/Users/currentUser/usr/local/bin/winpr-makecert --help
# 输出: makecert tool usage... (需要正确设置库路径)

# winpr-hash 验证
/storage/Users/currentUser/usr/local/bin/winpr-hash --help
# 输出: hash tool usage... (需要正确设置库路径)
```

### ⚠️ RPATH 问题
可执行文件的 RPATH 设置不正确，尝试从相对路径加载库：
- `../libwinpr-tools3.so`
- `../../libwinpr/libwinpr3.so`

这需要通过修改 CMake 配置或使用 patchelf 修复。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| freerdp-3.26.0-ohos-aarch64.tar.gz | 14.2MB | 预编译包 |
| freerdp-3.26.0-ohos-aarch64-debug.tar.gz | 2.9MB | 调试符号包 |

### 产物清单

**bin/ 目录:**
- winpr-hash (22KB)
- winpr-makecert (18KB)
- ⚠️ 无 xfreerdp（因为禁用了 X11 和 SDL 客户端）

**lib/ 目录:**
- libwinpr3.so (2.0MB) - Windows Portable Runtime
- libwinpr-tools3.so (43KB) - WinPR 工具库
- libfreerdp3.so (2.8MB) - FreeRDP 核心库
- libfreerdp-client3.so (231KB) - FreeRDP 客户端库

**include/ 目录:**
- winpr3/ - WinPR 头文件
- freerdp3/ - FreeRDP 头文件

## 注意事项

1. **客户端功能受限**: 由于禁用了 X11、Wayland、SDL，没有图形客户端（xfreerdp/sdl-freerdp）
2. **仅提供库文件**: 编译产物主要是库文件和开发工具，适合作为依赖库使用
3. **RPATH 待修复**: 可执行文件需要正确设置库路径才能运行
4. **依赖路径**: CMake 配置需要手动指定依赖路径，不适合自动化编译

---

**编译结束**: 2026-05-26 16:07
**最终状态**: built