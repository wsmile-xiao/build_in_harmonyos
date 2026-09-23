# libart-lgpl

> LGPL 的独立 2D 矢量图形库（GNOME libart 的独立分支）。

## 简介

libart_lgpl 提供与渲染目标无关的 2D 图形基础件：

- **矢量路径**（ArtVpath）：直线段路径构造、包围盒、仿射变换、扰动；
- **仿射变换**（`art_affine_*`）：缩放/旋转/平移/错切/求逆/合成、膨胀率、正交性判定；
- **SVP**（sorted vector path）：路径展平、求交与重排（nonzero/odd-even 等环绕规则）、
  包围盒与点判定；
- **光栅化**：灰度/RGB/RGBA 运行填充与 alpha 混合，以及模块化的
  抗锯齿渲染器（`art_render_new` + SVP/渐变/alpha 掩码 + 图像源）。

库不依赖任何第三方组件（仅 `libm`），常用于需要轻量矢量光栅化的场景
（如早期 GNOME 组件、PostScript/图形工具）。

## OHOS 适配要点

- 上游为 2010 年的 autotools 工程，自带 `config.sub` **不识别 aarch64 与 HarmonyOS**：
  `patches/0002-config-sub-ohos.patch` 以 17 行早退分支补上 `aarch64-*-linux*` /
  `aarch64-*-ohos*` / `aarch64-linux-ohos` 三元组；并显式传 `--build`/`--host`，避免在
  HMDFS 上执行 `config.guess`（现代 config.guess 在此会因无法创建临时文件而失败，E007）。
- `configure`（autoconf 2.63）用 `umask 077 && mktemp -d` 建临时目录，
  HarmonyOS HMDFS 为 setgid 挂载、0700 目录不可写 → 打补丁放宽为 `umask 022`（**E011**）。
- libtool 2.2.6 无需升级即可在 OHOS 生成 arm64 共享库/静态库。
- 产物：`lib/libart_lgpl_2.so.2.3.21`（soname `libart_lgpl_2.so.2`）、
  `lib/libart_lgpl_2.a`、`include/libart_lgpl/*.h`、`lib/pkgconfig/libart-2.0.pc`。
- 上游无 `make check`；适配时在真机运行 `testuta` 与
  `testart {testpat,gradient,dash,dist,intersect}` 作为上游证据。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| libm | OHOS libc 提供 | 三角函数等数学运算 |

## 使用

Conan 消费者（CMake）：

```cmake
find_package(libart-lgpl CONFIG REQUIRED)
target_link_libraries(app PRIVATE libart-lgpl::libart-lgpl)
```

pkg-config：

```sh
pkg-config --cflags --libs libart-2.0
```

代码示例（画一个圆并做仿射变换）：

```c
#include <libart_lgpl/art_affine.h>
#include <libart_lgpl/art_vpath.h>

double scale[6];
ArtVpath *circle = art_vpath_new_circle(60.0, 60.0, 20.0);
art_affine_scale(scale, 3.0, 3.0);
ArtVpath *big = art_vpath_affine_transform(circle, scale);
/* ... 交给 SVP / 渲染器 ... */
art_free(big);
art_free(circle);
```

## 功能验证

```sh
conan create archives/l/libart-lgpl/2.3.21 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 上游演示程序 6/6 exit 0；消费者 20/20 断言通过
```

## 目录

```
archives/l/libart-lgpl/
├── README.md            # 本文件（软件级）
├── manifest.yaml        # 软件级元数据
└── 2.3.21/
    ├── conanfile.py
    ├── conandata.yml
    ├── manifest.yaml    # 版本级元数据
    ├── notes.md
    ├── patches/         # config.sub 三元组补丁 + umask 补丁
    ├── reports/         # 测试报告 / 质量报告
    └── test_package/    # 消费者测试（CMake + 20 断言）
```
