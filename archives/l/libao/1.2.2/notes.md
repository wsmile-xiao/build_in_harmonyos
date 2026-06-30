# libao 1.2.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 1. 源码准备
```bash
# URL: https://gitlab.xiph.org/xiph/libao/-/archive/1.2.2/libao-1.2.2.tar.gz
tar xf libao-1.2.2.tar.gz
cd libao-1.2.2
```

### 2. 补丁应用（26 个补丁）
主要补丁类型：
- **构建系统适配**: config.guess, config.sub, ltmain.sh, aclocal.m4
- **Makefile 适配**: 所有目录的 Makefile.in (8 个插件目录)
- **平台适配**: os_types.h (OHOS 平台类型定义)

### 3. 构建脚本生成
libao 使用 autotools，源码包缺少 configure 脚本，需要运行 autogen.sh：
```bash
bash autogen.sh  # 执行 autoreconf -isf 生成 configure
```

### 4. Configure
```bash
./configure --prefix=$DEFAULT_PREFIX
# 无特殊参数，标准 autotools 配置
```

### 5. 编译与安装
```bash
make -j1
make install DESTDIR=$TEST_PREFIX  # staging 安装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本不存在 | autotools 源码未预生成 | 创建 hooks/pre-configure.sh 执行 autogen.sh |
| 2 | config.status 权限错误 | umask 077 导致临时文件权限不足 | sed -i 's/umask 077/umask 002/' config.status |
| 3 | 平台识别失败 | config.guess/config.sub 不识别 OHOS | 补丁更新平台识别逻辑 |
| 4 | os_types.h 缺少 OHOS 定义 | 平台头文件未包含 OHOS 类型 | 补丁添加 OHOS 宏定义 |

## 源码修改

### 关键补丁说明

**0026-include-ao-os_types.h.patch**
- 添加 OHOS 平台类型定义
- 确保 int16_t, int32_t, uint16_t, uint32_t 等类型正确

**0021-config.guess.patch, 0022-config.sub.patch**
- 添加 aarch64-ohos 平台识别
- 支持其他 OHOS 架构

**0002-ltmain.sh.patch**
- libtool 脚本适配 OHOS 链接器
- 解决共享库编译问题

## 依赖版本

无外部库依赖，仅依赖：
- libc.so (系统库)
- autotools 工具链 (automake, autoconf, libtool)

## 验证结果

### pkg-config 验证
```bash
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
pkg-config --modversion ao  # 输出: 1.2.2
pkg-config --cflags ao      # 输出: -I$DEFAULT_PREFIX/include
pkg-config --libs ao        # 输出: -L$DEFAULT_PREFIX/lib -lao
```

### ELF 验证
```bash
file libao.so.4.1.1
# 输出: ELF shared object, 64-bit LSB arm64, not stripped
readelf -d libao.so.4.1.1 | grep SONAME
# 输出: Library soname: [libao.so.4]
```

### 插件验证
```bash
file liboss.so
# 输出: ELF shared object, 64-bit LSB arm64, not stripped
# OSS 音频输出插件，可动态加载
```

### API 符号验证
```bash
nm -D libao.so.4.1.1 | grep ao_
# 输出: 所有核心 API 正确导出
# - ao_initialize, ao_shutdown (初始化/清理)
# - ao_driver_info 系列函数 (驱动查询)
# - ao_open_file, ao_open_live, ao_close (设备操作)
# - ao_play (音频播放)

nm -D liboss.so | grep ao_plugin_
# 输出: OSS 插件接口完整 (8 个插件 API)
# - ao_plugin_test, ao_plugin_device_init
# - ao_plugin_open, ao_plugin_play, ao_plugin_close
```

### 功能编译验证
```bash
# 编写测试程序验证 libao API
clang -o test_libao test_libao.c \
  -I$DEFAULT_PREFIX/include \
  -L$DEFAULT_PREFIX/lib -lao \
  -Wl,-rpath,$DEFAULT_PREFIX/lib
# 编译成功，证明库文件可被正确使用
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libao-1.2.2-ohos-aarch64.tar.gz | 469KB | 预编译包（主交付物） |
| libao-1.2.2-ohos-aarch64-debug.tar.gz | 115KB | 调试符号包 |
| patches/*.patch (26个) | ~1.4MB | 平台适配补丁集 |
| hooks/pre-configure.sh | 291B | 构建前脚本 |

## 注意事项

1. **必须运行 autogen.sh**: libao 源码包不包含 configure 脚本，必须先执行 autogen.sh（或 autoreconf -isf）
2. **umask 修正**: configure 后需修改 config.status 的 umask 设置（077 → 002）
3. **插件目录**: libao 编译 OSS 插件（liboss.so），其他插件（ALSA, PulseAudio 等）因缺少依赖未编译
4. **无测试套件**: libao 没有 make check，验证依赖 pkg-config 和 ELF 检查

---

**编译开始**: 2026-05-20 00:00
**编译结束**: 2026-05-20 10:00
**最终状态**: published
**门禁结果**: G0-G4 全 PASS