# conan 2.29：dict 型 conf 不能用 `:子键` 取值，必须整字典取出后再取键

**条目**: `DRAFT-genht-1.1.3-conan-conf-dict-subkey-get-raises`
**来源**: genht 1.1.3 适配（配方 build() 首行抛 ConfException）
**状态**: DRAFT

## 现象

```python
cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
```

conan 2.29.1 直接抛：

```
ConanException: [conf] 'tools.build:compiler_executables:c' does not exist
in configuration list. Run 'conan config list' to see all the available confs.
```

即使 profile 里确实写了：

```ini
[conf]
tools.build:compiler_executables={"c": "/data/service/hnp/bin/clang", "cpp": "/data/service/hnp/bin/clang++"}
```

## 根因

`tools.build:compiler_executables` 是 **dict 型** conf，2.29.1 不支持把它当成分层键用
`:` 取子项。仓库自带的 `templates/conanfile-makefile.py.tmpl` 示例正是旧写法，
属模板缺陷（建议后续修订）。

## 正确写法（本仓 1849 例惯例）

```python
def _compiler(self):
    """R33: 编译器只从 conan conf 取，绝不读 ${CC}/${CFLAGS}（CI worker 上为空）。"""
    executables = self.conf.get(
        "tools.build:compiler_executables", default={}, check_type=dict
    ) or {}
    compiler = executables.get("c")
    if compiler:
        return compiler
    if cross_building(self):
        raise ConanInvalidConfiguration(
            "cross builds require tools.build:compiler_executables[c]"
        )
    return "cc"
```

参考实现：`archives/a/abootimg/0.6/conanfile.py`。

## 要点

- 取不到时**不要**静默回落 `"clang"`：交叉编译下会用错工具链，必须显式报错。
- `default={}` 与 `check_type=dict` 要同时给，否则 conf 缺失时 path 不同。
- 实证：genht 1.1.3 改写法后 conan create 通过，W3 `L0/L1/L4/L5` 全过。
