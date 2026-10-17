# plyara 2.2.8 适配笔记

## 一、目标与结论

| 项 | 值 |
|---|---|
| 上游 | https://github.com/plyara/plyara （tag `v2.2.8`） |
| 类型 | 纯 Python noarch 库 + CLI（`package_type = "python-require"`） |
| 依赖 | **零**运行时第三方依赖（`pyproject.toml [project]` 无 `dependencies`） |
| 内嵌 submodule | `third_party/ply` = github.com/plyara/ply @ `5c4dc94d4c6d059ec127ee1493c735963a5d2645`（PLY 4.x / 2022.10.27） |
| 源码 SHA256 | plyara `0d546061140fe11edcabae9cbb9ae417496a07288464c0bfd036892a1da096a1` |
| submodule SHA256 | ply `31bf86a459026e5abfa9ef4312d75922a6c69df52ca322238b670ca4f35892cd` |
| 环境 | HarmonyOS PC / aarch64 / Python 3.12.9 / Conan 2.29.1 / profile `ohos-aarch64` |
| 状态 | built |

## 二、依赖核验（W0）

```
$ bash ci/scripts/preflight_check.sh plyara/2.2.8
[INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。
[OK] 预检通过（无依赖需要检查）                          exit=0

$ conan download plyara/2.2.8 -r=ohpcd --only-recipe
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]   exit=1
$ conan download ply/1.0      -r=ohpcd --only-recipe
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]   exit=1
$ conan download pycodestyle/2.11.1 -r=ohpcd --only-recipe
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]   exit=1

# 远端健全性对照（证明上面的 exit=1 是"配方不存在"而非远端不可用）
$ conan list "zlib/*" -r=ohpcd   → Found 8 pkg/version recipes   exit=0
```

结论：plyara 无 conan 级依赖 → **无 R36 阻塞**。唯一外部代码来源是上游自有
submodule（随源码分发，非独立 conan 包），测试期可选依赖三个 linter 已从社区
PyPI 索引真实安装（pycodestyle 2.15.0 / pydocstyle 6.3.0 / pyflakes 4.0.0）。

## 三、构建/交付形态

纯 Python noarch，无 configure/make：

