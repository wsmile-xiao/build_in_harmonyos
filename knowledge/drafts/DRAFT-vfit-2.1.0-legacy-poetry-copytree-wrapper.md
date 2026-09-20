# DRAFT-vfit-2.1.0-legacy-poetry-copytree-wrapper
> legacy poetry后端缺失时纯Python包免构建直拷打包与wrapper注入PYTHONPATH

## 问题特征（真实日志片段/标记）
- 真机 `package()` 阶段执行 `pip install --prefix staging src_dir` 失败：`pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'poetry.masonry.api'`
- 伴随日志：`BackendUnavailable: Cannot import 'poetry.masonry.api'` / `ERROR: vfit/2.1.0: Error in package() method, line 62 self.run(ConanE`
- `conan create` 退出码 1，`v2:compile:compiler_error` 未通过；`--no-build-isolation` 仍需该后端无法绕过
- 辅助门禁：`settings = "os", "arch"` 缺少 `compiler/build_type` 触发 L0p 拦截（CI #51325），需四项完整 settings

## 根因
vfit 2.1.0 的 `pyproject.toml` 使用 legacy poetry 构建后端 `poetry.masonry.api`。真机环境仅有现代 pip，未安装 poetry，即使使用 `--no-build-isolation` 仍需导入该后端，触发 `BackendUnavailable`。原配方 `package()` 依赖 `pip install --prefix` 必然失败；纯Python包实际无需构建，属构建系统与真机环境不匹配，非源码编译错误。

## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/v/vfit/2.1.0/conanfile.py:package()` 移除 `self.run("pip install --prefix ...")` 调用，改为直接拷贝：`shutil.copytree(os.path.join(self.source_folder, "vfit"), os.path.join(self.package_folder, "lib/python{}.{} /site-packages/vfit".format(...)))`，目标为 `package_folder/lib/pythonX.Y/site-packages/vfit`
2. 同文件 `package()` 自生成可执行 `bin/vfit` wrapper：创建 `package_folder/bin/vfit`，写入 `#!/usr/bin/env python3`、`import sys, os`、`sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib/pythonX.Y/site-packages"))`、`from vfit.app import main; sys.exit(main())`，并 `chmod +x`
3. `archives/v/vfit/2.1.0/conanfile.py:build()` 将运行时依赖 `pip install fonttools tqdm brotli` 包裹为 `try/except`，失败仅 `self.output.warning()`，实现 best-effort、幂等与重入，不阻塞打包
4. `archives/v/vfit/2.1.0/conanfile.py` 与 `test_package/conanfile.py` 将 `settings = "os", "arch"` 补齐为 `settings = "os", "compiler", "build_type", "arch"`，保留 `package_id().clear()` 与 `configure()` 去安全化逻辑以维持 noarch 特性，满足 `ci/conan/build_and_test.sh` L0p 四项校验
5. 验证：`conan create` 日志无 `BackendUnavailable`，`package_folder` 下 `lib/pythonX.Y/site-packages/vfit` 与 `bin/vfit` 存在且可执行

## 禁止策略
- 禁止模式：`pip install.*--prefix|poetry\.masonry\.api` — 禁止在未提供 `poetry.masonry.api` 的环境中继续以 `pip install --prefix` 触发 legacy poetry 构建
- 原因：必然复现 `BackendUnavailable: Cannot import 'poetry.masonry.api'`
- 后果：`package()` 直接报错退出，`conan create` 退出码 1，HMBS 真机门禁不通过

## 与相近条目的边界（查重）
- 查重命中仅为 compiler error/ICE、autotools 头安装等相邻条目，现有知识库无 `poetry.masonry.api` / `BackendUnavailable` 相关条目，强增量
- 本条目抽象为 `legacy poetry后端缺失时纯Python包免构建直拷通用模式`（含 `build()` best-effort 与 wrapper 生成），可跨同类纯Python库复用；不适用于需编译扩展或复杂 `entry_points` 需真实构建的包（此类走 fallback 安装 poetry 后端）
- 与 `autotools`/`cmake` 构建类条目正交，与 `compiler error` 非同因

## 适用判断
- 适用：`pyproject.toml` 声明 `build-backend = "poetry.masonry.api"` 或同类 legacy poetry 后端，且源码为纯Python无扩展，日志出现 `BackendUnavailable` / `poetry.masonry.api` 时
- 不适用：含 C 扩展需编译、或 wrapper 无法覆盖的复杂插件发现机制时，改用 fallback 先安装 poetry 后端再 pip 安装
- 判定：命中 `match_keywords` 中 `backendunavailable + poetry.masonry.api + pure_python_copytree` 且 `phase=packaging` 时优先采用本模式
