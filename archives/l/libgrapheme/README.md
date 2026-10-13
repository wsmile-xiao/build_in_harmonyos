# libgrapheme

## 简介

libgrapheme 是一个小巧且易用的 C 库，用于高效处理字素簇（grapheme clusters）和单词分割。它遵循 Unicode 标准（3.0.0 对应 Unicode 17.0.0），提供跨平台的文本处理能力。

## 主要功能

- **字素簇分割**：正确处理 Unicode 字素边界，支持复杂文字（如 emoji、组合字符）
- **单词分割**：按 Unicode 标准进行单词边界检测
- **行/句子分割**：Unicode 行断行与句子边界检测
- **双向文本**：Unicode 双向算法（bidi）嵌入级别与重排序
- **大小写转换与判定**：含 UTF-8 变体 API
- **UTF-8 编解码**：原生支持 UTF-8 编码

## 编译信息

### 当前版本

- **版本**: 3.0.0
- **构建系统**: suckless 自研 Makefile + configure（非 autotools/CMake）
- **外部依赖**: 无（仅需 C99 编译器；测试数据随发布包附带，离线可测）

### HarmonyOS 适配

libgrapheme 使用 suckless 风格的 `configure` 脚本（按 `uname` 选择
`.a`/`.so` 预设），需增加 HarmonyOS 系统识别支持。

**补丁**: `3.0.0/patches/0001-configure.patch`
- 在 `configure` 的系统识别分支中加入 `HarmonyOS`，复用 Linux 预设
  （静态库 + 版本化动态库 + symlinks）
- 仅触及 shell 脚本，不改 C 源码，不含平台宏

**安装说明**: OHOS 没有 `ldconfig`，配方以
`make install PREFIX=<package> LDCONFIG=` 完成安装，跳过该调用。

**测试说明**: 上游 `make test` 运行 8 个测试程序、共 884674 条断言
（Unicode 官方测试数据驱动）；其中 `test/bidirectional` 恒返回 0，
配方解析各程序打印的 `X/Y tests passed.` 分数行聚合结果。
`benchmark/` 需要第三方 libutf8proc，本配方不构建。

## 使用方法

### 编程接口

```c
#include <grapheme.h>

/* UTF-8 变体（消费者常用） */
size_t grapheme_decode_utf8(const char *, size_t, uint_least32_t *);
size_t grapheme_encode_utf8(uint_least32_t, char *, size_t);
size_t grapheme_next_character_break_utf8(const char *, size_t);
size_t grapheme_next_word_break_utf8(const char *, size_t);
size_t grapheme_next_sentence_break_utf8(const char *, size_t);
size_t grapheme_next_line_break_utf8(const char *, size_t);
size_t grapheme_to_uppercase_utf8(const char *, size_t, char *, size_t);
bool grapheme_is_lowercase_utf8(const char *, size_t, size_t *);
```

### 示例代码

```c
#include <stdio.h>
#include <string.h>
#include <grapheme.h>

int main(void) {
    static const char text[] = { 'e', '\xcc', '\x81', '\0' }; /* e + U+0301 */
    size_t br = grapheme_next_character_break_utf8(text, 3);
    printf("first cluster bytes: %zu\n", br); /* 3: base + combining mark */
    return br == 3 ? 0 : 1;
}
```

Conan 消费者（CMake）：

```cmake
find_package(libgrapheme CONFIG REQUIRED)
target_link_libraries(app PRIVATE libgrapheme::libgrapheme)
```

## 产物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| libgrapheme.a | 静态库 | 静态链接库（默认） |
| libgrapheme.so.3.0.0 (+ symlinks) | 动态库 | `shared=True` 时打包 |
| grapheme.h | 头文件 | C API 头文件 |
| libgrapheme.pc | pkg-config | 链接配置 |
| man3/*.3, man7/libgrapheme.7 | 文档 | API 文档 |

## 许可证

ISC License

## 参考链接

- 官方网站: https://libs.suckless.org/libgrapheme/
- 上游源码包: https://dl.suckless.org/libgrapheme/libgrapheme-3.0.0.tar.gz
- 上游 git: https://git.suckless.org/libgrapheme/
