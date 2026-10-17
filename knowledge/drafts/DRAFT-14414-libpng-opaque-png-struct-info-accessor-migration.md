# DRAFT-14414: libpng 1.5 把 `png_struct`/`png_info` 变成不透明类型

- **来源**：metapixel 1.0.2 适配（2026-10-01）
- **领域**：三方库 API 演进（libpng 1.5+ 不透明化）
- **邻近但不同**：DRAFT-14413（giflib 5.x 仅两个出参）—— 同为图像库 API 漂移，
  但迁移面与根因不同，本条未被图谱命中

## 现象

同一个文件里一次性爆几十条同源错误：

```
rwimg/rwpng.c:60:29: error: incomplete definition of type 'struct png_struct_def'
    if (setjmp(data->png_ptr->jmpbuf))
rwimg/rwpng.c:67:28: error: incomplete definition of type 'struct png_info_def'
    *width = data->info_ptr->width;
...
/root/.conan2/p/libpn*/p/include/png.h:437:16: note: forward declaration of 'struct png_struct_def'
fatal error: too many errors emitted, stopping now [-ferror-limit=]
```

## 根因

libpng 1.5（2014）把 `png_struct` / `png_info` 从**可见结构体**改成只在
`png.h` 里前置声明的**不透明类型**。2006 年前后的手写 PNG 读写层普遍直接摸
字段，于是全线崩。

**注意 `-ferror-limit=20`**：日志只显示 20 条，**真实触点远不止 20 处**。
read 侧还有 `bit_depth` / `color_type` / `interlace_type` / `rowbytes` 的多处引用，
write 侧更是一整段 12 行手工赋值。必须按访问器**逐类**替换，不能照错误列表改。

## 修复：读侧换访问器，写侧折叠成一次 `png_set_IHDR`

```c
/* 错误处理：jmpbuf 必须每次重新求值 */
if (setjmp(png_jmpbuf(data->png_ptr))) ...

/* 尺寸：两个指针都要给，只有 info_ptr 不够 */
*width  = (int)png_get_image_width(data->png_ptr,  data->info_ptr);
*height = (int)png_get_image_height(data->png_ptr, data->info_ptr);

/* 原本直接摸字段的断言 */
assert(png_get_bit_depth(data->png_ptr, data->info_ptr) == 8 || ...);
assert(png_get_color_type(data->png_ptr, data->info_ptr) == PNG_COLOR_TYPE_RGB || ...);
assert(png_get_interlace_type(data->png_ptr, data->info_ptr) == PNG_INTERLACE_NONE);

/* 写侧：替换原来那 12 行手工赋值 */
png_set_IHDR(data->png_ptr, data->info_ptr,
             (png_uint_32)width, (png_uint_32)height, 8, PNG_COLOR_TYPE_RGB,
             PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT,
             PNG_FILTER_TYPE_DEFAULT);
png_write_info(data->png_ptr, data->info_ptr);
```

### 三个容易改错的语义要点

1. **`png_jmpbuf()` 返回 `jmp_buf`，每次调用都必须重新求值** —— 错误路径上
   `png_ptr` 可能已失效。
2. **写侧那 12 行不是逐字段平移。** `width`/`height`/`valid`/`rowbytes`/
   `palette`/`num_palette`/`num_trans`/`bit_depth`/`color_type`/
   `compression_type`/`filter_type`/`interlace_type` —— 整段换成一次
   `png_set_IHDR()`：这是填充 info 结构**唯一受支持**的入口，
   `rowbytes` 由 `width*channels` 推导，`valid`/`num_palette`/`num_trans`
   由 libpng 自行初始化。照抄成逐个 `png_set_*` 反而会写出与 libpng 内部状态
   冲突的组合。
3. **`png_set_filler()` 仍应在 `png_set_IHDR()` 之前调用**（官方推荐顺序，
   上游原本就是先 filler 后赋值，不要调换）。
4. `png_get_*` 返回 `png_uint_32`/`png_byte`，原上游把宽高当 `int` 用，
   迁移时加显式 `(int)` 转换，否则 `-Wall` 会冒出符号比较告警。

## 排查口诀

> 成片出现 `incomplete definition of type 'struct png_*_def'` +
> `forward declaration of` + `too many errors emitted` → 就是本条。
> 先按类别（jmpbuf / 尺寸 / 位深 / 颜色类型 / 交错 / rowbytes）**列全触点**，
> 再一次性替换，**不要被 `-ferror-limit=20` 误导成"只有 20 处"**。

**选版本**：ohpcd 现有 libpng `1.6.39` / `1.6.58.x`；1.6 与 1.5 同样不透明。
`png_jmpbuf` / `png_get_*` / `png_set_IHDR` 三个 API 从 1.5 起一直可用。

## 三段式证据链（本条已实测）

| 步骤 | 结果 |
|------|------|
| 不打补丁，只编 `rwimg/rwpng.c` | 20 条 `incomplete definition` 后 `fatal error: too many errors emitted`；另 14 个 `.c` 全 0 error |
| 打补丁 | `conan create` rc=0，编译期 0 error |
| 端到端闭环 | 用例 8 生成 `mosaic.png`，用例 9 用随包 `metapixel-imagesize` 读回 `64 64`；用例 10 校验 PNG 签名；W4 审计另用 Python zlib 解出 IDAT 长度与 `rowbytes*height` 完全吻合、CRC 全对 |

第 3 行是**关键**：写侧 `png_set_IHDR` 与读侧访问器互相印证，且 IDAT 长度/CRC
经独立解码核对，**排除"尺寸碰巧对"的假阳性**。

反向验证：撤掉补丁，用例 4/9 由 PASS 转 FAIL。

## 红线提醒

PNG 是 metapixel 的**默认输出格式**。为绕开 libpng API 变更就去掉 `-DRWIMG_PNG`，
等于交付不能用的产物 —— 这类"为过编译而裁剪功能"是 P0。

## 适用范围

- 任何用 libpng 1.5+ 且直接读写 `png_struct`/`png_info` 字段的 C/C++ 项目
- 手写 PNG 读写层的老代码（图像马赛克、贴图/图集工具、缩略图生成器等）
- 任何会打出 `incomplete definition of type struct png_*_def` 的构建

## 关联文件

- `archives/m/metapixel/1.0.2/patches/0002-rwimg-rwpng-c-libpng-opaque-struct-access.patch`
- `archives/m/metapixel/1.0.2/notes.md`（问题 #2）
- `archives/m/metapixel/1.0.2/test_package/test.sh`（用例 4/8/9/10 为回归测试）
