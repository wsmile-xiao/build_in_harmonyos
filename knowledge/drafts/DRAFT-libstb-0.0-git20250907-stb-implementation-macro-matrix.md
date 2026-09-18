# stb 单头库 IMPLEMENTATION 宏矩阵（草稿）

- **来源**：libstb 0.0-git20250907.fede005（nothings/stb @ fede005）适配，真机
  conan create 首轮 test_package 链接失败排障
- **日期**：2026-09-15
- **证据**：`archives/l/libstb/0.0-git20250907.fede005/notes.md` 问题表 #4、
  fede005 源码逐头 grep（宏矩阵）、`test_package/test_libstb.c`

## 现象

真机（OHOS aarch64）首轮 conan create，test_package 编译通过、**链接失败**：

```text
ld.lld: error: undefined symbol: stb_div_trunc
ld.lld: error: undefined symbol: stb_div_floor
ld.lld: error: undefined symbol: stb_div_eucl
```

## 根因

stb 全系列单头库是"声明/实现分离"设计：默认 `#include` 只有 extern 声明，
必须在**恰好一个**翻译单元里 `#define STB_<名>_IMPLEMENTATION` 后再 include
才生成实现。`stb_divide.h` 最易漏——源码 94-96 行只示 extern 声明，实现体在
105-390 行的 `#ifdef STB_DIVIDE_IMPLEMENTATION` 内；心理上它像"内联小函数"
不像"库"，漏 define 时**编译完全静默**（声明存在），链接才爆。

上游自家的 `tests/test_c_compilation.c` 里就有两处宏拼写错误
（`STB_C_LEXER_IMPLEMENTATIOn`、`STB_HERRINGBONE_WANG_TILE_IMEPLEMENTATIOn`），
因没调用函数而编译照过——证明错宏/漏宏在编译期不设防。

## 宏名矩阵（fede005 源码逐头 grep 实测，21 个根文件）

| 头文件 | 宏 | 备注 |
|---|---|---|
| stb_image.h | `STB_IMAGE_IMPLEMENTATION` | |
| stb_image_write.h | `STB_IMAGE_WRITE_IMPLEMENTATION` | |
| stb_image_resize2.h | `STB_IMAGE_RESIZE2_IMPLEMENTATION` | **兼容旧名** `STB_IMAGE_RESIZE_IMPLEMENTATION`，任一生效；旧名没有"2" |
| stb_ds.h | `STB_DS_IMPLEMENTATION` | |
| stb_sprintf.h | `STB_SPRINTF_IMPLEMENTATION` | |
| stb_rect_pack.h | `STB_RECT_PACK_IMPLEMENTATION` | |
| stb_truetype.h | `STB_TRUETYPE_IMPLEMENTATION` | |
| stb_divide.h | `STB_DIVIDE_IMPLEMENTATION` | **本轮实证最易漏** |
| stb_dxt.h | `STB_DXT_IMPLEMENTATION` | |
| stb_textedit.h | `STB_TEXTEDIT_IMPLEMENTATION` | |
| stb_tilemap_editor.h | `STB_TILEMAP_EDITOR_IMPLEMENTATION` | |
| stb_voxel_render.h | `STB_VOXEL_RENDER_IMPLEMENTATION` | |
| stb_c_lexer.h | `STB_C_LEXER_IMPLEMENTATION` | |
| stb_connected_components.h | `STB_CONNECTED_COMPONENTS_IMPLEMENTATION` | |
| stb_hexwave.h | `STB_HEXWAVE_IMPLEMENTATION` | |
| stb_include.h | `STB_INCLUDE_IMPLEMENTATION` | |
| stb_leakcheck.h | `STB_LEAKCHECK_IMPLEMENTATION` | |
| stb_perlin.h | `STB_PERLIN_IMPLEMENTATION` | |
| stb_herringbone_wang_tile.h | `STB_HBWANG_IMPLEMENTATION` | **缩写宏名**；传递依赖 image/image_write 两宏 |
| stb_easy_font.h | （无宏） | 声明实现一体，include 即用 |
| stb_vorbis.c | （无宏） | 本身是实现文件：`#include "stb_vorbis.c"` 一次 |

多个 `STB_*_IMPLEMENTATION` 放同一翻译单元是官方支持用法，无需拆文件。

## 验证

真机修复后 conan create：`test_libstb.c` 同一 TU 定义 6 个宏并调用对应 API，
16 断言全 PASS。不确定宏名时用
`grep -o "STB[A-Z_0-9]*_IMPLEMENTATION" stb_xxx.h | sort -u` 从头文件反查。
