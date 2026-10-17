# libtk-img (Img / TkImg) 2.1.1 — 测试报告（OHOS PC / aarch64）

- 目标库：`libtk-img` 2.1.1（上游工程名 TkImg，发行包 `Img-2.1.1.tar.gz`）
- 平台：HarmonyOS PC / HongMeng Kernel（`os=OHOS`，arch=armv8，clang 15，Release）
- Conan：2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 包引用：`libtk-img/2.1.1`（CI 形态：`conan create <pkg_dir>` 不带 user/channel）
- 日期：2026-10-08

## 日志留存说明

按仓库 `docs/TEST_QUALITY_SPEC.md` 与归档惯例，**原始日志不随 PR 提交**（体积 + AI 检视规模）。
本报告把上游测试的**逐用例结论**完整内联（315 行），并给出本地复现方式；
构建日志请按 §5 的命令在本地重新生成。

---

## 1. 源码核验

| 项 | 值 |
|---|---|
| 上游工程 | SourceForge `tkimg`（Tcl/Tk image format extension，又称 Img / TkImg） |
| 发行包 | `Img-2.1.1.tar.gz` |
| URL | `https://downloads.sourceforge.net/project/tkimg/tkimg/2.1/tkimg%202.1.1/Img-2.1.1.tar.gz` |
| 大小 | 12,451,223 B |
| sha256 | `0e41efa886c470ca0c38663e66640eb6d89e9e5f746724535ac224e2509ae34f`（实测） |
| 压缩格式 | tar.gz |
| 校验 | `sha256sum` 与 `conandata.yml` 一致；`conan create` 首次 `get()` 校验通过 |

**为何用 `downloads.sourceforge.net` 直链**：`/download` 形式会 302 到镜像并可能返回
HTML 页面，conan 的 `get()` 会报解压/校验失败；直链可跟随重定向拿到真实 gzip。

## 2. 上游测试入口核验

上游构建系统是 TEA（Tcl Extension Architecture），**没有 `make check`**。顶层
`Makefile.in` 中与测试相关的目标是：

```makefile
test: all tcltests visualtests dpitests
tcltests:
	cd tests && tclsh all.tcl
visualtests:
	cd tests/visualtests && tclsh RunTests --auto
dpitests:
	cd tests/dpitests && tclsh DpiReadWrite.tcl
```

| 入口 | 位置 | 本报告是否纳入 | 原因 |
|---|---|---|---|
| `tcltests` | `tests/all.tcl` + 19 个 `*.test` | ✅ 真实执行 | tcltest 框架，纯软件、可完全自动化 |
| `visualtests` | `tests/visualtests/RunTests` | ❌ | 需要真实显示设备 / 人工目视比对 |
| `dpitests` | `tests/dpitests/DpiReadWrite.tcl` | ❌ | 依赖屏幕 DPI，需真实 X 屏幕 |
| `bmpsuite` / `pngsuite` | `tests/bmpsuite/RunBmpTests.tcl`、`tests/pngsuite/RunPngTests.tcl` | ❌ | 独立于 `*.test` 的第三方图像集脚本，未被 `all.tcl` 收集 |

`tests/all.tcl` 的实现（关键片段）：

```tcl
puts "Using Tcl version: [info patchlevel] (${bits}-bit)"
puts "Using Tk  version: [package require Tk] (${bits}-bit)"
puts "Using Img version: [package require Img]"
package require tcltest
package require Img
proc tcltest::cleanupTestsHook {} { ... set ::exitCode [expr {$numTests(Failed) > 0}] }
::tcltest::configure -testdir [file dirname [file normalize [info script]]]
eval ::tcltest::configure $argv
::tcltest::runAllTests
exit $exitCode
```

因此：**上游有真实自动化测试入口**（`tests/all.tcl`，由 `*.test` 目录自动收集），
本次真实执行并统计；`test_package` 的结论**不用于替代**上游统计（见 §4）。

## 3. 适配新增的鸿蒙测试用例（必备项）

按任务要求「适配后的上游测试用例必须至少新增一个鸿蒙测试用例（消费者用例测试可行性）」，
本次以补丁形式新增 **`tests/ohos.test`**（25 个 tcltest 用例），由 `tests/all.tcl`
自动收集执行：

