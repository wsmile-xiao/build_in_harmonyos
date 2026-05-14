# blockhash 0.1 编译笔记

## 编译摘要

| 项目 | 状态 |
|------|------|
| 软件 | blockhash 0.1 |
| 状态 | **published** |
| 构建系统 | custom (手动编译) |
| 编译日期 | 2026-05-07 |

## HarmonyOS 适配

### 原始问题

blockhash 原版依赖 MagickWand (ImageMagick)，ImageMagick 在 HarmonyOS 上编译遇到：
1. **E064**: autotools configure 在 HMDFS 上有权限问题
2. **依赖链过长**: ImageMagick 需要大量依赖库

### 解决方案

使用 **stb_image.h** 单头文件库替代 MagickWand：
- stb_image 是单头文件，无需编译，直接 `#include` 即可
- 支持 JPEG、PNG、BMP、GIF 等常见格式
- 无外部依赖，编译简单

### 代码修改

```diff
--- a/blockhash.c
+++ b/blockhash.c
-#include <wand/MagickWand.h>
+#define STB_IMAGE_IMPLEMENTATION
+#include "stb_image.h"
```

### 编译命令

```bash
clang -O3 -DVERSION="0.3.2-harmonyos" -o build/blockhash blockhash.c -lm
/data/service/hnp/bin/binary-sign-tool sign -inFile build/blockhash -outFile build/blockhash.signed -selfSign 1
mv build/blockhash.signed build/blockhash
```

## 测试结果

```bash
$ blockhash --version
0.3.2-harmonyos

$ blockhash testdata/*.jpg testdata/*.png
f81bf99ffb803400e07f8c7d049f058706013e233fe33fe11f600e638ea30def  testdata/00002701.jpg
3fff1ca004e80fe81fe00fe01fe81de8fffb0ffb00610031003b03ff80df01ff  testdata/00011601.jpg
... (17 images processed successfully)
```

## 知识提取

### E064: conftest 无法执行导致配置检测失败

| 项目 | 内容 |
|------|------|
| 触发工具 | autotools configure |
| 根因 | HMDFS 上创建临时目录 `./confXXXXXX/` 失败 |
| 解决方案 | 使用 clang-wrapper 自动签名 conftest |

### 替代方案: stb_image 替代 MagickWand

| 项目 | 内容 |
|------|------|
| 适用场景 | 需要图像加载但不想编译 ImageMagick |
| 优点 | 单头文件，无依赖，编译简单 |
| 缺点 | 功能较少，不支持所有 ImageMagick 格式 |

---

**编译开始**: 2026-05-07 11:50
**编译结束**: 2026-05-07 11:55
**最终状态**: published