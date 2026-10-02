# keyd-application-mapper 2.6.0 适配笔记

## 编译环境

- 构建系统: 上游为单 `Makefile`（GNU make）；本产物本身无编译步骤，仅 `cp`（`Makefile:37`）
- 编译日期: 2026-09-19
- 目标平台: OHOS / HarmonyOS PC aarch64（`os=OHOS, os.version=6.0, arch=armv8, clang 15, libc++, cppstd 17, Release`）
- 编译器: clang 15.0.4（本包构建不调用编译器；仅在核验同树守护进程/测试驱动时使用）
- 状态: built

## 源码与版本核验

```
$ git ls-remote --tags https://github.com/rvaiya/keyd.git v2.6.0
fatal: unable to access '...': Failed to connect to github.com port 443 after 65203 ms   rc=128
    # 直连 git 协议不通；改用 GitHub API 核验 tag
$ curl -sSL https://api.github.com/repos/rvaiya/keyd/git/ref/tags/v2.6.0
    → refs/tags/v2.6.0 = 7c0aecb8bfd34dc8642bf4eefd2e59c89e61cec3                        rc=0
$ sha256sum ~/tmp/builds/keyd-application-mapper-2.6.0.tar.gz
697089681915b89d9e98caf93d870dbd4abce768af8a647d54650a6a90744e26                          rc=0
    # 同一 URL 二次下载 sha256 相同（确定性验证通过）
$ grep -n "^VERSION=" Makefile        → 2:VERSION=2.6.0                                   rc=0
```

## 编译步骤

上游 `Makefile:35-38` 的 `all:` 同时服务两个产物：

```
mkdir -p bin
cp scripts/keyd-application-mapper bin/                      # ← 本包的产物步骤（Makefile:37）
$(CC) ... src/*.c src/vkbd/uinput.c -lpthread -o bin/keyd    # ← 同树 keyd 守护进程（另一包）
```

本包只做第一条（`build()` 内用 `shutil.copyfile` 等价实现），并在 `build()` 里用**声明的解释器**
跑一次 `keyd-application-mapper -h` 作为入口自检；`package()` 安装 `bin/keyd-application-mapper`
与上游预生成的 `data/keyd-application-mapper.1.gz`。

本地 staging 实测（`reports/` 内 `build-and-staging.log`）：

```
$ patch -p1 < patches/0001-scripts-keyd-application-mapper.patch
patching scripts/keyd-application-mapper                                                 rc=0
$ head -1 scripts/keyd-application-mapper      → #!/usr/bin/env python3                 rc=0
$ mkdir -p bin && cp scripts/keyd-application-mapper bin/                                rc=0
$ cp bin/keyd-application-mapper $TEST_PREFIX/bin/ && chmod 755 ...                      rc=0
$ cp data/keyd-application-mapper.1.gz $TEST_PREFIX/share/man/man1/ && chmod 644 ...     rc=0
$ HOME=$(mktemp -d) $TEST_PREFIX/bin/keyd-application-mapper -h   → usage 输出           rc=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 制品仓无本项目配方（0 命中） | 首次适配 | 按同树拆包先例（`kea-shell/3.0.3` 只 require 第三方依赖、不 require `kea/3.0.3`）只打包本命令 |
| 2 | 上游 shebang 为 `#!/usr/bin/python3`，OHOS 无此路径（`ls /usr/bin/python3` → No such file） | 上游把解释器路径写死为构建机约定 | 补丁 `0001-scripts-keyd-application-mapper.patch` 改为 `#!/usr/bin/env python3`；解释器由 `python/3.12.9` 依赖提供（Conan run 环境把其 `bin/` 前置进 PATH） |
| 3 | 同树 `make all` 在 OHOS 首个错误：`ld.lld: error: unable to find library -linotify`（rc=2） | `Makefile:26-33` 用 `uname -s == Linux` 判定平台；OHOS 报告 `HarmonyOS` → 走非 Linux 分支 `LDFLAGS+=-linotify`，而 OHOS sysroot 无 libinotify | **本包不构建该产物**（守护进程属 keyd 包）。核验结论：`make platform=Linux` 可正常链接出 `bin/keyd`（rc=0），说明 C 源码本身可移植，问题只在 Makefile 的平台分支 |
| 4 | 上游 `t/run.sh` 在 OHOS 失败（rc=255） | ① Toybox 无 `whoami`/`id`，脚本第 9 行 root 判定语法错误；② 非 root 且无 sudo，`/dev/input`、`/dev/uinput` 权限拒绝；③ run.sh 未覆盖 `platform`，make 仍加 `-linotify` | 上游主入口在本环境**不可运行**（逐项技术原因见 `reports/upstream-test-runsh.log`）。改用同树可离线运行的 `make test-io` 实测：**94/94 PASSED** |
| 5 | OHOS Toybox 无 `install` 命令（`command -v install` rc=1） | 上游 `Makefile:77/82` 使用 coreutils `install -m755/-m644` | 等价替换为 `cp` + `chmod`（Conan `copy()` 天然如此） |
| 6 | KDE / X11 后端在本制品仓不可完整 | `dbus-python`、`python-xlib` 均未发布到 ohpcd（`conan download` rc=1） | 二者在脚本内都是**延迟 import**（`KDE.__init__` / `XMonitor.init`），`get_monitor()` 依次 try/except 五个后端并降级；因此不声明依赖，也不属本包强制缺口 |

