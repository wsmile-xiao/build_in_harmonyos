# DRAFT-vkeybd-0.1.18d — PF8 要求的软件级 commands.json 与 PF9 路径闸结构性互斥；及 make 变量"覆盖组成项而非覆盖被拼变量"

> 状态：草稿（待知识库主编审核，拟提升正式编号 Exxx）
> 来源：vkeybd 0.1.18d 适配（feat/vkeybd-0.1.18d，PR #13962，2026-09-30）
> 配对条目：`knowledge/drafts/DRAFT-vkeybd-0.1.18d-pf8-pf9-commands-json-vs-path-gate.kv`
>
> **差异化定位**（本轮先 grep 既有 drafts 的结果）：
> - E691（`DRAFT-E691-header-library-run-false-bindirs-not-in-conanrun-path.md`）讲的是
>   **header-library/static 包 `run=False` 导致 bindirs 被短路**，根因在 conan 源码的
>   `require.run` 分支。本条讲的是 **CLI/application 包 `run=True`、bindirs 明确非空，
>   仍不进 conanrun PATH**——同一表象、相反根因，两条需并存。
> - `DRAFT-postgresql-18.3-make-args-shell-quote.md` 讲 make args 的**引号被 shell 剥离**
>   （四层传递）。本条讲的是 make 变量赋值**根本没加引号导致词分割**，是"该加而没加"，
>   与 postgresql 的"加了也被吃掉"方向相反。
> - `DRAFT-hoedown-3.0.7-makefile-cflags-override.md` 讲 **Makefile 内赋值覆盖环境 CFLAGS**
>   （命令行 > Makefile > 环境），处方是命令行覆盖 CFLAGS 本身。本条讲的是**上游 Makefile
>   在 CFLAGS 内部自拼 define**，此时命令行覆盖 CFLAGS 会连带丢掉那些 define，处方是
>   反向的——覆盖被拼进去的组成项而非被拼出来的 CFLAGS。
> - `DRAFT-conan-get-url-filename.md` 讲带**查询串**的 URL 无法推断 filename。本条是
>   **codeload URL 无 `.tar.gz` 后缀**导致误判 zip 报 BadZipFile，同一处理但触发面不同。
> - PF8/PF9 互斥本身在现有草稿中**无对应条目**（tarlz #13424 / wavegain #13442 /
>   tardy 是实测先例，但未沉淀条目）。

## 一、PF8 与 PF9 结构性互斥：CLI 包的 commands.json 必被 PF9 误判

### 问题（error_signature）
```
PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
——CI 将报 No packages to build（490 例）:
archives/v/vkeybd/commands.json, archives/v/vkeybd/manifest.yaml
```

### 根因（root_cause）——两条门禁判据互斥，无法同时满足
- **PF8/R38 口径**：CLI 包（`package_type=application` 或 `bindirs` 非空）的
  `commands.json` **必须在软件级目录** `archives/<字母>/<包>/commands.json`
  （新格式 name/description/homepage/type=tool/versions{<版>:{ref,binary}}）。
- **PF9 判据**：`scripts/ohc/preflight.py:570` 是
  `bad = [f for f in arch if len(f.split("/")) < 5]`——要求每条变更路径至少 5 段
  即 `archives/<字母>/<包>/<版本>/<文件>`。
- 软件级 `commands.json` 与 `manifest.yaml` 只有 **4 段**，按 PF8 是必放的正确位置，
  按 PF9 必然命中。**这是判据层面的结构性冲突，不是本 PR 的疏漏。**

### 反例与先例核对（rec_priority: 1，限制条件明确）
- 已合入 main 的同形态条目（本轮 `git ls-tree origin/main` 实查）：
  `archives/t/tarlz/commands.json`（PR #13424）、`archives/w/wavegain/commands.json`
  （PR #13442），二者真实 CI 均绿。
- **不能挪进版本目录**：`commands.json` 塞进 `0.1.18d/` 能骗过 PF9（变成 5 段），
  但直接违反 PF8/R38——CI 的 L0k 用 AST 判 CLI 后报 `commands_json_r38`。这是
  tarlz/tardy 实测过的同形误报。
