# libdrawtext 0.6 适配笔记

## 结论

- **适配路径：路径 B（知识库扩展）**。上游自身提供无 GL 构建分支（基础
  适配零构建补丁）；消费者级符号审计发现公共头文件↔库导出符号契约漂移，
  沉淀为路径 B 知识草稿 E566（见文末「本次知识贡献」）。
- **构建结果**：OHOS armv8（ohos-aarch64 profile）`conan create` 通过，
  test_package 真实运行全绿。
- **补丁：1**（`patches/0001-glyphmap-image-export.patch`，bugfix 类）：
  公共头文件与库导出符号契约修复，详见下文「符号契约修复」。

## 上游核实（W0/W1）

| 项 | 结果 |
|---|---|
| 仓库 | https://github.com/jtsiomb/libdrawtext（John Tsiombikas） |
| 版本 | v0.6 tag（2018-11-03 发布的正式 tag） |
| 归档 | `.../archive/refs/tags/v0.6.tar.gz`，81726 字节 |
| SHA256 | `714d94473622d756bfe7d70ad6340db3de7cc48f4f356a060e3cb48900c6da01`（两次独立下载一致，并与 Homebrew formula 一致） |
| 许可证 | LGPL-3.0-or-later（COPYING.LESSER，包内 `licenses/` 收录） |
| 构建系统 | 自定义 `sh configure`（往 `Makefile.in` 前置小段头）→ 纯 make |
| 依赖 | freetype2（默认启用；`--disable-freetype` 可关）、pthread |
| GL | 默认 `-lGL -lGLU`（桌面 GL + GLU）；OHOS 均无 |

## 构建适配（make 变量注入，零补丁）

`configure` 只把 PREFIX 与 freetype 开关烘进 Makefile；CC/AR/CFLAGS/
LDFLAGS 全部可在 make 命令行覆盖，因此无需补丁：

```sh
./configure --prefix=<stage> --enable-freetype
make -j1 CC=clang AR=llvm-ar \
     CFLAGS="-O2 -g -fPIC -DUSE_THREADS -DNO_OPENGL -I<conan-freetype>/include" \
     LDFLAGS="-L<conan-freetype>/lib -lfreetype -lpthread"
```

- `-DNO_OPENGL`：上游 `src/drawgl.c` 的 `#ifndef NO_OPENGL` 官方 stub
  分支（`dtx_target_opengl()` 变为告警 no-op）。公共 API 完整保留。
- freetype 头路径直指 Conan 依赖包（其头在 `include/freetype2`，非
  `include/`）；不用 pkg-config（见下）。
- `-Wno-unused-command-line-argument`：OHOS clang 包装器在编译步注入
  链接器标志，避免 `-Wall` 噪声。
- **E525**：`make -j1`，上游隐式 `.d` 依赖非并行安全。

## 不用 pkg-config 的原因（E075/E468 相关）

上游 Makefile 以反引号内联 `pkg-config --cflags freetype2`。Conan 缓存
的 freetype/2.14.3 包虽带 `lib/pkgconfig/freetype2.pc`，但其
`libdir=//lib`（相对前缀 `/`）为坏路径——`--libs` 会产出错误的 `-L`。
配方整体覆盖 CFLAGS/LDFLAGS，freetype 路径直接取自 Conan 依赖图，
彻底绕开该 .pc。

## 符号契约修复（patches/0001-glyphmap-image-export.patch）

消费者级双向符号审计（包内 so `nm -D` ↔ `drawtext.h` 公共声明）发现一处
真实契约漂移：**头文件声明但库不导出** `dtx_get_glyphmap_image`
（drawtext.h:121，无条件声明），而库实际导出的同名功能符号是
`dtx_get_glyphmap_pixels`（font.c:721，返回 `gmap->pixels` 借用指针，
签名/所有权/语义完全一致）。外部消费者直接调用 `dtx_get_glyphmap_image`
必然 undefined reference——这不是 OHOS 特有问题，任何链接该库的下游
都在受损，只是上游 0.6 的 examples/tools 均未直接调用该 API 故未暴露。

修复（最小、保守）：

- 库内新增转发别名 `dtx_get_glyphmap_image` → `dtx_get_glyphmap_pixels`
  （保留 `_pixels` 原符号，不破坏既有消费者）；
- 公共头补齐 `dtx_get_glyphmap_pixels` 声明（库导出但头未声明的反向
  漂移，补上后双向一致）；
- `dtx_vertex_attribs`（drawgl.c `#ifndef NO_OPENGL` 块内）属条件编译
  非真实缺失，不处理。

反向验证：**无补丁时**消费者直接调用 `dtx_get_glyphmap_image` 链接失败
（undefined reference to `dtx_get_glyphmap_image`）；**有补丁时**编译、
链接、运行全通过且两符号返回同一指针（真别名）。补丁以
`apply_conandata_patches` 接入 build()（a52dec/0.7.4 先例），
`patch_type: bugfix`。

双向集合复核（包内 so `nm -D` ↔ `drawtext.h`，白名单口径）：

