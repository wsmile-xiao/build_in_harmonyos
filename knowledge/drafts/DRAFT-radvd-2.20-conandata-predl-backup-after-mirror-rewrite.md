# 本地 W3 的 conandata.yml「先注入镜像列表、后做预下载备份」顺序缺陷 —— 每次跑完必留脏提交态

> 草稿（DRAFT）。与同目录 `DRAFT-radvd-2.20-conandata-predl-backup-after-mirror-rewrite.kv` 成对，随同一原子 PR 提交。
> 触发实证：radvd/2.20（HarmonyOS PC B 机，分支 `feat/radvd-2.20`，HEAD `2130d7ad8251e47ecbaeddb5c2e766f92f28979b`），2026-09-25。
> 关联：E549（单值 url 才拿得到镜像兜底）、E415（同症状的既有已 promote 条目）、E017（镜像注入总目）、DRAFT-E323（conan_verify.py 侧另一枚独立缺陷）、DRAFT-8543 / DRAFT-libnbd-1.9.6（同族但不同签名）。
> 影响面：**所有走本地 W3 的源码包**，与 radvd 无关；radvd 只是把这条链子完整走通并留下的第一枚可复核实证。

## 现象

在 worktree 里跑一次本地 W3（`python3 scripts/ohc-run.py finish <pkg> <ver> built`，其 Step 5/10 会调 `ci/conan/build_and_test.sh`），日志里会出现

```text
[step] Mirror fallback: rewriting source URLs in conandata.yml...
        [ok] Source URLs rewritten with mirror fallback
[step] Pre-download: extracting source URLs from conandata.yml...
...
[step] Pre-download: conandata.yml 已还原为官方 URL          # trap 自己宣布已还原
```

于是收工前 `git status` 看着「已经还原了」，但实际 `archives/<l>/<pkg>/<ver>/conandata.yml` 的提交形态变成

```yaml
sources:
  "2.20":
    url:
      - "https://gh-proxy.com/https://github.com/radvd-project/radvd/releases/download/v2.20/radvd-2.20.tar.gz"
      - "https://github.com/radvd-project/radvd/releases/download/v2.20/radvd-2.20.tar.gz"
    sha256: "af37c5a81d59f3bdc00d83056606ffa1810d4550beed6caa4f81181246494220"
```

即**第 3 行 `url:` 被拆成列表、第 4 行躺着 `gh-proxy.com`**。这一枚文件若随 `git add archives/<l>/<pkg>`（或 pipeline `run` 第 [4/8] 步的按目录暂存）进提交，就是把镜像域名写进 PR：PF7 源 URL 闸与 R39 官方源约束都把它列黑名单，先例是 gulkan PR #7121 被 W4 判 P0 打回。

同一位置的更凶形态是 `file://` —— 预下载段（L1293）会把 url 换成 `file://<worktree 绝对路径>/.build-cache/predl_cache/<hash8>_<name>`，远端 CI 必然 `source()` FileNotFoundError（libnbd 1.9.6 的 R02 返工即此）。那种形态**恰好会被下面的 trap 撤销**，所以 trap 看起来是好用的；真正漏网的是镜像列表那一层。

## 根因（行号在该 HEAD 上逐条 `grep -n` 复核，文件共 1824 行）

`ci/conan/build_and_test.sh` 里这件事分两段，**第二段的备份点晚于第一段的改写点**：

