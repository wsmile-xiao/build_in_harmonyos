# tabledata 1.3.5 适配笔记

## 编译环境
- 构建系统: python（纯 Python 库，无编译）
- 编译日期: 2026-08-29
- 状态: built（HarmonyOS 验证通过）
- 特殊说明: 纯 Python 库，无 C 扩展、无 .so、无 ELF 签名，不受 HMDFS/SELinux dlopen 限制

## 库简介

tabledata 是用于表示表格数据的 Python 库，供 pytablewriter / pytablereader /
SimpleSQLite 等库使用。
- 上游仓库: https://github.com/thombashi/tabledata
- 许可证: MIT
- 类型: 纯 Python（依赖 dataproperty + typepy）

## Conan 配方说明

### 配方结构
- `conanfile.py`: Conan 配方（纯 Python——source() 下载 + package() 拷贝
  tabledata/ 到 lib/python3）
- `conandata.yml`: PyPI sdist 下载 URL 和 SHA256
- `test_package/`: 消费者测试，验证 import tabledata

### 关键配置
- `package_type = "application"`：纯 Python 库
- `requires = "dataproperty/1.1.1", "typepy/2.0.0"`：运行时依赖
  （tabledata 的 requires_dist 为 `DataProperty>=1.0.2,<2` 与
  `typepy>=1.2.0,<3`；loguru 是 optional extra "logging"——test_logger
  用 NullLogger 不依赖 loguru，故不入 requires）
- 纯 Python 库——无编译——安装 tabledata/ 到 site-packages

## 依赖

| 依赖 | 版本 | 状态 |
|------|------|------|
| dataproperty | 1.1.1 | main 已合入 |
| typepy | 2.0.0 | main 已合入 |

## 测试说明

### 上游测试（实测，rule 4）
上游 test/ 目录 5 个测试文件（pytest），本地实测 **79 passed = 100%**：
- test_common.py / test_converter.py / test_logger.py / test_normalizer.py /
  test_tabledata.py（含 parametrize 展开的最小测试单元）
- 依赖 DataProperty/typepy 安装后全量通过（test_logger 用 NullLogger，
  不需要 loguru）

### test_package 测试
- 文件: `test_package/test_tabledata.py`
- 验证内容:
  1. import tabledata（纯 Python 库——lib/python3）
  2. tabledata.__version__ 读取

## 验证结果

HarmonyOS 验证通过：上游 pytest 79/79（100%），Conan `test_package`
消费者测试 1/1。

## 注意事项

1. **纯 Python 特性**：无编译、无 .so，无需 ELF 签名/RPATH
2. **依赖链**：dataproperty/typepy 已合入 main，无需额外适配
3. **test_package PYTHONPATH**：遍历依赖的 site-packages 全加
   PYTHONPATH（dataproperty 模板教训——逐个加易漏）
