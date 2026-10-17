# libstb 0.0-git20250907.fede005 适配笔记

## 软件信息
- **名称**: libstb
- **版本**: 0.0-git20250907.fede005
- **上游**: https://github.com/nothings/stb @ fede005abaf93d9d7f3a679d1999b2db341b360f（2025-09-07 快照）
- **类型**: 单头文件库合集（header-only，无构建系统）
- **许可证**: MIT / Unlicense（双许可，任选）

## 与已有包的关系（重要，评审请看）
本仓库已有 5 个 stb 单头包：`stb_image/2.30`、`stb_ds/0.67`、`stb_sprintf`、`stb_image_write`、`stb_image_resize`。
它们与 libstb 同属上游仓库 nothings/stb，其中 **stb_image/2.30 用的就是同一 commit fede005**
（源码 URL 与 sha256 完全一致，可互相印证）。libstb 不是重复适配：
单头包每个只装一个头文件，libstb 是**合集包**，一次安装全部 20 个 `stb_*.h` + `stb_vorbis.c`，
对应 Alpine 的 libstb 打包口径（版本号 0.0-git20250907 即 Alpine 风格）。

## 打包内容
- 复制根目录全部 `stb_*.h`（20 个）+ `stb_vorbis.c`（vorbis 的官方 include-式实现文件，
  消费者 `#include "stb_vorbis.c"` 一次获得实现，惯例随头文件安装）到 `include/`
- `LICENSE` 到 `licenses/`
- **不打包 `deprecated/`**：上游已标记弃用（`stb.h`、`stretchy_buffer.h`、`rrsprintf.h`、
  旧 `stb_image_resize.h` 等）；旧 resize 由根目录 `stb_image_resize2.h` 取代

头文件清单（21 个）：
stb_c_lexer.h, stb_connected_components.h, stb_divide.h, stb_ds.h, stb_dxt.h,
stb_easy_font.h, stb_herringbone_wang_tile.h, stb_hexwave.h, stb_image.h,
stb_image_resize2.h, stb_image_write.h, stb_include.h, stb_leakcheck.h,
stb_perlin.h, stb_rect_pack.h, stb_sprintf.h, stb_textedit.h, stb_tilemap_editor.h,
stb_truetype.h, stb_voxel_render.h, stb_vorbis.c

## 配方要点
- `package_type = "header-library"`，`no_copy_source = True`，`package_id()` 清空
- 无 requirements（W0 依赖检查：零依赖，直接通过）
- `basic_layout(src_folder="src")`，`get(strip_root=True)`（GitHub archive 含顶层目录）
- `cpp_info.bindirs/libdirs = []`；cmake 文件名/目标名 `libstb` / `libstb::libstb`，pkg-config `libstb`
- 无补丁：源码与上游完全一致（sha256 校验）

## test_package 设计（16 + 5 断言，两个消费者用例，非空壳）

**用例 1 `test_libstb.c`（16 断言）**：多组件 API 断言。单一 C 文件，多个
`STB_*_IMPLEMENTATION` 实现段放同一翻译单元（stb 官方支持用法）：

1. **stb_image_write + stb_image 往返**：8x8 RGB 渐变 → `stbi_write_png_to_mem` 内存编码 PNG →
   `stbi_load_from_memory` 解码 → 尺寸/通道断言 + `memcmp` 逐字节无损比对（PNG 无损，等式有保证）
2. **stb_ds**：`arrput/arrlen` 动态数组、`hmput/hmget/hmlen` int key 哈希表、`shput/shget/shlen`
   字符串哈希表。刻意只使用 stb_ds/0.67 真机包已验证的安全 API 集——上游 `STBDS_ADDRESSOF`
   宏在 clang C 模式对 literal-array key 自认 "currently broken for clang"（见 stb_ds 适配笔记）
3. **stb_sprintf**：`%d-%s-%05d`、`%.2f`、`%x/%X` 三类格式化与预期字符串比对
4. **stb_rect_pack**：4 个 20x10 矩形装入 64x64，断言全部 was_packed、不出界、两两不重叠（O(n²) 显式判交）
5. **stb_divide**：`stb_div_trunc/floor/eucl(-7,2)` 与数学定义（-3/-4/-4）比对

**用例 2 `consumer_image_pipeline.c`（5 断言，路径 B 消费者用例）**：终端用户图像管线——
四象限纯色图生成 → `stbi_write_png_to_mem` 编码 → `stbi_load_from_memory` 无损解码 →
`stbir_resize_uint8_linear` 2x 放大（stb_image_resize2，**新宏 STB_IMAGE_RESIZE2_IMPLEMENTATION**）→
象限内部采样颜色校验（距边界 ≥6px 采样点对任何正确滤波核必等于原象限色）。

测试不用 `assert()`：Release/NDEBUG 会把 assert 编译掉变成空壳；全部显式判定+计数，按失败数返回非 0。

## 上游测试套件（2026-09-15 真机执行，上游文件零修改，5/5 通过）

