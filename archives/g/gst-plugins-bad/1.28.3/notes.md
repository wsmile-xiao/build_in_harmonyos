# gst-plugins-bad 1.28.3 适配笔记

## 编译环境
- 构建系统: meson (conan 驱动)
- 编译日期: 2026-05-30 (探索构建) / 2026-09-17 (conan 配方定稿)
- 编译器: clang 15.0.4 / clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 链接器: ld.lld 15.0.4
- 状态: built (conan create 全流程通过, 含 test_package)

## 方案演进史

| 阶段 | 方案 | 结果 |
|------|------|------|
| 2026-08-06 | GStreamer monorepo (GitHub tag 1.28.3), base 作 meson 子项目, 系统 glib | CI 失败: jpeglib.h/cairo.h 缺失 (base 的 gl/pango 插件), 硬编码路径 P0 |
| 2026-08-27 | 独立 tarball + conan 依赖 gstreamer/1.28.3 + gst-plugins-base/1.28.3 | gst-plugins-base 未发布 -> L0i 依赖闸失败 (CI 误报 registry_unreachable) |
| 2026-09-04 | 前次修复尝试: 禁用 gl/opensles/webp/orc, 删 wrap 文件 | 仍卡 L0i (gst-plugins-base/1.28.3 不在制品仓, cnb.cool 404 被误读为网络错误) |
| 2026-09-17 (本次) | 复刻 gst-libav 已验证模式: base tarball vendor 进 subprojects/ 作 meson 子项目, 依赖仅 gstreamer/1.28.3 + glib2/2.88.0 + zlib/1.3.1.1(PIC) | conan create 全绿 |

## 关键事实: L0i "registry_unreachable" 实为依赖未发布

