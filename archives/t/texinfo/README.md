# GNU Texinfo

## 简介
GNU 项目的文档编写系统，可以生成 Info、HTML、PDF 等多种格式的文档。

## OHOS 适配
- 3 处独立的 config.guess/config.sub 需修补（主目录、tta/、tta/perl/CheckXS/）
- 使用 --disable-nls 禁用 NLS（HarmonyOS 缺少相关库）
- 文档目录需从 SUBDIRS 移除以跳过文档构建
- 官方测试套件 138 测试中 92 通过、46 跳过（缺外部工具），无失败

## 依赖
- Perl（运行 makeinfo 等工具）

## 功能验证
```bash
texi2any --version
makeinfo --version
```

## 参考
- 官网: https://www.gnu.org/software/texinfo/