| 行 | 代码 | 作用 |
|---|---|---|
| L1019 | `# ── Mirror fallback (通用镜像映射) ──` | 第一段起点 |
| L1027 | `if grep -qE 'url:.*https://(github\.com\|...)/' "$CONANDATA"` | 判定入口：**要求 `url:` 与 `https://` 同行**（正是 E549 要求合规配方写成的单值形态） |
| L1029 | `cp "$CONANDATA" "${CONANDATA}.orig"` | 存下**全流程唯一一份改写前的干净快照** |
| L1032–L1157 | `python3 - "$CONANDATA" <<'PYEOF' … PYEOF` | 内嵌改写块（heredoc 体即此范围） |
| L1050–L1054 | `if re.match(r'^https?://github\.com/', url): return ['https://gh-proxy.com/' + url, url]` | GitHub 分支的镜像列表来源 |
| L1141 | `def replace_url(match)` | 把单值 url 展开成 `url:` + `- <镜像>` 列表 |
| L1153 | `pattern = r'^([ \t]*)url:[ \t]*(["\'])(https?://[^\s"\']+)\2[ \t]*$'` | 匹配式 |
| **L1154** | `content = re.sub(pattern, replace_url, content, flags=re.MULTILINE)` | **改写发生在这里** |
| L1156–L1157 | `with open(path, 'w') as f: f.write(content)` | **回写磁盘** |
| L1160 | `echo "[ok] Source URLs rewritten with mirror fallback"` | |
| L1165 | `# ── Pre-download source archives with retry ──` | 第二段起点 |
| L1176–L1178 | 注释「脚本退出时恢复官方 URL —— 防止 file:// 残留被提交（gulkan PR #7121 被 W4 判 P0 打回…）」 | 作者的本意 |
| **L1179** | `PREDL_BACKUP="${PREDL_DIR}/conandata.yml.predl-orig"` | **备份点，比 L1154 晚 25 行** |
| **L1180** | `cp "$CONANDATA" "$PREDL_BACKUP"` | 此刻 `$CONANDATA` **已是镜像列表形态** |
| L1181–L1187 | `_restore_conandata()`（`cp "$PREDL_BACKUP" "$CONANDATA"`） | 还原函数 |
| L1188 | `trap _restore_conandata EXIT` | 退出时执行 |
| L1293 | `content = content.replace(url, f'file://{local_path}')` | 预下载命中后的 file:// 替换 |

于是：**trap 撤销的是 L1293，而 L1179 的快照里根本没有「L1154 之前」的状态** ⇒ 镜像列表注入在结构上不可撤销。而唯一持有干净快照的 L1029 `.orig` 在整个脚本里再没有第二次引用（`grep -n "\.orig" ci/conan/build_and_test.sh` 全文只命中 L1029 一处），没有任何代码路径会用它还原。

一句话机制 —— **备份发生在改写之后，所以「还原」必然还原到污染态；越合规的单值 url 写法越必脏。**

## 最小复现（零构建，不编译不下载不占槽）

把脚本自己的改写块抽出来对一枚同形态 conandata 跑一遍，再照 L1179/L1293/L1188 的顺序演一遍：

```bash
W=$HOME/qzy/<worktree>; D=$HOME/tmp/uc2/<task>/w3-repro; mkdir -p "$D"
sed -n '1032,1157p' "$W/ci/conan/build_and_test.sh" > "$D/rewrite_block.py"   # 真实改写块
printf 'sources:\n  "2.20":\n    url: "https://github.com/radvd-project/radvd/releases/download/v2.20/radvd-2.20.tar.gz"\n    sha256: "af37c5a81d59f3bdc00d83056606ffa1810d4550beed6caa4f81181246494220"\n' > "$D/conandata.yml"
python3 "$D/rewrite_block.py" "$D/conandata.yml"          # 演 L1154 —— url 变列表
cp "$D/conandata.yml" "$D/conandata.yml.predl-orig"       # 演 L1180 —— 备份点（已脏）
python3 - "$D/conandata.yml" <<'PY'                        # 演 L1293 —— file:// 替换
import sys; p = sys.argv[1]; s = open(p).read()
open(p, 'w').write(s.replace('https://github.com/radvd-project/radvd/releases/download/v2.20/radvd-2.20.tar.gz',
                             'file:///dev/null/radvd-2.20.tar.gz'))
PY
cp "$D/conandata.yml.predl-orig" "$D/conandata.yml"       # 演 L1188 的 trap 还原
grep -cE 'file://|ghfast|gh-proxy' "$D/conandata.yml"     # ⇒ 输出 1，还原后仍脏
```

2026-09-25 在 B 机 feat/radvd-2.20 HEAD 上实测该脚本（`~/tmp/uc2/z34-radvd/repro-w3-pollution.sh`）四段输出 ——

- 改写后（B）第 3 行 `url:`、第 4 行 `- "https://gh-proxy.com/https://github.com/..."`；
- file:// 替换后（C）两行列表项分别变成 `- "https://gh-proxy.com/file:///dev/null/..."` 与 `- "file:///dev/null/..."`；
- **trap 还原后（D）回到的是 B 的形态**（列表 + `gh-proxy.com`），不是 A 的单值形态；
- 禁词命中行数 = **1**（非 0 即脏）。

