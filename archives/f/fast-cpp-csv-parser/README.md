# fast-cpp-csv-parser

## 软件描述
fast-cpp-csv-parser 是一个 header-only 的 C++11 CSV 解析库（单头文件 csv.h），以极快的速度解析 CSV 数据，支持编译期模板特性开关。

## 功能概述
- **CSV 解析**：流式读取（`csv::io::CSVReader`），按行读取到结构体
- **模板特性开关**：转义字符串等特性编译期启用/禁用（只付所需性能开销）
- **裁剪策略**：`csv::io::trim_chars` 自定义列首尾忽略字符
- **缺失列处理**：`ignore_missing_column` 容忍缺失列

## OHOS 适配

### 构建方式
- **header-only C++11**：无构建系统（无 CMake/Makefile）——`package()` 拷贝 `csv.h`（单头文件）到 include
- 编译需 `-std=c++11` + `-lpthread`（README 明示——线程用于并行解析）

### 关键攻坚点
1. **header-only**：单头文件——aarch64 OHOS 直接可编译（无平台限制）
2. **无正式测试套件**：上游仅有 `.clusterfuzzlite` 模糊测试（parse_fuzzer.cpp，非单元测试）——rule 4 如实记录，R34 消费验证代替（编译运行真实 CSV 解析）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only；编译需 -lpthread）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| master | built | 2026-08-28 | header-only 无构建系统适配 |

## 参考资料
- 上游仓库: https://github.com/ben-strasser/fast-cpp-csv-parser
