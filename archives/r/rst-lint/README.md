# rst-lint 2.0.2 for OpenHarmony

`rst-lint`（PyPI 包名 `restructuredtext-lint`，导入包 `restructuredtext_lint`）是一个 reStructuredText
语法/结构检查器命令行工具，用于在文档发布前发现 reST 排版错误。本 Conan 配方打包上游官方发行包，
不引入任何 C/C++ 依赖。

## 上游来源

- 上游仓库：https://github.com/twolfson/restructuredtext-lint （tag `2.0.2`）
- PyPI：https://pypi.org/project/restructuredtext-lint/2.0.2/
- 源码：`restructuredtext_lint-2.0.2.tar.gz`（sha256 `dd25209b9e0b726929d8306339faf723734a3137db382bcf27294fa18a6bc52b`）
- 许可证：Unlicense（Public Domain）

## 产物

- `lib/pythonX.Y/site-packages/restructuredtext_lint/`（Python 包，含 `VERSION`）
- `bin/rst-lint`、`bin/restructuredtext-lint`（上游 `setup.py` 的两个 console_scripts 入口）

## 依赖

- `docutils/0.23` —— 上游 `requirements.txt` 声明 `docutils>=0.11,<1.0`，由已发布的
  `docutils/0.23` 满足（conan 消费，未使用 `--build=missing` 绕过）。

## 使用

```bash
conan install --requires=rst-lint/2.0.2
source conanrun.sh
rst-lint README.rst          # 0 = 通过，2 = 存在 lint 错误
```

## 验证

- 上游官方测试入口 `test.sh`（`flake8 --max-line-length=120 restructuredtext_lint` + `nosetests --nocapture`）：
  **16/16 用例通过**（9 个 API 用例 + 7 个 CLI 用例）。
- `test_package`：消费者视角断言（import/`lint()`/`lint_file()` + `bin/rst-lint` 端到端），
  含 1 个 OpenHarmony 平台用例（POSIX entry script + `$TMPDIR` 路径语义）。
- `conan create`（OHOS aarch64 profile）与 `conan-verify` 通过。

上游 `test.sh` 额外依赖 `flake8-quotes==3.4.0`（requirements-dev.txt）。该包在可用镜像
（pypi.cnb.cool / pypi.repo.openharmony.cn / pypi.org）均不可获取；上游 `test.sh` 的 flake8
调用未启用任何 flake8-quotes 选项，`setup.cfg` 亦无 flake8 配置段，故 lint 步骤不依赖它。
详见 `2.0.2/notes.md`。
