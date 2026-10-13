# DRAFT-ubelt-1.4.0-ohos-python-platform-posix-xdg：OHOS CPython 平台标识为 `'ohos'`，平台分派须覆盖/退化为 POSIX 并遵循沙箱 XDG 路径

> Contributor: lyl_ling | Status: Draft | Updated: 2026-10-04
> Source: ubelt 1.4.0 适配 HarmonyOS PC（`test_package/test_ohos_ubelt.py` 鸿蒙专项测试）
> 对应：`knowledge/drafts/DRAFT-ubelt-1.4.0-ohos-python-platform-posix-xdg.kv`

## 现象

在本平台运行 Python 时：

```console
$ python3 -c "import sys; print(sys.platform)"
ohos
$ python3 -c "import os; print(os.environ.get('XDG_CACHE_HOME'))"
/data/storage/el2/base/haps/entry/files
```

即 `sys.platform` 不是 `'linux'` 而是 `'ohos'`；同时 OHOS 运行时把
`XDG_CACHE_HOME` 注入到**应用沙箱**。

## 根因 / 契约

纯 Python 包的平台分派若用 `startswith('linux') / =='darwin' / =='win32'`
三选一穷举，会在 OHOS 落入 `else`（例如
`raise NotImplementedError('Unknown Platform %r' % (sys.platform,))`）。

正确判据是**模块级 POSIX 布尔**：

```python
POSIX = 'posix' in sys.builtin_module_names   # OHOS 下为 True
```

ubelt 1.4.0 的 `ubelt/util_platform.py` 正是如此，故其
`platform_cache_dir()/platform_data_dir()` 在 OHOS 上取 POSIX 分支、读取
`XDG_*`，不会抛 `NotImplementedError`。

附带的坑：本平台**无该 uid 的 passwd 记录**——
`pwd.getpwnam('100')` 抛 `KeyError`、`getpass.getuser()` 返回字符串 `'100'`。
因此依赖 passwd 的 `userhome(username)` 不可用；无参 `userhome()` 仍正常。
ubelt 的 2 项上游失败（`util_path.py::userhome:0`、
`tests/test_path.py::test_pathlib_compatability`）源于此。

## 方案

1. 平台分派统一用 POSIX 判据（`'posix' in sys.builtin_module_names`），不要
   穷举 `sys.platform` 白名单。
2. 用户目录统一走 `XDG_*`（由 OHOS 运行时注入沙箱），不要硬编码
   `/data/storage/el2/...`。
3. 对依赖 passwd 的旧接口，评估改为 `os.environ` 回退。
4. 鸿蒙专项测试断言：`sys.platform=='ohos'`、`POSIX is True`、
   `Path.appdir()` 落在 `XDG_CACHE_HOME` 之内、沙箱目录可写。