## 源码修改

- `0001-scripts-keyd-application-mapper.patch`：仅第 1 行解释器行
  `#!/usr/bin/python3` → `#!/usr/bin/env python3`（`patch -p1 --dry-run` rc=0；逐字节比对差异仅此一行）

未修改任何其它上游文件（无生成文件改动）。

## 依赖版本

| 依赖 | 版本 | 类型 | 核验 |
|------|------|------|------|
| python | 3.12.9（rrev `d8eda770878152bea40b42db9f7024cd`） | 运行时强制 | `conan download "python/3.12.9:*" -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"` → rc=0（38.2MB） |
| libffi / openssl / zlib / ncurses / readline / bzip2 / xz / sqlite3 / gdbm / proxy-libintl | 3.5.2 / 1.1.1w / 1.3.1.1 / 6.6 / 8.3 / 1.0.8 / 5.6.2 / 3.49.1 / 1.24 / 0.5 | python 传递 | 逐个 `conan download` 10/10 rc=0 |
| dbus-python / python-xlib | 未发布 | 可选后端 | `conan list` 0 命中、`conan download` rc=1 → 非必需（延迟 import） |
| keyd（守护进程） | 2.6.0（同 tarball） | 运行期对端 | 制品仓无 `keyd*/*` 配方（rc=1）；按同树拆包先例由 keyd 包负责 |

## 验证结果

```bash
# 本包构建 + staging
$ patch -p1 < patches/0001-...patch && mkdir -p bin && cp scripts/keyd-application-mapper bin/      # rc=0
$ $TEST_PREFIX/bin/keyd-application-mapper -h                                                       # rc=0
$ HOME=<空> $TEST_PREFIX/bin/keyd-application-mapper
ERROR: could not find app.conf, make sure it is in ~/.config/keyd/app.conf                          # rc=0（上游 die() 实现为 exit(0)）
$ HOME=<有 app.conf> $TEST_PREFIX/bin/keyd-application-mapper   # 无桌面环境
Could not detect app environment :(.                                                                # rc=255

# 上游测试（同树，OHOS aarch64 实测）
$ make test-io        → t/*.t 94 个用例：94/94 PASSED, 0 FAILED, 0 SKIPPED                          # rc=0
$ sh t/run.sh         → 未通过（rc=255，原因见上表 #4）
$ make test           → 未通过（rc=2，等价于再跑 run.sh）
$ grep -rn 'application-mapper\|app.conf' t/  → 无命中（rc=1）  ⇒ 上游对本命令零覆盖
```

## 注意事项

- 本命令**必须**与 keyd 守护进程同机运行（`/var/run/keyd.socket`，调用方需在 `keyd` 组），否则
  `keyd bind reset` 失败且窗口检测在本机无桌面环境时直接退出；不可脱离守护进程单独验收功能。
