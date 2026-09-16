# vips 8.18.4.1 adaptation notes — 启用 JPEG/PNG 编解码器

Branch: feat/vips-8.18.4.1
Archive path: archives/v/vips/8.18.4.1
Source: 与 8.18.4 同一 tarball（vips-8.18.4.tar.xz，sha256 相同）

## 为什么需要这一版

archives/v/vips/8.18.4 是「核心最小构建」：`_disabled_optional_features()` 把
**全部**可选编解码器硬编码为 disabled，配方也不暴露任何 codec option。其制品
因此**无法解码任何 JPEG/PNG**：

```
VipsForeignLoad: "/path/to/photo.jpg" is not a known file format
```

实测于 nip4/9.1.5 的上游测试套件（PR #9517，CI #44345）：31 项测试全部要读
`.jpg`/`.png`，vips 报 `not a known file format` → 全部无法运行。

要给下游解封，只能重出一份带 codec 的制品。按本仓惯例（glib 2.84.0.1 /
2.84.0.2），**不原地改已发布版本**，新增版本目录 `8.18.4.1`。

## 改动

- `requirements()` 新增 `libjpeg-turbo/3.2.0`、`libpng/1.6.58`（均
  `transitive_libs=True`），并用 `zlib/1.3.1.1` 的 **`override=True`** 统一整图
  zlib 版本——glib2/2.88.0 钉 zlib/1.3.1、libpng 钉 zlib/1.3.1.1，不收口必报
  `Version conflict`（CI #44364 实测）。必须收到 **1.3.1.1**（PIC 变体）：制品仓
  libpng/1.6.58 二进制正是基于它构建，收到 1.3.1 会让 libpng 回退源码构建。
- `generate()` 显式 `jpeg=enabled` / `png=enabled` / `zlib=enabled`；三者同时从
  `_disabled_optional_features()` 移除（其余可选栈仍 disabled）。
- `package_info().requires` 补上三个依赖，使静态链接的消费方（CMakeDeps /
  PkgConfigDeps）能自动带上 `-ljpeg -lpng -lz`。

## 关键点

- **pkg-config 名要对上**：libvips Meson 用 `dependency('libjpeg')` /
  `dependency('libpng')` / `dependency('zlib')`。PkgConfigDeps 生成的 .pc 名分别
  来自各包的 `pkg_config_name`——libjpeg-turbo 配方从 `lib/pkgconfig/*.pc` 探测
  得到 `libjpeg`，libpng 显式声明 `libpng`，zlib 无声明→按包名出 `zlib.pc`。三者
  与 Meson 询问名一致。
- **zlib 必须收口到 PIC 变体**：`glib2/2.88.0`（zlib/1.3.1，非 PIC）与
  `libpng/1.6.58`（zlib/1.3.1.1，PIC）在同一张图里必然冲突。惯例做法是
  consumer 侧 `self.requires("zlib/1.3.1.1", override=True)`（先例：
  abiword-plugin-pdf 3.0.8、gmime 3.0.6、awf-gtk 4.2.0）。
- **`modules=disabled` 保持**：codec loader 直接编进 libvips，运行期不需要
  `$VIPSHOME/lib/vips-modules-8.18/` 之类的模块目录，避免「vips 模块路径」这一
  类环境问题。
- **其余 codec 仍关闭**：tiff/webp/magick/heif/… 等各自的 Conan 包未确认前不开，
  保持与 8.18.4 相同的风险面。

## test_package 自证

旧 test_package 只做一次 `vips_avg(matrix)`，**完全不碰图像 I/O**，所以 8.18.4
的「无 codec」问题在 CI 里不可见。本版 test 增加：

1. 生成 16×16 三通道 uchar 常量图 (10,20,30)；
2. `vips_jpegsave` → `vips_foreign_find_load` 确认 loader 是 jpeg → 重新载入，
   断言尺寸/通道/像素（容差 8）；
3. `vips_pngsave` → 同上，像素**逐位精确**（容差 0）。

即：CI 通过 = JPEG/PNG 的 loader/saver 确实存在且可用。
