# rst-lint 2.0.2 适配笔记

## 编译环境
- 构建系统: custom（纯 Python：copytree staging + 生成 console_scripts 入口脚本）
- 编译日期: 2026-10-02
- Python: 3.12.9（cmd-pkgs 预装）；conan 2.29.1（OHOS 适配版）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 / compiler=clang 15 / libc++ / cppstd=17 / Release）
- 状态: built

## 构建步骤

1. **源码核验**：`conandata.yml` 下载上游 sdist 并按 sha256 校验
   （`dd25209b9e0b726929d8306339faf723734a3137db382bcf27294fa18a6bc52b`，与上游 Homebrew formula
   及 PyPI 记录一致）。
2. **语言预检（R47）**：`lang-preflight --lang python` → 语言匹配（setuptools manifest，主体 Python 100%）。
3. **staging**：把源码包 `restructuredtext_lint/` 复制到 `build/site-packages/`（剔除 `__pycache__`/`*.pyc`），
   构建期先 `compile()` 逐个 `.py` 做语法校验（fail fast）。
4. **打包**：`restructuredtext_lint/` → `lib/python3.12/site-packages/`，并依据上游
   `setup.py` 的 `entry_points.console_scripts` 生成 `bin/rst-lint` 与 `bin/restructuredtext-lint`
   （POSIX shebang + `sys.path` 注入，docutils/0.23 先例）。
5. **依赖**：`requires("docutils/0.23")`（conan 消费，已发布；未使用 `--build=missing` 绕过）。

真实命令（关键）：

```bash
python3 scripts/ohc-run.py init-build rst-lint 2.0.2 --url <sdist> --tar tar.gz
python3 scripts/ohc-run.py lang-preflight rst-lint 2.0.2 --src <work> --lang python
conan create archives/r/rst-lint/2.0.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=<user> --channel=<channel>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `test.sh` 需要 `nosetests`（nose-py3 1.8.0） | nose 生态在 Python 3.12 上易碎 | 实测 nose-py3 1.8.0 wheel 在 Python 3.12.9 可正常发现并执行 16 个用例（见下） |
| 2 | `flake8-quotes==3.4.0` 三个镜像均不可获取 | 镜像未收录该包 | 上游 `test.sh` 的 flake8 调用未启用 flake8-quotes 选项、`setup.cfg` 无 flake8 段，lint 步骤不受影响；如实记录 |
| 3 | 目标为纯 Python，但 L0p 要求 `settings` 含 os/compiler/build_type/arch | 门禁要求 | `settings` 声明四项（profile 提供 clang 15），构建无编译步骤 |

## 源码修改

无补丁（`patches/` 为空）。上游改动仅 2.0.2 的发布说明：`2.0.2 - Fixed timing of wheel compilation and publish`。

## 依赖版本

- 运行时直接依赖：`docutils>=0.11,<1.0` → conan `docutils/0.23`（可消费，EXIT=0）
- 运行时传递依赖：无（docutils 纯标准库实现）
- 仅测试/构建：`nose-py3==1.8.0`、`flake8==7.3.0`、`flake8-quotes==3.4.0`（+ flake8 传递 `mccabe`/`pycodestyle`/`pyflakes`）——pip 生态，不进入制品

## 验证结果

上游测试入口 `test.sh` 实测（PYTHONPATH 含已安装 docutils 0.23 与源码树）：

```bash
$ flake8 --max-line-length=120 restructuredtext_lint
FLAKE8_EXIT=0
$ nosetests --nocapture -v
... 16 tests ...
Ran 16 tests in 1.421s
OK
NOSETESTS_EXIT=0
```

- 用例总数 **16** / 通过 **16** / 失败 **0** / 跳过 **0**
- 用例清单：`TestRestructuredtextLint`（9）+ `TestRestructuredtextLintCLI`（7），逐项名称见
  `test_package/MANIFEST.yml` 的 `upstream_tests.cases`。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/python3.12/site-packages/restructuredtext_lint/` | Python 包（含 `VERSION`） |
| `bin/rst-lint`、`bin/restructuredtext-lint` | CLI 入口脚本（纯 Python，无 ELF，无需签名） |

## 注意事项

- `cli.py` 在 import 期读取包内 `VERSION` 文件——打包必须保留该文件。
- 纯 Python，无 ELF 二进制，不涉及 OHOS 签名/`L4/L5` 安全扫描。
- 上游入口脚本依赖 `python3` 在 PATH（OHOS 由 cmd-pkgs 提供）。
- OHOS `/tmp` 只读（Gotcha E002）：运行时与测试使用 `$TMPDIR`。
---

**编译结束**: 2026-10-02 13:28
**最终状态**: built