- **声明未导出**：补丁前为 `dtx_get_glyphmap_image` +
  `dtx_vertex_attribs`；补丁后仅剩 `dtx_vertex_attribs`
  （drawgl.c:184 `#ifndef NO_OPENGL` 条件块内，非真实漂移，豁免）。
- **导出未声明**：补丁前为 `dtx_get_glyphmap_pixels` + 20 个内部符号；
  补丁后 `dtx_get_glyphmap_pixels` 已补声明（出列），仅剩内部实现
  符号（tpool.h 的 13 个 `dtx_tpool_*`、drawtext_impl.h 的
  `dtx_proc_char`/`dtx_gl_(get|set)opt`/`dtx_rast_(get|set)opt`）与
  链接器产物 `_fini`/`_init`——公共头从未承诺，属老库无 visibility
  控制的常态，非契约漂移，豁免。
- 两个方向的真实漂移经补丁后均为 0，且补丁增量精确（导出集恰新增
  `dtx_get_glyphmap_image`，声明集恰新增 `dtx_get_glyphmap_pixels`，
  无其他变化）。

## 打包（E492）

上游 `make install` 在 DESTDIR 树内建 `libdrawtext.so → .so.0 →
.so.0.5` 符号链接链。`package()` 按 **E492** 将 `libdrawtext.so` 与
`libdrawtext.so.0` 物化为 `libdrawtext.so.0.5` 的真实文件副本：
包重定位后不悬空；SONAME（`libdrawtext.so.0`）与 ELF `DT_SONAME` 保持
一致（readelf 验证）。

## ELF 验证

```
$ readelf -d libdrawtext.so.0.5
(SONAME) Library soname: [libdrawtext.so.0]
(NEEDED) Shared library: [libfreetype.so.6]
(NEEDED) Shared library: [libc.so]
```

无 GL/EGL 依赖；`dtx_target_raster/dtx_string/dtx_use_font/dtx_open_font`
等全套 API 符号导出（llvm-nm -D 验证）。

## 上游测试清点（R51 三步法，全新解压复核）

清点对象：`libdrawtext-0.6.tar.gz`（SHA256 `714d9447…c6da01`，与 conandata
一致）全新解压于独立目录，日志存 `~/tmp/r51-fresh/r51-inventory.log`。

可审计命令与结论：

```sh
# 1) 测试目录：无输出 → 0 个
find . -type d \( -iname test -o -iname tests -o -iname testing -o -iname check \)
# 2) test/check 目标：无输出 → 0 个
grep -nE "^[a-zA-Z_-]*(test|check|installcheck|check-local)[a-zA-Z_-]*:" Makefile.in configure
grep -n "installcheck\|check-local\|make check\|make test" Makefile.in configure README.md
# 3) 测试框架/源文件：无输出 → 0 个
find . -name CMakeLists.txt -o -name meson.build -o -name Makefile.am \
     -o -name pytest.ini -o -name "*.yml" -o -name "*.yaml"
find . -name "*test*.c" -o -name "*test*.cc" -o -name "*test*.cpp" -o -name "*test*.h"
```

| 类别 | 数量 | 对应文件/目标 |
|---|---|---|
| 正式单元测试 | 0 | — |
| 正式集成测试 | 0 | — |
| 其他正式测试 | 0 | — |

上游 v0.6 测试总数 **0**（无 tests/ 目录、无 check/test/installcheck 目标、
无任何框架注册）。全部实际执行：N/A（0 项，无失败）。

### examples/tools 单独归类（非上游测试，补充验证）

examples/ 为 GL 演示程序（simple/unicode/userdraw/distfield/nofreetype 需
GLEW+GLUT 或桌面 GL，OHOS 无）；其中唯一 `assert` 出现在 distfield.c 但
仅 include 未用于测试断言（GL 交互演示）。按要求对安全可执行者做了
编译+运行补充验证（**不冒充上游测试**）：

| 程序 | 模式 | 结果 | 退出码 |
|---|---|---|---|
| examples/raster（无 GL 依赖，serif.ttf 换用系统 HarmonyOS_Sans.ttf） | 默认 32 次 | 输出 output.ppm，223197/307200 非背景像素 | 0 |
| examples/raster | `-blend` 1000 次 | 292117 非背景像素，26ms | 0 |
| examples/raster | `-opaque` 64 次 | 输出正常 | 0 |
| tools/font2glyphmap（CLI） | `-size 24` ASCII | 生成 HarmonyOS_Sans_s24.glyphmap（270468B，P5 格式） | 0 |
| tools/font2glyphmap | `-dist` 距离场 | 512 行扫描全跑 + 线程池 20 worker 收尾 + 缩放 | 0 |

（examples/raster/RUN 脚本调 X11 `display`，无法在 OHOS 运行——仅作记录。）


## test_package（消费者集成测试，R34/R40）

**1 个集成测试用例**：`test.c` 直接链接消费者可执行程序（上层应用
视角）——编译 `-I<package>/include` + `-L<package>/lib -ldrawtext`，
仅用包内 `drawtext.h` 与 `libdrawtext.so`，不引用源码目录。直接调用
完整公开 API 链（非 dlsym 函数指针）：