| 用例 | 断言内容 |
|---|---|
| `ohos-0.1` | `package require Img` 返回 `2.1.1`（主包在 OHOS 上可加载） |
| `ohos-0.2` | `info sharedlibextension` == `.so`（OHOS 消费者 load 机制） |
| `ohos-0.3` | `tcl_platform(platform)` == `unix` 且 `pointerSize` == 8 |
| `ohos-0.4` | 宿主 OS 标识属 OHOS 系（HarmonyOS / Linux） |
| `ohos-1.<fmt>` × 19 | 逐个 `package require img::<fmt>`：bmp gif ico jpeg pcx pixmap png ppm ps sgi sun tga tiff window xbm xpm dted raw flir —— 真实 dlopen 每个处理器 `.so` |
| `ohos-2.1` | 消费者真实读图：`image create photo -file testimgs/img.bmp` → 尺寸 40×7 |
| `ohos-2.2` | 消费者真实往返：写盘 → 重新读回 → 逐像素一致（`imageCompare` 返回 1） |

补丁：`patches/0001-ohos-consumer-test.patch`（仅**新增**文件，不改动任何上游既有代码）。
实测 `patch -p1 --dry-run` 干净通过，无 `.orig`/`.rej` 残留。

## 4. 上游测试真实执行结果（层 1）

### 4.1 测试命令

```bash
# 与上游 Makefile 的 `tcltests`（cd tests && tclsh all.tcl）语义等价
cd <build>/tests
LD_LIBRARY_PATH="<tcl>/lib:<tk>/lib:<libx11>/lib:<libxcb>/lib:<libxau>/lib:<libxdmcp>/lib" \
TCLLIBPATH="<build>/_stage/lib/Img2.1.1 <tcl>/lib <tk>/lib" \
timeout 2400 <tcl包>/bin/tclsh9.0 <build>/_unbuffered_all_tcl.tcl <build>/tests/all.tcl
```

说明：
- 宿主默认 `PATH` 上没有 `tclsh`（它来自 tcl conan 包），上游 `tcltests` 目标里的裸
  `tclsh` 在 CI 会 `127`，故用 tcl 包内 `bin/tclsh9.0` 绝对路径执行同一入口脚本。
- `<build>/_unbuffered_all_tcl.tcl` 是配方在构建期生成的无缓冲包装器
  （`fconfigure stdout -buffering none`），并额外注入 `-verbose "pass skip fail error"`
  以便逐用例留证。
- OHOS 上解释器退出路径可能被 Tk 拆除拖住，故用 `timeout` 包裹；无缓冲保证超时强杀
  时不丢已打印结果。

### 4.2 原始输出（尾部汇总）

```
Tests began at 2026-10-08 23:09:19 +0800
bmp.test / dted.test / flir.test / gif.test / ico.test / jpeg.test / ohos.test /
pcx.test / pdf.test / pixmap.test / png.test / ppm.test / ps.test / raw.test /
sgi.test / sun.test / tga.test / tiff.test / xbm.test / xpm.test
Tests ended at 2026-10-08 23:09:43 +0800
all.tcl:	Total	315	Passed	297	Skipped	18	Failed	0
Sourced 20 Test Files.
Number of tests skipped for each constraint:
	18	Ghostscript
```

退出码：`0`（`tcltest::cleanupTestsHook` 以 `numTests(Failed) > 0` 决定 `::exitCode`）。

### 4.3 统计

| 指标 | 数值 |
|---|---|
| 测试命令 | `tclsh9.0 <build>/_unbuffered_all_tcl.tcl <build>/tests/all.tcl`（等价上游 `make tcltests`） |
| 测试文件 | **20**（上游 19 个 `*.test` + 新增 `ohos.test`） |
| 用例总数 | **315** |
| 通过 | **297** |
| 失败 | **0** |
| 跳过 | **18** |
| 日志路径 | 构建期 `<build_folder>/upstream-tests.log`（本机复现：`reports/` 未随 PR 提交原始日志） |

跳过 18 例的**全部原因**是上游 `constraints.tcl` 的 `Ghostscript` 约束未满足
（`haveGs` 依次探测 `gs` / `gswin64c.exe` / `gswin32c.exe`，OHOS 宿主无 ghostscript）：

| 跳过用例 | 数量 |
|---|---|
| `pdf-1.1` `pdf-1.2` `pdf-1.3` `pdf-1.4` `pdf-1.5` `pdf-2.1` `pdf-2.2`(×2) `pdf-5.7` | 9 |
| `ps-1.1` `ps-1.2` `ps-1.3` `ps-1.4` `ps-1.5` `ps-2.1` `ps-2.2`(×2) `ps-5.7` | 9 |