## 真实落地证据（radvd/2.20，两枚提交互为前后对照）

```text
fc7a4a8637  【主窗停工接管】radvd/2.20 收工前落盘
  - archives/r/radvd/2.20/conandata.yml 第 3 行 =
    url: "https://ghfast.top/https://github.com/radvd-project/radvd/releases/download/v2.20/radvd-2.20.tar.gz"
42d8b5a231fac17628078bbc75c08b7b064488e1  radvd/2.20: 还原 conandata 官方源 URL（sha256 未动）
  + archives/r/radvd/2.20/conandata.yml 第 3 行 =
    url: "https://github.com/radvd-project/radvd/releases/download/v2.20/radvd-2.20.tar.gz"
```

`git show HEAD:archives/r/radvd/2.20/conandata.yml` 的禁词计数 = **0**，sha256 全程未动（`af37c5a81d59f3bdc00d83056606ffa1810d4550beed6caa4f81181246494220`，与 dlcache 内 tarball 实测一致）。工作区另有 `conandata.yml.ghfast-bak`、`conandata.yml.orig` 两枚改写期快照，`git check-ignore -v` 证实分别被 `archives/.gitignore:2`（`*.ghfast-bak`）与 `:4`（`*.orig`）忽略，不会随目录级 add 进 PR —— **这一点要每包核一次，不能默认**。

## 规避做法（当成收口建 PR 前的固定第 0 步）

```bash
cd <worktree>
P=archives/<l>/<pkg>/<ver>/conandata.yml
git show "HEAD:$P" > "$P"                      # 只对这一枚文件，从 HEAD 逐字节取回
n=$(grep -cE 'file://|ghfast|gh-proxy' "$P"); echo "forbidden-hit=$n"   # 必须 0
git diff --name-only | grep -F "$P" && echo "STILL-DIRTY 停手" || echo "CLEAN 可以 add"
git check-ignore -v "$P".orig "$P".ghfast-bak 2>/dev/null || echo "残留未被忽略 ⇒ 单列，绝不 add"
```

要点：

1. **只还原这一枚文件**。不要整目录 `checkout`/`restore`（会连累同目录的 notes.md、reports/ 证据），不要 `add -A`。
2. **绝不为让禁词变 0 去动 sha256**。镜像只换传输通道不换源码身份；动 sha256 会把「取源污染」升级成「源码身份造假」。
3. `grep -c` 无命中时退出码是 1，属正常，别读成失败。
4. 还原要**放在按目录 `git add` 之前**（`pipeline run` 第 [4/8] 步是按目录暂存的，不会替你挑文件）。
5. 若 HEAD 版本本身就是脏的（上一轮已把镜像 URL 提交进去），应急可用 L1029 留下的 `conandata.yml.orig`（改写前快照），但取完必须删掉以免撞 JC1 残留闸，最终仍以 HEAD / 手工修回官方单值 URL 为准。

## 适用边界与反例

- **适用**：任何 conandata.yml 写成单值 url 且域名命中 L1027 白名单（github.com / archives.boost.io / ftpmirror.gnu.org / download.savannah.gnu.org / download.gnome.org / cdn.kernel.org / sourceforge.net / release-assets.githubusercontent.com / curl.se / ftp.jaist.ac.jp …）的源码包，且**在本地跑过** `finish`/`build_and_test.sh`。
- **不适用**：url 已写成多行列表形态的配方 —— L1153 的单行正则不匹配，改写段整段跳过，不会有本条污染（但会中 E549 的另一半雷，cache miss 时裸连失败）。
- **不适用**：只跑 `conan-verify` 不跑 `finish` 的场景 —— 那是 `scripts/conan_verify.py` 自己的 ghfast 注入面（`.ghfast-bak`，见 DRAFT-E323 的崩溃恢复回滚缺陷），症状同为「提交态脏」但**机制不同、脚本不同、还原点不同**，本条不覆盖它。radvd 的 `fc7a4a8637` 恰好就是那一侧的形态（单行 `ghfast.top/` 前缀而非列表），一并列出以免读者把两件事混成一件。
- **本条不改框架**：把 L1179 的备份提到 L1154 之前（或在 trap 里改成先恢复 `.orig`）才是真修，但 `ci/` 是多窗口共享框架红线面、影响所有包的取源路径 ⇒ 属**另一个独立 PR 且需用户批准**。本 PR 只交付副作用管理与事后还原这一层（既成事实面）。

