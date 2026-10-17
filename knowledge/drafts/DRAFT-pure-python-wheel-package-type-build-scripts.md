# DRAFT-pure-python-wheel-package-type-build-scripts（草稿）

- **软件**：tornado 6.5.2 / snakeviz 2.2.2（纯 Python，wheel 交付）
- **构建系统**：setuptools（`pip wheel --no-deps`）
- **平台**：HarmonyOS PC / aarch64，Python 3.12.9
- **状态**：DRAFT

## 现象

1. 直接把 `package_type` 写成 `library`：

```
ERROR: Package type is 'library', but self.options['shared'] is required
```

2. `settings` 只写 `"os", "arch"` 时被 W3 的 L0p 闸拦下：

```
[fail] L0p: settings 缺少 'compiler' — OHOS profile 需要全部四项
[fail] L0p: settings 缺少 'build_type' — OHOS profile 需要全部四项
[fail] leapp... gate failed: missing_setting_compiler missing_setting_build_type
```

## 根因

1. Conan 2 没有 "python" 这个 package_type；`library` 会被强校验要求 `shared`
   选项（E216），而 wheel 产物不是可链接库。语义最贴近的是 `build-scripts`
   ——不可链接的模块集合。
2. W3 的 L0p 闸要求 OHOS profile 的 settings 四件套齐全（os/arch/compiler/
   build_type），缺一即拦截。
3. wheel 解包后消费者不知道往哪 `import`，需要显式暴露站点目录。

## 适配做法

| 环节 | 做法 |
|------|------|
| package_type | `build-scripts` |
| settings | `"os", "arch", "compiler", "build_type"`（四件套） |
| build | `pip wheel . --no-deps --wheel-dir <build_folder>` |
| package | `zipfile` 解包 wheel 到 `<pkg>/lib/python3.12/site-packages` |
| package_info | `conf_info.define("user.<name>:sitedir", <site-packages 绝对路径>)` |
| test_package | 用 `dep.conf_info.get("user.<name>:sitedir")` 取路径插入 `sys.path` |

- 可选 C 加速扩展（tornado 的 `speedups`）在上游 `setup.py` 里是
  `optional=True`：不要设置禁用开关，让 clang 正常尝试编译，失败自动回退纯
  Python；test_package 如实报告 `speedups: present / absent`。
- 上游测试若驱动 CLI（如 snakeviz `-s`），用
  `pip install --prefix <build>/prefix` 装到构建本地前缀并注入 PATH/PYTHONPATH，
  确保测的是被测 wheel 而非环境残留。

## 验证

- tornado 6.5.2：`conan create` 通过，上游 1222 例（1219 通过、3 例沙箱限制豁免、
  57 例上游 skipif），test_package 4/4（含真实 IOLoop 回环 HTTP 请求）。
- snakeviz 2.2.2：上游 pytest 12/12，test_package 3/3（起 `snakeviz -s` 服务 +
  `/snakeviz/<prof>` 回环断言 viz.html）。

## 相关

- `archives/t/tornado/6.5.2/conanfile.py`
- `archives/s/snakeviz/2.2.2/conanfile.py`
- `archives/a/aiohttp-fast-zlib/0.3.0/conanfile.py`（同范式先例）
