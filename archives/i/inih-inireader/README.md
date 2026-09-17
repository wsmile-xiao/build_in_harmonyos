# inih / INIReader

> 简单、小巧的 C 语言 INI 解析库，以及配套的 C++ `INIReader` 封装。

## 简介

inih (INI Not Invented Here) 是一个用 C 写的、面向嵌入式场景的小型 INI 解析器，
兼容 Python `ConfigParser` 风格的 `.INI` 文件（含 RFC 822 风格多行值、`name: value`
条目、UTF-8 BOM、内联注释）。同一仓库还提供 C++ 的 `INIReader` 类，把解析结果存进
`std::map`，并附带 `Get`/`GetInteger`/`GetReal`/`GetBoolean` 等取值接口。

## OHOS 适配要点

- 上游是 Meson 工程（`meson.build`）；本仓库**直接编译** `ini.c` 与
  `cpp/INIReader.cpp` 为两个静态库，不引入 Meson 依赖。
- 安装内容：`include/ini.h`、`include/INIReader.h`、`lib/libinih.a`、
  `lib/libINIReader.a`、`licenses/LICENSE.txt`。
- 静态链接顺序为 `INIReader` → `inih`；Conan 侧通过
  `cpp_info.libs = ["INIReader", "inih"]` 声明。
- 无外部依赖，仅使用 C / C++ 标准库。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | C 标准库 + C++ 标准库（`std::map` / `std::string`） |

## 功能验证

```cpp
#include <cstring>
#include <ini.h>
#include <INIReader.h>

int main() {
    const char *ini = "[user]\nname = Bob\n";
    INIReader reader(ini, std::strlen(ini));
    return reader.Get("user", "name", "?") == "Bob" ? 0 : 1;
}
```

## 参考

- [源码仓库](https://github.com/benhoyt/inih)
- [上游 README](https://github.com/benhoyt/inih/blob/master/README.md)
