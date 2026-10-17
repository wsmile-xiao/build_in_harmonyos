# pydantic 1.10.19 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-08-28
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/pydantic/1.10.19 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist（355KB——含 tests/，pydantic 1.x sdist 自带
测试套件），`strip_root` 后解压。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `pydantic/` 模块（含 v1/ 子包
与 py.typed）到 `lib/python3.12/site-packages/`；`env_info.PYTHONPATH`
暴露导入路径。

### 3. 上游测试（build() 集成——rule 4 实测回填）
sdist 自带 tests/（40 个 test_*.py），跑 pytest：
```bash
PYTHONPATH=<src> python3 -m pytest tests/ -q --no-header \
  --override-ini=filterwarnings= --basetemp=/data/storage/el2/base/cache/pyd-bt
```

**实测结果：2494 passed / 1 failed / 98 skipped（2495 收集）**

关键处理（环境差异修复）：
1. **filterwarnings=error 与 pytest 9.x 冲突**：上游 setup.cfg 设
   `filterwarnings=error`，pytest 9.x 的 PytestRemovedIn10Warning
   （parametrize 非集合迭代器弃用）被升级为错误导致收集失败——
   `--override-ini=filterwarnings=` 覆盖（上游固定 pytest 7.2.1，但
   pytest 7.2.1 与 Python 3.12 不兼容实测——装后 pytest 无法导入，
   故用 9.x + 覆盖）
2. **tmp_path fixture 属主异常**：pytest-of-<uid> 临时目录 owner 异常
   （Permission denied）——`--basetemp` 指定可写目录（同 aiohttp/
   python-dotenv 教训）
3. **1 failed：test_assert_raises_validation_error**——pytest 9.x
   断言重写注入格式与上游固定 7.2.1 不同（错误消息多一个换行）——
   环境/版本差异如实记录，非 pydantic 代码缺陷
4. **98 skipped**：mypy/dotenv/email_validator/memray 未安装 +
   Python 版本分支（3.9+/3.11+ 特性）——上游测试可选依赖跳过明细

## 验证结果
- **构建**: `pydantic/1.10.19: Package created`
- **上游测试**: 实测 **2494/2495 = 99.96%**——2494 passed / 1 failed
  （pytest 版本差异）/ 98 skipped（可选依赖）——build() 集成回填
  （rule 4，分母=全部收集用例）
- **R34 消费者验证**: test_package——模块可导入 + BaseModel 构造/校验/
  dict 真实 API（1/1 = 100%）
