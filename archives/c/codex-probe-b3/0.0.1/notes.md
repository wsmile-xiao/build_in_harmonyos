# codex-probe-b3 0.0.1 鸿蒙适配笔记

## 环境信息
- 操作系统：HarmonyOS 6.0（aarch64）
- Python：3.12.9
- Conan：2.12.0

## 项目类型
纯 Python、零依赖 CLI 工具，无需编译。

## 构建步骤
1. 下载源码包（通过 ghfast.top 镜像）
2. 复制 Python 源码到包目录
3. 设置 PYTHONPATH 环境变量

## 测试

### 上游测试（81 项）
- 框架：unittest
- 运行：python3 -m unittest discover tests/ -v
- 结果：Ran 81 tests, OK
- 明细：
  - test_http_retry.py: 9
  - test_scoring.py: 56
  - test_validators.py: 16

### 鸿蒙消费者测试（5 项）
- 运行：conan create 时自动执行 test_package
- 通用测试：模块导入、CLI --help
- 鸿蒙专属：数据文件路径、list-baselines 子命令、平台指纹
- 结果：5/5 通过

## 平台指纹
- platform.system() = HarmonyOS
- platform.machine() = aarch64
- Python = 3.12.9
