# libagg 2.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-11
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 上游事实核查

| 项 | 值 |
|---|---|
| 官方 URL | https://www.antigrain.com/agg-2.5.tar.gz （已失效，DNS 不解析） |
| 可用镜像 | https://ftp.osuosl.org/pub/blfs/conglomeration/agg/agg-2.5.tar.gz （BLFS，字节一致） |
| SHA256 | ab1edc54cc32ba51a62ff120d501eecd55fceeedf869b9354e7e13812289911f |
| MD5 | 0229a488bc47be10a2fee6cf0b2febd6 （与 BLFS book / Fedora src.rpm 一致） |
| License | GPL-2.0-or-later（copying 为 GPLv2 全文；头文件注明 "version 2 or (at your option) any later version"） |
| 构建系统 | autotools（tarball 仅含 configure.in，需 autoreconf） |
| 必需依赖 | 无（核心库零依赖；freetype/SDL/X11/gpc 均为可选层） |
| 公共头文件 | include/agg2/（agg2 前缀目录） |
| 库名 | libagg |
| SONAME | libagg.so.2（libtool -version-info 2:4:0 → libagg.so.2.0.4） |
| 上游正式测试数 | 0（无 check target、无测试源文件；examples/ 为交互式 GUI 演示） |

## 编译步骤

tarball 缺预生成 configure（仅 configure.in），本地 autoreconf 生成产物提交为
preconf/（CI worker 无 libtoolize/aclocal/automake）。构建链:
patch configure.ac → autoreconf -fi → conanfile.py 复制 preconf 覆盖 →
configure（E165 shebang + HMDFS mktemp 已由 conanfile 内联 patch）→ make -j1 → install。

configure 选项（最小核心库）:
--disable-examples --disable-ctrl --disable-platform --disable-freetype --disable-gpc
（静态: --enable-static --disable-shared / 共享: --enable-shared --disable-static）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AM_PATH_SDL undefined | OHOS 无 SDL m4 宏 | patch configure.ac 移除 SDL/FT2 autodetection（同 2.7） |
| 2 | automake 1.16 报 AC_ISC_POSIX/AM_C_PROTOTYPES 不存在 | 2.5 时代宏已从 automake 移除 | patch configure.ac 删除（2.7 已无这些宏，2.5 有） |
| 3 | AUTHORS/NEWS/README not found | automake GNU 严格模式要求 | 本地 autoreconf 前从 tarball 小写 authors/news/readme 复制为大写名 |
| 4 | agg_renderer_outline_aa.h:1378 const 绑定错误 | 非常量 profile() 重载返回非 const 引用，C++11 起非法 | 0002 补丁删除该重载（所有发行版通用补丁） |
| 5 | C++17 下 register 关键字错误 | 2006 年代码用 register | 消费者编译加 -Wno-register（不改上游源码，非错误场景） |
| 6 | config.status Permission denied | HMDFS 拒 700 权限子目录写入 | conanfile 内联 patch configure: umask 077 → 022（沿用 2.7） |

## 源码修改

- patches/0001-configure.ac.patch — 移除 AM_PATH_SDL / PKG_CHECK_MODULES(FREETYPE) /
  AC_ISC_POSIX / AM_C_PROTOTYPES（OHOS 无对应 m4 宏 + automake 1.16 兼容）
- patches/0002-const-profile-fix.patch — 删除非常量 profile() 重载（C++11 起非法，
  Debian/Fedora/BLFS 均携带等效补丁）

## 测试

上游无测试（见 manifest 上游事实核查）。消费者测试 test_package/test.cpp 17 项
像素级断言（矩形填充、抗锯齿线段/三角形、50% 混合、退化/越界/1x1 边界），
全部通过。鸿蒙特有检查 test_ohos.sh: ELF64 AArch64、musl libc.so、
SONAME=libagg.so.2、NEEDED 无 glibc/libstdc++ 泄漏、.codesign、RPATH 干净。

## 注意事项

- 共享构建产物: libagg.so.2.0.4 + libagg.so.2 (SONAME symlink) + libagg.so (dev symlink)
- NEEDED: libc.so + libc++_shared.so（OHOS musl + libc++），实测无 libstdc++/libgcc_s
- 渲染测试断言必须按 BGRA 内存序索引（B=0, R=2），rgba8 是逻辑序 (r,g,b,a)
- 上游 2.5 与 2.7 API 同源；include 前缀同为 agg2/