这与平台适配无关（属于外部工具缺失），且上游在同一条件下会得到相同的跳过集合。

### 4.4 每文件分布

| 测试文件 | 总数 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| bmp.test | 19 | 19 | 0 | 0 |
| dted.test | 11 | 11 | 0 | 0 |
| flir.test | 13 | 13 | 0 | 0 |
| gif.test | 14 | 14 | 0 | 0 |
| ico.test | 14 | 14 | 0 | 0 |
| jpeg.test | 16 | 16 | 0 | 0 |
| **ohos.test（新增）** | **25** | **25** | 0 | 0 |
| pcx.test | 19 | 19 | 0 | 0 |
| pdf.test | 16 | 7 | 0 | 9 |
| pixmap.test | 8 | 8 | 0 | 0 |
| png.test | 19 | 19 | 0 | 0 |
| ppm.test | 14 | 14 | 0 | 0 |
| ps.test | 17 | 8 | 0 | 9 |
| raw.test | 14 | 14 | 0 | 0 |
| sgi.test | 14 | 14 | 0 | 0 |
| sun.test | 14 | 14 | 0 | 0 |
| tga.test | 14 | 14 | 0 | 0 |
| tiff.test | 22 | 22 | 0 | 0 |
| xbm.test | 18 | 18 | 0 | 0 |
| xpm.test | 14 | 14 | 0 | 0 |
| **合计** | **315** | **297** | **0** | **18** |

### 4.5 逐用例清单

### `bmp` — total 19 / pass 19 / fail 0 / skip 0

```
bmp-0.1        PASSED
bmp-1.1        PASSED
bmp-1.2        PASSED
bmp-1.3        PASSED
bmp-1.4        PASSED
bmp-1.5        PASSED
bmp-2.1        PASSED
bmp-2.2        PASSED
bmp-3.1        PASSED
bmp-4.1        PASSED
bmp-5.1        PASSED
bmp-5.2        PASSED
bmp-5.3        PASSED
bmp-5.4        PASSED
bmp-5.5        PASSED
bmp-5.6        PASSED
bmp-5.7        PASSED
bmp-5.8        PASSED
bmp-5.9        PASSED
```

### `dted` — total 11 / pass 11 / fail 0 / skip 0

```
dted-0.1       PASSED
dted-1.1       PASSED
dted-1.2       PASSED
dted-1.3       PASSED
dted-1.4       PASSED
dted-1.5       PASSED
dted-2.1       PASSED
dted-5.1       PASSED
dted-5.2       PASSED
dted-5.3       PASSED
dted-5.4       PASSED
```

### `flir` — total 13 / pass 13 / fail 0 / skip 0

```
flir-0.1       PASSED
flir-1.1       PASSED
flir-1.2       PASSED
flir-1.3       PASSED
flir-1.4       PASSED
flir-1.5       PASSED
flir-2.1       PASSED
flir-3.1       PASSED
flir-3.2       PASSED
flir-5.1       PASSED
flir-5.2       PASSED
flir-5.3       PASSED
flir-5.4       PASSED
```

### `gif` — total 14 / pass 14 / fail 0 / skip 0

```
gif-0.1        PASSED
gif-1.1        PASSED
gif-1.2        PASSED
gif-1.3        PASSED
gif-1.4        PASSED
gif-1.5        PASSED
gif-2.1        PASSED
gif-3.1        PASSED
gif-5.1        PASSED
gif-5.2        PASSED
gif-5.3        PASSED
gif-5.5        PASSED
gif-5.6        PASSED
gif-5.7        PASSED
```

### `ps` — total 17 / pass 8 / fail 0 / skip 9

```
ps-5.4         PASSED
ps-0.1         PASSED
ps-1.1         SKIPPED  (Ghostscript)
ps-1.2         SKIPPED  (Ghostscript)
ps-1.3         SKIPPED  (Ghostscript)
ps-1.4         SKIPPED  (Ghostscript)
ps-1.5         SKIPPED  (Ghostscript)
ps-2.1         SKIPPED  (Ghostscript)
ps-2.2         SKIPPED  (Ghostscript)
ps-2.2         SKIPPED  (Ghostscript)
ps-5.1         PASSED
ps-5.2         PASSED
ps-5.3         PASSED
ps-5.4         PASSED
ps-5.5         PASSED
ps-5.6         PASSED
ps-5.7         SKIPPED  (Ghostscript)
```

