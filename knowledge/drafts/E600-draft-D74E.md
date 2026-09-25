# E600（草稿）— libpng ≤1.2 私有 API 在 libpng ≥1.4 下全面失效

> 状态：草稿（`knowledge/drafts/E600-draft-D74E.kv`），来源：pngmeta 1.11 适配
> （`archives/p/pngmeta/1.11`，libpng 1.6.58.3）。

## 现象

一份 1998–2005 年前后写成的 PNG 工具，在旧发行版上能编译，换到现代工具链（libpng 1.6）
后一次编译报出几十个互不相同的错误，典型片段：

```
pngmeta.c:445:109: error: use of undeclared identifier 'ZLIB_VERSION'
pngmeta.c:118:12: error: no member named 'idat_size' in 'struct png_struct_def'
pngmeta.c:136:8:  error: call to undeclared function 'png_handle_IHDR'
pngmeta.c:549:22: error: no member named 'valid' in 'struct png_info_def'
pngmeta.c:641:3:  error: call to undeclared function 'png_read_destroy'
```

源码里通常能看到这一行，它是最明显的指纹：

```c
/* Needed to access various internal PNG chunk routines */
#define PNG_INTERNAL
#include <png.h>
```

## 根因

libpng 1.4 把 `png_struct` / `png_info` 改成不透明类型，并停止随 `png.h` 安装内部头。
于是过去合法的四类写法同时失效：

| 旧写法 | 现状 |
|---|---|
| `#define PNG_INTERNAL` + `png_handle_IHDR/tEXt/zTXt/iTXt/tIME/IEND/unknown`、`png_crc_read`、`png_read_data` | 分块级函数不再对外声明 |
| `png_ptr->idat_size` / `->chunk_name` / `->mode` / `->jmpbuf`；`info_ptr->bit_depth` / `width` / `height` / `color_type` / `num_text` / `mod_time` / `valid` | 结构体不透明，报 incomplete type |
| 依赖 `png.h` 间接带进来的 zlib 声明（如 `ZLIB_VERSION`） | `png.h` 不再包含 `zlib.h` |
| `png_read_destroy()`；`png_convert_to_rfc1123()` | 前者已移除，后者自 1.6 起标记 `PNG_DEPRECATED` |

因为失败点分散，容易被误判成"缺头文件"或"编译器太严格"，进而走上逐行 `#ifdef` 的歧路。

## 推荐做法：整体迁移到公共 API

关键是**换读取方式**，而不是逐个错误打补丁。

1. **删掉自制的分块遍历函数**（形如 `png_skip_till_end()`），改用一次性读取：

   ```c
   png_init_io(png_ptr, in_fp);
   png_read_png(png_ptr, info_ptr, 0, NULL);   /* IDAT 之后的 tEXt/tIME 同样进 info */
   ```

   历史代码之所以手写遍历，是因为当年 `png_read_info()` 读不到 IDAT 之后的块；
   `png_read_png()` 读完整张图，这个理由不再成立。

2. **字段改用 getter**：

   ```c
   png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth,
                &color_type, &interlace_type, NULL, NULL);
   png_get_text(png_ptr, info_ptr, &text_ptr, &num_text);
   png_timep mod_time;
   if (png_get_tIME(png_ptr, info_ptr, &mod_time) & PNG_INFO_tIME) { ... }
   ```

3. **setjmp 与销毁**：

   ```c
   if (setjmp(png_jmpbuf(png_ptr))) { ... }
   png_destroy_read_struct(&png_ptr, &info_ptr, &end_info);   /* 取地址，不是传值 */
   ```

4. **时间格式化**用带调用方缓冲区的接口，并处理非法 tIME：

   ```c
   char timebuf[29];
   if (png_convert_to_rfc1123_buffer(timebuf, mod_time)) { ... }
   else { /* 月份等字段越界，libpng 无法给出 RFC1123 形式 */ }
   ```

5. **补回 zlib 声明**：`#include <zlib.h>`。

## 两个反模式

- **不要用平台宏包住**（`-D__OHOS__` / `#ifdef __OHOS__`）。这是 libpng 版本演进导致的可
  移植性问题，与运行平台无关；补丁会被 PF5 平台宏闸拦截，即便放行，同一份代码在别的平台
  照样编译不过。
- **不要在自己的代码里重新声明 `struct png_struct_def` 来"恢复"字段访问**。实际编译 libpng
  时的配置决定了结构体布局，自行声明必然与之不一致，编译能过但运行时读到错位字段，表现为
  随机乱码或段错误，比编译失败更难定位。

## 验证

```bash
# 迁移前：确认命中范围
grep -nE 'PNG_INTERNAL|png_handle_|png_ptr->|info_ptr->' <src>/*.c

# 迁移后：编译 + 跑上游用例
make && make check
```

pngmeta 1.11 按上述方案迁移后（`patches/0001-pngmeta.c.patch`，+58/−103），
aarch64-linux-ohos 交叉编译通过，上游 4 项测试（`TESTS = test1 test2 test3 test4`）
在 qemu-aarch64 下 4/4 全部通过。

## 查重

- `knowledge/graph/index.tsv` 中 libpng 相关条目数为 0；`draft-review` 判定 `create`，
  最相似条目得分 0.0。
- 唯一已知先例停留在归档笔记层面：`archives/p/pngnq/` 记录过 "libpng ≥1.5 的 png.h 不再
  内嵌 zlib.h"，属于本条目第 (3) 项的子集；其余三项（`PNG_INTERNAL` 失效、结构体字段私有化、
  `png_read_destroy` 移除与 `png_convert_to_rfc1123` 弃用）没有任何已有条目覆盖，
  也没有进入检索路径——pngmeta 适配时 `engine` 对该错误日志返回的是完全无关的 E493
  （`program_invocation_name`，仅"undeclared identifier"关键词重合）。

## 关联

- 适配归档：`archives/p/pngmeta/1.11/`（`notes.md` 记录了完整的 7 条踩坑）
- 同类先例：`archives/p/pngnq/`（zlib.h 子项）
- 顺带值得留意：这类老包的 `configure` 多由 autoconf 2.13 生成，不认识 `--datarootdir`，
  Conan 默认注入该选项会让 configure 以 "invalid option" 退出，需要在 `generate()` 里按
  白名单过滤 `configure_args`。