```bash
conan create archives/p/plyara/2.2.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

产物：

```
lib/python3.12/site-packages/plyara/{__init__,command_line,core,exceptions,utils}.py
lib/python3.12/site-packages/ply/{__init__,lex,yacc}.py     # 内嵌 PLY（submodule）
bin/plyara                                                  # R38 命令行入口
```

## 四、问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 步骤 `_create_dual_track` 报 `[Errno 1] Operation not permitted`（全部文件） | **HMDFS 不支持硬链接**（框架用 `shutil.copytree(copy_function=os.link)`） | 框架已有 `copy2` 兜底（自动降级），非阻塞 |
| 2 | 兜底 `copy2` 报 `[Errno 2] No such file or directory: .../src/ply` | **上游 GitHub tag 归档不含 git submodule 内容**，`src/ply` 成为悬空符号链接 | conanfile.py `source()` 按 `.gitmodules` 里 pin 死的 commit 单独 `get()` 并落位 `third_party/ply`（ableton-link 3.1.2 先例）；本地探索期同样手工落位后再跑测试 |
| 3 | `/tmp` 无法写入（`touch: Read-only file system`） | OHOS 平台特性 E002（且 `/tmp` 连读都是 `Permission denied`） | 临时目录统一用 `$TMPDIR` / `$HOME/tmp`；`tempfile` 在 OHOS 上自动回退到 `$TMPDIR` |
| 4 | 上游 `test_linters` 报 `ModuleNotFoundError: No module named 'pycodestyle'` | 上游 `[project.optional-dependencies].tests` 未安装 | 本机从社区索引安装三个 linter；配方 `build()` 中尽力装到 `build_folder/test-extras` 私有目录（R49：不写共享前缀、不污染 worker） |
| 5 | worktree `git status` 恒报 `archives/l/libXext`、`archives/l/libxext` 为 modified | **本机 HMDFS 大小写不敏感**，而仓库 HEAD 中这两个路径同时存在（真实不同文件），磁盘上只能存在一个 | 平台限制（E046 类），不阻塞；提交时**只做路径白名单 add，禁用 `git add -A`**，避免把该噪声带入 PR |

## 五、上游测试（真实执行，baseline `python -m unittest discover`）

```bash
cd plyara-src
PYTHONPATH=$PWD/src:<pip-global> python3 -m unittest discover -v
```

**实测结果：`Ran 107 tests in 913.568s` → `OK`（107 通过 / 0 失败 / 0 错误 / 0 跳过）**

| 模块 | 用例数 | 说明 |
|---|---|---|
| `tests/test_core.py` | 80 | 解析核心（TestRuleParser 24 / TestYaraRules 43 / TestImports 8 / TestStoreRawSections 4 / TestRuleParserKVMeta 1；含多线程解析） |
| `tests/test_issues.py` | 15 | GitHub issue 回归（issue 63/99/107/109/112/115/118/141×2/143/144/145/150/153/156） |
| `tests/test_utils.py` | 5 | `generate_hash` / `rebuild_yara_rule` / legacy 哈希 |
| `tests/test_command_line.py` | 3 | CLI 输出哈希与上游期望集合比对 |
| `tests/test_linters.py` | 3 | pycodestyle / pydocstyle / pyflakes 全绿 |
| `tests/test_third_party_repositories.py` | 1 | 真实 `git clone` 14 个公开 YARA 规则仓库并逐条解析（非空壳：本机实测 `git clone github.com` exit=0） |
| 合计 | **107** | 全部通过 |

日志：
- 全量：`$HOME/tmp/plyara-logs/upstream-tests-FULL.log`（详细用例名）+ `.time`（汇总/耗时）
- 首轮（环境失误复现）：`$HOME/tmp/plyara-logs/upstream-tests-v.log`
- linters 单跑：`$HOME/tmp/plyara-logs/upstream-test-linters.log`

## 六、OHOS 适配点

1. **交付形态适配（核心）**：上游把 PLY 作为 submodule 内嵌、用 `src/ply` 符号
   链接暴露给 `plyara.core`。GitHub 归档丢 submodule → 配方必须在 `source()`
   单独获取 PLY 并落位；`package()` 拷贝**真实内容**而非符号链接（HMDFS 下
   符号链接存续不可依赖，E046 类）。
2. **R38 命令行声明**：上游 `[project.scripts] plyara = plyara.command_line:main`
   → 交付物含可执行文件，软件级 `commands.json` 必需，并生成 `bin/plyara`
   （shebang + sys.path 注入 + 调用 main，docutils/awscli 先例）。
3. **只读文件系统契约**：内嵌 PLY 为 4.x（`yacc()` 已无 `write_tables` 参数），
   运行时不再写 `parsetab.py`/`parser.out` —— 这是交付到 OHOS 只读工作目录的
   前提，由鸿蒙专项测试 `test_ohos_plyara.py` 的 OHOS-3 断言（运行后目录内
   除输入文件外零残留）。
4. **只读临时目录契约**：OHOS `/tmp` 不可写；`test_ohos_plyara.py` OHOS-3/OHOS-4
   将 `cwd`/`TMPDIR` 固定到同一目录及 `/data/storage/el2/...` 应用沙箱后仍须
   产出逐字节一致结果。
5. **无源码补丁**：`src/plyara/*.py` 与 `src/ply/*.py` 中 `sys.platform` /
   `os.name` / `platform.*` 判断 **grep 零命中**，故不做任何 OHOS 条件分支；
   适配集中在交付形态与运行时契约（符合 R8：不引入空壳平台宏）。

## 七、test_package

| 文件 | 断言数 | 内容 |
|---|---|---|
| `test_plyara.py` | 6 组 | R34 消费者测试：包内导入 `plyara`+内嵌 `ply`、`parse_string` 的 meta/tags/strings/condition 解析、`store_raw_sections`/`meta_as_kv`/`import_effects` 三选项、`utils.generate_hash`/`rebuild_yara_rule`/`detect_imports` |
| `test_ohos_plyara.py` | 11（OHOS-1..5） | **鸿蒙专项**：平台身份 HarmonyOS/aarch64；内嵌 PLY 落位包内；只读 cwd+TMPDIR 下 CLI 输出一致且零生成物；TMPDIR 指向 `/data/storage/el2` 沙箱可用；`bin/plyara` 对上游官方 CLI 夹具的输出 sha256 命中上游期望基线 |

## 八、W4 独立审计与修复记录（2026-09-27）

独立上下文审计子任务对 11 个变更文件逐条比对 `.gitcode/code-style.md` 与
`.gitcode/review-memory.md`，结论 **fail（1×P1 + 1×P3）**，全部命中已修复：

| # | 严重度 | 问题 | 根因 | 修复 |
|---|--------|------|------|------|
| 6 | **P1** | `conandata.yml` 泄漏镜像域名 `gh-proxy.com`（R39 / preflight PF7 硬闸，两处 URL 首项） | **框架还原缺陷**：`ci/conan/build_and_test.sh` 的 "Mirror fallback: rewriting source URLs"（约 line 1145-1160）先执行并落盘，之后预下载段的备份（约 line 1178 `cp "$CONANDATA" "$PREDL_BACKUP"`）才备份 —— 备份到的是**已污染版本**，EXIT 时 `_restore_conandata()` 把污染版本原样写回。烟雾证据：`reports/w3-local-ci.log:96` 打印 `found 5 source URL(s)`（正常应为 2 条 + 注释 1 条 = 3 条）。可稳定复现：每次 `finish` / `conan-verify` / W3 之后 conandata 均被改写 | 人工还原为单 URL 官方源（本文件当前形态）；已在文件头加警示注释 |
| 7 | P3 | `conanfile.py` 方法顺序违反 `.gitcode/code-style.md §3`（`requirements` 在 `export_sources` 之前） | 首稿书写顺序 | 调整为 `export_sources → requirements → source → build → package → package_info` |

修复后重新验证：

```
# 最终配方（官方源单 URL + 方法顺序修正）的真实构建
$ conan create archives/p/plyara/2.2.8 -pr:h=...ohos-aarch64 -pr:b=...ohos-aarch64 --build=missing
plyara/2.2.8: Sources correctly downloaded from https://github.com/plyara/plyara/archive/refs/tags/v2.2.8.tar.gz
plyara/2.2.8: Sources correctly downloaded from https://github.com/plyara/ply/archive/5c4dc94d4c6d059ec127ee1493c735963a5d2645.tar.gz
plyara/2.2.8: upstream unittest: Ran 107 tests in 1088.476s
plyara/2.2.8: upstream unittest: OK
OK: plyara 2.2.8 consumer test passed
plyara 2.2.8 OHOS-specific test: PASS (11 assertions)          exit=0

# 官方 URL 网络路径独立复核
$ curl -sL -o official-recheck.tar.gz https://github.com/plyara/plyara/archive/refs/tags/v2.2.8.tar.gz
curl_exit=0  size=61566
0d546061140fe11edcabae9cbb9ae417496a07288464c0bfd036892a1da096a1  official-recheck.tar.gz

# 对【已提交内容】的闭环复跑（recipe revision 与提交版逐位一致）
$ conan create archives/p/plyara/2.2.8 -pr:h=...ohos-aarch64 -pr:b=...ohos-aarch64 --build=missing
plyara/2.2.8: Exported: plyara/2.2.8#7118cc3ef315926e76b158f7287bb398
plyara/2.2.8: upstream unittest: Ran 107 tests in 1457.015s
plyara/2.2.8: upstream unittest: OK
plyara/2.2.8: Package '6b129b068851896169fae42d399fa922d239ce8a' created
OK: plyara 2.2.8 consumer test passed
plyara 2.2.8 OHOS-specific test: PASS (11 assertions)          exit=0

# finish → W3 本地 CI（最终配方）
W3 本地 CI 模拟通过；.ci-result.json: exit_code=0, integrity_hash=3f5c8b73048e41a6,
log_sha256=0b25c83d19950d1d285e1131ab1b548d6b9508134f28af55e36879a8a00be0c5
```

> 说明：`.ci-result.json` 由 `finish` 写入（未手改）。其 `integrity_hash`
> 只覆盖 `timestamp:software:version:exit_code`，不覆盖配方内容；W3 构建期
> 框架会将 conandata 临时改写为镜像优先（与 CI 完全同路径），故 W3 的
> 通过结果与"官方源单 URL 提交形态"在 CI 上等价（CI 同样会自行注入镜像）。

**第二轮复审（独立子任务）：verdict = pass**（0×P0/P1/P2，仅 2 个零风险 P3 观察项）。
复审独立取证：重新下载官方归档复算两个 sha256 与 conandata 完全一致；直接调用
`preflight.check_source_urls` 返回 `[]`（PF7 零命中，且确认文件头注释中的镜像
字面量不进入 PF7 的 URL 提取路径）；独立重跑两个 test_package → exit=0 / 11 断言
PASS；`git diff --name-status origin/main...HEAD` 恰 11 文件全为 `A`；
逐模块 `grep -c "def test"` 合计 107 与文档一致。审计结果归档于
`reports/audit-result.json`（verdict=pass）。

## 九、本地环境缺陷（非本包问题，供框架参考）

1. **本机 Python 裸名 PATH exec 全面失败**：`subprocess.run(["git"|"ls"|"sh"|"cat"|
   "python3"|"conan"|"true", ...])` 全部 `FileNotFoundError: [Errno 2]`，而绝对路径
   均可执行。影响 `scripts/ohc/preflight.py` PF0 环境闸（fail-closed，用裸名
   `["git", ...]`）与 `ci/conan/build_and_test.sh` 预下载段
   （`[fail] [Errno 2] No such file or directory: 'curl'`）。本包配方不受影响
   （`build()` / `test_package` 全部使用绝对路径解释器）。
2. **PF8 与 PF9 互斥**：PF8 要求 CLI 包在软件级提供 `archives/<字母>/<包>/commands.json`
   （R38），PF9 又要求所有 `archives/` 变更路径 ≥5 段 → 软件级 `commands.json` /
   `README.md` / `manifest.yaml` 被判"缺版本目录层"。main 现状：软件级 ≤4 段
   `commands.json` 3048 个 vs 版本级 15 个（dbview/dwz/liblqr/jaaa/awscli/appdirs
   均为软件级）→ 新 CLI 包在该闸下不可满足。

---
---

**编译结束**: 2026-09-27 21:39
**最终状态**: built
