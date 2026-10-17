# DRAFT-14413: giflib 5.x 的源码不兼容面只有两个 `Error` 出参；大改是 6.0 才有的事

- **来源**：metapixel 1.0.2 适配（2026-10-01）
- **领域**：三方库 API 演进（giflib 5.0/5.2 vs 6.0）
- **邻近但不同**：DRAFT-14414（libpng 不透明化）—— 同为图像库 API 漂移，但
  迁移面与根因都不同，本条未被图谱命中

## 现象

2006 年的 C 代码对现代 giflib 编译，报两条一模一样的错：

```
rwimg/rwgif.c:57:43: error: too few arguments to function call, expected 2, have 1
    data->file = DGifOpenFileName(filename);
rwimg/rwgif.c:140:36: error: too few arguments to function call, expected 2, have 1
    assert(DGifCloseFile(data->file) == GIF_OK);
```

## 根因：网上的「giflib 5 适配」经验大多讲的是 6.0

流传的说法是：giflib 5 把 `GifFileType` 变成不透明结构体、`DGifGetExtension`
消失、必须改用 `DGifSlurp` + `SavedImages` 遍历。

**那是 giflib 6.0 的 API 面。** 实测 ohpcd 的 `giflib/5.2.2` 头文件
（`GIFLIB_MAJOR 5` / `GIFLIB_MINOR 2`）后确认 5.2 的真实情况：

- `GifFileType` 仍是**可见结构体**，`SWidth`/`SHeight`/`SColorMap`/`Image`/
  `SavedImages`/`Error`/`UserData`/`Private` 字段全部可直接读写；
- `DGifGetRecordType` / `DGifGetImageDesc` / `DGifGetLine` / `DGifGetExtension` /
  `DGifGetExtensionNext` **全部保留原签名**；
- 唯一的不兼容点是 5.0 给 `DGifOpenFileName()` 和 `DGifCloseFile()` 各加了
  一个 `int *Error` 出参。

旁证：Gentoo portage 里 metapixel-1.0.2 那个叫
`metapixel-1.0.2-giflib5.patch` 的补丁只有 **529 字节**（Pacho Ramos, 2016,
bug 571934）—— 529 字节不可能是一次 slurp 重写。

## 修复：两处各补一个局部 int 出参

```c
    gif_data_t *data = (gif_data_t*)malloc(sizeof(gif_data_t));
    int error;                                   /* 新增 */
    data->file = DGifOpenFileName(filename, &error);
    ...
    assert(DGifCloseFile(data->file, &error) == GIF_OK);
```

`error` 与两次调用同在 `open_gif_file()` 作用域内，无需传参。原有 `assert`
仍检查返回值（`DGifOpenFileName` 失败返回 NULL，后续 assert 会抓住），
**失败语义与上游完全一致**。

## 排查口诀

> 撞到 giflib 报错先做两件事：
> 1. `grep -E 'GIFLIB_MAJOR|GIFLIB_MINOR' <includedir>/gif_lib.h` 确认主次版本；
> 2. 看 `expected N, have M` 的 N 是否 = M+1 且只出现在这两个函数上。
>
> 两者都成立就补出参，**不要启动 6.x 重写**。

**选版本建议**：需要 GIF 读的老 C 项目优先选 giflib/5.x（改动最小）；
ohpcd 现有 `giflib/5.2.2` 与 `giflib/6.1.3` 均已发布。

## 三段式证据链（本条已实测）

| 步骤 | 结果 |
|------|------|
| 不打补丁，只编 `rwimg/rwgif.c` | 恰好 2 条 error，同一份源码另 14 个 `.c` 全 0 error → 不兼容面只有这个文件 |
| 读 giflib/5.2.2 头文件 | `GifFileType` 可见，5 个 `DGif*` 签名原样 |
| 打补丁 | `conan create` rc=0；用例 6 真实解码一张 GIF 并生成图库条目；`readelf` 可见 `NEEDED libgif.so.7` 且动态符号表有 `DGif*` → GIF 后端真在链上、真被调用 |

反向验证：撤掉补丁，用例 6 由 PASS 转 FAIL。

## 红线提醒

GIF 读是 metapixel 1.0.2 的主打特性（NEWS 明写 *GIF reading and JPEG writing
support*）。**为绕开这两个签名就去掉 `-DRWIMG_GIF`，等于交付残废软件** ——
这类"为过编译而裁剪功能"是 P0。

## 适用范围

- 任何依赖 giflib 的 C 项目（老照片/图像处理工具、动图工具、`gif2*` 类）
- 直接读写 `GifFileType` 字段或调用 `DGifOpenFileName` 的 2000 年代前后源码
- 需要 GIF 能力、且不愿为绕开库 API 变更而裁剪功能的适配任务

## 关联文件

- `archives/m/metapixel/1.0.2/patches/0001-rwimg-rwgif-c-giflib5-error-out-parameters.patch`
- `archives/m/metapixel/1.0.2/notes.md`（问题 #1 与「没有踩的坑」小节）
