# justbackoff 0.6.0 — 适配笔记

## 概述
- 上游: https://github.com/alexferl/justbackoff（历史路径 `admiralobvious/justbackoff`，
  GitHub 301 重定向；PyPI `Home-page` 仍写旧名）
- 版本/时点: tag `v0.6.0` = commit `b8ca3e58074959e0bb5cf937752c39396e4fa8cd`
  （PyPI 发布 2020-05-02，上游最新版）
- 类型: 纯 Python 分发库（单模块包 `justbackoff`，`packages=["justbackoff"]`），
  无 C/C++ 代码、无本地扩展
- 依赖: **零第三方依赖**（唯一 import 为标准库 `random`）
- 语言（R47 判定）: `python`（lang-preflight: task=python / detected=python，
  构建系统 setuptools，源文件 4 个全为 python，主体占比 100%）
- 补丁数: **0**

## 源码身份核验（真实命令 / 原始输出）
```
$ curl -sSL -o justbackoff-0.6.0.tar.gz \
    https://files.pythonhosted.org/packages/9c/67/d1a9a9b0035c6314e93d7ef381e0c01571b069400899a0f606b5b3b7751a/justbackoff-0.6.0.tar.gz
curl rc=0
$ sha256sum justbackoff-0.6.0.tar.gz
a30d1683b81bd67655f7a0188f7dedd6384fea6b80a157668d1583ad02618097   # == PyPI digest
$ curl -sSL -o jb-repo-v0.6.0.tar.gz https://codeload.github.com/alexferl/justbackoff/tar.gz/refs/tags/v0.6.0
$ sha256sum jb-repo-v0.6.0.tar.gz                  # 下载两次，逐字节一致
a9cb2c6ad619b3e9c9c5caef981cf3e0a6179bb89b72a2d9a1e6eee9eb1f8625
$ cmp sdist/justbackoff-0.6.0/justbackoff/__init__.py repo/justbackoff-0.6.0/justbackoff/__init__.py ; echo rc=$?
rc=0        # 两个归档的模块文件逐字节一致（e8f25fcbde407079560e2953f66d7c75daee0d81c9c3f92d3636c06c0459b4be）
$ git ls-remote --tags https://github.com/alexferl/justbackoff.git
refs/tags/v0.1.0 … refs/tags/v0.6.0                # 上游只有 0.1.0~0.6.0，无 0.8.3
```
日志: `justbackoff-0.6.0-evidence/logs/01_upstream_download.log`、`02_source_identity.log`

## 适配要点
1. **零源码补丁**：模块只有 `import random`（标准库），无 ABI/平台分支、无文件系统
   访问 → OHOS 上由平台 CPython 3.12 解释执行，与上游行为一致。
   R40 不适用（非图形/多媒体/系统底层类库），R32 的 settings.os 分支在本配方不存在。
2. `package_type = "python-require"`；package() 用 `shutil.copytree` 把 sdist 的
   `justbackoff/` 拷到 `lib/python3.12/site-packages/justbackoff`
   （本环境 pip/setuptools 构建不可用；同 jinja2/3.1.6、appdirs/1.4.4、
   jmespath/1.1.0 的 python-require 形态）。
3. `package_info()` 注入 runenv/buildenv 的 PYTHONPATH（aiohttp 教训：只 print 不够）。
4. R38: 上游 setup.py 无 `scripts=` / console_scripts / entry_points，
   `packages=["justbackoff"]` 纯库包、无 bin/ 产物 → **不创建 commands.json**。
5. **双源码**（conandata.yml）：包载荷取 PyPI 官方 sdist；上游测试取官方仓库
   tag tarball（sdist 未打包 `tests/`）。两者均为 R39 合规 https 官方源，sha256 双固定。

