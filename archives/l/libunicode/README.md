# libunicode

Unicode 字符处理库，提供：
- Unicode 字符属性查询
- 字符大小写转换
- 文本分段（词、句子、字形）
- UTF-8 编码处理
- Emoji 序列检测

## 版本
- 0.9.0 (2024)

## 依赖
- 无外部依赖（纯 C++20）

## 编译要点
- Clang 15 需禁用 std::format/std::simd/std::formatter
