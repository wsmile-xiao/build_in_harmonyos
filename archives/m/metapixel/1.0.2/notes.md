# metapixel 1.0.2 适配笔记

## 编译环境

- 构建系统: makefile（顶层 Makefile + `rwimg/Makefile` 两份手写 Makefile；无 configure / autotools / cmake / SCons）
- 编译日期: 2026-10-01
- 编译器: clang 15（OHOS aarch64，`target aarch64-linux-ohos`）
- 目标平台: HarmonyOS PC (OHOS) aarch64（本地 profile `ohos-aarch64-wsl`，CI profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan create 全绿；尚未 CI release 上传制品仓）

## 上游背景

Metapixel 是 Markus Schani 的照片马赛克生成器，1997–2006 年由 Mark Probst
编写，最后一次发布是 **2006-12-10 的 1.0.2，此后上游再无新版本**。它把源图
切成网格，用图库里最匹配的小图逐格替换，产出 PNG 或 JPEG。

交付三个可执行文件：

| 可执行文件 | 作用 |
|---|---|
| `metapixel` | 主程序，`--prepare` 配图库 / `--metapixel` 生成马赛克 |
| `metapixel-imagesize` | 打印图片宽高 |
| `convert` | 在 `.mxt` 表格式与 lisp 配置之间转换成分图数据 |

外加两个 Perl 编排脚本 `metapixel-prepare` / `metapixel-sizesort`，它们只是
`metapixel --prepare` / `--print-prepare-settings` 的封装，因此**构建和运行
全部功能都不需要 Perl**。

## 编译步骤

1. 官方源码（Debian 官方镜像的 orig tarball）:
   `https://deb.debian.org/debian/pool/main/m/metapixel/metapixel_1.0.2.orig.tar.gz`
   上游官网 `www.complang.tuwien.ac.at/schani/metapixel/` 的下载链接已失效
   （实测 HTTPS 握手被重置 / 返回 HTML），故改用权威镜像，并用两个独立
   权威清单交叉核对校验和：

   | 算法 | 本配方 | 权威清单 | 结论 |
   |---|---|---|---|
   | md5 | `af5d77d38826756af213a08e3ada9941` | Debian `.dsc` 记录的 md5 | 一致 |
   | sha512 | `88a718fc…2e30e156` | Gentoo portage distfiles Manifest 的 DIST 校验和 | 一致 |

   两者独立一致，认定与上游 1.0.2 发布件逐字节相同。
2. 依赖发布检查（W0/R35，用 `conan download --only-recipe`）:
   `libpng/1.6.58.3`、`libjpeg-turbo/3.2.0`、`giflib/5.2.2`、`zlib/1.3.2`
   全部已发布于 `ohpcd`，无需先适配依赖。
3. 打补丁（`apply_conandata_patches`）:
   - `0001-rwimg-rwgif-c-giflib5-error-out-parameters.patch`
   - `0002-rwimg-rwpng-c-libpng-opaque-struct-access.patch`
4. 构建（依赖的 include/lib 目录通过 make 命令行覆盖 `CCOPTS` / `LDOPTS` 注入，
   **不需要改写任何 Makefile 规则**）:
   ```bash
   make CC=<conan conf 里的 clang> \
        CCOPTS="-I. -Irwimg -O2 -Wall -DMETAPIXEL_VERSION=\"1.0.2\" <dep -I…>" \
        LDOPTS="<dep -L…> -Wl,-rpath,<dep libdir>…" \
        -j1 metapixel convert metapixel-imagesize
   ```