## 首个真实错误 / 根因 / 修复
- 本包在本机**没有出现编译类错误**（纯 Python 无编译步骤）。
- 过程中遇到的**唯一真实阻塞**是平台/工具链层面（非本包引入）：
  1. **宿主解释器无 pytest**（`python3 -m pytest` → `No module named pytest`）。
     修复：按 jinja2/3.1.6 先例，在 `build()` 内从平台 pip 镜像
     （`ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX`）把 `pytest>=7` 取到
     `build/test-deps` 独立目录，再以其为 PYTHONPATH 运行上游套件；
     **取依赖失败显式抛 ConanException**，不静默降级、不跳过（R51）。
  2. **本平台 Python subprocess 无法执行裸命令名**（实测 `git`/`conan`/`python3`/
     `bash`/`tar` 全部 `FileNotFoundError`，只有绝对路径可执行）→ 配方内一律用
     `sys.executable`（绝对路径），不使用裸 `python3`/`pip`。

## 上游测试（R51 如实申报）
- 上游声明运行器：**pytest**（三处一致 —— `.travis.yml`
  `script: pytest --cov=./justbackoff`；`Makefile` `test: ${PYTHON} -m pytest`；
  `setup.cfg` `[aliases] test=pytest`）
- 唯一测试源：`tests/test_backoff.py`（unittest 风格，`TestBackoff` 类）
- 用例 6 个：`test_defaults` / `test_factor` / `test_for_attempt` /
  `test_get_attempt` / `test_jitter` / `test_integers`
- 命令：`python3 -m pytest tests -v --no-header -p no:cacheprovider --basetemp=<build>/pytest-basetemp`
- 实测：**6 passed / 0 failed / 0 skipped**（`6 passed in 0.05s`，rc=0）→ 6/6 = 100%
- 无漏测：上游声明用例数 = 6，实际执行 = 6，未实例化 = 0
  （`tests/__init__.py` 为空包标记文件，非用例）
- 双口径: `source_declared_total=6`, `configured_executable_total=6`,
  `executed_passed_total=6`, `failed=0`, `uninstantiated=0`
- 日志（build 阶段逐用例的**权威来源**）：
  * `archives/.../reports/w3-local-ci.log` —— W3 本地 CI 模拟（`build_and_test.sh` 以
    `--build="justbackoff/*"` 强制重建）：build 阶段 6 条用例逐条 PASSED +
    test_package 42/11 断言 + L0/L1 门禁结果
  * `.ci_logs/conan_build_justbackoff_0.6.0.log` —— CI 同路径日志（脚本写入位置）
  * `archives/.../reports/conan-create.log` —— 手动
    `conan create --build="justbackoff/*"` 的输出；⚠️ **该文件会被其后任意一次
    `conan create` 覆盖**：若末次调用来自 `conan-verify` G2 的 `--build=missing`，
    则是缓存复用运行、**不含 build 阶段**（W4 第二轮审计据此提出过归属修正），
    因此 build 阶段一律以 `w3-local-ci.log` 为准
  * `justbackoff-0.6.0-evidence/logs/07_upstream_pytest_local.log` —— 探索期本地实跑

## test_package（消费者视角，R34）
- `test_justbackoff.py`：42 断言，真实调用 `Backoff` / `to_seconds` / `to_ms`
  （单位换算、默认值、duration 序列 + attempt + reset、for_attempt 直查、
  factor=1.5、max_ms 封顶边界、int 参数等价、jitter 有界与可复现、
  jitter=False 确定性、模块落位于被安装 site-packages）
- `test_ohos_justbackoff.py`：**11 断言（鸿蒙特有，≥1 达标）** ——
  O1 运行时身份（CPython 3.12，实测 `sys.platform=ohos` / `aarch64`）；
  O2 导入路径落在 `<pkg>/lib/python3.12/site-packages/justbackoff`（conanrun
  PYTHONPATH 接线）；O3 noarch 契约（.so/.pyd/.dylib/.a/.o 计数 0）；
  O4 平台熵源（stdlib `random` 是模块唯一非上游表面，8 次 `random()` 落在
  [0,1) 且 jitter 有界）；O5 只读安装契约（`python3 -B` 全新解释器导入成功
  且不落 `__pycache__`）
- test_package **不替代**上游测试统计（上游统计独立申报，见上）。

