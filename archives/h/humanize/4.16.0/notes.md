# humanize 4.16.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-08-28
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/h/humanize/4.16.0 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist（90KB——src/humanize/ + tests/），
`strip_root` 后解压。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `src/humanize/` 模块（含
locale/ 多语言目录 + py.typed）到 `lib/python3.12/site-packages/`；
`env_info.PYTHONPATH` 暴露导入路径。

### 3. 上游测试（build() 集成——rule 4 实测回填）
sdist 自带 tests/（6 个 test_*.py），跑 pytest：
```bash
PYTHONPATH=src python3 -m pytest tests/ -q --no-header \
  --override-ini=filterwarnings= \
  --basetemp=/data/storage/el2/base/cache/hum-bt
```

**实测结果：784 passed / 0 failed / 0 skipped（9.23s）**

关键处理（环境差异修复）：
1. **filterwarnings=error 与 pytest 9.x 冲突**：上游 tox.ini/pyproject 设
   filterwarnings 严格——pytest 9.x 的 PytestRemovedIn10Warning 被升级为
   错误导致收集失败——`--override-ini=filterwarnings=` 覆盖
2. **tmp_path fixture 属主异常**：pytest-of-<uid> 临时目录 owner 异常
   ——`--basetemp` 指定可写目录（同 aiohttp/python-dotenv 教训）
3. **测试依赖**：freezegun/pytest-benchmark 需安装（本地 pip 装）——
   测试数字以本地实测为准如实记录
4. **conan 沙箱 PATH 无 python3**——绝对路径调用

## 验证结果
- **构建**: `humanize/4.16.0: Package created`
- **上游测试**: 实测 **784/784 = 100%**——784 passed / 0 failed /
  0 skipped——build() 集成回填（rule 4，分母=全部用例）
- **R34 消费者验证**: test_package——模块可导入 + filesize/intcomma/
  naturalsize 真实 API（1/1 = 100%）