| 套件 | 编译方式 | 结果 |
|---|---|---|
| tests/test_sprintf.c | `clang -DTEST_SPRINTF -DSTB_SPRINTF_IMPLEMENTATION -I src` | **pass**（rc=0；14 条 -Wformat 警告为 stb 扩展格式符 %b/%$/I64d 与 libc 不兼容的固有差异，非错误） |
| tests/test_png_paeth.c | `clang`（自包含，2^24 穷举） | **pass**（rc=0，"all ok!"） |
| tests/test_ds.c | `clang++ -O2 -std=c++17 -DDS_TEST -I src`（C++ 模式，同 stb_ds/0.67 先例） | **pass**（rc=0，"Ok!"，UNIT_TESTS+SMALL_BUCKET+8 组 churn）。**-O0/无优化标志下同套件必 SIGSEGV（stdout 全空）**，优化级单因素，详见草稿 DRAFT-libstb-...-stbds-test-ds-o0-segv |
| tests/test_c_compilation.c | `clang -I src` + 独立驱动 main 调 quicktest()（上游文件不动） | **pass**（12+ 头 implementation 宏全定义，编译+链接+运行 rc=0） |
| tests/test_easyfont.c | `clang -I src` + 独立驱动 main（编译覆盖） | **pass**（上游该文件即 NULL 参数 API 桩，设计意图为编译覆盖；编译链接通过即达标） |

注：tests/test_image.c、test_perlin.c、test_dxt.c 在 fede005 上游即为空占位文件（0-6 行）；
tests/image_test.c 的 PNG 套件（77 文件）已由 stb_image/2.30 包（同一 commit fede005）在真机
全量跑过并通过，本 PR 引用其结果作同源佐证。上游 test_c_compilation.c 自带两处宏拼写错误
（`STB_C_LEXER_IMPLEMENTATIOn`/`IMEPLEMENTATIOn`），未修改、如实保留。

## 知识草稿（路径 B，3 份，kv+md 成对）

- `knowledge/drafts/DRAFT-libstb-0.0-git20250907-stb-implementation-macro-matrix` ——
  stb 全系 IMPLEMENTATION 宏矩阵（21 文件逐头 grep 实测）+ stb_divide 链接坑 +
  vorbis/resize2/easy_font 三个特殊件 + 上游 c_compilation 自带宏拼写错误的佐证
- `knowledge/drafts/DRAFT-libstb-0.0-git20250907-bundle-vs-single-header-packaging` ——
  合集包打包口径：copy() 通配符跨目录误打包（实测 21>20）→ 显式清单；
  deprecated/ 剔除；stb_vorbis.c 照装；同 commit sha256 与单头包互证防重复适配误判
- `knowledge/drafts/DRAFT-libstb-0.0-git20250907-stbds-test-ds-o0-segv` ——
  test_ds 在 clang-15/OHOS -O0 下必 SIGSEGV、-O2 全过（stb_ds.h 与 0.67 包逐字节
  一致，优化级单因素；与 catdoc -O1+ 误编译互为反向镜像）

## 遇到的问题与决策
| # | 问题 | 决策 |
|---|------|------|
| 1 | stb_vorbis 实现是 `.c` 文件 | 照惯例打包进 include/，test_package 不编译它（拖入整条 vorbis 解码依赖链，由单独 stb 包真机用例覆盖更合适） |
| 2 | deprecated/ 旧头是否打包 | 不打包，上游已弃用，避免与 stb_image_resize2.h / 已有单头包语义冲突 |
| 3 | 上游测试（tests/ 每组件一套）是否全跑 | 合集包按组件取代表性证据：stb_image PNG 套件与 stb_ds 套件在单头包已真机全绿（同 commit 同源码）；libstb 以 16 断言消费者测试为准，上游套件可按需补跑 |
| 4 | 首次真机链接失败：`stb_div_trunc/floor/eucl` undefined symbol | stb_divide.h 同为声明/实现分离模式，实现被 `#ifdef STB_DIVIDE_IMPLEMENTATION` 守卫（实现体在 105-390 行），测试需 `#define STB_DIVIDE_IMPLEMENTATION` 后再 include。已修复，复跑全绿 |

## 验证状态
- [x] 源码 URL/sha256：本机下载复核 = `3c45e9ab...8a42`，与已合入 stb_image/2.30 同 commit 同哈希
- [x] 本机 `conan export` + `conan create -tf=""` 配方与打包校验通过（20 .h + stb_vorbis.c + LICENSE 精确无误）
- [x] W0：零依赖
- [x] **真机 conan create + test_package 全绿（2026-09-15，10.62.178.77 直连，ohos-aarch64 profile，clang-15/libc++，jobs=1）：test_libstb 16/16 + consumer_image_pipeline 5/5 = 21/21 断言 PASS，exit 0**
- [x] **上游 5 套件真机 5/5 通过（上游文件零修改；test_ds 需 -O2，见上表）**，作业目录设备 `$HOME/tmp/libstb-pathb/`
- [ ] shadow CI 单包验证（待 push 建 PR 后触发）

## 下一步命令（真机复跑/复核）
```sh
# 真机直连（局域网）：
ssh -T -p 2222 -i ~/.ssh/id_rsa currentUser@10.62.178.77
# 复跑（隔离 home 已建在 $HOME/tmp/libstb-conan-home，tarball 已入 download_cache 离线可用）：
cd $HOME/build_in_harmonyos && CONAN_HOME=$HOME/tmp/libstb-conan-home TMPDIR=$HOME/tmp/libstb-tmp \
  PATH=/data/service/hnp/bin:$HOME/.local/bin:$PATH $HOME/.local/bin/conan create \
  archives/l/libstb/0.0-git20250907.fede005 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

---

**配方完成**: 2026-09-15
**最终状态**: built（待真机 test_package 验证）
