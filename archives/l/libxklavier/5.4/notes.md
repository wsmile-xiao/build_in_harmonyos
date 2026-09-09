# libxklavier 5.4 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-08-26
- 编译器: clang/clang++ (15.0.4 OHOS toolchain)
- 目标: aarch64-linux-ohos (OHOS 6.0, armv8)

## 依赖决策（W0 检查）

| 依赖 | 版本 | 状态 | 处理 |
|------|------|------|------|
| libx11 | 1.8.13 | 已发布 | `requires("libx11/1.8.13")` |
| glib | 2.88.0.1 | 已发布 | `requires("glib/2.88.0.1")` |
| libxml2 | 2.15.3.1 | 已发布 | `requires("libxml2/2.15.3.1")` |
| gettext | 0.22.5.1 | 已发布 | `tool_requires`（msgfmt） |
| libxkbfile | 1.1.3 | **未发布** | 配方内内嵌构建（静态）并链接进 libxklavier.so |
| libxi | — | **未发布** | 可选，configure 自动回退裁剪 |
| iso-codes | — | **未发布** | 配方内生成最小 iso-codes.pc |
| gobject-introspection | — | **未发布** | 可选，--disable-introspection 裁剪 |
| vala | — | **未发布** | 可选，--disable-vala 裁剪 |

### 关键判断：libxkbfile 不可裁剪
- ayatana-indicator-keyboard 使用 `xkl_engine_get_instance`、`xkl_config_rec_get_from_server`、
  `xkl_engine_lock_group` 等 XKB 后端 API。
- 源码 `libxklavier/xklavier_xkb.c` 中 `xkl_xkb_init()` 在 `#ifndef LIBXKBFILE_PRESENT`
  分支直接 `return -1`，导致 XKB 后端永不初始化，`xkl_engine_get_instance()` 返回 NULL。
- 因此 libxkbfile 是 XKB 功能的**硬依赖**，无法裁剪，且系统未提供 → 内嵌构建。

## 编译步骤

1. 下载源码 tarball: libxklavier_5.4.orig.tar.xz
   (sha256: a30b302f3490e6423d21844dae4411a38e9c9d4f5196df571bc8276a03a53e63)
   - 上游 github/gitlab 均不可达（网络受限），改用 Debian pool 的 pristine 上游 tarball。
2. 下载内嵌依赖: libxkbfile-1.1.3.tar.xz
   (sha256: a9b63eea997abb9ee6a8b4fbb515831c841f471af845a09de443b28003874bec)
3. 配置:
   ```
   ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
     --disable-introspection --disable-vala --disable-gtk-doc \
     --with-xkb-base=/usr/share/X11/xkb
   ```
4. 编译: `make -j1`
5. 上游测试: `make check`（tests/ 下 xklavier 测试）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 github.com / gitlab.freedesktop.org 不可达 | 网络受限 | 使用 Debian pool 的 pristine 上游 tarball |
| 2 | libxkbfile 未发布且系统未提供 | 制品仓无此包 | 配方内内嵌构建（静态 libxkbfile.a）并链接进 libxklavier.so |
| 3 | configure 要求 iso-codes.pc | iso-codes 是数据包未发布 | 配方内生成最小 iso-codes.pc（prefix 指向安装前缀） |
| 4 | gobject-introspection/vala 宏 | 可选特性 | --disable-introspection --disable-vala 裁剪 |
| 5 | OHOS autotools 通用问题 | E002/HMDFS + 无 /bin/sh | umask 077→022、shebang 替换、--build/--host 指定 triplet |
| 6 | libxi 缺失 | 可选依赖未发布 | configure 自动回退 have_xinput=no，XKB 后端不受影响 |

## 验证结果

```bash
conan create archives/l/libxklavier/5.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

---

**编译结束**: 2026-08-26
