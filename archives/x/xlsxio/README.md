# xlsxio — C 库，用于读写 .xlsx 文件

XLSX I/O 是一个用 C 语言编写的库，用于读取和写入 Microsoft Excel .xlsx 文件。.xlsx 格式本质上是一个包含 XML 文件的 ZIP 压缩包。

## 功能

- 读取 .xlsx 文件中的数据和元数据
- 写入 .xlsx 文件
- 支持多工作表（worksheet）
- 流式 API，适合处理大文件

## 组件

| 组件 | 说明 |
|------|------|
| `libxlsxio_read` | 读取库，依赖 minizip + expat |
| `libxlsxio_write` | 写入库，依赖 minizip |
| `xlsxio_xlsx2csv` | 命令行工具：XLSX → CSV |
| `xlsxio_csv2xlsx` | 命令行工具：CSV → XLSX |

## 编译依赖

- zlib ≥ 1.2.x
- minizip ≥ 1.2.x（或 minizip-ng / libzip）
- expat ≥ 2.0.x（读取库需要）

## 构建系统

CMake

## 许可证

MIT License

## 主页

https://github.com/brechtsanders/xlsxio

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.2.36 | published | 2026-06-24 |
