# shoco

**shoco**：快速短字符串压缩/解压 C 库（C99，零依赖，MIT License）。

- 上游仓库：https://github.com/Ed-von-Schleck/shoco
- 版本归档：`archives/s/shoco/master/`
- 构建系统：纯 Makefile（无 configure / install 目标）
- 平台：HarmonyOS PC aarch64（OHOS）

## 功能

- `shoco_compress(const char *in, size_t len, char *out, size_t bufsize)`：短字符串压缩
- `shoco_decompress(const char *in, size_t len, char *out, size_t bufsize)`：短字符串解压
- CLI 工具 `shoco`：`shoco {c|d} <infile> <outfile>`（压缩/解压文件），见 `commands.json`

## 帮助文档

- 版本适配笔记：`master/notes.md`
- 验证报告：`master/reports/test-report.md`
- 消费者示例：`master/consumer_example.c`
- 鸿蒙专项测试：`master/ohos_special_test.c`
- Conan 配方：`master/conanfile.py` + `master/conandata.yml`