5. 验证: `conan create`（含 test_package 自动执行）→ 17/17 断言通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `rwimg/rwgif.c:57 error: too few arguments to function call, expected 2, have 1`（`DGifOpenFileName`），`:140` 同样错误（`DGifCloseFile`） | giflib 5.0 给这两个函数各加了一个 `int *Error` 出参（用于回填 GIF_ERROR 细节），1.0.2 仍按 1 参形式调用 | 补丁 0001：函数内加一个局部 `int error` 并传 `&error`。两处原有的 `assert()` 判据一个字未动，上游失败语义完全保留 |
| 2 | `rwimg/rwpng.c` 20 处 `error: incomplete definition of type 'struct png_struct_def'` / `'struct png_info_def'` | libpng 1.5 起把 `png_struct` / `png_info` 改成**不透明类型**，上游直接读写 `->jmpbuf` / `->width` / `->height` / `->bit_depth` / `->color_type` / `->interlace_type` / `->rowbytes` / `->valid` / `->palette` 全部不再编译 | 补丁 0002：读侧改用 `png_jmpbuf()` 与 `png_get_image_width/height`、`png_get_bit_depth`、`png_get_color_type`、`png_get_interlace_type`；写侧那整段 12 行手工赋值折叠成一次 `png_set_IHDR()`——这是填充 info 结构唯一受支持的方式，`rowbytes` / `valid` / `palette` / `num_trans` 由 libpng 自行推导 |
| 3 | `metapixel.c:2114 error: expected ')'`，宏 `METAPIXEL_VERSION` 展开成裸数字 `1.0.2` | `-DMETAPIXEL_VERSION="1.0.2"` 要穿过 **sh（conan）→ make 变量 → recipe shell → clang** 三层。手工用 `\"…\"` 给 `CCOPTS` 加外层双引号时，第一层 sh 就把内层引号当成结束符吃掉了 | 用 `shlex.quote()` 包裹（它选单引号，sh 原样透传 backslash），backslash 留到最后一层 recipe shell 才被去掉，clang 最终收到 `-DMETAPIXEL_VERSION="1.0.2"`。手写 Makefile 项目注入 flag 时凡带引号/宏定义的都必须走 `shlex.quote()` |
| 4 | 链接产物只在 conanrun 环境下才能跑 | 依赖是共享库（`libpng16.so.16` / `libjpeg.so.62` / `libgif.so.7`），裸执行会 `Error loading shared library` | `LDOPTS` 里为每个依赖 libdir 加 `-Wl,-rpath,<dir>`，把路径固化进 RUNPATH。`test_ohos` T4 对「所有非系统 NEEDED 都能经 RUNPATH 解析」做门禁 |
| 5 | 上游默认目标表含 `metapixel.1`，需要 `xsltproc` + `docbook-xsl`，而 CI 无此工具链 | `metapixel.1` 由 `metapixel.xml` 经 docbook 转换生成，属于**文档再生成**步骤；发布 tarball 本身已带生成好的 `metapixel.1` | 显式只构建三个代码目标，并把 tarball 里那个**同一个** `metapixel.1` 直接打包。交付产物一字未变，省掉 docbook-xml / docbook-xsl / xsltproc 三个构建期依赖和一次 `--nonet` 离线 xsltproc 调用 |

### 没有踩的坑（已逐项核验，避免走弯路）

- **`rwjpeg.c` 零改动。** libjpeg-turbo 3.x 仍保留 libjpeg 6 的 API 面，1.0.2 的
  JPEG 读写代码原样编译通过。Debian 的 `build-dep: libjpeg-dev` 指向
  `libjpeg-turbo8-dev`，与制品仓的 libjpeg-turbo 同源。
- **giflib 只需改两个函数签名。** 网上流传的 "giflib5 适配" 大改
  （`DGifSlurp` 重写、`GifFileType` 不透明化）只针对 giflib **6.0**；本配方
  锁 `giflib/5.2.2`，其头文件里 `GifFileType` 仍是**可见结构体**，
  `DGifGetExtension` / `DGifGetExtensionNext` / `DGifGetLine` 也都还在，
  所以只有 `DGifOpenFileName` / `DGifCloseFile` 两处签名要补出参。
- **不裁剪任何功能。** `-DRWIMG_JPEG -DRWIMG_PNG -DRWIMG_GIF` 三个格式后端
  全部保留（Makefile 自带，未覆盖）。GIF 读 + JPEG 写正是 1.0.2 的 NEWS
  主打特性，若为绕开 giflib 签名而砍掉 GIF 就等于裁剪软件，因此补丁 0001
  是硬需求而非可选项。
