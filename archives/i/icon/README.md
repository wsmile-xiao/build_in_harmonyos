# Icon Programming Language

Icon 是一种高级通用编程语言，具备强大的字符串处理、列表处理和图形功能。广泛用于文本分析、数据处理和算法研究。

- 官网: https://www.cs.arizona.edu/icon
- 源码: https://github.com/gtownsend/icon
- 许可证: Public Domain

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 9.5.25a | built | 2026-06-16 | NoGraphics 配置，需 ELF 签名 |

## 编译注意事项

- Icon 使用自有构建系统（`make Configure name=linux`），非标准 autotools/cmake
- 编译 Ilib 前必须对 icont/iconx 进行 ELF 签名
- 无图形支持（NoGraphics 配置）
- make Install 不支持标准 DESTDIR 模式，需手动适配