### `ico` — total 14 / pass 14 / fail 0 / skip 0

```
ico-0.1        PASSED
ico-1.1        PASSED
ico-1.2        PASSED
ico-1.3        PASSED
ico-1.4        PASSED
ico-1.5        PASSED
ico-2.1        PASSED
ico-3.1        PASSED
ico-5.1        PASSED
ico-5.2        PASSED
ico-5.3        PASSED
ico-5.4        PASSED
ico-5.5        PASSED
ico-5.6        PASSED
```

### `jpeg` — total 16 / pass 16 / fail 0 / skip 0

```
jpeg-0.1       PASSED
jpeg-1.1       PASSED
jpeg-1.2       PASSED
jpeg-1.3       PASSED
jpeg-1.4       PASSED
jpeg-1.5       PASSED
jpeg-2.1       PASSED
jpeg-2.2       PASSED
jpeg-3.1       PASSED
jpeg-4.1       PASSED
jpeg-5.1       PASSED
jpeg-5.2       PASSED
jpeg-5.3       PASSED
jpeg-5.4       PASSED
jpeg-5.5       PASSED
jpeg-5.6       PASSED
```

### `ohos` — total 25 / pass 25 / fail 0 / skip 0

```
ohos-0.1       PASSED
ohos-0.2       PASSED
ohos-0.3       PASSED
ohos-0.4       PASSED
ohos-1.bmp     PASSED
ohos-1.gif     PASSED
ohos-1.ico     PASSED
ohos-1.jpeg    PASSED
ohos-1.pcx     PASSED
ohos-1.pixmap  PASSED
ohos-1.png     PASSED
ohos-1.ppm     PASSED
ohos-1.ps      PASSED
ohos-1.sgi     PASSED
ohos-1.sun     PASSED
ohos-1.tga     PASSED
ohos-1.tiff    PASSED
ohos-1.window  PASSED
ohos-1.xbm     PASSED
ohos-1.xpm     PASSED
ohos-1.dted    PASSED
ohos-1.raw     PASSED
ohos-1.flir    PASSED
ohos-2.1       PASSED
ohos-2.2       PASSED
```

### `pcx` — total 19 / pass 19 / fail 0 / skip 0

```
pcx-0.1        PASSED
pcx-1.1        PASSED
pcx-1.2        PASSED
pcx-1.3        PASSED
pcx-1.4        PASSED
pcx-1.5        PASSED
pcx-2.1        PASSED
pcx-2.2        PASSED
pcx-3.1        PASSED
pcx-4.1        PASSED
pcx-5.1        PASSED
pcx-5.2        PASSED
pcx-5.3        PASSED
pcx-5.4        PASSED
pcx-5.5        PASSED
pcx-5.6        PASSED
pcx-5.7        PASSED
pcx-5.8        PASSED
pcx-5.9        PASSED
```

### `pdf` — total 16 / pass 7 / fail 0 / skip 9

```
pdf-0.1        PASSED
pdf-1.1        SKIPPED  (Ghostscript)
pdf-1.2        SKIPPED  (Ghostscript)
pdf-1.3        SKIPPED  (Ghostscript)
pdf-1.4        SKIPPED  (Ghostscript)
pdf-1.5        SKIPPED  (Ghostscript)
pdf-2.1        SKIPPED  (Ghostscript)
pdf-2.2        SKIPPED  (Ghostscript)
pdf-2.2        SKIPPED  (Ghostscript)
pdf-5.1        PASSED
pdf-5.2        PASSED
pdf-5.3        PASSED
pdf-5.4        PASSED
pdf-5.5        PASSED
pdf-5.6        PASSED
pdf-5.7        SKIPPED  (Ghostscript)
```

### `pixmap` — total 8 / pass 8 / fail 0 / skip 0

```
pixmap-0.1     PASSED
pixmap-1.1     PASSED
pixmap-1.2     PASSED
pixmap-1.3     PASSED
pixmap-2.1     PASSED
pixmap-2.2     PASSED
pixmap-2.3     PASSED
pixmap-2.1     PASSED
```

### `png` — total 19 / pass 19 / fail 0 / skip 0

