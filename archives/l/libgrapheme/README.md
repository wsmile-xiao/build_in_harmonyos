# libgrapheme

## 简介

libgrapheme 是一个小巧且易用的 C 库，用于高效处理字素簇（grapheme clusters）和单词分割。它遵循 Unicode 标准，提供跨平台的文本处理能力。

## 主要功能

- **字素簇分割**：正确处理 Unicode 字素边界，支持复杂文字（如 emoji、组合字符）
- **单词分割**：按 Unicode 标准进行单词边界检测
- **字符计数**：准确计算用户感知的字符数量
- **UTF-8 支持**：原生支持 UTF-8 编码

## 编译信息

### 当前版本

- **版本**: 3.0.0
- **编译日期**: 2026-05-21
- **状态**: built（编译成功）
- **构建系统**: custom configure (suckless style)

### HarmonyOS 适配

libgrapheme 使用 suckless 风格的 configure 脚本，需要添加 HarmonyOS 系统识别支持。

**补丁**: `0001-configure.patch`
- 在 configure 脚本的系统识别部分添加 HarmonyOS 支持
- 将 HarmonyOS 映射为 Linux 系统

### 编译依赖

无外部依赖，仅依赖标准 C 库。

## 使用方法

### 安装

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libgrapheme 3.0.0
```

### 编程接口

```c
#include <grapheme.h>

// 字素簇分割
size_t grapheme_next_character_break(const char *str, size_t len);

// 单词分割
size_t grapheme_next_word_break(const char *str, size_t len);

// 字符计数
size_t grapheme_character_len(const char *str, size_t len);
```

### 示例代码

```c
#include <stdio.h>
#include <grapheme.h>

int main() {
    const char *text = "Hello, 世界! 👋";
    size_t len = strlen(text);
    size_t char_count = grapheme_character_len(text, len);

    printf("字符数: %zu\n", char_count);
    return 0;
}
```

编译：

```bash
clang -I/usr/local/include -L/usr/local/lib -lgrapheme -o example example.c
```

## 产物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| libgrapheme.a | 静态库 | 静态链接库 |
| libgrapheme.so.3.0.0 | 动态库 | 动态链接库 |
| grapheme.h | 头文件 | C API 头文件 |
| man3/*.3 | 文档 | API 文档 |
| man7/libgrapheme.7 | 文档 | 总览文档 |

## 注意事项

1. **系统识别**: suckless 风格的 configure 脚本需要手动添加 HarmonyOS 支持
2. **ldconfig**: HarmonyOS 不支持 ldconfig，make install 时需忽略错误
3. **gen 目录**: 首次编译需确保 gen/*.h 文件存在

## 许可证

ISC License

## 参考链接

- 官方网站: https://libs.suckless.org/libgrapheme/
- GitHub 镜像: https://github.com/FRIGN/libgrapheme
- 上游源码: https://git.suckless.org/libgrapheme/