- **上游两个编译器告警不处理。** `getopt()` 无原型声明、`mosaic` 可能未初始化
  都是 2006 年代码在现代 clang 下的既有告警，不影响产物正确性；`-e global`
  分支实际不可达（`-i/-q` 权重为 0 时才走到）。改动它们属于超出适配范围的
  上游代码修改，故保留原样并在 W4 审计中披露。

## 源码修改（补丁）

| 补丁 | 修改内容 | 平台宏 |
|------|----------|--------|
| `0001-rwimg-rwgif-c-giflib5-error-out-parameters.patch` | `rwimg/rwgif.c`: 加局部 `int error`，`DGifOpenFileName(filename)` → `DGifOpenFileName(filename, &error)`，`DGifCloseFile(f)` → `DGifCloseFile(f, &error)` | 无 |
| `0002-rwimg-rwpng-c-libpng-opaque-struct-access.patch` | `rwimg/rwpng.c`: 6 处 `setjmp(png_ptr->jmpbuf)` → `setjmp(png_jmpbuf(png_ptr))`；读侧字段访问 → `png_get_*` 系列；写侧 12 行手工赋值 → 1 次 `png_set_IHDR()` | 无 |

两个补丁都是**纯 API 兼容修复**（libpng / giflib 版本演进），不引入任何平台
宏（R8），在 glibc 环境下同样适用，不属于平台特判。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libpng | 1.6.58.3 | ohpcd 制品仓 | PNG 读写（`libpng16.so.16`） |
| libjpeg-turbo | 3.2.0 | ohpcd 制品仓 | JPEG 读写（`libjpeg.so.62`），API 面兼容 libjpeg 6 |
| giflib | 5.2.2 | ohpcd 制品仓 | GIF 读（`libgif.so.7`），5.x 需补 Error 出参 |
| zlib | 1.3.2 | ohpcd 制品仓 | `-lz` 直接链接（同时经 libpng 传递引入） |
| docbook / xsltproc | — | **不引入** | 仅用于重新生成已随包发布的 man page |

## 验证结果

```bash
# W3 本地编译验证（硬门槛）
conan create archives/m/metapixel/1.0.2 --name=metapixel --version=1.0.2 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
# → Package 'ed5c7c75…' created ；test_package 17/17 PASS
```

test_package 真实执行 OHOS aarch64 产物，17 条断言全过：

```
PASS: T0 test fixtures generated (target.png + PNG/JPEG/GIF tiles)
PASS: T1 --version reports metapixel 1.0.2
PASS: T2 --help documents --library/--prepare/--metapixel
PASS: T3 --print-prepare-settings reports a positive tile size (128 x 128)
PASS: T4 PNG decode - --prepare produced library entry tile_a
PASS: T5 JPEG decode - --prepare produced library entry tile_d
PASS: T6 GIF decode - --prepare produced library entry tile_c
PASS: T7 library table tables.mxt was written
PASS: T8 classic photomosaic written to PNG
PASS: T9 mosaic.png decodes as 64x64 via metapixel-imagesize
PASS: T10 mosaic.png carries a valid PNG signature
PASS: T11 classic photomosaic written to JPEG
PASS: T12 mosaic.jpg decodes as 64x64 via metapixel-imagesize
PASS: T13 --collage mosaic written and decodes as 64x64
PASS: T14 -m wavelet metric produced a mosaic
PASS: T15 convert emitted a small-image record with a positive size (64 64)
PASS: T16 convert output depends on its input and is reproducible
METAPIXEL_TEST_SUMMARY total=17 passed=17 failed=0
```

鸿蒙专项验证（`test_ohos/run_ohos_test.sh`）5/5 PASS：

