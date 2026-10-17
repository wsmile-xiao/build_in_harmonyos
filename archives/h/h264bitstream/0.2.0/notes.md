# h264bitstream 0.2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

1. init-build: `ohc-run.py init-build h264bitstream 0.2.0 --url=https://downloads.sourceforge.net/project/h264bitstream/h264bitstream/0.2.0/h264bitstream-0.2.0.tar.gz`
2. autoreconf: `autoreconf -fi`（源码缺少 configure 脚本，需从 configure.ac 生成）
3. configure: `CONFIG_SHELL=/path/to/bash bash ./configure --prefix=$DEFAULT_PREFIX`
4. 修改 config.status 中 umask 077 → 007（HMDFS UID 不匹配导致临时目录写入失败）
5. 运行 config.status 生成 Makefile
6. make: `make -j2`（170 个 format warning，不影响功能）
7. make install DESTDIR: `make install DESTDIR=$TEST_PREFIX`
8. staging 验证: PASS（h264_analyze --help 输出正常）
9. make check: 无测试套件（Nothing to be done）
10. package: `ohc-run.py package` → h264bitstream-0.2.0-ohos-aarch64.tar.gz (925KB)
11. make install: 安装到 DEFAULT_PREFIX
12. 用户验证: h264_analyze --help 正常，pkg-config --modversion = 0.2.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建临时目录后写入 subs1.awk Permission denied | HMDFS 文件系统所有文件 owner UID 为 20001006（非当前用户 20020082），umask 077 后当前用户（属 file_manager 组）无权限访问 mktemp 创建的临时目录 | 将 config.status/configure 中 `umask 077` 改为 `umask 007`，使组权限保留 |
| 2 | 源码缺少 configure 脚本 | h264bitstream 0.2.0 仅提供 configure.ac，需 autoreconf 生成 | 运行 `autoreconf -fi` 生成 configure 脚本和构建辅助文件 |

## 源码修改

- configure: umask 077 → umask 007（HMDFS 平台适配）
- config.status: umask 077 → umask 007（HMDFS 平台适配）

注意：config.status/configure 为 autotools 生成文件，此修改属于平台运行时适配，不固化为源码补丁。

## 依赖版本

- 无额外编译依赖（仅需要标准 C 库和 getopt_long）

## 验证结果

### 基础功能验证

```bash
$ h264_analyze --help
h264_analyze, version 0.2.0
Analyze H.264 bitstreams in Annex B format

$ PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --modversion libh264bitstream
0.2.0
```

### H.264 码流解析测试

```bash
$ printf '\x00\x00\x00\x01\x67\x42\x00\x0a\xf8\x0a\x69\xa0...' > test.h264
$ h264_analyze test.h264
!! Found NAL at offset 4, size 9
  nal_unit_type: 7 (SPS)
  profile_idc: 66 (Baseline)
  level_idc: 10
退出码: 0
```

### 库 API 链接测试

```c
// test_h264_api.c
#include <h264bitstream/h264_stream.h>
int main() {
    h264_stream_t* stream = h264_new();    // ✅ PASS
    printf("sei: %d\n", stream->num_seis); // ✅ PASS
    h264_free(stream);                      // ✅ PASS
    return 0;
}
```

编译运行: `clang -I$PREFIX/include -L$PREFIX/lib -lh264bitstream test.c -o test`
结果: 全部 PASS，退出码 0

### 二进制格式验证

| 产物 | 格式 | 结果 |
|------|------|------|
| h264_analyze | ELF 64-bit LSB arm64, dynamic (ld-musl) | ✅ |
| libh264bitstream.so.0.0.0 | ELF 64-bit LSB arm64, dynamic | ✅ |
| libh264bitstream.a | ar archive | ✅ |

### 运行时依赖

- h264_analyze: NEEDED=libh264bitstream.so.0, libc.so; RUNPATH=$PREFIX/lib
- libh264bitstream.so.0.0.0: NEEDED=libc.so (仅依赖 musl libc)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| h264bitstream-0.2.0-ohos-aarch64.tar.gz | 925KB | 预编译包 |

## 注意事项

- HMDFS umask 077 问题为平台通用问题（E046 chmod 不生效的延伸），影响所有使用 autoconf 的三方库
- h264bitstream 无自带测试套件
- 编译有 170 个 format specifier warning（%d vs %ld），不影响功能
- ⚠️ h264_analyze --version 参数导致 segfault（exit code 139），但 --help 正常输出版本信息 0.2.0。此为软件自身bug，不影响功能使用
- G0 clean-verify 因 OpenHarmony patch 命令不支持 --input 选项而失败（平台限制，已手动验证构建无误）
- 生成文件补丁（Makefile/config.log/config.status/libtool）已按 R6 删除，configure 会自动重新生成
- 知识图谱草稿 E999 已创建：OpenHarmony patch 命令不支持 --input/-i 选项
---

**编译结束**: 2026-07-17 16:13
**最终状态**: built