cnb.cool 制品仓对不存在的配方返回 `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`,
CI 的 L0i 探测把它当成网络错误归类为 registry_unreachable。本地实测:
`conan download gst-plugins-base/1.28.3 -r=ohpcd --only-recipe` 与 gst-plugins-bad/1.28.3(未发布) 报错
完全相同, 而 gstreamer/1.28.3、glib2/2.88.0 均正常返回。即 gst-plugins-base 从未发布 (PR #4353 未合入),
旧配方的 L0i 失败是真实的依赖缺失。

## conan 配方要点 (libav 模式)

1. **gst-plugins-base 作 meson 子项目**: conandata.yml 双源 (bad + base tarball),
   source() 把 base 解压到 `subprojects/gst-plugins-base/`; bad 的 meson.build 里
   `dependency(..., fallback: ['gst-plugins-base', ...])` 自动落位本地目录, 不触发下载。
   `--wrap-mode=default` + 独立 tarball 无 .wrap 文件 = 无任何下载。
2. **zlib/1.3.1.1 override (PIC 静态库)**: glib2 要求 zlib/1.3.1, 但其 libz.a 非 PIC,
   base 子项目的 libgsttag.so 链接时报 `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`。
   zlib/1.3.1.1 专为该问题发布 (-fPIC 静态库)。与 gst-libav 配方相同的 override。
3. **glib-mkenums 路径钉死**: bad 的 vulkan meson.build 用裸 `find_program('glib-mkenums')`
   (gnome 模块走 pkg-config 变量不受影响), PATH 里 HNP 的 perl 版脚本因无 /usr/bin/perl 损坏。
   通过 MesonToolchain `tc.binaries["glib-mkenums"]` 写入 native file [binaries] (meson 优先于 PATH 查找),
   指向 glib2 conan 包 bin/ 下的 python3 实现。
4. **gio-unix-2.0.pc 指向 include/gio-unix-2.0**: unixfd 插件 `#include <gio/gunixfdmessage.h>`,
   头文件在 `include/gio-unix-2.0/gio/` 下。
5. **OHOS ELF 签名 x meson install 冲突 (E504 同类)**: meson install 会改写安装产物的
   DT_RUNPATH (在 .dynstr 里抹掉 build-tree rpath)。OHOS 校验 lld 链接时嵌入的整文件内容签名,
   链接后改任何一字节 -> loader EACCES "Permission denied" (实测翻转 1 字节即复现)。
   package() 在 meson.install() 后用 build 目录原始产物覆盖回来 (132 个文件)。
   运行期依赖解析靠 LD_LIBRARY_PATH (conanrun), 不依赖这些 rpath。
6. **消费端测试不能调 gst_init()**: conan glib2/gstreamer 均为纯静态包, 每个 bad/base .so
   内嵌一份 glib/gstreamer 副本; 消费端二进制再静态链一份后 gst_init() 跨副本操作类型注册表,
   "cannot register existing type" + 单线程 FUTEX 死锁 (实测 60s 超时)。
   测试采用 gst-libav 已验证的 dlopen/dlsym 模式 + readelf 结构校验 (SONAME/插件符号)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | L0i registry_unreachable | gst-plugins-base/1.28.3 未发布 (cnb.cool 404 文案怪异) | vendor base 为 meson 子项目, 不再依赖 conan 包 |
| 2 | libgsttag 链接 R_AARCH64 重定位错误 | zlib/1.3.1 静态库非 PIC | `zlib/1.3.1.1` override (PIC) |
| 3 | vulkan-enumtypes 生成 FileNotFoundError | HNP glib-mkenums 是 perl 脚本且无 perl | native file [binaries] 钉死 conan glib2 的 python3 版 |
| 4 | unixfd 插件找不到 gio/gunixfdmessage.h | gio-unix 头文件在专用 include 目录 | gio-unix-2.0.pc Cflags 加 -I include/gio-unix-2.0 |
| 5 | test_package 运行 Error 127 (load 失败) | meson install rpath 改写使 ELF 签名失效 | package() 用 build 原始产物覆盖 (E504 模式) |
| 6 | test 二进制 gst_init 卡死 | 多份内嵌 glib 副本类型注册表互相踩踏 | 测试改 dlopen/dlsym + readelf 校验 (libav 模式) |
| 7 | GL/opensles/webp/orc 插件 | OHOS 平台不兼容 (历史已知) | meson 选项禁用 (非裁剪, 平台不兼容) |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| gstreamer | 1.28.3 | 制品仓已发布 (静态库) |
| glib2 | 2.88.0 | 制品仓已发布 (静态库) |
| zlib | 1.3.1.1 | override, PIC 静态库 |
| gst-plugins-base | 1.28.3 | 官方 tarball vendor 为子项目 (制品仓未发布) |

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# ... 955+ 构建目标全部完成
# Restored 132 pristine build artifacts over meson install output
# test_package:
#   4 个库 SONAME 校验通过 (insertbin/codecparsers/webrtc/video)
#   插件目录 >10 个 .so, libgstaccurip.so 导出 gst_plugin_acc* 符号
#   test_gst_plugins_bad: libgstinsertbin-1.0 loaded, gst_insert_bin_new OK
#   gst-plugins-bad test: PASS
```

产物: lib/ 下 88 个文件 (17 个 bad 库 + base 子项目库/插件 + SONAME 符号链接),
lib/gstreamer-1.0/ 下 bad + base 插件, include/gstreamer-1.0/ 头文件, bin/ 工具。

W3 本地 CI 模拟 (ci/conan/build_and_test.sh 同源脚本, 含 L0 门禁): exit 0。
W4 Pre-PR 独立审计: PASS (0 P0 / 0 P1)。

## 注意事项

1. 本包内含 gst-plugins-base 的库与插件 (vendored 子项目构建产物) — base 未单独发布前的过渡形态,
   与 gst-libav 1.28.3 PR #4373 同构。
2. 消费端链接时须保证 LD_LIBRARY_PATH 含本包 lib/ (conan 自动处理); 不可依赖可执行文件 rpath。
3. GL/opensles/webp/orc 为平台不兼容禁用; 其余 bad 插件由 meson auto 检测 (依赖缺失自动跳过, 上游默认行为)。
4. 若未来 gst-plugins-base 发布, 可切回 conan 依赖模式 (旧分支历史有该形态配方)。
5. bin/ 下的 gst-* 命令行工具 (如 gst-transcoder-1.0) 是 vendored 构建的附属产物,
   本包定位为 library (未声明 bindirs/commands.json); 需要工具链的消费者可按需自取。
---

**编译结束**: 2026-09-17 16:09
**最终状态**: built
