# ubelt

A Python utility belt containing simple tools, a stdlib like feel, and extra
batteries. Pure Python (`py3-none-any`), no C/C++ code, **zero mandatory
runtime dependencies** (all third-party packages are opt-in extras).

- 上游仓库: https://github.com/Erotemic/ubelt
- 版本: 1.4.0
- 适配说明: 纯 Python noarch 包，无编译；以 `package_type=python-require`
  将 `ubelt/` 包目录安装到 `site-packages`，供 HarmonyOS PC 上
  Python 3.12（`sys.platform == 'ohos'`）使用。

## 依赖

强制第三方依赖：**无**。`setup.py` 的 `install_requires` 取自空的
`requirements/runtime.txt`；`PKG-INFO` / wheel `METADATA` 中非 extra 的
`Requires-Dist` 计数为 0。numpy / xxhash / Pygments / python-dateutil /
packaging / colorama / pydantic 等仅出现在 extras（`optional`/`all`/
`tests`/`docs`/`types`）之下，默认安装不会拉取。

## 上游测试

```bash
python3 -m pytest -v -p no:doctest --xdoctest --xdoctest-style=google ubelt tests
```

`tests/` 含 25 个测试文件、244 个 `def test_` 用例，另加包内 xdoctest
doctest。OHOS 真机实测：548 passed / 17 failed / 43 skipped（17 项失败为
平台环境限制，详见 `1.4.0/notes.md`）。
