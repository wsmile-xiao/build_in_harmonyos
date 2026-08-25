# md4c

md4c is a fast C Markdown parser with a SAX-like callback interface, created by Martin Mitas.
Upstream repository: https://github.com/mity/md4c

## 基本信息

- **名称**: md4c
- **主页**: https://github.com/mity/md4c
- **许可证**: MIT
- **分类**: library
- **语言**: C

## 鸿蒙适配要点

- 上游使用标准 CMake 构建, 无需重写构建系统
- 仅打包 `md4c` (核心 parser) 与 `md4c-html` (HTML renderer) 两个库
- 关闭 `md2html` 命令行可执行文件 (库包不需要)
- R26: OHOS 交叉编译强制 `BUILD_SHARED_LIBS=OFF` 静态库
- 无外部依赖, 纯 C 单文件 parser

## API

核心解析入口:

```c
int md_parse(const MD_CHAR* text, MD_SIZE size,
             const MD_PARSER* parser, void* userdata);
```

通过 `MD_PARSER` 结构体中的回调函数交付解析事件:

- `enter_block` / `leave_block` — 块级元素 (文档/标题/段落/列表/代码块等)
- `enter_span` / `leave_span` — 行内元素 (强调/加粗/链接/代码等)
- `text` — 文本内容

`md4c-html` 库在此基础上提供直接输出 HTML 的便捷接口 (`md_html()`).

## CMake 目标

消费方使用:

```cmake
find_package(md4c REQUIRED)
target_link_libraries(myapp md4c::md4c)        # 核心 parser
# 或
target_link_libraries(myapp md4c::md4c-html)   # HTML renderer
```