```
png-0.1        PASSED
png-1.1        PASSED
png-1.2        PASSED
png-1.3        PASSED
png-1.4        PASSED
png-1.5        PASSED
png-2.1        PASSED
png-2.2        PASSED
png-3.1        PASSED
png-4.1        PASSED
png-5.1        PASSED
png-5.2        PASSED
png-5.3        PASSED
png-5.4        PASSED
png-5.5        PASSED
png-5.6        PASSED
png-5.7        PASSED
png-5.8        PASSED
png-5.9        PASSED
```

### `ppm` — total 14 / pass 14 / fail 0 / skip 0

```
ppm-0.1        PASSED
ppm-1.1        PASSED
ppm-1.2        PASSED
ppm-1.3        PASSED
ppm-1.4        PASSED
ppm-1.5        PASSED
ppm-2.1        PASSED
ppm-3.1        PASSED
ppm-5.1        PASSED
ppm-5.2        PASSED
ppm-5.3        PASSED
ppm-5.4        PASSED
ppm-5.5        PASSED
ppm-5.6        PASSED
```

### `raw` — total 14 / pass 14 / fail 0 / skip 0

```
raw-0.1        PASSED
raw-1.1        PASSED
raw-1.2        PASSED
raw-1.3        PASSED
raw-1.4        PASSED
raw-1.5        PASSED
raw-2.1        PASSED
raw-3.1        PASSED
raw-5.1        PASSED
raw-5.2        PASSED
raw-5.3        PASSED
raw-5.4        PASSED
raw-5.5        PASSED
raw-5.6        PASSED
```

### `sgi` — total 14 / pass 14 / fail 0 / skip 0

```
sgi-0.1        PASSED
sgi-1.1        PASSED
sgi-1.2        PASSED
sgi-1.3        PASSED
sgi-1.4        PASSED
sgi-1.5        PASSED
sgi-2.1        PASSED
sgi-3.1        PASSED
sgi-5.1        PASSED
sgi-5.2        PASSED
sgi-5.3        PASSED
sgi-5.4        PASSED
sgi-5.5        PASSED
sgi-5.6        PASSED
```

### `sun` — total 14 / pass 14 / fail 0 / skip 0

```
sun-0.1        PASSED
sun-1.1        PASSED
sun-1.2        PASSED
sun-1.3        PASSED
sun-1.4        PASSED
sun-1.5        PASSED
sun-2.1        PASSED
sun-3.1        PASSED
sun-5.1        PASSED
sun-5.2        PASSED
sun-5.3        PASSED
sun-5.4        PASSED
sun-5.5        PASSED
sun-5.6        PASSED
```

### `tga` — total 14 / pass 14 / fail 0 / skip 0

```
tga-0.1        PASSED
tga-1.1        PASSED
tga-1.2        PASSED
tga-1.3        PASSED
tga-1.4        PASSED
tga-1.5        PASSED
tga-2.1        PASSED
tga-3.1        PASSED
tga-5.1        PASSED
tga-5.2        PASSED
tga-5.3        PASSED
tga-5.4        PASSED
tga-5.5        PASSED
tga-5.6        PASSED
```

### `tiff` — total 22 / pass 22 / fail 0 / skip 0

```
tiff-0.1       PASSED
tiff-1.1       PASSED
tiff-1.2       PASSED
tiff-1.3       PASSED
tiff-1.4       PASSED
tiff-1.5       PASSED
tiff-2.1       PASSED
tiff-2.2       PASSED
tiff-3.1       PASSED
tiff-4.1       PASSED
tiff-5.1       PASSED
tiff-5.2       PASSED
tiff-5.3       PASSED
tiff-5.4       PASSED
tiff-5.5       PASSED
tiff-5.6       PASSED
tiff-5.7       PASSED
tiff-5.8       PASSED
tiff-5.9       PASSED
tiff-5.10      PASSED
tiff-5.11      PASSED
tiff-5.12      PASSED
```

### `xbm` — total 18 / pass 18 / fail 0 / skip 0

```
xbm-0.1        PASSED
xbm-1.1        PASSED
xbm-1.2        PASSED
xbm-1.3        PASSED
xbm-1.4        PASSED
xbm-1.5        PASSED
xbm-2.1        PASSED
xbm-3.1        PASSED
xbm-5.1        PASSED
xbm-5.2        PASSED
xbm-5.3        PASSED
xbm-5.4        PASSED
xbm-5.5        PASSED
xbm-5.6        PASSED
xbm-5.7        PASSED
xbm-5.7        PASSED
xbm-5.8        PASSED
xbm-5.9        PASSED
```

