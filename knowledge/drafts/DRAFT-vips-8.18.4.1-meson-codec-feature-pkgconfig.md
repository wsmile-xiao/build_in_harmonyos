# DRAFT-vips-8.18.4.1-meson-codec-feature-pkgconfig

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-11
> Source: vips (libvips) 8.18.4.1 HarmonyOS PC 适配（Meson，为 8.18.4 补回 JPEG/PNG 编解码器）
> Evidence: PR !9567 / 下游 nip4 !9517 CI #44345

## 现象：编译全绿，运行期说「格式不认识」

下游应用（nip4 9.1.5）上游测试套件 31 项全部要读 `.jpg` / `.png`，CI 里每一项都倒在：

```
VipsForeignLoad: "/…/images/…/foo.jpg" is not a known file format
```

这句话很容易被读成「路径错 / 权限错 / 文件名怪」。实际是 libvips 里**根本没有
注册 JPEG/PNG 的 loader**——制品在编译期就把这两个编解码器关掉了，而构建日志里
没有任何报错。

根因是两条叠加：

### 一、Meson feature option 的 auto 会「静默 disabled」

libvips 的 `meson.build` 把每个可选编解码器做成：

```meson
jpeg = get_option('jpeg')      # meson_options.txt: type: 'feature', value: 'auto'
if jpeg.allowed()
  libjpeg_dep = dependency('libjpeg', required: jpeg)
  ...
```

`feature` 的 `auto` 语义是「探测到就启、探测不到就悄悄关」，**既不改 exit code 也不
打印 error**。所以「codec 没编进去」在 build 阶段零信号。

### 二、pkg-config 名必须与 Meson 询问名逐一对上

libvips 问的是：

| Meson 询问 | Conan 包 | PkgConfigDeps 产出的 .pc 名 | 来源 |
|---|---|---|---|
| `dependency('libjpeg')` | libjpeg-turbo/3.2.0 | `libjpeg` | 配方**探测式** `pkg_config_name`：把 install 出的 `lib/pkgconfig/*.pc` 排序取第一个文件名 stem（`libturbojpeg.pc` 排在后面） |
| `dependency('libpng', >=1.2.9)` | libpng/1.6.58 | `libpng` | 配方显式 `set_property("pkg_config_name", "libpng")` |
| `dependency('zlib', >=0.4)` | zlib/1.3.1.1 | `zlib` | 配方未声明 → 回落包名 |

任意一个对不上（例如想当然以为 libjpeg-turbo 会产 `libjpeg-turbo.pc`），
对应 codec 静默掉，**只有运行期才暴露**。

### 三、把 libpng 拉进 glib2 图 = 必然撞 zlib 版本冲突

开启 PNG 还会带出第二个坑：`glib2/2.88.0` 钉 `zlib/1.3.1`（非 PIC），
`libpng/1.6.58` 钉 `zlib/1.3.1.1`（PIC）→ 同一张图里直接：

```
ERROR: Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1 in the graph.
Conflict originates from glib2/2.88.0
```

（CI #44364 实测。）consumer 侧收口：

```python
self.requires("zlib/1.3.1.1", override=True)   # 必须 1.3.1.1，不能 1.3.1
```

**必须收到 1.3.1.1**：制品仓 `libpng/1.6.58` 的二进制就是基于 zlib/1.3.1.1 构建的，
收到 1.3.1 会让 libpng 的 package_id 失配 → `--build=missing` 回退源码构建 → 撞上
沙箱 configure 失败；收到 1.3.1.1 则 libpng 直接用现成二进制。
（先例：abiword-plugin-pdf 3.0.8、gmime 3.0.6、awf-gtk 4.2.0 都是这一手。）

## 反面样本：把常见 codec 也塞进「默认全关」清单

`archives/v/vips/8.18.4` 的配方把**全部**可选特性硬编码进
`_disabled_optional_features()`（jpeg/png/zlib/tiff/webp/heif/… 一个不漏），且不暴露
任何 codec option。于是它的制品确定性地无法解码任何 JPEG/PNG，下游整套图像测试 0 可跑。

## 测试盲区：test_package 不碰 I/O = 缺陷隐身

8.18.4 的 `test_package/test.c` 只有：

```c
VipsImage *image = vips_image_new_matrixv(2, 2, 1.0, 2.0, 3.0, 4.0);
vips_avg(image, &average, NULL);   /* 纯内存算子 */
```

纯内存算子跑得再好也不能证明任何图像 I/O 能力 → 「制品没有 codec」这个致命缺陷
在 CI 里 100% 不可见，一路绿到合并、到下游才炸。

## 修复（配方侧，不改上游源码，不改已发布版本）

