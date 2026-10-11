# xbitmaps 1.1.3 适配笔记

## 形态

纯数据包（X11 位图数据）：71 个位图文件以 C 源码形态提供——每个文件是
`#define <name>_width N` / `#define <name>_height N`（部分带 `_x_hot`/`_y_hot`）
加 `static char <name>_bits[] = { … }`。上游 autotools 只做数据安装
（`dist_bitmap_DATA` → `$includedir/X11/bitmaps`），**零编译、零链接、零三方依赖**。

## 做法与验证

- 配方按 `header-library` 打包：`package_type="header-library"`、
  `package_id().clear()`、只装头（数据）文件到 `include/X11/bitmaps/`。
- `build()` 无编译可做，改为**数据完整性校验**（真实消费者口径）：
  - 解析上游 `Makefile.am` 的 `dist_bitmap_DATA` 列表，断言恰好 71 个文件；
  - 每个文件必须有 `<name>_width` / `<name>_height` 两个 define 和
    `<name>_bits[]` 数组；
  - 数组内 0x 字节数必须等于 `((width+7)/8)*height`（X11 位图打包规则）。
- 消费者测试（test_package）两级：
  - `test_xbitmaps.c`：真实 `#include <X11/bitmaps/boxes>` 等 5 个位图并编译
    运行，断言尺寸与字节数；
  - `test_bitmaps.sh`：扫描安装目录全部 71 个文件，逐个做同口径校验。

## 坑

- 官方 tarball 主机（www.x.org）在真机 DNS 直接解析失败；改用
  `xorg.freedesktop.org` 同内容 URL（CI 镜像链能接管），sha256 与官方一致
  （`93b433b7…`，1.1.3 发布即此值）。
- 文件名如 `1x1` 展开成宏名 `1x1_width` 不是合法 C 标识符——上游历史如此，
  该类文件只能按数据解析消费（`#include` 会编译失败）；消费者 C 测试只
  `#include` 标识符合法的位图（boxes/target/cross_weave/gray/plaid）。