- 上游 `die()` 以 `exit(0)` 退出：`could not find app.conf` 这类错误路径返回码为 0，脚本判定不可依赖退出码。
- 脚本在 `import` 期读取 `HOME`（`CONFIG_PATH = os.getenv('HOME') + '/.config/keyd/app.conf'`），
  无 `HOME` 时会 `TypeError`；CI/构建环境调用该命令时必须设置 `HOME`。
- `/tmp` 只读（SKILL E002）：脚本内 KDE 后端会写 `/tmp/keyd-kwin-<uid>.js`，该后端在 OHOS 上不可用时不会走到这里；
  本地构建/测试的临时文件一律使用 `$TMPDIR`。
---

## 本地门禁状态（2026-09-19，未 commit，按要求停在提交前）

| 门禁 | 命令 | 结果 |
|------|------|------|
| init-build | `ohc-run.py init-build keyd-application-mapper 2.6.0 --url=<官方 url>` | rc=0 |
| 真实 conan create | `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同>` | **rc=0**；test_package 16/16 |
| conan-verify | `ohc-run.py conan-verify keyd-application-mapper 2.6.0` | **rc=0，Verdict PASS**（G1/G2/G3/G4/L2/L4/L5） |
| finish built | `ohc-run.py finish keyd-application-mapper 2.6.0 built` | **rc=0**；Step 10/10「submit 就绪」 |
| W3 本地 CI 模拟 | finish Step 5/10 → `ci/conan/build_and_test.sh keyd-application-mapper/2.6.0` | **通过**；`.ci-result.json`（exit_code=0，含 integrity_hash + log_sha256） |
| JC 杂项检查 | `JUNK_PR_DIFF=<本包 PR 清单> bash ci/scripts/junk_check.sh <worktree>` | **pass**（prdiff 模式，11 文件 / 单软件合规） |
| PR 文件原子性 | `git add --dry-run archives/k/keyd-application-mapper` | 恰好 11 个文件，全部属本软件本版本 |

## 待办与已知限制

1. **W4/pre-PR 独立审计本阶段无法执行**：`scripts/pre_pr_audit.py generate` 通过
   `git diff --name-only origin/main...HEAD` 取变更集，未 commit 时直接返回「没有变更文件，无需审计」。
   本阶段按要求在 commit 前停止，故 W4 需在提交动作之后运行（`submit` 内置 W4 前置门禁）。
2. **`conandata.yml` 被 W3 镜像改写后不会自动还原**：`ci/conan/build_and_test.sh:1029` 会把 `url:` 单值
   改写成 `[gh-proxy.com/…, github.com/…]` 列表（仅当走预下载分支时由 `trap _restore_conandata` 还原，
   见 `:1181-1188`）。本包 W3 未走预下载分支，改写留在工作区；已用备份 `conandata.yml.orig`
   还原为**单值官方 URL**（R39/PF7 要求）。**提交前务必确认 `conandata.yml` 的 `url` 是单值官方 HTTPS URL。**
3. **G0 干净构建验证（finish Step 3/10）不适配本包**：G0 以 autotools `./configure` 为驱动，
   仅对「无 `./configure` 且存在 `CMakeLists.txt`/`meson.build`」的工程显式跳过
   （`scripts/ohc/clean_verify.py:129-136`）；keyd 只有 `Makefile` → `./configure` exit 127。
   该步骤在 SKILL 中声明为非阻塞，等价验证由 conan-verify G2（干净 conan create）与 W3 覆盖，二者均通过。
4. **`reports/` 被 `.gitignore` 忽略（第 96 行）**：本目录的 `test-report.md` 与全部上游测试日志
   属**本地证据**，不进入 PR（与近期合并包一致）；上游测试结论由 `test_package/MANIFEST.yml`
   与 PR 正文对外呈现。
5. **HMDFS 大小写冲突噪音**：工作区里 `archives/l/libXext/{README.md,manifest.yaml}` 恒为 modified
   （git 内同时存在 `libXext` 与 `libxext` 路径，HMDFS 大小写不敏感 → 检出互相覆盖），
   该现象存在于全部 worktree，非本次改动。**提交时必须用路径限定**
   `git add archives/k/keyd-application-mapper`，不要用 `git add archives/`。