## 环境
- Python 3.12.9（`sys.platform=ohos`，aarch64），Conan 2.29.1，remote `ohpcd`
- `/tmp` 只读（E002）→ 临时目录用 `$HOME/tmp` / `$TMPDIR`
- 平台限制：Python subprocess 裸命令名不可执行（一律绝对路径）

### 对话 #1 — 版本号纠错、双源码选型与平台坑（关键决策与教训）

1. **版本号先核验再动手**：派发版本写作 `0.8.3`，但上游（PyPI JSON、鸿蒙社区
   PyPI 分发源、GitHub tags、crates.io/npm/Homebrew/RubyGems）**一致只到 0.6.0**。
   取证后与用户确认改为 `0.6.0`，避免用 0.6.0 的源码伪造 0.8.3 版本号
   （会被 CI L0j/PF8 拦截）。**结论：适配前必须先做版本线核验。**
2. **sdist 不含 tests/ 时用「双源」而非运行时联网**：sdist（13 entries）没有
   `tests/`，上游测试只在仓库 tag tarball 里。方案对比后选择在 conandata.yml 声明
   两个固定 sha256 的官方源（PyPI sdist 供包载荷 + GitHub tag tarball 供测试），
   并用逐字节哈希证明两者模块文件一致；比在 build() 里联网抓测试文件更可复现、无静默降级。
3. **`github.com/<o>/<r>/archive/refs/tags/<t>.tar.gz` 与 codeload 直链逐字节相同**
   （实测 sha256 一致），但前者命中 CI 的镜像 fallback 白名单（`github.com`），
   后者（`codeload.github.com`）不在白名单 → 选用前者。
4. **宿主无 pytest 不构成跳过理由**：本机 `python3 -m pytest` 直接
   `No module named pytest`。按 jinja2/3.1.6 先例，build() 内从平台 pip 镜像把
   `pytest>=7` 取到 `build/test-deps` 独立目录再跑上游套件，**取依赖失败显式抛错**
   （R51：拒绝把没跑过的套件报成通过）。实测镜像取到 pytest 9.1.1。
5. **本平台 Python 无法执行裸命令名**（`git`/`conan`/`python3`/`bash`/`tar` 全部
   `FileNotFoundError`，`shutil.which` 却能找到）→ 配方内所有子进程必须用
   `sys.executable` 等绝对路径；`self.run("python3 ...")` 因走 shell 解析仍可用。
6. **本地 W3 会把 conandata.yml 改写成镜像列表且不还原**：`build_and_test.sh` 的
   Mirror fallback 步骤把 `upstream_tests` 的 github.com URL 改写成
   `["https://gh-proxy.com/https://github.com/...", "<原 URL>"]` 并留在工作树
   （同时留下 `conandata.yml.orig` / `.ghfast-bak` 残留）。**该 URL 命中 PF7
   镜像黑名单**，必须在提交前还原（本次已还原并核对 sha256 =
   `d71955e3c3a39a210171979e8edbe8d9d93ec9bb1aff0cbf7f6b4b03f9b35766`）。
7. **本地 W3 的 JC 门禁默认退回 full 模式**（分支无 commit → `origin/main...HEAD`
   为空 → 整仓 `git ls-files`），会命中 origin/main 里既有的 5 个被跟踪运行期状态
   文件与 5 个未登记隐藏文件。按 CI 同口径（`JUNK_PR_DIFF=<pr.diff>` → prdiff 模式，
   只查本 PR 的 10 个文件）运行后 `JC_RESULT=pass` / `Junk Files: 0` / `JC6 涉及软件数: 1`。
8. **test_package 先本地试跑再进配方**：两个测试脚本先在对拍 site-packages 上跑通
   （42 + 11 断言），再进 `conan create`，避免在 CI 里浪费一轮。
9. **`-B`/只读安装契约**：OHOS 沙箱安装目录可能不可写，故鸿蒙专项测试用
   `python3 -B` 子进程验证「不写字节码也能导入」，而不是只断言算法正确。
---

**编译结束**: 2026-10-02 15:32
**最终状态**: built
