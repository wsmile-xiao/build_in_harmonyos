# libfm 1.3.2

libfm 是一个文件管理库，为 LXDE 桌面环境提供文件管理功能。

## 版本信息

- **版本**: 1.3.2
- **状态**: ✅ 已发布
- **构建系统**: Autotools
- **构建日期**: 2026-06-05

## 编译说明

### 源码获取

```bash
wget https://download.savannah.nongnu.org/releases/libfm/libfm-1.3.2.tar.gz
tar -xzf libfm-1.3.2.tar.gz
cd libfm-1.3.2
```

### 应用补丁

```bash
patch -p1 < patches/0001-config-guess-ohos.patch
```

### 配置选项

```bash
./configure --prefix=/path/to/install \
    --with-extra-only \
    --disable-nls \
    CC=clang \
    CXX=clang++ \
    LDFLAGS="-Wl,--whole-archive -lintl"
```

### 编译和安装

```bash
make -j$(nproc)
make install
```

## 依赖项

- glib >= 2.88.0
- libintl >= 8.4.0
- pcre2 >= 0.11.0

## 输出产物

| 文件 | 说明 |
|------|------|
| libfm-extra.so.4.1.3 | 动态库（已签名） |
| libfm-extra.a | 静态库 |
| libglibintl-shim.so | 运行时依赖库 |
| libfm-extra.pc | pkg-config 文件 |

## 运行时说明

运行时需要 LD_PRELOAD libglibintl-shim.so：

```bash
LD_PRELOAD=/path/to/libglibintl-shim.so your_application
```

## 关键问题与解决方案

### E007/E072: config.guess 不识别 OHOS

**问题**: autotools 的 config.guess 无法识别 HarmonyOS 平台

**解决**: 应用 `0001-config-guess-ohos.patch`，添加 HarmonyOS 平台识别支持

### 静态链接 libintl

**问题**: glib 静态链接时需要完整的 libintl 符号

**解决**: 使用 `-Wl,--whole-archive -lintl` LDFLAGS

### g_libintl_* 符号缺失

**问题**: libfm-extra 需要 g_libintl_* 符号，但 glib 不提供

**解决**: 创建 libglibintl-shim.so shim 库提供这些符号

## 补丁说明

| 补丁文件 | 说明 |
|----------|------|
| 0001-config-guess-ohos.patch | 添加 HarmonyOS 平台识别 |

## 测试结果

| 测试项 | 状态 |
|--------|------|
| 库文件完整性 | ✅ PASS |
| ELF 签名 | ✅ PASS |
| 运行时加载 | ✅ PASS |
| API 功能 | ✅ PASS |

## 许可证

GPL-2.0-or-later

## 参考链接

- 官方网站: https://sourceforge.net/projects/pcmanfm/
- 源码下载: https://download.savannah.nongnu.org/releases/libfm/