### `xpm` — total 14 / pass 14 / fail 0 / skip 0

```
xpm-0.1        PASSED
xpm-1.1        PASSED
xpm-1.2        PASSED
xpm-1.3        PASSED
xpm-1.4        PASSED
xpm-1.5        PASSED
xpm-2.1        PASSED
xpm-3.1        PASSED
xpm-5.1        PASSED
xpm-5.2        PASSED
xpm-5.3        PASSED
xpm-5.4        PASSED
xpm-5.5        PASSED
xpm-5.6        PASSED
```

## 5. test_package（层 2，消费者视角）

`test_package/` 用 **tcl/9.0.3.2 包自带的 `tclsh9.0`**（OHOS aarch64 原生解释器）
真实启动，把 `libtk-img` 当成外部消费方，仅通过 `pkgIndex.tcl` → `load` →
`package require` 的公开机制使用它：

```bash
conan create archives/l/libtk-img/2.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="libtk-img/*"
# → test_package/test() 内执行:
LD_LIBRARY_PATH="<tcl>/lib:<tk>/lib:<libx11>/lib:<libxcb>/lib:<libxau>/lib:<libxdmcp>/lib" \
TCLLIBPATH="<pkg>/lib/Img2.1.1 <tcl>/lib <tk>/lib" \
timeout 600 /bin/sh run_test.sh <tcl包>/bin/tclsh9.0 test_consumer.tcl <pkg>/lib/Img2.1.1
```

`run_test.sh` 是 test_package 的入口脚本（仓库惯例，见 `archives/c/combat/0.8.1/test_package/`），
做参数/前置校验后 `exec` 真实的 `test_consumer.tcl`。宿主机 **没有 `/bin/bash`**（仅 `/bin/sh`），
故入口显式用 `/bin/sh`。

断言 31 项：

| 组 | 断言 |
|---|---|
| 1.1–1.4 | `package require Img` = 2.1.1；`info sharedlibextension` = `.so`；`pointerSize` = 8；`platform` = unix |
| 2.base + 2.<fmt> × 19 | 20 个处理器 `.so` 全部 dlopen 成功（`img::base` 及 19 个格式处理器） |
| 3.zlibtcl / pngtcl / tifftcl / jpegtcl | 4 个内置 compat 包装全部 dlopen 成功 |
| 4.1–4.3 | `image create photo` 生成 16×8 图 → BMP 写盘 → 读回 → 尺寸与逐像素一致 |

## 6. 结论

- 上游自动化测试入口存在且被**真实执行**：`Total 315 / Passed 297 / Skipped 18 / Failed 0`。
- 唯一跳过来源是外部工具 ghostscript 缺失（上游自带约束），非平台适配缺陷。
- 新增鸿蒙消费者用例 `tests/ohos.test` 25 例全绿，覆盖「处理器 dlopen + 真实图像往返」。
- `test_package` 在 OHOS 宿主上以真实 `tclsh9.0` 加载并使用本包，31 项断言通过。

## 7. 门禁链与本地 CI 模拟（W3）

### 7.1 CI 形态 `conan create`

```bash
# 与 ci/conan/build_and_test.sh:1364 完全同形态（不带 --user/--channel）
conan create archives/l/libtk-img/2.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="libtk-img/*"
```

原始输出（关键行）：

```
libtk-img/2.1.1: Building from source          ← 仅本包，无任何依赖被构建
libtk-img/2.1.1: Apply patch (portability): … tests/ohos.test
libtk-img/2.1.1: umask 077→022：改写 28 个 configure
libtk-img/2.1.1: uname shim 已注入 PATH 头部: …/_uname_shim
libtk-img/2.1.1: compat/**/config.guess 桩替换: 3 个 → aarch64-unknown-linux-gnu
libtk-img/2.1.1: Makefile 修正完成（47 个）：tcl/tk stub 路径 + '-L<libx11>/lib -lX11' + '-I<xorgproto>/include'
libtk-img/2.1.1: 安装完成: <build>/_stage/lib/Img2.1.1（24 个 .so）
libtk-img/2.1.1: 上游测试结果: all.tcl:	Total	315	Passed	297	Skipped	18	Failed	0
libtk-img/2.1.1: 上游测试通过: Total=315 Passed=297 Skipped=18 Failed=0
libtk-img/2.1.1: Package 'b36c021a925ef7fa1d411248b818074c4bba5ac9' created
```