- **平台侧不是问题**：`/api/prs/overview` 的 `path_violations` 对本 PR 为 `[]`，
  平台自身路径闸已通过——只有本地 preflight 脚本误判。

### 处方（rec_approach: no-preflight-with-declared-device-evidence）
1. 保持 `commands.json` 在软件级（PF8/R38 正确位置），不动。
2. `python3 scripts/gitcode_pr.py create-pr ... --no-preflight`。
3. PR 正文设「preflight 说明」节，完整声明：真实 merge-base、逐条 finding、
   PF9 判据行号、与 PF8 的互斥论证、已合入先例、平台 `path_violations` 为空、
   设备 `CREATE_RC=0` 全绿证据。
4. **必须实拉 merge-base 复核**：`preflight.py <repo> $(git merge-base origin/main HEAD) HEAD`。
   两点 diff 会把主线几百个提交的新文件全算进来，噪声淹没真 finding。
5. 其余门禁须**逐条确认无 finding**（PF1-PF8 + PF9 分支名），才能主张"仅此一项误报"。

### 影响面与恢复条件
- 影响一切 CLI/tool 包的新增适配（本仓 2400+ 分支的包绝大多数是 CLI）。
- 恢复条件：PF9 的 `len(...) < 5` 改为「跳过软件级已知文件名白名单
  （commands.json / manifest.yaml / README.md）」或改为「变更集里存在任一
  5 段路径即视为合规」，冲突即消失。在此之前一律按本条走。

## 二、make 变量赋值不加引号 → 词分割 → make 收裸选项

### 问题
```
make: invalid option -- /
```
出现在 `make COPTFLAGS=-O2 -fPIC -I/a -I/b` 之后——make 收到的是裸的
`-fPIC`/`-I/a`/`-I/b`，当成自己的命令行选项解析。

### 根因
`ConanFile.run()` 经 `sh -c` 执行，make 变量赋值**必须整体作为单个 argv 传给 make**。
不加引号时外层 shell 先按空白词分割，赋值与其"值"被拆成多个 argv，make 在解析
自己选项时就撞上 `-I/...` 这类以 `-` 开头的 token。
与 postgresql 条目的方向相反：那里引号**加了也被外层 shell 剥掉**，这里**根本要加且加了就对**。

### 处方
```python
from shlex import quote as shell_quote

def q(name, value):
    return shell_quote("{0}={1}".format(name, value))

self.run("make -C {0} {1}".format(self.source_folder, " ".join(map(q, overrides))))
```
每一条 override 都过 `shlex.quote()`，多空格与 `-` 开头的值都不再被拆。

### 反例/限制
- 值不含空格与 shell 元字符时直传也能过，但**不要据此省略**——加引号无副作用，
  省略则把故障推迟到某个特定 `-I` 路径出现时才爆。
- 本条只解决"传给 make 的 argv 边界"；若 Makefile 内部又把该变量 `+=` 展开并
  二次引用，见第三条。

## 三、上游 Makefile 自拼 define 时，覆盖"被拼进去的组成项"而非 CFLAGS 本身

### 问题
vkeybd 的 Makefile 在 CFLAGS **内部**自行追加：
`-DVKB_TCLFILE="$(VKBLIB_DIR)/vkeybd.tcl"`、`-DVKBLIB_DIR=...`、`-DVKB_USE_ALSA`。
配方若按常规做法命令行覆盖 `CFLAGS=...`（含 OHOS target/sysroot 与 include 路径），
这三个 define 会**静默消失**——编译不报错，但 `-DVKB_USE_ALSA` 没了会让
`vkb.c` 走进未定义分支。

### 根因
命令行覆盖是**整变量替换**，不是合并。上游"自己往 CFLAGS 里拼东西"的写法，
等价于把 CFLAGS 定义成 `CFLAGS = <它拼好的整体>`；外部整赋值必然把那部分拼装逻辑顶掉。

### 处方
- **不覆盖 `CFLAGS`**；改覆盖它的**组成项**（本例是 `COPTFLAGS`，Makefile 里
  `CFLAGS = $(COPTFLAGS) ... $(CFLAGS)`），让上游的拼接逻辑继续执行。