```
dtx_open_font → dtx_target_raster → dtx_use_font → dtx_prepare_range →
dtx_position → dtx_string（ASCII + UTF-8 CJK）→ dtx_string_width/height →
dtx_get_font_glyphmap → dtx_get_glyphmap_width/height →
dtx_get_glyphmap_image（补丁 0001 补上导出）→ dtx_close_font
```

glyphmap 像素断言直接调用公共头声明的 `dtx_get_glyphmap_image` 内存
遍历（补丁 0001 后可链接），并验证与 `dtx_get_glyphmap_pixels` 返回
同一指针（真别名）。

| # | 用例内部断言（不单独计数） | 实测 |
|---|---|---|
| 1 | 渲染缓冲非零像素 ≥ 500（字符真实写入像素） | 1462 像素 |
| 2 | 清零重渲染像素再次出现（非残留背景） | ok |
| 3 | `dtx_string_width/height` 度量 > 0 且量级合理 | 176.0×34.0 |
| 4 | glyphmap 非空 + `dtx_get_glyphmap_image` == `dtx_get_glyphmap_pixels` | 512×512，33886 墨水像素 |
| 5 | 资源正常释放（`dtx_close_font`）且退出码 0 | ok |

补充检查（不单独计数）：`-DSYMBOL_PROBE` 编译的 `test_probe` 用
dlopen SONAME 库 + 14 个核心符号 dlsym 解析（运行时符号视图，含补丁
符号 `dtx_get_glyphmap_image`）。消费者可执行文件 `readelf -d` 可见
**NEEDED libdrawtext.so.0**。

## test_ohos.sh（鸿蒙特有测试，独立统计）

按硬性要求新增 1 个鸿蒙特有测试，独立执行、独立统计（test() 中单独
`self.run` 一条），任一失败即非零退出：

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 包内安装产物 `lib/libdrawtext.so.0` 存在 | ok |
| 2 | readelf -h：ELF64 + AArch64 | ok |
| 3 | readelf -d：SONAME == libdrawtext.so.0 | ok |
| 4 | readelf -d：NEEDED 含 libfreetype.so.6 | ok |
| 5 | readelf -d：NEEDED 无桌面 GL（libGL/GLU/GLEW/GLUT/EGL/OSMesa） | ok |
| 6 | readelf -SW：.codesign 段存在（E212） | ok |
| 7 | 软件光栅化消费者真实运行（NO_OPENGL）+ 消费者 NEEDED soname | ok |

字体取自系统字体回退链（HarmonyOS_Sans_SC → HarmonyOS_Sans →
FZHeiT-SC-Regular），覆盖 ASCII 与 CJK（U+4E2D，走 utf8.c 多字节
路径）。运行环境按 **E505** 收集全部依赖 lib 目录（含传递依赖
freetype）至 LD_LIBRARY_PATH。

```console
$ conan create ... -tf=test_package
ok: rendered 1462 nonzero pixels
ok: re-render after clear
ok: string metrics 176.0x34.0
ok: glyphmap 512x512, 33886 ink pixels (image==pixels)
ALL TESTS PASSED            # test_consumer（直接链接）
ok: dlopen .../lib/libdrawtext.so
ok: all 14 symbols resolved
ALL TESTS PASSED            # test_probe（符号补充检查）
OHOS TESTS PASSED           # test_ohos.sh（鸿蒙特有，独立统计）
```

## 知识库使用记录

| 知识 | 用途 |
|---|---|
| E075 | 环境变量/pkg-config 陷阱认知（促成绕开 .pc 的决策） |
| E095 | 自定义 configure 的编译器注入（CC/AR 命令行覆盖） |
| E492 | SONAME 链别名的物化 |
| E505 | test 运行时 LD_LIBRARY_PATH 收集依赖 lib 目录 |
| E525 | make -j1 |
| E348 | freetype 传递依赖声明（transitive_headers） |

（E321-B1GL 草稿不适用：gl4es 面向“必须有桌面 GL 固定管线”的软件；
libdrawtext 有官方 NO_OPENGL 分支，核心能力不经 GL。）

## 本次知识贡献（路径 B）

- ✅ K1（new_draft → E566）：公共头文件与 ELF 动态库导出符号契约漂移
  ——双向审计（声明未导出/导出未声明）与最小别名修复，跨库可复用
  （knowledge_ref: knowledge/drafts/E566-draft-header-export-symbol-contract-drift.kv）

## 本机工具链备注

- profile 引用的 `/data/service/hnp/ohos-sdk.org/...` clang 路径在本机
  不存在；实际可用的是 PATH 上的 `clang`（clang 15.0.4，随包装器注入
  OHOS sysroot）。配方对 CC 的解析顺序：profile 显式路径（存在且可执
  行才用）→ 环境变量 → PATH。
- 本机即目标机（OHOS PC aarch64），test_package 可原生运行。

---

**编译结束**: 2026-09-08
**最终状态**: built
