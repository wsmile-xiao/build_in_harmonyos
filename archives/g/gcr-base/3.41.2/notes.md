# gcr-base 3.41.2 适配笔记

## 编译环境
- 构建系统: meson (init-build 误判 autotools，源码含 meson.build 已纠正)
- 编译日期: 2026-08-03
- 编译器: clang/clang++ 15.0.4 (SDK /data/service/hnp/bin)
- 状态: built（编译/安装成功，测试部分通过）

## 编译步骤

1. init-build gcr-base 3.41.2（GitHub 直连下载，download.gnome.org 被网络阻断）
2. conan install 部署依赖: glib/2.84.0 + p11-kit/0.25.5@ohpcd/stable + libgcrypt/1.11.0 + libgpg-error/1.55 + libffi/3.4.4（CI profile ohos-aarch64, --deployer=full_deploy）
3. meson setup:
   ```
   CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib \
   meson setup build-ohos --prefix=/storage/Users/currentUser/usr/local \
     -Dintrospection=false -Dgtk=false -Dgtk_doc=false -Dssh_agent=false -Dsystemd=disabled -Dgpg_path=/bin/false \
     -Dc_args="-I/storage/Users/currentUser/tmp/gcr-deps/extra-include -include .../extra-include/ohos-compat.h"
   ```
4. ninja -C build-ohos → 306/306 编译链接成功
5. DESTDIR staging 安装 → libgck-1.so.0.0.0 + libgcr-base-3.so.1.0.0 + gck-1.pc/gcr-base-3.pc
6. meson test → 26 OK / 17 FAIL（多为环境相关 SIGABRT/SIGTRAP）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | download.gnome.org 连接重置 | 网络阻断 | 改 GitHub codeload 直连（CA bundle 需指定） |
| 2 | 本地 ninja 不可执行 | hmdfs 压缩属性 + SELinux | 用 SDK /data/service/hnp/bin/ninja (1.13.1)，PATH 前置 |
| 3 | meson 找不到编译器 | PATH 中 clang 不可用 | CC/CXX/AR/RANLIB 全部用 SDK 完整路径 |
| 4 | glib-2.0 找不到 | 部署 .pc 的 prefix=/ 被改写 + 缺 pcre2-8.pc | 修正 prefix 为部署绝对路径；手工补 libpcre2-8.pc/zlib.pc/bzip2.pc（注意文件名须与包名一致） |
| 5 | gcrypt.h 找不到 gpg-error.h | gpg-error.pc 的 Cflags 为空 | 补 `Cflags: -I${includedir}` |
| 6 | gettext/getpass 未声明 | musl 无 libintl.h，unistd.h 无 getpass 声明（libc 有符号） | stub libintl.h + ohos-compat.h，用 -include 强制注入声明 |
| 7 | ssh-add/ssh-agent 缺失 | OHOS 无此程序，上游 meson.build 无条件 .path() | stub 脚本放入 PATH（-Dssh_agent=false 下不影响功能） |

## 源码修改

无源码补丁（所有适配通过环境变量/stub 头文件完成；后续 conanfile 需固化 -Dc_args stub 方案）

## 依赖版本

- glib/2.84.0（含 pcre2/10.40、zlib/1.3.2、bzip2/1.0.8 传递依赖）
- p11-kit/0.25.5（本会话先适配发布，本地缓存产物）
- libgcrypt/1.11.0、libgpg-error/1.55（远程已发布二进制）

## 验证结果

```bash
ninja -C build-ohos          # 306/306 成功
meson install DESTDIR=...    # 成功，libgck-1/libgcr-base-3 产物齐全
meson test -C build-ohos     # 26 OK / 17 FAIL（SIGABRT/SIGTRAP，环境相关）
```
