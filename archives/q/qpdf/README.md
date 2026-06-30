# qpdf

[qpdf](https://github.com/qpdf/qpdf) 是一个命令行程序和 C++ 库，用于查看、结构检查和修复 PDF 文件。

## 功能特性

- PDF 文件结构检查和修复
- PDF 文件合并和拆分
- PDF 加密和解密
- PDF 元数据操作
- 保留 PDF 文件的原始结构

## 编译状态

| 版本 | 状态 | 日期 |
|------|------|------|
| 11.6.3 | built | 2026-05-20 |

## 使用方法

```bash
# 检查 PDF 文件
qpdf --check input.pdf

# 合并 PDF 文件
qpdf --empty --merge input1.pdf input2.pdf -- output.pdf

# 拆分 PDF 文件
qpdf input.pdf --split-pages output.pdf

# 加密 PDF
qpdf --encrypt user-password owner-password 128 input.pdf output.pdf
```

## 依赖

- libjpeg-turbo
- zlib
- openssl（可选）

## 注意事项

- qpdf 11.6.3 使用 CMake 构建系统，能够直接识别 HarmonyOS 平台
- 无需修改源码即可编译