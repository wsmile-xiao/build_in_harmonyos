# libtiff 4.7.2.2 上游测试真机执行记录（2026-09-28）

> 对应审查意见 rule4「上游有用例 153 个但一个也没测（0/153）」：已解决。
> 本记录为 HarmonyOS PC 真机上对上游 git tag v4.7.2 test/ 全部 153 个测试入口的
> 真实执行证据。

## 1. 环境与源码

| 项 | 值 |
|---|---|
| 设备 | HarmonyOS PC 真机（aarch64，/storage 为 hmdfs，无符号链接） |
| 工具链 | OHOS NDK ohos.toolchain.cmake（clang 15，libc++，Release；自动发现，ML-0035） |
| 构建工具 | cmake 4.1.2 / ctest / make（/data/service/hnp/bin） |
| 源码 | 上游原版 tiff-4.7.2.tar.gz（sha256 672bd7d1…）；test/ 以 git tag v4.7.2 树补齐 40 个发行 tarball 未带的工具脚本（上游 Makefile.am 未将其列入发行） |
| 依赖 | 与配方完全一致的 conan cache 8 依赖：zlib/1.3.1.1（P=01d92cf3…）、xz/5.6.2（6b129b06…）、jbigkit/2.1（f23d5a9b…）、libdeflate/1.25、libjpeg-turbo/3.2.0、zstd/1.5.7、libwebp/1.6.0、lerc/4.1.1 |
| 接线 | 与配方 build() 同款：FindXxx 缓存变量、LDFLAGS -L/-rpath-link、CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON |

补充：6 个 `*.t1iff.sh` 脚本引用的 `images/quad-tile.jpg.t1iff` 为上游拼写错误
（git 树中无此文件，真实文件为 quad-tile.jpg.tiff）→ 已按真实文件内容补同名副本后执行。

## 2. 构建（全量，tiff-tests=ON）

```
cmake -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> \
      -Dtiff-tools=ON -Dtiff-tests=ON -Dtiff-docs=OFF -Dtiff-contrib=OFF \
      + 8 编解码开关全 ON + 依赖缓存变量 + LDFLAGS
cmake --build . -j2
```

配置结果：8 个编解码 Support:TRUE。产出 20 个命令行工具 + 18 个测试程序。
（注：配方制品仍以 `-Dtiff-tools=OFF -Dtiff-tests=OFF` 构建；本节为验证上游测试
而做的同接线全量构建，源码零改动、零补丁。）

## 3. 执行一：ctest（上游 CMake 注册套件）—— 158/158（100%）

```
cd tiff-build && ctest -j2
100% tests passed, 0 tests failed out of 158
Total Test time (real) = 8.31 sec
```

上游 CMakeLists.txt 注册口径（原文引用）：
- 行 25：`# Images for tiff2bw (8-bit RGB only)` —— `RGBIMAGES` 白名单仅
  palette-1c-8b / rgb-3c-8b / quad-lzw-compat 三张；
- 行 538：`add_convert_tests(tiff2bw default "" RGBIMAGES TRUE)`；
- 行 495-498（Old-JPEG 转换测试被上游注释掉）：
  `#--- tiffcp does not support subsampled images, as the OldJPEG ones are ---`
  `#    ToDo: a test for OldJPEG is missing.`

## 4. 执行二：129 个 .sh 脚本逐个直跑 —— 108/129

```
for f in $SRC/test/*.sh; do ( srcdir=$SRC/test sh "$f" > ~/shlogs/$(basename $f).log 2>&1 ) ...; done
SH_TOTAL=129 SH_PASS=108 SH_FAIL=21
```

- 发行 tarball 自带 89 个脚本：**89/89 全过**
- git-only 40 个（上游 ctest 未注册、未随发行的工具脚本）：19 过 / 21 挂
  （其中 tiff2rgba-* ×3 全过——与上游 `add_convert_tests(tiff2rgba default "" TIFFIMAGES_OJPEG TRUE)` 的注册口径一致）

## 5. 21 个失败的根因：上游工具硬编码输入约束（平台无关）

### 5.1 tiff2bw ×13 —— 上游工具只支持 8-bit RGB/Palette（源码两道硬校验）

tools/tiff2bw.c main()：
- 行 182：`"%s: Bad photometric; can only handle RGB and Palette images."`（photometric 非 RGB/PALETTE 即拒）
- 行 199-200：`TIFFGetField(in, TIFFTAG_BITSPERSAMPLE, &bitspersample); if (bitspersample != 8)` → "Sorry, only handle 8-bit samples."