6. **知识图谱建议**：可为本包沉淀草稿（「上游 Makefile 用 `uname -s` 判定平台 → OHOS 报 HarmonyOS 走非 Linux 分支加 `-linotify`」、
   「W3 镜像改写未还原」）；本阶段未创建草稿。
## 提交前只读审计发现（2026-09-19）

### 发现 1（真实缺陷，已修复并全链重验）：requires 版本被写成格式化占位符

- 现象：`scripts/ohc/preflight.py` 的 PF4 依赖闸报
  `requires 'python/{}' 版本不在制品仓（在仓版本: 3.12.9）`。
  根因：配方原先写 `self.requires("python/{}".format(PYTHON_VERSION))`，PF4 的
  `_REQ_CALL` 正则把 `requires("...")` 的参数按**字面 ref** 解析，得到版本 `{}`。
- 修复：改为字面量 `self.requires("python/3.12.9")`，并删除 `PYTHON_VERSION` 常量；
  解释器路径改为从依赖自身取主版本（`py.ref.version.major`），保持单一事实源。
- 修复过程中出现并解决的次生错误（真实报错→根因→修复）：
  `AttributeError: 'Version' object has no attribute 'split'`
  （`py.ref.version` 是 conan `Version` 对象而非 `str`；改用 `.major`）。
- 重验：`conan create` rc=0（test_package 16/16）→ `conan-verify` rc=0（Verdict PASS）
  → `finish built` rc=0（W3 通过、`.ci-result.json` 重写、submit 就绪）→ JC prdiff pass。
  日志：`.ci_logs/step14-recreate-after-fix.log`、`step15-conan-verify-after-fix.log`、
  `step16-finish-after-fix.log`。

### 发现 2（框架判定与规范冲突，未修改框架，需上层决策）：PF9 会把软件级文件判为"缺版本目录层"

- 现象：PF9 报 `变更路径缺版本目录层 …: archives/k/keyd-application-mapper/README.md,
  commands.json, manifest.yaml`（判据 `len(f.split("/")) < 5`）。
- 冲突证据：这 3 个文件是 **ARCHIVE-SPEC §2.1 强制**的软件级文件
  （`commands.json` 更是 CI L0k 对 `package_type="application"` 包的硬要求，读取路径即
  `archives/<字母>/<包>/commands.json`，见 `ci/conan/build_and_test.sh:684-712`）；
  且当日合并进 main 的包同样携带这三个 depth-4 文件（`git show --name-only d12cecbe28`
  = weighttp 0.5，另有 tau/jpegoptim/libmegapixels 等），origin/main 中已有 4146 个软件级
  `README.md`、3696 个软件级 `manifest.yaml`。PF9 规则自 2026-09-03（`17f38c6e19`）引入后一直如此。
- 处置：**不删除**这 3 个文件（删掉将直接违反 ARCHIVE-SPEC 并触发 L0k 失败）；本阶段不修改框架
  （框架修复须按独立流程单独提 PR）。提 PR 时若 PF9 触发，需按框架例外处理
  （`--no-preflight` 或框架层修正 PF9 对 software 级文件的判定）。

### 发现 3（工具行为，已在提交前处置）：W3 反复改写 conandata.yml

- `finish` 的 W3（`ci/conan/build_and_test.sh`）每次都会把 `url:` 单值改写成
  `[gh-proxy.com/…, github.com/…]` 列表且不还原；本次审计已再次还原为单值官方 URL
  （R39/PF7）。**每次跑 finish/W3 之后都必须复核并还原 `conandata.yml`。**
### 发现 4（真实缺陷，已修复并全链重验）：test_package/MANIFEST.yml 不是合法 YAML

- 现象：提交前只读审计中 `yaml.safe_load` 解析失败 ——
  `ScannerError: mapping values are not allowed here`（line 37, column 24）；
  `file -b` 亦将文件判为 `data`（同仓同类文件均为 `UTF-8 text`，是同一问题的旁证）。
