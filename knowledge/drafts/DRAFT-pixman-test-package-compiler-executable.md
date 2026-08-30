# pixman: test_package 手写编译命令要读取 compiler_executables

## 触发场景

pixman 0.46.4 首轮真机 shadow CI 中，主包 Meson 构建和打包已成功，但 `test_package` 编译失败：

```text
/system/bin/sh: clang: inaccessible or not found
ERROR: pixman/0.46.4 (test package): Error in build() method
```

## 根因

主包构建使用 Conan profile 中的 `tools.build:compiler_executables`，编译器是 `/data/service/hnp/bin/clang`。但 `test_package` 手写编译命令时只用了 `os.environ.get("CC", "clang")`，没有读取 profile，因此退回裸名 `clang`。

## 修法

在 `test_package/conanfile.py` 中：

```python
executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
cc = os.environ.get("CC") or executables.get("c") or "clang"
```

同时用 `shlex.quote` 拼接 include/lib/macro 参数。

## 验证

第二轮 shadow CI 中，`test_package` 调用 `/data/service/hnp/bin/clang`，编译并运行成功：

```text
pixman 0.46.4: API smoke + dlopen ok
```
