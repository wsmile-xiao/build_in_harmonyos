# identify — Python file type identification library

identify 是一个纯 Python 实现的文件类型识别库，
用于通过文件名、文件内容和 shebang 识别文件类型。
它是 pre-commit 的运行时依赖，也被 all-repos 等工具间接依赖。

## 用途

- 识别文件类型（编程语言、数据格式、文本/二进制等）
- 识别文件名对应的标签（如 `.py` → `python`）
- 识别解释器（shebang 行）
- 识别许可证类型（可选功能，需安装 ukkonen 扩展）

## 安装

```bash
pip3 install identify
```

## 上游地址

https://github.com/pre-commit/identify

## 许可证

MIT License
