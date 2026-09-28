# libtiff 4.7.2.2 编译笔记（HarmonyOS PC · Conan cmake）

> R37 递增说明：上游 main 已有 4.7.2（bootstrap 产物，status: built 真机 conan create 通过），
> 按 R37「适配修复加后缀 X.Y.Z.N」以 **4.7.2.2** 起步（同 rapidjson 1.1.0.1 / any-lite 0.3.0.2 /
> mypaint-brushes 2.0.2.1 先例）。conandata 的 URL/sha256 仍指上游原版 tiff-4.7.2.tar.gz，
> 源码版本（TIFFLIB_VERSION_STR=4.7.2）与制品 revision（4.7.2.2）解耦。

## 产物
`libtiff.so`（共享库，tiff-tools/tests/docs/cxx/contrib 均关闭）。

## 编解码后端
八个后端全部接入，均由 conan 依赖提供（不依赖设备上预装的系统库）：

| 后端 | CMake 开关 | 依赖包 |
|------|-----------|--------|
| zlib | `-Dzlib=ON` | zlib/1.3.1.1 |
| libdeflate | `-Dlibdeflate=ON` | libdeflate/1.25 |
| JPEG | `-Djpeg=ON` | libjpeg-turbo/3.2.0 |
| Zstd | `-Dzstd=ON` | zstd/1.5.7 |
| WebP | `-Dwebp=ON` | libwebp/1.6.0 |
| LERC | `-Dlerc=ON` | lerc/4.1.1 |
| JBIG | `-Djbig=ON` | jbigkit/2.1 |
| LZMA | `-Dlzma=ON` | xz/5.6.2 |

## 关键适配
- 关掉不需要的构建目标：`-Dtiff-tools=OFF -Dtiff-tests=OFF -Dtiff-docs=OFF -Dtiff-contrib=OFF`。
- 产物 `.so` 经 `llvm-objcopy --remove-section .codesign` 去旧签名后由
  `binary-sign-tool sign -selfSign 1` 自签（HarmonyOS XPM 拒绝未签名/被改动的 ELF）。
- 依赖接线：全用自带 FindXxx 模块 + 预设 find 缓存变量绕过交叉链 FIND_ROOT_PATH_MODE=ONLY；
  链接期 -L + -rpath-link 处理传递 NEEDED（lerc 的 libc++_shared 等）。
- 真机适配（取证）：设备 /storage 为 hmdfs 挂载，不支持符号链接（ln -s → EPERM，/tmp 只读），
  版本化共享库要建 libtiff.so.6 / libtiff.so 软链 → 链接后一步必挂（首轮真机构建实踩）。
  build() 先探测构建目录软链能力，不支持则 CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON 去版本化
  （产出裸 libtiff.so、SONAME 无版本）；Linux 农场支持软链 → 不触发，布局与上游 4.7.2 一致。
- 无源码补丁。

## test_package 升级（相对 4.7.2 空壳探针）
4.7.2 的 test.c 只做 `dlopen` + `dlsym("TIFFOpen")`（notes 明记「待改进」）。4.7.2.2 升级为
**直接链接 libtiff 的功能 roundtrip 探针**（消费方真实形态）：

- 编译期/运行期版本断言（TIFFLIB_VERSION_STR / TIFFGetVersion 均报 4.7.2）+ 错误路径（打开
  不存在文件返回 NULL）。
- 核心路径（内建编解码，任何构建下都必须绿）：strip LE 64x32 + BE 31x17 PACKBITS 写读逐字节
  比对、tiled 48x48/16x16 写读逐字节比对、字节序（TIFFIsByteSwapped）校验。
- 编解码后端矩阵（8 后端中 7 个可压缩路径；libdeflate 与 zlib 共用 DEFLATE 路径）：DEFLATE /
  ZSTD / LZMA / JPEG / WEBP / LERC / JBIG 各写图再读回比对——构建未含该后端时 SKIP 不判失败，
  已含但不绿则 FAIL（R34 反空壳：证明运行期真实可用）。无损后端逐字节比对；JPEG/WEBP（默认
  有损质量）按容差比对；LERC 以 LERC_MAXZERROR=0 无损模式逐字节比对。
- 全绿环境执行断言数 83（MANIFEST.yml assertion_count 对应）。
- 两个 API 约束（真机实证）：JBIG 编解码均为 strip 级（无 row 接口，编码器还要求整图恰好
  一条 strip）；JPEG 伪标签 JPEGCOLORMODE 由 codec 注册——写侧须在 COMPRESSION 之后设置，
  读侧须先触发目录读取再设置。

## 上游测试清点与真机执行（R51，2026-09-28 更新）
上游 git tag v4.7.2 test/ 目录共 153 个测试入口：129 个 .sh 脚本 + 24 个 .c 测试程序
（编译为 18 个测试可执行目标；发行 tarball 仅随 89 个 .sh + 24 个 .c = 113 入口，
另 40 个 tiff2bw*/tiff2rgba*/tiffcrop-* 工具脚本仅存于 git——上游 Makefile.am 未将其
列入发行；其中 21 个喂给上游工具自身硬编码拒绝的输入，见下）。

