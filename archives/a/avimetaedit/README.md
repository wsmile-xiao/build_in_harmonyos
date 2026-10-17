# avimetaedit

AVI-MetaEdit — 编辑 AVI 文件元数据的命令行工具（公共领域 CC0-1.0）。

上游：MediaArea / US National Archives
- 官网: https://mediaarea.net/AVIMetaEdit
- 源码: https://mediaarea.net/download/source/avimetaedit/1.0.2/avimetaedit_1.0.2.tar.gz

## 功能

- 技术元数据导出（--out-tech，CSV 格式）
- XMP / aXML / iXML chunk 的插入、移除、导出
- INFO chunk 编辑（--ISFT= 等）
- MD5 生成、校验、嵌入（--MD5-Generate / --MD5-Verify / --MD5-Embed）
- --simulate 模拟模式（不写盘）
- --append 将新/扩展 chunk 放到文件末尾

## 构建

Autotools（autogen.sh 生成 configure），自包含（vendored ZenLib/TinyXml/MD5），
运行时唯一系统依赖 pthread。详见 `1.0.2/` 配方。

## 版本

- 1.0.2 — 上游 1.0.2 GNU/FromSource 源码包适配