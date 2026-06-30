# libxlsxwriter 1.2.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-22
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 1. 初始化构建环境
```bash
python3 ohc-run.py init-build libxlsxwriter 1.2.4
```

### 2. 配置 CMake（关键步骤）
```bash
export ZLIB_ROOT="$HOME/usr/local"
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
cd $BUILD_SRC_DIR
rm -rf CMakeCache.txt CMakeFiles
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DZLIB_ROOT=$HOME/usr/local \
      -DBUILD_TESTS=OFF \
      -DBUILD_EXAMPLES=OFF .
```

### 3. 编译和安装
```bash
make -j2
make install DESTDIR=$TEST_PREFIX
```

### 4. 打包和部署
```bash
python3 ohc-run.py package libxlsxwriter 1.2.4
make install  # 安装到本地 ~/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 找不到 ZLIB | ZLIB_ROOT 未设置 | 设置环境变量 `ZLIB_ROOT=$HOME/usr/local` |
| 2 | pkg-config 找不到 zlib | PKG_CONFIG_PATH 未包含 zlib.pc 路径 | 设置 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig` |

## 源码修改

无补丁，无需修改源码。

## 依赖版本

- zlib: 1.3.1（预编译包）

## 验证结果

```bash
# 检查静态库
ls -la ~/usr/local/lib/libxlsxwriter.a
# 输出: 734814 bytes

# 检查头文件
ls ~/usr/local/include/xlsxwriter.h
ls ~/usr/local/include/xlsxwriter/*.h
# 输出: 27 个头文件

# 检查 pkg-config
cat ~/usr/local/lib/pkgconfig/xlsxwriter.pc
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxlsxwriter-1.2.4-ohos-aarch64.tar.gz | 1351908 bytes | 预编译包 |

## 注意事项

1. 本软件为纯静态库，无可执行文件，质量门禁 G4 "无二进制文件" 为预期行为
2. 必须设置 `ZLIB_ROOT` 环境变量，否则 CMake 无法找到 zlib
3. 必须设置 `PKG_CONFIG_PATH`，否则后续依赖软件无法通过 pkg-config 发现此库