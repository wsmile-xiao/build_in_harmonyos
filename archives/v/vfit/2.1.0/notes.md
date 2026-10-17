# vfit 2.1.0 HarmonyOS PC 适配笔记

## 1. 上游信息
- 名称: vfit (Variable Font Instancing Tool)
- 版本: 2.1.0 (2020-12-31, tag v2.1.0, commit 6c083cf)
- 仓库: https://github.com/jonpalmisc/vfit
- 源码: PyPI sdist https://files.pythonhosted.org/packages/92/59/4cb8e5cc1b4698ad8fc029efd052ab0fb718c073950df2b6c25cdb8889c4/vfit-2.1.0.tar.gz (sha256 67ec63131e009b5030d9caf77f41cd824948719ca0e0eb498a44f88596abc906)；GitHub tag 归档 5e3a50da4122318ade9108489ae78523b8490e3e52e17e360165421f741b3c4a 为同版本另一打包
- 许可证: MIT
- 构建系统: poetry (poetry.masonry.api), 纯 Python, 无 C 扩展
- 依赖: python ^3.6, tqdm ^4.48.0, fonttools ^4.13.0, brotli ^1.0.7
- 入口: pyproject.toml `[tool.poetry.scripts]` vfit = "vfit.app:main"

## 2. 上游测试审计
- 解压 pypi sdist 及 GitHub tag 归档，均无 `tests/`、`test/`、`*_test.py` 目录
- `pyproject.toml` 无 `[tool.pytest]` 配置，`poetry.lock` dev 仅含 yapf
- `setup.py` / `PKG-INFO` 亦无测试声明
- 结论: 上游 **无测试用例**，需走 `upstream_tests_exist: false` + 审计说明路径，test_package 补全消费者测试

## 3. 平台适配要点
- 纯 Python noarch, 无需交叉编译, `settings = os, arch` 并 `package_id clear`
- 运行时依赖 fonttools/tqdm/brotli 非 Conan 包，需在 build() 阶段 `pip install --break-system-packages` 全局安装，保证 `import vfit` 不报 ModuleNotFoundError；打包时仅打包 vfit 本身 (`--no-deps`)
- pip --prefix staging 在不同 Python / pip 版本下会产生 `lib/python3.12/site-packages`、`lib64`、`local/lib` 等多种布局，package() 需探测 5 个候选并递归查找 `vfit` 目录
- console_scripts 在 `--prefix` 模式下可能落于 `staging/bin` 或 `staging/local/bin`，先 copy 再检查 `bin/vfit` 是否存在，不存在则手写 wrapper (`from vfit.app import main`)
- OHOS Python 路径: 通过 `sys.version_info` 动态推导 `python3.12` 目录，适配 `python3.12~3.13` 均可

## 4. 遇到问题与解决
- pip 安装时网速/镜像: conandata.yml 提供 4 个 pypi 镜像（华为云/阿里云/腾讯云/官方）共享同一 sha256，CI 自动重试
- poetry 构建隔离: 使用 `--no-build-isolation` + 预装的 fonttools/tqdm/brotli 避免在隔离环境中重复下载；sdist 本身不含 poetry.lock，无需 poetry
- 可执行权限: 手写 bin/vfit 后需 chmod 0o755，否则 CI 的 smoke test 无法执行

## 5. 验证方法
- 本地(OHOS aarch64 真机预检):
  ```
  conan create archives/v/vfit/2.1.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
  ```
- test_package 阶段会自动运行 `python3 test_vfit.py` 并输出 HMBS markers
- 上游测试: 无 (status no_tests)，新增测试 8 assertions 全部通过
