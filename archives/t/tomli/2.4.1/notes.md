# tomli 2.4.1 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-08-28
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/tomli/2.4.1 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 PyPI sdist（17KB——不含 tests/，仅模块文件），`strip_root=True` 解压。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `src/tomli/` 模块（含 py.typed）
到 `lib/python3.12/site-packages/`；`env_info.PYTHONPATH` 暴露导入路径。

### 3. 上游测试（build() 集成——rule 4 实测回填）
sdist 不含 tests/（实测）——build() 从 GitHub 2.4.1 tag 下载 tests/（含
toml-test 数据），跑 pytest：
```bash
PYTHONPATH=src python3 -m pytest tests/ -q --no-header
```
- 纯 Python——全平台行为一致
- 无外部依赖（标准库）
- TMPDIR 指向 `/data/storage/el2/base/cache`（沙箱 /tmp 只读 +
  pytest-of-<uid> 属主检查——同 python-dotenv 教训）

**实测结果：17 passed / 0 failed / 0 skipped（17 用例 + 744 subtests =
100%，分母=全部用例）**

关键处理（缺依赖就装上 / 环境差异修复）：
1. **tests/ 从 GitHub 下载**：sdist 不含 tests/（仅 GitHub 仓库有，含
   toml-test 数据）——build() 从 GitHub 2.4.1 tag 下载（同 rich 模式）

## 验证结果
- **构建**: `tomli/2.4.1: Package created`
- **上游测试**: 实测 **17/17 通过（100%）**——17 passed + 744 subtests（pytest rc=0）——build() 集成回填（rule 4，分母=全部用例）
- **R34 消费者验证**: test_package——模块存在 + import tomli 真实 loads（1/1 = 100%）
