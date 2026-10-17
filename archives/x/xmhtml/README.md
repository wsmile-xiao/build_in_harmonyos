# XmHTML

Motif HTML 3.2 widget library：为 X Toolkit / Motif 应用提供可嵌入的 HTML 查看器 widget（`xmHTMLWidgetClass`）。

- 上游：<https://sourceforge.net/projects/xmhtml/>（上游 `www.xmhtml.org` 与 SourceForge release 文件均已不可达，源码取 **FreeBSD ports 权威 distfile** `XmHTML-1.1.10.tgz`，与 `x11-toolkits/xmhtml/distinfo` 一致）
- 许可：LGPL-2.0
- 构建系统：上游**手写 Makefile**（`Makefile` + `Makefile.motif`；无 configure / Imake / CMake，也**无 install 目标**）
- 包类型：**库**（`libXmHTML.a` + `libXmHTML.so.1.1.10`；无 CLI ⇒ 无 `commands.json`）

## 版本矩阵

| 版本 | 状态 | 适配方式 | 补丁 | 备注 |
| --- | --- | --- | --- | --- |
| 1.1.10 | built | 手写 Makefile 直编 + 交叉 clang（上游覆盖点 `EXTRA_CFLAGS` / `EXTRA_INCLUDES` / `LOADLIBES`） | 0 | 零源码补丁；W3 conan-verify G0–G4 + L2/L4/L5 全绿 |

## 依赖组合

`motif/2.3.8`、`libxmu/1.3.1.1`、`libxt/1.3.1`、`libxext/6.4.0.1`、`libx11/1.8.13`(force)、`xorgproto/2025.1`、
`libsm/1.2.6`、`libice/1.1.2`、`libxpm/3.5.17`、`libxft/2.3.9`、`libxrender/0.9.12`、`freetype/2.14.3`、
`fontconfig/2.18.3`、`libpng/1.6.58.3`、`libjpeg-turbo/3.2.0`、`zlib/1.3.2`。

## 适配要点

- **Xft 属公共接口**：`XmHTML.h` 在 `HAVE_XFT=1` 时链入 `<X11/Xft/Xft.h>` → 进而 `<X11/extensions/Xrender.h>`，
  因此 `libxft`/`libxrender`/`fontconfig`/`freetype` 必须是**直接依赖**且保持 `transitive_headers=True`，
  否则消费者拿到 `.so` 却缺头文件。
- **freetype 头在 `include/freetype2`**（`ft2build.h` 不在 include 根）→ 构建期需补该子目录（及 `include/fontconfig`）。
- **无 install 目标**：制品由 `package()` 显式收集（`include/XmHTML/*.h`、`include/common/*.h`、库文件），
  并补 `libXmHTML.so.1.1` 与 `libXmHTML.so` 软链（HMDFS 不能 `ln -sf` 覆盖 ⇒ 先删后建）。
- **零补丁**：上游特性宏已把 musl 缺口（`rindex`/`bcopy`/`bzero`/`bcmp`/`sys_errlist`）挡在编译路径之外
  （实测 `-Wimplicit-function-declaration` 0 条、链接期 0 undefined）。
- **版本组合要点**：`motif`/`libxt` pin `libx11/1.8.13`，而 `libxext` pin `libx11/6.4.0`
  ⇒ `libx11/1.8.13` + `force=True`，并选用 `libxext/6.4.0.1`。

## 测试

- 上游 tarball **无 tests/ 目录**，Makefile 无 `check`/`test` 目标（清点见版本目录 `test_package/MANIFEST.yml`）。
- 本包自带 `test_package/`（L1 explicit，N=1）：`test_xmhtml_consumer.c`（10 断言，分解见 `test_package/MANIFEST.yml`：
  版本串 2 + 数值版本 1 + 类符号 1 + 头宏 1 + 构建/运行前置 2 + 脚本分类/降级验证 3）
  + `test_xmhtml_consumer.sh`（运行期加载校验与分级判据）。
- 实测详情与如实回填见 `1.1.10/reports/test-report.md`。

## 知识沉淀

- 知识库扩展包：`knowledge/drafts/ohos-loader-refused-map-gap/`
  （`README.md` + `detect_loader_refused_map.py` + `reproduce.sh`）——覆盖
  "已发布依赖二进制存在却被设备拒绝映射" 这一类共性问题：判据、处置分级、禁 stub 顶替、边界实测。
- 条目草稿：`knowledge/drafts/DRAFT-xmhtml-1.1.10-ohos-loader-refused-dependency-map.{kv,md}`。