退出码 `0`；`^ERROR|error:|Traceback|undefined reference|No rule to make target` 命中数 **0**。

### 7.2 W3 本地 CI 模拟（真实执行 `ci/conan/build_and_test.sh`）

| 门禁 | 结果 | 依据 |
|---|---|---|
| setup.sh | ✅ 通过 | — |
| KC（知识检查） | ✅ `KC_RESULT=pass` | — |
| JC（杂项文件拦截） | ✅ `JC_RESULT=pass`、`Junk Files: 0` | 以 PR-diff 模式限定本次变更的 14 个文件（`检查模式: prdiff (14 个文件)`）；JC6 单软件原子性 `涉及软件数: 1（合规）` |
| L0（质量门禁，含 R36/R37/R38） | ✅ `L0_RESULT=pass: all checks passed` | L0m 目录结构有效 |
| L1（测试真实执行） | ✅ `L1_RESULT=pass: test_package executed` | 含 **L1e 破坏性反向测试**：搬走 `lib/` + `include/` 后消费者测试确实失败 → 证明测试真实依赖本包 |
| L2（smoke test） | ⏭️ `skip: no bin/ dir` | 纯 dlopen 库包无可执行程序 |
| L4（补丁静态扫描） | ✅ `L4_RESULT=pass: patches clean` | — |
| L5（产物基线） | ✅ `L5_RESULT=pass: lib/ has content` | — |
| Build Summary | ✅ `Total 1 / Success 1 / Pass rate 100.0%` | `All packages built and tested successfully ✅` |

`.ci-result.json`（`finish` 写入，防伪造）：

```json
{"timestamp":"2026-10-09T00:35:19.329377","exit_code":0,"software":"libtk-img",
 "version":"2.1.1","step":"W3_local_ci","integrity_hash":"30a03225c1ec2159",
 "log_sha256":"4a18e0a1285a92f90f0338cb095c3653a44c4a3c0295d7e3422fb2eaf0680814"}
```

双哈希溯源实测一致：
`integrity_hash == sha256("2026-10-09T00:35:19.329377:libtk-img:2.1.1:0")[:16]` ✅；
`log_sha256 == sha256(reports/w3-local-ci.log)` ✅。

### 7.3 `ohc conan-verify`

`Verdict: PASS`，G0/G1/G2/G3 全 PASS（详见 `reports/conan-verify-report.md`）。
G0 命中知识条目 E490（autotools helper 可执行位）并给预警，但 **G2 实测通过 → E490 未发生**。

### 7.4 `ohc finish`（status=`built`）

| 步骤 | 结果 |
|---|---|
| 1 refresh-patch --auto | ✅ 编辑追踪器无变更记录 → **保留现有补丁**（1 个，未被丢弃） |
| 2 close-archive | ✅ `manifest.yaml → built`、`.build-closed` 落盘 |
| 3 G0 clean-verify | ⚠️ **预期行为（非阻塞）**：`clean_verify` 只跑裸 `./configure`、不执行 `build()`，无法复现本 recipe 在 build() 内的运行时修复（umask 022 / config.guess 桩 / Makefile 路径修补）→ `configure: error: <tcl包>/lib directory doesn't contain tclConfig.sh`。`clean_verify.py` 据此判为「预期行为」；真实构建证据由 G2 + W3 提供 |
| 4 conan-verify | ✅ PASS（G0/G1/G2/G3） |
| 5 W2 + W3 本地 CI | ✅ **W3 通过**（见 §7.2） |
| 6 finalize-archive | ⚠️ RC=2：**一致性问题 0**、补丁 1、报告 3；缺失项 1 = 缺 release tar.gz（纯 dlopen 扩展无独立程序，见 `packaging/README.md`；该告警全仓普遍） |
| 7 check-knowledge-gap (W5) | ⚠️ doc↔kv 542 对完整、`graph validate` 通过、本包 `knowledge_count=9 unreferenced=0`；报错来自**他包** E219/E253/E305（见 §7.5）与仓库既有 2797 条草稿 |
| 8 gen_summary | ⚠️ 框架解析器缺陷（见 §7.5），非本包可修；`step6` 不计入失败步骤 |
| 9 PR 原子性 (W2) | ✅ 报告"无变更文件"（无提交分支上恒空）；**等效结论由 §7.2 的 JC6 prdiff 模式 + `preflight.check_single_package`（PF1 PASS）给出** |
| 10 submit 就绪预检 | ✅ `test-report.md` / `packaging/` / `.staging-verified` / `build-closed marker` 四项全 ✅ → **submit 就绪** |