- 先读 Makefile 确认它到底往哪个变量里拼——不同项目拼的变量名不同
  （COPTFLAGS / CPPFLAGS / MY_CFLAGS …）。判据是"**被拼进去的那个变量**"，
  不是"看起来该覆盖的那个变量"。
- 配套：把依赖 include 路径也并入同一个被覆盖的变量，避免上游只认自己那几个。

### 反例/限制
- 若上游 Makefile **不**往 CFLAGS 里拼任何东西，则直接覆盖 CFLAGS 才是对的
  （hoedown 条目的处方，属正常路径）。
- 两者的区别只能靠读 Makefile 判定，不能从"CFLAGS 有没有被覆盖"的结果反推。
- 自检手段：构建后 grep 二进制里本该由 define 决定的字符串/分支
  （本例是烤进去的 `VKB_TCLFILE` 路径），确证 define 真的生效。

## 四、codeload URL 无 `.tar.gz` 后缀 → get() 误判 zip → BadZipFile

### 问题
`conan.tools.files.get()` 对 codeload 形态
`https://codeload.github.com/<o>/<r>/tar.gz/refs/tags/<tag>` 报
`BadZipFile`——URL 里虽有 `tar.gz` 字样但**不在路径末尾**，扩展名推断失败，
回退成 zip。

### 处方
conandata.yml 用扁平 `sources:` + **显式 `filename:`**：
```yaml
sources:
  url: "https://codeload.github.com/tiwai/vkeybd/tar.gz/refs/tags/v0.1.18d"
  filename: "vkeybd-v0.1.18d.tar.gz"
  sha256: "df5dece0e18db3ac17222faa537e9b450d6ab0044792be194077d669d46d4b45"
```
同时**不要**用 `**conan_data["sources"]` 配按版本嵌套的 conandata——版本号会被
当成 `get()` 的关键字参数，报 `unexpected keyword '0.1.18d'`。

与 `DRAFT-conan-get-url-filename.md`（查询串形态）同一处理、触发面不同，
两条可复用同一处方。

## 五、附带记录（低于正式条目门槛，仅留证）

- **CLI 测试里 `command -v` 通过 ≠ 可执行**：vkeybd 缺失时脚本仍报 PASS，
  因为后续调用 exit=127 被宽松断言放过。断言要三层：
  `[ -x "$path" ]` + 显式拒绝 rc=127 + 拒绝空输出。
- **无头设备验证 X11/Tk GUI 二进制**：不要求开窗口，改为断言（a）编译期路径
  真的烤进二进制字符串（b）一次真实调用能动态解析全部共享库并走到自己的参数处理。
  headless 下退出码非零是预期，exit=127 或 `error while loading shared libraries` 才算失败。

## 验证证据（真实执行，非推断）

- 设备 3QC0124C11000071，clang 15.0.4 aarch64-unknown-linux-ohos，Conan 2.29.1，
  profile `ohos-aarch64`：
  ```
  clang ... -DVKB_USE_ALSA -c -o vkb.o vkb.c
  clang -L...tcl -L...tk -L...x11 -L...alsa -o vkeybd \
        vkb.o vkb_device.o oper_alsa.o -ltcl9tk9.0 -ltcl9.0 -lX11 -lasound -ldl -lm
  CREATE_RC=0
  ALL_VKEYBD_TESTS_PASSED
  ```
- preflight：`merge-base = f6e62fd828a7c4f63a7cee04923bc5b7ce752776`，
  diff 恰 9 个 vkeybd 文件 / 622 行新增；`FINDING_COUNT = 1`（仅 PF9 本条误报）。
- 先例核对：`git ls-tree origin/main archives/t/tarlz/` 与 `archives/w/wavegain/`
  均含软件级 `commands.json`。

## 验证日期与限制

- 验证日期：2026-09-30（配方构建与 preflight 均在该日设备/本机实跑）。
- 限制：PF8/PF9 互斥结论基于 `preflight.py` v12.20 的当前判据；
  若判据变更（见"恢复条件"）须重新核对。E691 对照结论基于 `run=False` 的
  conan 源码路径，未在本轮重跑。