| 脚本 | 输入图像 | 触发约束 |
|---|---|---|
| tiff2bw-logluv-3c-16b.sh | logluv-3c-16b.tiff（LOGLUV） | photometric（行 182） |
| tiff2bw-lzw-single-strip.sh | lzw-single-strip.tiff（minisblack 灰度） | photometric（行 182） |
| tiff2bw-minisblack-1c-16b.sh | minisblack-1c-16b.tiff | photometric（行 182） |
| tiff2bw-minisblack-1c-8b.sh | minisblack-1c-8b.tiff | photometric（行 182） |
| tiff2bw-minisblack-2c-8b-alpha.sh | minisblack-2c-8b-alpha.tiff | photometric（行 182） |
| tiff2bw-miniswhite-1c-1b.sh | miniswhite-1c-1b.tiff | photometric（行 182） |
| tiff2bw-ojpeg_chewey_subsamp21_multi_strip.sh | ojpeg_chewey…（YCbCr OJPEG） | photometric（行 182） |
| tiff2bw-ojpeg_zackthecat_subsamp22_single_strip.sh | ojpeg_zack…（YCbCr OJPEG） | photometric（行 182） |
| tiff2bw-quad-tile.jpg.sh | quad-tile.jpg.tiff（YCbCr JPEG） | photometric（行 182） |
| tiff2bw-quad-tile.jpg.t1iff.sh | quad-tile.jpg.t1iff（同内容副本） | photometric（行 182） |
| tiff2bw-rgb-3c-16b.sh | rgb-3c-16b.tiff（16-bit RGB） | bitspersample≠8（行 199-200） |
| tiff2bw-palette-1c-1b.sh | palette-1c-1b.tiff（1-bit palette） | bitspersample≠8（行 199-200） |
| tiff2bw-palette-1c-4b.sh | palette-1c-4b.tiff（4-bit palette） | bitspersample≠8（行 199-200） |

真机日志摘录（真实执行）：
```
/storage/.../tiff2bw .../images/quad-tile.jpg.tiff o-tiff2bw-quad-tile.jpg.tiff
.../quad-tile.jpg.tiff: Bad photometric; can only handle RGB and Palette images.
Returned failed status 1!
```
```
.../images/rgb-3c-16b.tiff: Sorry, only handle 8-bit samples.
Returned failed status 1!
```

### 5.2 tiffcrop ×8 —— 上游工具拒绝亚采样 OJPEG

tools/tiffcrop.c loadImage() 行 8220：
`"Can't copy/convert subsampled image with subsampling 2 horiz 2 vert"`

| 脚本 | 输入图像 |
|---|---|
| tiffcrop-R90-ojpeg_chewey_subsamp21_multi_strip.sh | ojpeg_chewey_subsamp21_multi_strip.tiff |
| tiffcrop-R90-ojpeg_zackthecat_subsamp22_single_strip.sh | ojpeg_zackthecat_subsamp22_single_strip.tiff |
| tiffcrop-doubleflip-ojpeg_chewey_subsamp21_multi_strip.sh | 同上 chewey |
| tiffcrop-doubleflip-ojpeg_zackthecat_subsamp22_single_strip.sh | 同上 zack |
| tiffcrop-extract-ojpeg_chewey_subsamp21_multi_strip.sh | 同上 chewey |
| tiffcrop-extract-ojpeg_zackthecat_subsamp22_single_strip.sh | 同上 zack |
| tiffcrop-extractz14-ojpeg_chewey_subsamp21_multi_strip.sh | 同上 chewey |
| tiffcrop-extractz14-ojpeg_zackthecat_subsamp22_single_strip.sh | 同上 zack |

上游 CMakeLists.txt 行 495-498 自证（该注册被注释掉）：
`#--- tiffcp does not support subsampled images, as the OldJPEG ones are ---`
`#    ToDo: a test for OldJPEG is missing.`

真机日志摘录：
```
loadImage: Can't copy/convert subsampled image with subsampling 2 horiz 2 vert.
main: Unable to load source image.
Returned failed status 1!
```

### 5.3 可复现性

21 个失败均为工具入口的硬校验（main()/loadImage），与目标平台无关：任意 Linux 用同一
上游源码构建 tiff2bw/tiffcrop 后直跑这些脚本即得相同报错。正因如此，上游自己的
ctest 注册口径（RGBIMAGES 白名单、OJPEG 转换注释掉）从不执行这些输入——本记录额外
把它们全跑了，失败点与上游代码注释完全互证。

## 6. 结论

- 上游 153 个测试入口在 HarmonyOS PC 真机全部真实执行：
  - ctest（上游 CMake 注册套件）**158/158 = 100%**（8.31s）
  - 129 个 .sh 脚本直跑 **108/129**；其中发行 tarball 89 个脚本 **89/89**
  - 21 个失败全部根因为上游工具自身硬编码输入约束（tiff2bw 只收 8-bit
    RGB/Palette ×13；tiffcrop 拒亚采样 OJPEG ×8），上游源码行号 + 上游
    CMakeLists 注释 + 真机日志三方互证，非本适配引入
- 附：配方自带 test_package 探针 83/83（conan test，exit 0）
