# DRAFT-multipledispatch-version-metadata-reconciliation

## 现象

`multipledispatch` 发行版本是 `1.0.0`，但上游包内
`multipledispatch.__version__` 仍然返回 `0.6.0`。这两个值来自不同层：

- Conan/PyPI distribution metadata：`1.0.0`
- Python module attribute：`0.6.0`

## 风险

如果配方把模块属性强行改成发行版本，可能改变上游用户依赖的行为；
如果只检查模块属性，又可能把正确的 Conan 版本误判为 `0.6.0`。下游
工具还可能分别使用 `importlib.metadata.version()` 和
`module.__version__`，因此两者都需要被显式记录。

## 处理原则

1. Conan `name/version` 使用任务和发行物版本 `multipledispatch/1.0.0`。
2. 不修改上游 Python 源码，不制造本地版本补丁。
3. 消费者测试分别断言 distribution metadata 为 `1.0.0`、模块属性为
   上游保留值 `0.6.0`。
4. 在 manifest、notes 和 PR 正文中说明差异，避免审核者把它误认为
   配方版本漂移。

## 验证

```python
import importlib.metadata
import multipledispatch

assert importlib.metadata.version("multipledispatch") == "1.0.0"
assert multipledispatch.__version__ == "0.6.0"
```

两项断言都在生成的 Conan 包消费者测试中执行。多分派行为测试继续
验证 `dispatch` 和 `Dispatcher.add`，因此版本检查不会替代功能检查。

## 适用边界

适用于 Python 项目发行元数据与模块内版本常量由不同文件维护的情况。
若模块版本影响 ABI、协议或序列化格式，必须进一步评估是否需要上游
修复或适配版本后缀，不能只做记录。

## 查重结论

本草稿专注 `multipledispatch 1.0.0` 的双版本事实和验证方法，不是通用
版本升级规则的替代品。

## 关联文件

- `archives/m/multipledispatch/1.0.0/manifest.yaml`
- `archives/m/multipledispatch/1.0.0/notes.md`
- `archives/m/multipledispatch/1.0.0/test_package/test_multipledispatch.py`