真机全量构建（`-Dtiff-tools=ON -Dtiff-tests=ON`，与配方同工具链/同 8 依赖接线，
CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON）产出 20 个工具 + 18 个测试程序，上游测试入口
全量真实执行：

- ctest（上游 CMake 注册测试套件）：**158/158 通过（100%，8.31s）**。
- 129 个 .sh 逐个 `srcdir=<src/test> sh <script>` 执行：**108 过 / 21 挂**。
  - 发行 tarball 的 89 个脚本 89/89 全过；
  - git-only 40 个脚本 19 过 / 21 挂——21 个失败根因全部为上游工具自身硬编码的输入
    约束（与平台无关，Linux 构建同错，上游源码逐条可查）：
    - 13 个 tiff2bw-*：tools/tiff2bw.c 硬编码只接受 PHOTOMETRIC_RGB /
      PHOTOMETRIC_PALETTE（"Bad photometric; can only handle RGB and Palette
      images."），而这些脚本的输入是灰度（miniswhite/minisblack）或 YCbCr
      （quad-tile.jpg）图 → 工具设计即拒绝。
    - 8 个 tiffcrop-*-ojpeg_*：tools/tiffcrop.c loadImage 硬编码拒绝亚采样 OJPEG
      （"Can't copy/convert subsampled image with subsampling 2 horiz 2 vert"），
      上游 CMakeLists.txt 注释同证（"tiffcp does not support subsampled images, as
      the OldJPEG ones are"）。
  完整执行记录、失败清单与代表性日志见 reports/upstream-test-run.md。
结论：上游 153 入口在目标环境真实执行；成功项（ctest 158/158 + sh 108/129 通过）
证明库在 HarmonyOS PC 行为与上游一致；21 个失败项均有确定根因（上游工具自身输入约束），
非适配引入。

## 验证记录
- 本地（Windows MinGW 13.2 + cmake 3.27，静态库无外部后端构建）：探针编译零告警（-Wall -Wextra，
  -DPROBE_ALL_BACKENDS 同款配置），核心路径 28/28 全绿（版本/错误路径/strip LE+BE/tiled），
  后端矩阵本地无后端全部 SKIP；负向红测：EXPECT_TIFFLIB_VERSION 改错值 → 版本断言必红
  exit=1，绿跑 exit=0——探针灵敏度得证。
- 真机（HarmonyOS PC，通道2）三轮取证与收敛：
  1. 首轮：编译 100% 全过、链接成功，止步于版本化软链创建（hmdfs EPERM）→ 加入软链能力
     探测 + CMAKE_PLATFORM_NO_VERSIONED_SONAME 去版本化适配；
  2. 第二轮：包建成 + 签名 + 探针实跑 74/77——暴露两处探针写法的 API 层错误：JBIG 编码器
     只注册 encodestrip（TIFFWriteScanline 必报 "ISO JBIG scanline encoding is not
     implemented"，且要求整图单条 strip）、JBIG 解码器 decoderow 保留 _TIFFNoRowDecode
     默认桩（读必须 TIFFReadEncodedStrip）；JPEG 伪标签 JPEGCOLORMODE 由 codec 注册，
     必须放在 COMPRESSION 之后设置（写侧），读侧须先触发目录读取；
  3. 第三轮：探针修正后 `conan test` 83/83 断言全绿（含 7 后端矩阵），exit 0。
- 真机上游测试全量执行（2026-09-28）：同接线全量构建（tiff-tools=ON tiff-tests=ON）后
  ctest 158/158（100%）+ 129 个 .sh 直跑 108/129；21 个失败根因=上游工具硬编码输入
  约束（tiff2bw 只收 8-bit RGB/Palette ×13、tiffcrop 拒亚采样 OJPEG ×8，上游
  CMakeLists 注释自证），详见「上游测试清点与真机执行」与 reports/upstream-test-run.md。
- 真机结论：制品含 8 后端共享库（裸 libtiff.so 自签），test_package 83/83 通过。

## 路径 B 知识库
两条知识草稿随本 MR 提交至 `knowledge/drafts/`（task 7341，kv+md 成对）：

- `DRAFT-7341-libtiff-4.7.2.2-hmdfs-nosymlink-versioned-sharedlib` —— hmdfs 无符号
  链接 → 版本化共享库软链必挂（EPERM）；运行期探测 + CMAKE_PLATFORM_NO_VERSIONED_SONAME
  条件化，农场布局保持上游一致。
- `DRAFT-7341-libtiff-4.7.2.2-jbig-codec-strip-only-api` —— JBIG 仅 strip 级 API
  （编码器要求整图单条 strip）；JPEGCOLORMODE 伪标签须在 COMPRESSION 之后 / 目录
  读取之后设置。

版本级 manifest.yaml `knowledge_gained` 已回填两个草稿 ID。

## 状态
built —— 真机 `conan create` 包建成（含 XPM 自签），test_package 83/83 全绿。

## 版本递增说明（2026-09-27）

4.7.2.1 版本号已被他人抢先合入 main（提交 7b92aa7079，2026-09-27 05:48，路径A 无知识草稿），本分支二次递增为 4.7.2.2；配方与探针内容不变（真机探针 83/83 实测于 4.7.2.1 名下，断言均为上游版本语义，不受 recipe revision 影响）。
