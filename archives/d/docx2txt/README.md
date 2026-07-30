# docx2txt

docx2txt 是一个从 Microsoft Office DOCX 文件提取纯文本的 Perl 脚本工具。

## 功能概述
- 从 DOCX 文件提取文本内容
- 支持从 STDIN 读取 DOCX 文件
- 支持输出到文件或 STDOUT
- 支持处理列表、超链接等格式化内容
- 支持自定义配置文件

## OHOS 适配
- 纯 Perl 脚本项目，无需编译步骤
- Conan 配方直接安装脚本与配置，避免上游 Makefile 缺少 DESTDIR 支持
- 运行时从 PATH 查找 unzip，避免依赖 `/usr/bin/unzip`
- 临时文件优先写入 TMPDIR，避免使用 OpenHarmony 上不可写的 `/tmp`

## 依赖关系
- **运行依赖**: perl, unzip

## 参考资料
- 官网: https://sourceforge.net/projects/docx2txt/
- 源码: https://sourceforge.net/projects/docx2txt/files/docx2txt/v1.4/
