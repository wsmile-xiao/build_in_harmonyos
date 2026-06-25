# onigmo

正则表达式库，从 Oniguruma 分支而来。

## 描述

Onigmo 是一个从 Oniguruma 分支而来的正则表达式库。它提供了一套完整的正则表达式功能，支持多种字符编码。

## 特性

- 多编码支持（UTF-8、UTF-16、UTF-32、EUC-JP、Shift_JIS 等）
- POSIX API 兼容性
- GNU API 兼容性
- 扩展正则表达式功能（反向引用、前瞻、后瞻等）

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 6.2.0 | 已发布 | 2026-05-19 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- onigmo 6.2.0
```

## 使用示例

```c
#include <onigmo.h>

int main() {
    regex_t* reg;
    OnigErrorInfo einfo;
    
    int r = onig_new(&reg, pattern, pattern_end,
        ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8,
        ONIG_SYNTAX_DEFAULT, &einfo);
    
    // 使用正则表达式...
    
    onig_free(reg);
    return 0;
}
```

## 编译说明

由于 autotools 配置存在 automake 版本兼容性问题，本版本使用自定义 CMakeLists.txt 进行构建。

## 依赖关系

无外部依赖，为独立的静态库。