`finish` 的退出码由 `all(self.steps.values())` 决定。本包 **G0 不设 step 标志**（不影响退出码）、
`step6`（gen_summary）异常时也强制置 True。因此唯一使 `FINISH_RC=1` 的步骤是 **step5b**，
根因见 §7.5，属**框架解析器 + 他包内容**，非本 PR 引入。

### 7.5 两处框架级缺陷（非本包可修，均已定位到行）

**A. step5b：知识完整性检查不识别 YAML 块标量**
`workflow_checks.py:303-309` 用 `^(\w+):\s*(.*)` 取值，把块标量 `root_cause: |` 的值取成字符串 `"|"`，
再按"空值/TODO/`|`"判为空。全仓恰好 **3** 个 .kv 使用该写法，且**全部**被误判：

| 文件 | 解析器看到的 root_cause | 文件实际正文 | 主题（与本包无关） |
|---|---|---|---|
| `knowledge/graph/E219.kv` | `'\|'` → 判空 | ~8 行 | CI buildenv python |
| `knowledge/graph/E253.kv` | `'\|'` → 判空 | ~21 行 | OCaml 工具链 |
| `knowledge/graph/E305.kv` | `'\|'` → 判空 | ~21 行 | 字体/资源包 |

这三个文件在本 worktree 中 **git 状态为空（未改动）**。最小修法（框架侧，一行）：
把 `val == "|"` 的判空条件扩为 `re.fullmatch(r"[|>][+-]?\d*", val)`（识别块标量指示符）。

**B. gen_summary：解析器对重复 key 使用不覆盖的 `setdefault`**
`summary.py:89` `data.setdefault(current_list_key, []).append(item)`；当同一 key 先以标量出现、
后以列表出现时，`setdefault` 返回**已存在的字符串**而非新列表 → `'str'.append`。
触发源是 `archives/q/qpdf/{12.3.2,12.3.2.1}/manifest.yaml` —— 其 **`knowledge_gained` 出现两次**
（第 9 行 `knowledge_gained: []`、第 18 行 `knowledge_gained:` + 列表）。实测 14,255 个 manifest 中
**仅这 2 个**触发，本包 manifest 不触发。最小修法（框架侧）：`data[key] = []` 取代 `setdefault`，
或在 append 前做 `isinstance(..., list)` 兜底。

以上两处均为**共享框架/他包内容**问题；按 W2「配方 vs 框架隔离」不应混入本包 PR。

**修复状态：已修复，但按仓库规则落在独立分支，不随本 PR 提交。**
`check_pr_atomicity`（W2）自身要求「框架修改应单独提交 PR，配方 PR 只包含 `archives/` + `knowledge/`」，
故两处框架修正在独立分支 `fix/ohc-kv-block-scalar-parsers` 上完成（worktree `.wt/ohc-kv-parsers`，
基于 `main`，仅改 `scripts/ohc/{workflow_checks,summary}.py`，+34/−4）：

| 框架缺陷 | 修法 | 实测结果（修复前 → 修复后） |
|---|---|---|
| W5 不识别 YAML 块标量 | 新增 `_BLOCK_SCALAR_RE = ^[|>][+-]?\d*$`，命中即视为已填写 | `check_knowledge_completeness` **1 → 0**；日志由「❌ 字段缺失」变为「✅ 必填字段完整 (3 字段 × 542 条目)」 |
| `_parse_yaml_simple` 用不覆盖的 `setdefault` | 新增 `_as_list()`（`data[key] = []` 覆盖 + `isinstance(..., list)` 兜底） | 全仓 manifest 解析 **2 → 0** 异常；`generate_summary` **AttributeError → OK** |

用修复后的框架代码指向本工作树验证：`check_knowledge_completeness(pdir=<本包 wt>) = 0`、
`check_knowledge_gap(libtk-img, 2.1.1) = 0` → `step5b` 条件为 **True**，
即本包 `finish` 的 `FINISH_RC=1` 在框架修复合入后即消失（本 PR 侧无残留缺陷）。