新增 R 版本 `archives/v/vips/8.18.4.1`（源码 tarball 与 sha256 与 8.18.4 完全一致）：

1. `requirements()` 加 `libjpeg-turbo/3.2.0`、`libpng/1.6.58`（`transitive_libs=True`），
   并用 `self.requires("zlib/1.3.1.1", override=True)` 统一整图 zlib。
2. `generate()` 里三个 feature **显式 `enabled`**（关键：**不要留 auto**），
   同时把它们从 `_disabled_optional_features()` 移除；其余可选栈保持 disabled，
   风险面与 8.18.4 相同。
3. `package_info().requires` 补 `libjpeg-turbo` / `libpng` 两个**直接**依赖。
   **`zlib` 不能列进去**：它只是 `override=True` 引入的、用于统一图版本的项，
   conan 会双向校验并直接中断打包——
   `There are '(cpp_info/components).requires' that includes package 'zlib::',
   but such package is not a direct requirement of the recipe`（CI #44368 实测）。
   消费者仍能经 libpng/glib2 传递拿到 `-lz`（同 gmime 3.0.6 的注释）。
4. 保持 `modules=disabled`：loader 直接编进 libvips 本体，运行期不需要
   `$VIPSHOME/lib/vips-modules-8.18/` 这类模块目录。
5. test_package 变成**可判定 codec 存在**的测试：生成 16×16 三通道常量图 →
   `vips_jpegsave` / `vips_pngsave` 落盘 → `vips_foreign_find_load()` 断言 loader
   认领该扩展名 → 重新载入断言 尺寸/通道/像素（JPEG 容差 8，PNG 逐位精确）。
   任一 codec 缺失即大声失败（13 断言）。

## 测试自身也会踩坑：`vips_foreign_find_load()` 返回的是内部常量串

把「断言 loader 存在」写进 test_package 时踩到两个连带坑（CI #44552 实测，
第一次跑出 `no JPEG loader ... (got 'VipsForeignLoadJpegFile')` 紧接
`Signal 11 (core dumped)` → `Error 139`）：

1. **返回的是内部持有的 `const char *`，不能 free**。`vips_foreign_find_load()`
   返回 libvips 内部的 loader 名字符串（如 `VipsForeignLoadJpegFile`），
   对它调 `g_free()` 等于对非堆指针 free → SIGSEGV。编译器其实早有提示：
   `initializing 'char *' with an expression of type 'const char *' discards
   qualifiers`——把返回值声明成 `char *` 就是在掩盖这个问题。
2. **loader 名是大写开头的驼峰**（`VipsForeignLoadJpegFile` / `VipsForeignLoadPng`），
   `strstr(loader, "jpeg")` 会 miss，断言假失败。要大小写不敏感比较。

正确写法：`const char *loader = vips_foreign_find_load(path);` 后做
`g_ascii_strdown` 再 `strstr`，**不要 g_free**。

## 验证证据

- `nm -D --defined-only libvips.so | grep -i jpeg`（制品取证）或 Meson 摘要里
  `jpeg: ENABLED / png: ENABLED / zlib: ENABLED`。
- CI：`conan create archives/v/vips/8.18.4.1 … --build=missing`，test_package 内
  `vips_foreign_find_load("test_vips.jpg")` 必须返回含 `jpeg` 的字符串。
- 上游对照：gdk-pixbuf 用同一套组合（libjpeg-turbo/3.2.0 + Meson `jpeg=enabled`
  + PkgConfigDeps）是可运行的既有先例。

## 时序陷阱（跨 PR）

`conan create … --build=missing` 的 `--build=missing` **只从制品仓拉缺失依赖**，
不会去仓库目录里现编。所以下游（nip4）必须等 `vips/8.18.4.1` 合并并由 release
流水线上传制品仓后，再推「`requires("vips/8.18.4")` → `vips/8.18.4.1`」的下一个
PR，CI 才可能转绿（与 libxi → libxtst 同款时序）。

## 作用域与维护条件

- 作用域：配方级移植（显式 feature option + pkg-config 名对齐 + 制品自证测试）。
- 适用面：任何「可选特性 = Meson feature option + pkg-config 探测」的静态库
  （libvips、gdk-pixbuf 的 jpeg 分支、ffmpeg 系），以及「test_package 只覆盖纯
  内存/纯算法路径」的库。
- 禁忌：①不得把常见 codec（jpeg/png/zlib）与冷门 codec 一起塞进默认全关清单；
  ②不得对这类 feature 留 `auto` —— 名字对不上时是静默 disabled；
  ③test_package 不得只测纯内存算子就宣称「功能验证通过」。
