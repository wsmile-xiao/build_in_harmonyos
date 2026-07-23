# docx2txt 1.4 适配笔记

## 项目特征
- 纯 Perl 命令行应用，无本地编译产物。
- 上游 Makefile 仅提供 install 目标，不支持 DESTDIR，也没有自动测试目标。
- 运行依赖为 Perl 与 unzip，不引入 Conan 构建依赖。

## 适配方案
- Conan 配方直接安装 `docx2txt.pl`、`docx2txt.sh` 与 `docx2txt.config`。
- 提供 `docx2txt` 主命令，并保留上游脚本名。
- 通过 `DOCX2TXT_CONFIG` 指向包内配置文件。
- 从 PATH 查找 unzip，避免硬编码 `/usr/bin/unzip`。
- 临时目录优先使用 `TMPDIR` 或 `TEMP`，避免 OHOS 上不可写的 `/tmp`。

## 测试策略
- 上游 1.4 未提供自动测试套件，因此在 MANIFEST.yml 中记录豁免原因。
- test_package 从内置测试数据还原最小 DOCX 文件。
- 执行包内 docx2txt 命令生成文本文件，并校验预期文本。

## 已知限制
- 目标系统必须提供可用的 Perl 与 unzip。
- `docx2txt.sh` 依赖 Bash；主命令 `docx2txt` 可直接由 Perl 执行。