- 根因：第 37 行 `- file: Makefile test: 目标` 是**未加引号的纯量里含 `: `**，
  YAML 会把第二个 `: ` 当作嵌套映射。
- 修复：改为 `- file: "Makefile test: 目标"`（仅加引号，语义不变；其余字段逐项复验一致）。
- 为何此前未被 CI 发现：`ci/conan/build_and_test.sh:373-375` 的 **L0e 只校验该文件存在**
  （`[ ! -f "$TEST_PKG_DIR/MANIFEST.yml" ]`），不解析内容，故 W3 通过。
- 重验：`yaml.safe_load` 解析通过（18 个顶层键、upstream_tests 3 条、计数字段 94/94/0/0/16 一致）；
  `file` 判定回到 `UTF-8 text`；随后对**最终字节**重跑 `conan create`（rc=0，test_package 16/16）
  与 `finish built`（rc=0，G1/G2/G3 PASS、W3 通过、submit 就绪），并复算 `.ci-result.json` 双哈希 MATCH。

### 提交前审计中的其它确认项

- conan 缓存中当前列出的 recipe revision 由 W3 的 create 导出（其 `conandata.yml` 已被 W3 改写为
  镜像列表）。`conanfile.py` 与冻结字节**逐字节一致**（e94b06de…），`conandata.yml` 差异**仅为 url 写法**
  （官方单值 ↔ `[gh-proxy.com/…, github.com/…]`，sha256 与包 ID 6b129b06… 均相同）；
  冻结字节（官方单值）由 step14 的 create 实测通过（日志第 82 行：
  `Source https://github.com/rvaiya/keyd/archive/refs/tags/v2.6.0.tar.gz retrieved from local download cache`）。
- W2（finish Step 9/10）在"未提交"状态下无对象（输出「无变更文件」），已用 prdiff 模式等效复现（pass）。
- `reports/`、`test_package/build-release/`、`patches/.patch-backup-*/`、`conandata.yml.{orig,ghfast-bak}`、
  `ci-metadata.json`、`.build-closed` 等均被 `.gitignore` 覆盖，不会进入 PR（`git add --dry-run` 恰为 11 个文件）。
---

**编译结束**: 2026-09-20 12:48
**最终状态**: built

---

## CI 失败修复（2026-09-27）：test_package 使用依赖 python 解释器

- 现象：PR #11199 的 CI `conan-build-test` 失败（build #59733），`test()` method line 29 报
  `ConanException: Error 127 while executing`，`L1_RESULT=fail: conan create failed`。
  包本体构建、`package()`、打包全部成功，失败点在其后的 `test_package` 执行阶段。
- 原始报错（CI 日志原文）：
  ```
  (test package): RUN: "/data/service/hnp/bin/python3" ".../test_package/test_keyd_application_mapper.py"
  Error loading shared library libpython3.12.so.1.0: (needed by /data/service/hnp/bin/python3)
  Error relocating /data/service/hnp/bin/python3: Py_BytesMain: symbol not found
  ERROR: keyd-application-mapper/2.6.0 (test package): Error in test() method, line 29
      self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
      ConanException: Error 127 while executing
  ```
- 根因：`test_package/conanfile.py` 的 `test()` 用 `sys.executable`，即**运行 Conan 的解释器本身**
  （CI worker 上是 `/data/service/hnp/bin/python3`）。该解释器在干净 CI worker 上无法加载
  `libpython3.12.so.1.0`，于是测试脚本尚未启动即 exit 127。与 `b34c764725` 修复的 `build()` 属
  同一类问题（**依赖包提供的解释器 ≠ 运行 Conan 的解释器**），当时只改了 `build()`，`test_package` 被遗漏。
  本地长期通过的原因：本机 `sys.executable` 恰好是可用的解释器（依赖的 libpython 在外层 PATH/LD_LIBRARY_PATH 上）。
