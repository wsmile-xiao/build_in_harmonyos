# libgxps 0.3.2 编译笔记

## 基本信息
- 软件: libgxps
- 版本: 0.3.2
- 描述: GNOME XPS 文档解析库
- 构建系统: Meson
- 源码: https://download.gnome.org/sources/libgxps/0.3/libgxps-0.3.2.tar.xz

## 编译环境
- 编译器: clang 15.0.4
- 构建工具: meson 1.11.1, ninja
- 平台: OpenHarmony aarch64

## 依赖
### 必需依赖
- glib-2.0 >= 2.36.0 (已安装: 2.88.0)
- cairo >= 1.10.0 (已安装: 1.18.4)
- libarchive >= 2.8.0 (已安装: 3.7.4)
- freetype2 (已安装: 26.6.20)

### 额外依赖（libarchive 传递依赖）
- OpenSSL (libcrypto) - 已安装 3.5.6
- lzma (liblzma) - 已安装 5.6.2
- bzip2 (libbz2) - 已安装 1.0.8

### 可选依赖（已禁用）
- lcms2 - 禁用
- libjpeg - 禁用
- libtiff - 禁用

## 编译过程

### 1. 下载源码
```bash
curl -k -L -o libgxps-0.3.2.tar.xz "https://download.gnome.org/sources/libgxps/0.3/libgxps-0.3.2.tar.xz"
```

### 2. 初始化编译
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libgxps 0.3.2 --url="file:///storage/Users/currentUser/tmp/libgxps-0.3.2.tar.xz"
```

### 3. Meson 配置
```bash
meson setup build --prefix=~/usr/local \
    -Dwith-liblcms2=false \
    -Dwith-libjpeg=false \
    -Dwith-libtiff=false \
    -Denable-test=false \
    -Ddisable-introspection=true
```

### 4. 编译问题与解决

#### 问题1: libarchive 依赖传递
- **现象**: meson 配置成功但链接失败，缺少 lzma_end, BZ2_bzDecompressEnd 等符号
- **原因**: libarchive.pc 声明了 Libs.private: -llzma -llz4 -lbz2 -lz，但 meson 不处理 Libs.private
- **解决**: 手动链接时添加 lzma.a 和 bz2.a

#### 问题2: libpng NEON 符号
- **现象**: undefined reference to png_riffle_palette_neon 等
- **原因**: libpng.so 中引用了 NEON 函数但未定义
- **解决**: 移除 --no-undefined，添加 --allow-shlib-undefined

### 5. 手动链接命令
```bash
# 链接共享库
cc -shared -fPIC -o libgxps/libgxps.so.2.2.4 \
    libgxps/libgxps.so.2.2.4.p/*.o \
    -Wl,-soname,libgxps.so.2 \
    -Wl,-rpath,/storage/Users/currentUser/usr/local/lib \
    ... (各种静态库) \
    /storage/Users/currentUser/usr/local/lib/libarchive.a \
    /storage/Users/currentUser/usr/local/lib/liblzma.a \
    /storage/Users/currentUser/usr/local/lib/libbz2.a

# 链接 xpstopng
cc -o tools/xpstopng \
    tools/xpstopng.p/*.o \
    -Wl,-rpath,/storage/Users/currentUser/usr/local/lib \
    -Wl,--allow-shlib-undefined \
    ... (各种库)
```

### 6. 安装
```bash
# 复制库文件
cp build/libgxps/libgxps.so.2.2.4 ~/usr/local/lib/
ln -sf libgxps.so.2.2.4 ~/usr/local/lib/libgxps.so.2
ln -sf libgxps.so.2 ~/usr/local/lib/libgxps.so

# 复制头文件
cp libgxps/gxps.h ~/usr/local/include/libgxps/
cp build/libgxps/gxps-version.h ~/usr/local/include/libgxps/

# 复制工具
cp build/tools/xpstopng ~/usr/local/bin/

# 创建 pkg-config 文件
cat > ~/usr/local/lib/pkgconfig/libgxps.pc << 'EOF'
prefix=/storage/Users/currentUser/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: libgxps
Description: XPS document library
Version: 0.3.2
Requires: glib-2.0 cairo libarchive freetype2 libpng
Cflags: -I${includedir}/libgxps
Libs: -L${libdir} -lgxps
EOF
```

## 安装结果
- 库文件: ~/usr/local/lib/libgxps.so.2.2.4 (15MB)
- 头文件: ~/usr/local/include/libgxps/gxps.h, gxps-version.h
- pkg-config: ~/usr/local/lib/pkgconfig/libgxps.pc
- 工具: ~/usr/local/bin/xpstopng

## 验证
```bash
pkg-config --modversion libgxps
# 输出: 0.3.2
```

## 注意事项
1. xpstopng 工具存在运行时共享库加载问题
2. 建议后续改进：将工具编译为静态可执行文件
3. libarchive 的传递依赖需要在所有使用它的项目中手动处理

---
**编译结束**: 2026-05-21
**最终状态**: built（编译成功，库可用）