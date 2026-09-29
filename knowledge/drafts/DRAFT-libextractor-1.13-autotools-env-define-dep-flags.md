# DRAFT-libextractor-1.13-autotools-env-define-dep-flags — Conan2 autotools：`tc.environment()` 之后追加的 `extra_cflags/extra_ldflags` 静默丢失

## 现象 (What happened)

libextractor 1.13（任务 13908，autotools，插件运行期由 libltdl `dlopen`）在
`ohc-run.py conan-verify` 的 **G2 conan create** 阶段连续失败：

```
checking for libltdl... --with-ltdl not specified
checking for ltdl.h... no
configure: error: libextractor requires libltdl (from GNU libtool), try installing libltdl-dev
```

排查中容易误判的三件事，全部被实测排除：

- 依赖**没声明**？—— 声明了：`requirements()` 有 `self.requires("libtool/2.5.4.1")`；
- 依赖**未发布**？—— 已发布：`conan install --build=never` 与包缓存（`p/libto6f1e021582737/p/include`）
  都能取到 `ltdl.h` 与 `libltdl.so`；
- 需要 `--with-ltdl` 指路？—— 不需要，configure 只读 `CPPFLAGS`/`LDFLAGS`（本包 pkg-config
  只用于 glib 系探测，不参与 ltdl）。

决定性证据在 `config.log`：**CPPFLAGS 只有 `-DNDEBUG`、LDFLAGS 为空**——依赖目录根本没进 configure。

## 根因 (Root cause)

conan 2.29.1 `conan/tools/gnu/autotoolstoolchain.py`：

```python
def environment(self):            # :277  ← 调用瞬间新建 Environment 并组装 CFLAGS/LDFLAGS
    ...                           #        extra_cflags 在 :236、extra_ldflags 在 :251 被读取，
                                  #        只有这一次
def generate(self, env=None, scope="build"):   # :329
    env = env or self.environment()            # :331  自带 env ⇒ 不再二次计算
```

libextractor 配方的写法是：

```python
tc = AutotoolsToolchain(self)
env = tc.environment()          # ① 快照在此形成
...
tc.extra_cflags.append("-I…")   # ② 晚于 ①，不会被合并
tc.extra_ldflags.append("-L…")  # ③ 同上
tc.generate(env=env)            # ④ 传回 ① 的 env ⇒ 也不会重算
```

即 **`environment()` 是即时快照**，而"先取 env、后 append extra_*、再把 env 传回 generate"这个
顺序使两处追加完全失效。OHOS 适配里这个顺序很常见——因为往往还要在同一个 env 里注入
MAKEINFO、`SHELL/CONFIG_SHELL` 路由、`LD_LIBRARY_PATH`（musl 忽略 DT_RUNPATH，插件 `.so`
的依赖只能靠它）。

## 单变量复现（同一 CONAN_HOME / 同一 profile，只删两行）

| 形态 | `config.log` | G2 结果 |
|---|---|---|
| 仅保留 `extra_cflags/extra_ldflags`（删 `env.define("CPPFLAGS"/"LDFLAGS")`） | `CPPFLAGS='-DNDEBUG'`、`LDFLAGS=''` | **FAIL**：`checking for ltdl.h... no` → `requires libltdl` |
| 交付态（`env.define("CPPFLAGS"/"LDFLAGS")` 显式导出） | `CPPFLAGS` 含 10 个依赖 `-I`、`LDFLAGS` 含 10 个 `-L` | **PASS**：探到 libltdl，`src/main` 7/7 + `src/plugins` **23/23** 全绿（09-22 当时读数为 21/21；现 HEAD 同一判据重跑＝7/7 + 23/23 = 30/30） |

复现命令（副本上做，不污染 worktree）：

```bash
cp -r archives/l/libextractor/1.13 ~/tmp/uc2/<标识>/abtest/1.13
# 删掉 conanfile.py 中 env.define("CPPFLAGS" / "LDFLAGS") 两行
conan create ~/tmp/uc2/<标识>/abtest/1.13 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
grep -nE "^CPPFLAGS=|^LDFLAGS=" <build_folder>/config.log
```

## 解法 (Fix)

二选一：

**A. 只注入 `-I/-L`（本包采用）**——在自拼的 env 里显式 define，并且目录统一从
`self.dependencies[*].cpp_info` 遍历取（勿硬编码）：

```python
env = tc.environment()
incs = self._dep_dirs("includedirs")
libs = self._dep_dirs("libdirs")
env.define("CPPFLAGS", " ".join(["-I{}".format(i) for i in incs]))
env.define("LDFLAGS",  " ".join(["-L{}".format(l) for l in libs]))
tc.generate(env=env)
```

**B. 仍用 `extra_cflags/extra_ldflags`**——则必须在调用 `tc.environment()`（或不带 env 的
`tc.generate()`）**之前**完成追加。

## 适用边界与反例 (Scope / caveats)

- 适用：所有「取过 `environment()` 或把自建 env 传给 `generate(env=)`」的 Conan 2.x
  autotools 配方；不适用于 `extra_*` 在快照之前设置好的常规配方（那类是正常生效的）。
- 与 `DRAFT-scrypt-1.3.2-autotoolsdeps-ac-search-libs`、
  `DRAFT-E2186-autotools-deps-missing-dep-flags` 的关系：**同症状、不同通道**。那两条讲
  "漏调 `AutotoolsDeps`"，修法是补上它（会连 `-l` 一起进 LIBS）；本条讲"自带 env 时
  `extra_*` 因取值时机失效"。**如果上游 `AC_SEARCH_LIBS`/`AC_CHECK_LIB` 必须有真 `-l`
  才能命中（例如候选库名与依赖产物名不一致：ncurses 只出 `libncursesw`），应当走 Deps 或
  显式 LIBS，而不是照抄本条只 define `-I/-L`。**
- 本法的代价：依赖目录由配方自己维护，升级/新增依赖后若漏同步会**静默**退回"搜
  `/usr/include`"，因此务必走 `self.dependencies` 遍历而非抄死路径。

## 本次交付中的位置

- 配方：`archives/l/libextractor/1.13/conanfile.py` `generate()` 内
  `env.define("CPPFLAGS"/"LDFLAGS")`（附注释说明为何不能只靠 `extra_cflags`）
- 验证凭据：`reports/conan-verify-report.md`（G0/G1/G2 PASS）、
  `reports/w3-local-ci.log`（`# TOTAL: 7 / PASS: 7` 与 `# TOTAL: 23 / PASS: 23`；PASS 名单 L1166-1172 与 L1317-1347）。**日志 sha256 不写死**——该日志每轮 `finish` 重写、字面值必然过期，**以 `.ci-result.json` 的 `log_sha256` 实物为准**（字面三元组只在 PR 正文披露）