- 修复：`test()` 改用已声明依赖 `python/3.12.9` 提供的解释器
  `self.dependencies["python"].package_folder/bin/python3`（新增 `_python_executable()` helper），
  取法与主 recipe `build()` 一致；执行环境仍为 `env="conanrun"`（其 `LD_LIBRARY_PATH` 已含依赖 `lib/`）。
  不再引用 `sys.executable`。
- R33 依据：解释器/工具必须来自 Conan 依赖（`self.dependencies[...]`），不得依赖宿主环境隐含值。
- 本地重验（OHOS aarch64，`conan 2.29.1`）：
  - `python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify keyd-application-mapper 2.6.0` → **rc=0，Verdict PASS**（G1/G2/G3/G4/L2/L4/L5）；
  - G2 内 `conan create` 的 `test()` 实跑证据（`reports/conan-create.log`）：
    `RUN: "/storage/Users/.../.conan2/p/pytho3696188d16c3a/p/bin/python3" ".../test_keyd_application_mapper.py"`
    → `checks: 16, failures: 0`。

---

## CI 失败修复二（2026-09-29）：移除 test() 的 can_run() 提前返回（L1e 假测试误判）

- 现象：本地复跑 CI 门禁 `CI_PACKAGES=archives/k/keyd-application-mapper/2.6.0 zsh ci/conan/build_and_test.sh`，
  在 `L1e: Destructive negative test (R34)` 步骤失败：
  ```
  [sabotage] bin/ moved away
  [fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
  [fail] L1e: test does not depend on keyd-application-mapper — must call its API or execute its binary
  L1_RESULT=fail: negative test: test does not depend on package
  ```
- 根因：`test_package/conanfile.py` 的 `test()` 首行是 `if not can_run(self): return`。L1e 反向验证用
  「仅 host profile」重新执行 `conan test <test_package> keyd-application-mapper/2.6.0 -pr ci/conan/profiles/ohos-aarch64`，
  此时 build profile 取构建机默认 profile（x86_64 Linux），与 host(OHOS/armv8) 不同 →
  `cross_building()` 为真 → `can_run()` 为假 → `test()` 立即 return，**一条断言都没执行**，退出码 0；
  门禁据此判定「产物移走后测试仍通过 = 假测试」。
- 实测证据（本地逐字复现）：
  - `mv <pkg>/bin …` 后执行 `conan test … -pr ci/conan/profiles/ohos-aarch64` → `REAL_NEG_EXIT=0`，
    日志在 `Running test()` 之后**无任何输出**（消费者脚本未启动），与 `can_run()` 提前 return 的行为完全一致；
  - `inspect.getsource(can_run)`：`can_run = not cross_building(...)`，`cross_building` 比较 build/host 的 os 与 arch。
- 修复：删除 `can_run()` 提前返回，`test()` 无条件执行消费者脚本。目标解释器仍由声明的 `python/3.12.9`
  依赖提供：OHOS 主机（CI worker）上原生执行，x86_64 构建机上经 binfmt/qemu 透明执行
  （与 `build()` 中同解释器的入口自检一致）。这样 R34 反向验证才成立：产物移走后
  `shutil.which("keyd-application-mapper")` 取不到命令 → 脚本 FATAL 退出 1 → `conan test` 非 0 → 判定为真测试。
- 本地重验（2026-09-29，`zsh ci/conan/build_and_test.sh`，CI_PACKAGES=archives/k/keyd-application-mapper/2.6.0）：
  ```
  [ok] L0: All quality gate checks passed
  checks: 16, failures: 0
  [ok] keyd-application-mapper/2.6.0 — conan create passed
  [ok] L1e: Negative test confirmed — test genuinely depends on keyd-application-mapper
  [ok] L2: keyd-application-mapper --help OK
  L0_RESULT=pass / L1_RESULT=pass / L2_RESULT=pass / L4_RESULT=pass / L5_RESULT=pass
  Build Summary: Total 1, Success 1, Failed 0；Pass rate: 100.0% (1/1)；退出码 0
  ```
- 与上一节修复的关系：两者互不替代——上一节解决「干净 worker 上解释器不可用（exit 127）」，
  本节解决「L1e 反向验证被跨构建判定短路（假测试误判）」。
