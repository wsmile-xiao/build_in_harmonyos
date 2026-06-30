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
- OpenHarmony 缺少 GNU install 命令，需手动创建 staging 目录安装文件
- Makefile 不支持标准 DESTDIR 模式，需手动复制文件
- HTTPS 证书验证问题可通过 HTTP 协议下载解决

## 依赖关系
- **运行依赖**: perl, unzip

## 参考资料
- 官网: https://sourceforge.net/projects/docx2txt/
- 源码: http://downloads.sourceforge.net/project/docx2txt/docx2txt/v1.4/docx2txt-1.4.tgz