## 查重与新增价值（六条既有材料逐条比）

| 条目 | 它说了什么 | 与本条的差异 |
|---|---|---|
| **E415**（已 promote，`knowledge/doc/E415.md`） | CI mirror-fallback 原地改写 conandata.yml「且不恢复」，行号记为 928-980，处置为「CI 后核验并恢复与 HEAD 逐字节一致」 | 它把现象登记为「不恢复」，且行号已失效。本条给出**为什么恢复必然无效**（备份点 L1179 晚于改写点 L1154）+ 当前真实行号 + 触发前置条件是 E549 的合规单值形态 + 「干净快照存在于 `.orig` 却无人引用」这一半机制。**症状同源、根因层次不同**，本条是它的因果补全 |
| **E549 / DRAFT-conandata-single-url-ci-mirror-fallback** | 单值 url 才触发镜像注入；写多 URL 列表会被静默跳过 | 它站在「怎么写配方」一侧，本条站在「写了合规单值之后每次 W3 会留下什么」一侧；且它的行号 L1019-1027 段界被本条细化到 L1141/L1153/L1154/L1156。二者互为前因后果，`caused_by: [E549]` |
| **DRAFT-8543-conandata-comment-url-predl-rewrite** | 预下载的正则会抓注释里的裸 URL，前缀碰撞导致 `source()` NotADirectoryError；文中明确写「门禁另有 trap 在退出时把 conandata.yml 还原为官方 URL（:1188）」 | 它的前提是「trap 会还原成官方 URL」，**本条否证这个前提**（trap 只能回到改写态）。这正是本条最实际的价值 —— 后来者照 8543 的认知行事，会以为还原是白拿的，从而不做收口核验。`conflicts_with` 登记于此 |
| **DRAFT-libnbd-1.9.6-local-predl-url-pollution** | `file://` 本机绝对路径进了 commit/PR，远端 CI `source()` FileNotFoundError；处置为提交前扫描并恢复官方 HTTPS | 它覆盖的是 `file://` 那一层（**会被 trap 撤销的那一层**），所以它的处方在「只跑一次 W3 就提交」时是够用的；本条覆盖的是它没有解释为什么扫描每次都会重新出现脏值的镜像层（**trap 撤不掉的那一层**） |
| **DRAFT-lexy-2025.05.0-e017-mirror-injection-residual-cleanup** | 识别并物理删除 `.ghfast-bak` / `.orig` / `.build-cache/` / `.lock` 残留，避免 JC1/JC5 | 只管**旁生文件**的清理，不管 `conandata.yml` 自身内容必脏；本条补一句它的副作用 —— `.orig` 其实是有价值的干净快照（fallback 取源），删之前先看清 `conandata.yml` 有没有还原干净 |
| **DRAFT-E323-conan-verify-ghfast-bak-rollback** | `conan_verify.py` G2 的 `.ghfast-bak` 在 finally 里恢复但不删文件，下次崩溃恢复逻辑会用旧 bak 覆盖新改动 | 另一个脚本（`scripts/conan_verify.py`）、另一种失效模式（跨轮次回滚），与本条（`ci/conan/build_and_test.sh` 的备份顺序）不重叠，故在正文里以「同类不同机制」并列而非合并 |

**组合后新增的解题路径**（按仓内「组合型知识不判重」口径申报 create）：组分各自有登记，但
「trap 声称已还原 ⇒ 人相信已还原 ⇒ 按目录 add ⇒ 镜像域名进 PR」这条**因果闭环**没有任一条既有条目写成，
而它恰好是本轮 gulkan/knewstuff/ki18n/radvd 反复踩的那一步。新增价值 = 把「事后核验」从可选动作升级为**收口固定第 0 步**，并给出可机判的禁词计数判据与真实行号锚点。

## 待办 / 解除条件

- 框架真修（独立 PR，需用户批准）—— 二选一：① 把 L1179-1180 的备份移到 L1027 判定之前（与 L1029 的 `.orig` 合并为一次）；② `_restore_conandata()` 改为优先用 `${CONANDATA}.orig` 并在成功还原后删除该快照。任一落地后本条降级为历史记录，处方第 1-2 步仍应保留作纵深防御。
- 在真修落地前，本条处方对**每一个走本地 W3 的源码包**持续有效，无解除条件。
