# cube2font

cube2font 是 Cube Engine 2 系列游戏（Red Eclipse 及其衍生版）使用的字体位图生成工具：读取一个 TrueType 字体，把引擎字符集里的每个字符用 FreeType 光栅化成位图，按字符宽度/高度排序打包进若干张纹理页，可选地按内外描边参数生成描边字，最后输出一组 8 位灰度+alpha 的 PNG 纹理页和一个纯文本 `.cfg` 图集坐标文件，供游戏运行时按坐标取字。

## 功能概述

- 渲染 Cube 引擎内建字符集（`iscubeprint()` 共 249 个字符，覆盖 Latin-1、Latin Extended-A 与西里尔字母）为位图
- 支持外描边 / 内描边参数，边缘使用圆角连接（`FT_STROKER_LINECAP_ROUND`）
- 自动多页打包：字符按分组与尺寸排序，逐页填充到 `texwidth x texheight` 的纹理页
- 输出 PNG 纹理页（自实现 PNG 写入，`zlib` deflate + CRC32）与 `.cfg` 坐标表
- 附带上游 man 页 `cube2font.1`（完整参数说明）

## OHOS 适配

| 问题 | 根因 | 处理 |
|------|------|------|
| `freetype-config: inaccessible or not found` 后接 `'ft2build.h' file not found` | `src/Makefile` 用 `freetype-config` 探测编译/链接参数，该脚本自 FreeType 2.9.1 起被移除，Conan freetype 包也不提供 | 补丁 `0001-makefile-use-pkg-config-for-freetype.patch` 把编译与链接两条规则改为 `pkg-config --cflags/--libs freetype2`，`.pc` 由消费方 `PkgConfigDeps` 生成 |
| 每次展开 `PLATFORM` 都打印 `gcc: No such file or directory` | `PLATFORM= $(shell gcc -dumpmachine)`，OHOS 工具链无 gcc | 配方显式传 `PLATFORM=<arch>-unknown-linux-ohos`；命令行变量优先于文件内赋值，探测不再执行 |
| `-lz` 找不到 zlib 头与库 | 上游链接行硬编码 `-lz`，无 `-L`；OHOS zlib 包为静态库（`libz.a`） | 配方把 zlib 的 `--cflags/--libs` 注入 `CXXFLAGS`/`LDFLAGS` |
| 默认 `make` 会失败 | `all: client server` 需要 SDL/X11/enet | 只构建 `cube2font` 目标（与 Debian 打包一致） |

已知能力边界：ohpcd 发行的 `freetype/2.14.3` 未启用 zlib/bzip2/png 后端（`readelf -d libfreetype.so.6` 的 `DT_NEEDED` 只有 `libc.so`），因此 FreeType 不能读取 WOFF/gzip 压缩字体容器；未压缩的 TTF/OTF 输入不受影响，本包验证全部使用未压缩 TTF。

## 依赖关系

- 编译依赖：`freetype/2.14.3`、`zlib/1.3.1`
- 运行依赖：`libfreetype.so.6`（Conan 运行环境注入库路径，无 rpath）

## 参考资料

- 上游仓库：<https://github.com/red-eclipse/base>（本工具位于 `src/shared/cube2font.c`）
- 项目主页：<https://www.redeclipse.net>
- man 页：`doc/man/cube2font.1`（源码树内）
