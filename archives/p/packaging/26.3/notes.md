# packaging 26.3 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-08-28
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/packaging/26.3 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist（313KB——src/packaging/ + tests/），
`strip_root` 后解压。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `src/packaging/` 模块（含
py.typed）到 `lib/python3.12/site-packages/`；`env_info.PYTHONPATH`
暴露导入路径。

### 3. 上游测试（build() 集成——rule 4 实测回填）
sdist 自带 tests/（31 个 test_*.py），跑 pytest：
```bash
PYTHONPATH=src python3 -m pytest tests/ -q --no-header \
  --override-ini=filterwarnings= -m "not property" \
  --basetemp=/data/storage/el2/base/cache/pkg-bt
```

**实测结果：62422 passed / 1 skipped / 427 deselected**

关键处理（环境差异修复）：
1. **filterwarnings=error 与 pytest 9.x 冲突**：上游 pyproject.toml 设
   `filterwarnings=error`，pytest 9.x 的 PytestRemovedIn10Warning 被升级
   为错误导致收集失败——`--override-ini=filterwarnings=` 覆盖
2. **tmp_path fixture 属主异常**：pytest-of-<uid> 临时目录 owner 异常
   ——`--basetemp` 指定可写目录（同 aiohttp/python-dotenv 教训）
3. **property 标记 opt-in**：上游 addopts 默认 `-m "not property"`
   （property-based tests 可选）——同样排除（427 deselected）
4. **测试依赖**：pretend/tomli_w/hypothesis 需安装（本地 pip 装）——
   测试数字以本地实测为准如实记录
5. **1 skipped**：test_manylinux.py:180 requires a glibc-based Linux——
   OHOS 非 glibc 环境差异，如实记录

## 验证结果
- **构建**: `packaging/26.3: Package created`
- **上游测试**: 实测 **62422/62423 = 99.998%**——62422 passed / 1
  skipped（glibc 环境差异）/ 427 deselected（property opt-in）——
  build() 集成回填（rule 4，分母=全部收集用例）
- **R34 消费者验证**: test_package——模块可导入 + Version/SpecifierSet
  真实 API（1/1 = 100%）
