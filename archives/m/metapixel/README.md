# metapixel — A Photomosaic Generator

## 软件简介

metapixel 是一个照片马赛克生成器：它把源图切成等大的矩形网格（或任意位置的
矩形，拼贴模式），逐格从图库里挑出最匹配的小图替换进去，从而用一堆毫不相干
的小照片"拼"出目标图像。

**主要功能**:

- 经典矩阵马赛克（`--metapixel`）与拼贴排布（`--collage`）
- 两种匹配度量：`subpixel`（默认）与 `wavelet`
- 两种搜索策略：`local` 与 `global`
- 读取 **PNG / JPEG / GIF** 三种输入格式，输出按扩展名选 **PNG 或 JPEG**
- `-y/-i/-q` 调 YIQ 三通道权重；`-a/--cheat` 按百分比叠回原图
- `-c` 改用小图原始颜色（关闭匹配）；`-d` 设置同一小图的最小复用间距
- `-x/--antimosaic` 指定不参与匹配、仅作为"反马赛克"原样贴回的小图

上游作者 Markus Schani，1997–2006 年由 Mark Probst 维护，最后一次发布
**2006-12-10 的 1.0.2**（此后无新版本）。许可证 GPL-2.0-or-later。

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 1.0.2 | built ✅ | 2026-10-01 | 2 |

## 使用方法

```bash
# 1. 准备图库：把每张小图做成 8x8 的成分图 + 匹配系数（图库 = 目录 + tables.mxt）
metapixel -w 8 -h 8 --prepare tile.png  library/tile  library/tables.mxt

# 2. 生成经典马赛克
metapixel -w 8 -h 8 -d 0 --library library --metapixel target.png mosaic.png

# 3. 拼贴模式
metapixel -w 8 -h 8 -d 0 --library library --collage --metapixel target.png collage.png

# 附带的辅助程序
metapixel-imagesize mosaic.png      # 打印图片宽高
convert < config.lisp               # 成分图数据转换
```

批量配图库可用随包的 Perl 封装（等价于循环调用上面的 `--prepare`）：

```bash
metapixel-prepare --recurse --width 8 --height 8 ./原图目录 ./library
```

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**（2 个，均为纯 API 兼容修复，不含任何平台宏）:

1. `0001-rwimg-rwgif-c-giflib5-error-out-parameters.patch` —
   giflib 5.0 给 `DGifOpenFileName()` / `DGifCloseFile()` 各加了一个
   `int *Error` 出参，1.0.2 仍按 1 参形式调用。
2. `0002-rwimg-rwpng-c-libpng-opaque-struct-access.patch` —
   libpng 1.5 起 `png_struct` / `png_info` 变为不透明类型，读侧整体迁移到
   `png_get_*` 访问器，写侧那 12 行手工赋值折叠成一次 `png_set_IHDR()`。

`rwjpeg.c` 零改动：libjpeg-turbo 3.x 仍保留 libjpeg 6 的 API 面。

**编译依赖**: libpng 1.6.58.3 / libjpeg-turbo 3.2.0 / giflib 5.2.2 / zlib 1.3.2

**构建系统**: makefile（顶层 Makefile + `rwimg/Makefile` 两份手写 Makefile）

### 适配取舍

- 三个图像格式后端（`RWIMG_JPEG` / `RWIMG_PNG` / `RWIMG_GIF`）**全部保留**。
  GIF 读 + JPEG 写是 1.0.2 的主打特性，砍掉任一个都等于裁剪软件。
- 跳过 `metapixel.1` 的 `xsltproc` 重新生成。那是文档再生成步骤，发布 tarball
  已带生成好的同一个文件，直接打包即可，不改变任何交付产物。
- 产物按共享库 + RUNPATH 链接（`-Wl,-rpath,<dep libdir>`），不依赖 conanrun
  环境即可启动。**不要**改用 `-static-pie`：本 OHOS sysroot 缺 `rcrt1.o`。

## 验证结果

### 功能测试

`test_package` 真实执行 OHOS aarch64 产物跑完整马赛克流程，**17/17 通过**：
夹具生成、版本/帮助、配图库（PNG+JPEG+GIF 三种后端全部解码）、经典马赛克（PNG 与
JPEG 输出，且能被随包 `metapixel-imagesize` 读回 64x64）、拼贴模式、
wavelet 度量、`convert` 解析 lisp 配置。

### 质量门禁

| 阶段 | 结论 |
|---|---|
| G0 知识图谱完整性 | pass |
| L0 配方质量门禁 | pass |
| KC 知识一致性 | pass |
| JC 冗余/垃圾文件 | pass |
| L1 测试执行真实性（含 L1e 反向测试） | pass |
| L2 冒烟（`--version` / `--help`） | pass |
| L4 补丁危险函数扫描 | pass（无 strcpy/sprintf/gets/strcat） |
| L5 产物完整性 | pass |

### 鸿蒙专项验证

`test_ohos/run_ohos_test.sh` **5/5 通过**：aarch64 ELF、无宿主绝对路径泄漏、
走 OHOS musl 加载器、三个图像后端均可经 RUNPATH 解析、真实跑通一次马赛克。

## 源码信息

- 上游官网: https://www.complang.tuwien.ac.at/schani/metapixel/（下载链接已失效）
- 实际取源: https://deb.debian.org/debian/pool/main/m/metapixel/metapixel_1.0.2.orig.tar.gz
- sha256: `8d77810978da397c070b9b4e228ae6204e9f5c524518ad1a4fcab9462171f55b`
- 校验和与 Debian `.dsc`（md5）及 Gentoo distfiles Manifest（sha512）双向核对一致

## 相关资源

- 详细适配笔记: [`1.0.2/notes.md`](1.0.2/notes.md)
- 配方: [`1.0.2/conanfile.py`](1.0.2/conanfile.py)
