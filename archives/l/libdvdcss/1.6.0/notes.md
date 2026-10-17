# libdvdcss 1.6.0 适配笔记

## 编译环境
- 构建系统: Meson (>= 0.60.0)
- 编译日期: 2026-09-23
- 编译器: clang (DevEco SDK, aarch64-unknown-linux-ohos)
- 状态: built

## 项目说明

libdvdcss 是 VideoLAN DVD 库栈的解密层。1.6.0 相对 1.5.0 的关键变化是
构建系统从 autotools 完整迁移到 Meson。meson.build 不声明对 libdvdread
的任何依赖（仅 `meson.override_dependency('libdvdcss', ...)`），因此
libdvdcss 可作为独立 C 库单独编译安装。

## 编译步骤

1. 下载源码:
   `https://code.videolan.org/videolan/libdvdcss/-/archive/1.6.0/libdvdcss-1.6.0.tar.bz2`
   （sha256: `c43b5506604ab93e38fde11912c01239e00ba6331db0cf930acd1c204a57964f`，
   顶层目录 `libdvdcss-1.6.0`；等价镜像 `download.videolan.org/developers/libdvdcss/`）
2. meson setup（静态库、禁文档、禁示例）:
   ```bash
   meson setup build --prefix=$PREFIX \
     -Ddefault_library=static -Denable_docs=false -Denable_examples=false
   ```
3. meson compile -C build
4. meson install -C build
5. 产物:
   - `lib/libdvdcss.a`（静态库，soname 版本 2.4.0）
   - `include/dvdcss/dvdcss.h`、`include/dvdcss/dvdcpxm.h`
   - `lib/pkgconfig/libdvdcss.pc`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 1.5.0 配方基于 autotools，1.6.0 直接套用会失败 | 上游迁移到 Meson | 配方按 Meson 重写（MesonToolchain + Meson 工具类），沿用 libdvdread 7.1.0 的 OHOS 交叉构建注入逻辑 |
| 2 | OHOS 交叉构建时 meson 找不到 ar/ranlib | conan 生成的 cross file 未带归档工具 | `_inject_meson_archive_tools` 注入 llvm-ar/llvm-ranlib 到 conan_meson_cross.ini 的 [binaries] 段 |
| 3 | meson 头文件检测在 OHOS/musl 上部分失败 | musl 缺少部分系统头（scsi/sg.h 等） | 属预期：缺失头仅在配置探测阶段跳过，DVD ioctl 检测命中 linux/cdrom.h 分支，核心编译不受影响 |
| 4 | 上游 test/ 无法在 CI 运行 | csstest/dvd_region 需要真实 DVD 镜像输入 | 记 upstream_tests: 0，改用消费测试 + 故障注入覆盖 API 冒烟 |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- 无运行/构建依赖（libdvdcss 独立成库，不依赖 libdvdread）

## 验证结果

```bash
$ ./test_libdvdcss
PASS: symbol dvdcss_open resolves
PASS: symbol dvdcss_open_stream resolves
PASS: symbol dvdcss_close resolves
PASS: symbol dvdcss_seek resolves
PASS: symbol dvdcss_read resolves
PASS: symbol dvdcss_readv resolves
PASS: symbol dvdcss_error resolves
PASS: symbol dvdcss_is_scrambled resolves
PASS: symbol dvdcss_get_encryption_type resolves
test_libdvdcss: all assertions passed (normal)

$ ./test_libdvdcss --missing-path
PASS: symbol dvdcss_open resolves
... (9 项符号解析) ...
PASS: precondition: bad path really does not exist
PASS: dvdcss_open(missing path) returns NULL
test_libdvdcss: all assertions passed (fault-injection)
```

## 交付物

| 文件 | 说明 |
|------|------|
| libdvdcss.a | 静态库（aarch64-ohos） |
| include/dvdcss/*.h | 公开头文件 ×2 |
| libdvdcss.pc | pkg-config 文件 |

## 注意事项

- libdvdcss 与 libdvdread 7.1.0、libdvdnav 构成 VideoLAN DVD 栈；本库不反向依赖它们
- 消费方启用解密时需同时链接 libdvdcss 与 libdvdread（dvdread 通过 libdvdcss 回调调用）
- 上游示例程序（enable_examples=true）需真实 DVD 镜像，CI 不启用

---

**编译结束**: 2026-09-23
**最终状态**: built