```
PASS: T1 artifact is an ELF64 AArch64 binary
PASS: T2 no build-host absolute path leaked into the binary
PASS: T3 resolves against the OHOS aarch64 loader (/lib/ld-linux-aarch64.so.1)
PASS: T4 image backends reachable through RUNPATH ( libpng16.so.16 libjpeg.so.62 libgif.so.7)
PASS: T5 packaged binary built a photomosaic (5 tiles, size 64 64)
OHOS_TEST_SUMMARY total=5 passed=5 failed=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/metapixel` | 主程序：配图库 + 生成马赛克 |
| `bin/metapixel-imagesize` | 打印图片宽高 |
| `bin/convert` | 成分图数据转换 |
| `bin/metapixel-prepare` | Perl 编排脚本（封装 `metapixel --prepare`） |
| `bin/metapixel-sizesort` | Perl 编排脚本 |
| `share/man/man1/metapixel.1` | man page（取自发布 tarball，字节一致） |
| `share/metapixel/metapixelrc` | 配置样例 |
| `licenses/COPYING` | GPL-2.0 全文 |

## 测试夹具为什么是生成的而不是提交进仓库

CI worker 检出 PR 的方式是下载**文本** diff
（`https://<host>/pull/<n>.diff`）后用 `git apply` 应用，而该接口不携带二进制负载。
首版 PR 把测试用 PNG/JPEG/GIF 直接提交进 `test_package/images/`，结果整个 PR 在
`checkout-pr` 步失败：

```
error: missing binary patch data for 'archives/m/metapixel/1.0.2/test_package/images/target.png'
[ERROR] PR 14104 diff 无法应用——PR 与 main 分支存在冲突
```

（机器人把这一条误判为"网络问题"，真实根因是二进制补丁数据缺失。）

因此测试夹具改为**运行期生成**：`test_package/gen_images.py` 只用标准库
从零写出 PNG（含 zlib + CRC）与 GIF（**含手写 LZW 编码器**），JPEG 因手写编码器
不划算而用内嵌 base64 常量并锁定 SHA256，生成后自检魔数、最小尺寸与该摘要。
好处不只是规避门禁：夹具从 12KB 二进制变成几百行可读代码，且经**真实解码器**
反向验证——`metapixel --prepare` 能解开手写 LZW 产出的 GIF，`metapixel-imagesize`
能读出全部尺寸（64 64 / 16 16），`file(1)` 也确认格式正确。

## 注意事项

- **上游零自动化测试。** tarball 共 41 个条目（= 39 个文件 + 2 个目录条目），顶层 Makefile 无 `check`/`test`
  目标，`rwimg/Makefile` 只有 `all`/`librwimg.a`/`clean`，`.spec` 的 `%check` 段
  为空。17 条断言全部是本次适配补全的消费者视角用例。
- **经典马赛克默认不允许在小图附近重复用同一张。** 上游
  `metapixel.h:34` 定义 `DEFAULT_CLASSIC_MIN_DISTANCE 5`（拼贴模式是
  `DEFAULT_COLLAGE_MIN_DISTANCE 256`），语义是"同一张小图两次出现的位置
  曼哈顿距离不得小于该值"。图库 3 张、源图 64×64 按 8×8 小图切成 64 格时
  默认间距必然放不下，会报
  `Error: cannot find a matching image`，这是**正确行为**（实测 `-d 1`/`-d 2`/
  `-d 5` 均失败，只有 `-d 0` 成功）。测试用 `-d 0` 显式放开重复，这是
  metapixel 的既有语义，不是缺陷。
- **`-e global` 需要图库张数 ≥ 格子数**，本测试图库太小故未覆盖该分支。
- **构建期不要用 `-static-pie`。** 本 OHOS sysroot 缺 `rcrt1.o`
  （`ld.lld-15: error: cannot open rcrt1.o`）。本配方走共享库 + RUNPATH 路线。
- **本机 WSL 环境注意**：本机 clang shim 不在 `PATH` 里提供 `llvm-ar`
  （`/usr/lib/llvm-14/bin`），且跑 aarch64 动态产物需要
  `QEMU_LD_PREFIX=/root/ohos-run-prefix`。两者都只是**本地环境**问题，
  CI worker 的 `ci/conan/profiles/ohos-aarch64` 已把完整 OHOS SDK
  `/data/service/hnp/bin` 放进 PATH（含 `llvm-ar`），且是 aarch64 原生执行。

---

**编译结束**: 2026-10-01
**最终状态**: built
