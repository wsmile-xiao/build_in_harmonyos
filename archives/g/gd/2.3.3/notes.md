# gd 2.3.3 适配笔记

## 编译环境
- 构建系统: autotools (libtool)
- 编译日期: 2026-08-01
- 编译器: clang 15.0.4 (/data/service/hnp/bin/clang)
- 平台: HarmonyOS PC aarch64 (OHOS 6.0)，config.guess 输出 aarch64-unknown-linux-ohos
- 状态: published（make check 160/162 通过）

## 编译步骤
1. 下载源码 libgd-2.3.3.tar.gz 并解压
2. 应用 config.guess/config.sub 补丁（复用归档 0001/0002）
3. 修复 configure 脚本 umask 077 → umask 022（E011）
4. `./configure --prefix=$DEFAULT_PREFIX --with-zlib=DIR --with-png=DIR --without-freetype --without-jpeg`
5. `make -j4`
6. `make install DESTDIR=$TEST_PREFIX`
7. `make -j4 check` → 160 PASS / 2 SKIP / 0 FAIL

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 HarmonyOS | 版本过旧 | 应用 0001/0002 补丁（升级到支持 linux-ohos 的版本） |
| 2 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | E011: HMDFS UID 映射，umask 077 创建的 0700 临时目录对进程不可写 | `sed -i 's/umask 077/umask 022/g' configure` |
| 3 | configure: no acceptable C compiler found | PATH 中无 clang | 显式 `CC=/data/service/hnp/bin/clang` |

## 依赖
- 必需: zlib (Conan zlib/1.3.1.1 静态), libpng (Conan libpng/1.6.58 共享)
- 可选（本次禁用）: freetype, libjpeg-turbo, webp, heif, avif, tiff, fontconfig, xpm
- 注意: libpng 的 conan recipe 要求 zlib/1.3.1.1（不是 1.3.1），下游引用需一致

## 注意事项
- 构建产物包含 11 个 CLI 工具（bin/），软件级需 commands.json（R38）
- 编译参数最少化，只用 --prefix，不传 --build/--host/--target（R4）
---

**编译结束**: 2026-08-01 17:16
**最终状态**: published
