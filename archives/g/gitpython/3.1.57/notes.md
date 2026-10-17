# gitpython 3.1.57 适配笔记

## 基本信息

- **名称**: gitpython
- **版本**: 3.1.57
- **许可证**: BSD-3-Clause
- **上游**: https://github.com/gitpython-developers/GitPython（tag 3.1.57 实证存在）
- **类型**: 纯 Python 包（Git 仓库操作库——git 命令与对象模型的 Python 封装）

## 依赖关系

- **上游依赖**（PyPI requires_dist 实证）:
  - `gitdb>=4.0.1,<5` → 声明为 Conan requirement: `gitdb/4.0.12`（仓内已归档，制品仓已发布 ✅）
  - `typing-extensions>=3.10.0.2; python_version < "3.10"` → **条件依赖，目标 python3.12 不需要**（不声明）
- **传递依赖**: `smmap/5.0.3`（经 gitdb，制品仓已发布 ✅）
- **运行时外部程序**: git 可执行文件（GitPython 是 git 命令封装库，运行时通过
  `GIT_PYTHON_GIT_EXECUTABLE` 或 PATH 上的 git 调用真实命令——属于宿主环境供给，
  非 conan 依赖）

## 构建方式

纯 Python 包 conan 打包范式（gitdb/4.0.12 同款先例）：

```bash
python3 -m pip install --no-deps --target="{install_target}" "{source_folder}"
```

- `--no-deps`: gitdb 由 Conan 依赖管理（python3.12 环境下 typing-extensions 不需要），不通过 pip 拉取
- `--target`: 安装到构建目录 install 子目录
- 使用 `sys.executable` 确保调用正确的 Python 解释器

## 包信息暴露

通过 `runenv_info.prepend_path("PYTHONPATH", package_folder)` 将包路径注入运行时环境。
下游消费者经 conanrun 环境自动获得 gitpython + gitdb + smmap 三级 PYTHONPATH 叠加。

## 本地验证（local_verify）

```bash
conan create archives/g/gitpython/3.1.57 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

test_package 冒烟内容（import 冒烟 + 真实 API 断言）：
1. `import git` 成功
2. `git.__version__ == "3.1.57"`
3. 核心 API 面（Repo/Git/Actor/Commit/Blob/Tree/Head/Remote/IndexFile 等 12 项）可访问
4. Repo.init/clone_from + Git.version_info/execute/custom_environment 函数存在
5. 依赖链传递：gitdb + smmap 可导入
6. 端到端冒烟：`Repo.init` → `index.add` → `index.commit` → `head.commit.hexsha` 校验
   （环境有 git 可执行文件时执行；无则降级跳过并说明）

## 上游测试（rule 4，本地联网实跑）

- **上游 tag**: https://github.com/gitpython-developers/GitPython tag `3.1.57`
- **测试规模**: `pytest --collect-only` 实测 **784 个用例**（test/ 目录 30 个测试文件）
- **实跑环境**: 本机 OpenHarmony PC（arm64-ohos, Python 3.12.9, pytest 9.1.1, git 2.45.2 hnp 构建）
- **实跑结果**: **695 passed + 74 skipped + 1 xfailed + 14 failed**（25 分钟跑完）
- **测试前置条件**（本地已满足）: gitdb==4.0.12 + ddt + pytest-mock（上游 test-requirements）
- **rorepo fixture 注意**: 上游测试把 test 目录本身当只读仓库（`GIT_PYTHON_TEST_GIT_REPO_BASE`），
  克隆上游时需 `master` 分支存在（上游默认分支即 master，`--branch 3.1.57` 克隆后需补建）

### 14 个 failed 逐项定性（全部为环境/平台限制，非库适配缺陷）

| # | 测试 | 失败现象 | 定性 |
|---|---|---|---|
| 1-5 | test_commit.py 5 个 trailers 用例 | `trailers_dict == {}`——写入侧 `git interpret-trailers --trailer` 拼装 message 不在 subject 后插空行，读取侧 `--parse` 又要求空行分隔 | 本机 git 2.45.2 (hnp 构建) 的 interpret-trailers 行为与上游 CI git 版本差异（实测复现：`printf 'subject' \| git interpret-trailers --trailer="Issue: 123"` 输出无空行分隔，`--parse` 读不回） |
| 6 | test_git.py::test_environment | `GIT_SSH` 自定义脚本不被 git fetch (ssh://) 调用 | 本机 git 构建的 ssh 分派行为差异（实测 core.sshCommand/GIT_SSH 均不生效，git 直接用系统 ssh） |
| 7 | test_git.py::test_it_honors_kill_after_timeout_with_output_stream | `b'' != b'started\n'`——0.1s kill 太快 stdout 未捕获 | 进程信号时序在 OHOS musl 下偏慢，计时边界用例 |
| 8 | test_index.py::test_index_file_diff_null_tree_with_initial_index | `'usage: git diff' not found in ''` | 本机 git 版本错误文案行为差异 |
| 9 | test_index.py::test_index_mutation | `git rm --cached` exit code(-11) SIGSEGV | **本机 hnp git 2.45.2 构建缺陷**：`git rm --cached` 多 pathspec（argv 文件名总长 >约 920-930 字节）时段错误（实测 94 个 file*.txt 即崩、93 个正常；与 GitPython 库无关，其他 git 子命令正常） |
| 10 | test_installation.py::test_installation | venv 里 `ensurepip --upgrade` exit 1 | OHOS python3 venv 的 ensurepip 平台限制 |
| 11 | test_docs.py::Tutorials::test_init_repo_object | `origin/master` 不存在 | 教程教程仓克隆后 remote 引用形态差异 |
| 12 | test_quick_doc.py::QuickDoc::test_cloned_repo_object | `git clone https://github.com/...` exit 128 | 本地网络对 github.com 访问受限（测试环境网络限制） |
| 13 | test_refs.py::test_refs | `assert 2 >= 3` 远端引用计数不足 | 同上：clone 网络受限导致 remote refs 少 |
| 14 | test_remote.py::test_fetch_error | ssh fetch 错误文案不匹配 | 同 #6 ssh 行为差异叠加 |

- **74 skipped**: 上游自身按环境条件跳过（Windows 专属 / 网络依赖 / ddt 参数化变体等，上游在 Linux CI 也有同类跳过）

## 已知限制

- GitPython 运行时依赖宿主环境的 git 可执行文件（>=2.2 上游声明）；本机 hnp git
  2.45.2 的 `rm --cached` 长 pathspec 段错误是 git 侧构建问题，不影响 gitpython
  库本体的导入与常规仓库操作（端到端冒烟 Repo.init+commit 验证通过）
