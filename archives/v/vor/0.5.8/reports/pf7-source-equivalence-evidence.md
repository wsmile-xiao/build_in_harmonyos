# PF7 例外链后半段：上游 GitHub tag 件与本包所用 Debian pool `.orig` **不等价**（一手复算）

> 本件补的是**第 6 轮 W4 判决件**（`reports/z75q-audit-result.json:22`，rule_id
> `PF7/R39-SOURCE-URL-NOT-OFFICIAL`，定级 P1）指出的缺口：PF7 的例外处置链有**两半**，此前随 PR 的
> 文本里只有前半段。前半段 = 作者站没有可直取的发布物（已见 `conandata.yml:5-15`、
> `manifest.yaml:28-31`、`notes.md:40-41`）；**后半段 = 为什么不能改用上游 GitHub 的 tag 件**
> （三串关键读数在本 PR 正文与草稿里逐件 0 命中，复算见 §7 第 4 条）。
>
> 取证窗：主理-75 名下整改棒 **z75z** · 2026-09-27 · 设备 = **B 机**（HarmonyOS PC aarch64）·
> worktree `~/qzy/主理-75-vor-0.5.8` 分支 `feat/vor-0.5.8`，起点 HEAD
> `f05446bc3ba9fa12606417bf3f660775992df6ae`（`git ls-remote origin refs/heads/feat/vor-0.5.8` 回读同值）。
> 本窗复算命中面（命令与读数见 §7 第 4 条）：`codeload` / `99326` / `491131` 三串在本 PR 的
> `notes.md`、`manifest.yaml`、`conandata.yml`、`conanfile.py`、`test_package/` 三件、
> `archives/v/vor/commands.json`、草稿对两枚、以及 `reports/` 原五件里**逐件 0 命中**，
> 仅第 6 轮判决件自身各 1 命中（那是叙述，不是取证）⇒ 「后半段未随 PR 披露」成立。
> ⛔ 本件只补文本与证据，未动构建输入：`conanfile.py` / `conandata.yml` / `test_package/conanfile.py` /
> `test_package/test.sh` 四件 blob 未变 ⇒ W3 证据仍绑 verify 时点 `2ecf0e8b16`，本窗不重跑
> conan-verify / finish。
> §0–§6 每个数字都是**本窗现取**（命令原样抄录，读者可逐条复算）；他棒留下的读数一律只在 §7
> 标成「母本读数」，不作为本件结论的依据。

## 0. 读数一览（本窗现取）

| # | 量 | 本窗实测 |
|---|---|---|
| 1 | Debian pool `.orig` 取回 | HTTP **200** / **361789 B** / `application/x-gzip` |
| 2 | 其 sha256 | `9003089708327e1a3169b412e16725ccb669dd21465d49abec5aa4e6e4cce09a` **== `conandata.yml:19` 声明值** |
| 3 | GitHub tag 件（codeload）取回 | HTTP **200** / **99326 B** / `application/x-gzip` |
| 4 | 其 sha256 | `491131666a4a614dd2e8a6f263ad0e468d84b154ce9c67c3c7968a027444037b` |
| 5 | 两树常规文件数 | `.orig` = **112**，tag 件 = **52**，共同 = **51** |
| 6 | `diff -rq` | 输出 **58** 行，其中 `differ` 命中 **0**（正对照 `differ|Only in` = 58） |
| 7 | 51 枚共同文件的独立哈希比对 | 不匹配 **0** 枚 ⇒ 共同部分逐字节相同 |
| 8 | tag 件缺件（`.orig` 有而 tag 件无） | **61** 项：预生成 `configure`、`aclocal.m4`、`autom4te.cache/`（内含 5 枚文件）、**54** 枚 `data/*.png` |
| 9 | `Makefile.am` 递归计数 | 两侧均 **0** |
| 10 | PNG 再生工具 | `povray` / `pnmtopng` / `pnmcrop` 在 B 机 `command -v` 均 **NOT FOUND** |
| 11 | 作者站候选下载路径 | 全部 HTTP 200 的 HTML「Edit "<路径>"」catch-all 页；`vor-0.5.8.tar.gz` = **1535 B**（同族页 1502–1550 B） |
| 12 | 作者仓库 releases API | HTTP **200**、实体 **5 字节 = 空数组** |

## 1. 两枚 URL 的实测

命令（B 机 `~/tmp/uc2/z75z-vor-fix3/dl/`，curl 8.8.0-DEV / aarch64-linux-ohos）：

```sh
U_DB="https://deb.debian.org/debian/pool/main/v/vor/vor_0.5.8.orig.tar.gz"
U_GH="https://codeload.github.com/JasonWoof/vor/tar.gz/refs/tags/0.5.8"
curl -sS -L -o db.tar.gz -w "HTTP=%{http_code} SIZE=%{size_download} TYPE=%{content_type} EFF=%{url_effective}\n" "$U_DB"
curl -sS -L -o gh.tar.gz -w "HTTP=%{http_code} SIZE=%{size_download} TYPE=%{content_type} EFF=%{url_effective}\n" "$U_GH"
wc -c < db.tar.gz ; sha256sum db.tar.gz
wc -c < gh.tar.gz ; sha256sum gh.tar.gz
```

本窗原样输出：

```
HTTP=200 SIZE=361789 TYPE=application/x-gzip EFF=https://deb.debian.org/debian/pool/main/v/vor/vor_0.5.8.orig.tar.gz
361789
9003089708327e1a3169b412e16725ccb669dd21465d49abec5aa4e6e4cce09a  db.tar.gz
HTTP=200 SIZE=99326 TYPE=application/x-gzip EFF=https://codeload.github.com/JasonWoof/vor/tar.gz/refs/tags/0.5.8
99326
491131666a4a614dd2e8a6f263ad0e468d84b154ce9c67c3c7968a027444037b  gh.tar.gz
```

两条 URL 都**无重定向**（`EFF` 与请求同值）。`.orig` 的哈希与 `conandata.yml:19`、
`manifest.yaml:34`、`notes.md:38`、`reports/failure-state-evidence.md:303` 四处声明值逐字相同
⇒ PR 内四处声明与本窗现取实物同哈希。tag 件那枚哈希是本件首次写进 PR 正文的新读数
（本件落库前在正文与草稿里 0 命中，见 §7 第 4 条）。

## 2. 两树清单与逐字节对账

命令：

```sh
mkdir -p trees/db trees/gh
tar xf dl/db.tar.gz -C trees/db          # 根前缀 vor-0.5.8/
tar xf dl/gh.tar.gz -C trees/gh          # 根前缀同为 vor-0.5.8/
(cd trees/db && find vor-0.5.8 -type f | LC_ALL=C sort) > list-db.txt
(cd trees/gh && find vor-0.5.8 -type f | LC_ALL=C sort) > list-gh.txt
LC_ALL=C comm -12 list-db.txt list-gh.txt > common.txt
LC_ALL=C comm -23 list-db.txt list-gh.txt > only-db.txt
LC_ALL=C comm -13 list-db.txt list-gh.txt > only-gh.txt
diff -rq trees/db/vor-0.5.8 trees/gh/vor-0.5.8 > diff-rq.txt 2>&1
grep -c 'differ' diff-rq.txt ; grep -ciE 'differ|Only in' diff-rq.txt
```

本窗实测：`N_DB=112`、`N_GH=52`、**共同 51 枚**、`.orig` 独有 **61** 项、tag 件独有 **1** 项
（`only-gh.txt` 全文只有 `vor-0.5.8/.gitignore` 一行）。`diff -rq` 返回 rc=1、输出 **58 行**，
`grep -c 'differ'` = **0**，正对照 `grep -ciE 'differ|Only in'` = **58** ⇒ 零命中不是方言假象；
58 行拆开是「Only in db」57 行 + 「Only in gh」1 行。差集算术自洽：61 项独有里
`autom4te.cache` 的 5 枚文件在 diff 里折叠成 1 行目录项 ⇒ `61 - 5 + 1 = 57` ✓。

为不依赖 `diff` 的措辞，本窗另跑一遍独立哈希比对（对 51 枚共同文件逐枚比 sha256）：

```sh
: > sum-compare.txt
while read -r f; do
  a=$(sha256sum < "trees/db/$f" | awk '{print $1}')
  b=$(sha256sum < "trees/gh/$f" | awk '{print $1}')
  [ "$a" = "$b" ] || echo "MISMATCH $f" >> sum-compare.txt
done < common.txt
wc -l < sum-compare.txt
```

结果 **0 行** ⇒ 51 枚共同文件逐字节相同。**"共同部分相同"不等于"两树等价"**：差集是 61 项，
逐项见 §3–§5。

## 3. tag 件缺件清单（预生成 `configure`、`aclocal.m4`、`autom4te.cache`）

命令（`-type d` 口径是第 6 轮判决件说「目录名不入常规文件清单」的补法）：

```sh
for f in configure aclocal.m4 Makefile.in install-sh config.guess config.sub autom4te.cache; do
  printf '%s db=%s gh=%s\n' "$f" \
    "$(find trees/db/vor-0.5.8 -maxdepth 1 -name "$f" | wc -l)" \
    "$(find trees/gh/vor-0.5.8 -maxdepth 1 -name "$f" | wc -l)"
done
find trees/db/vor-0.5.8 -type d -name autom4te.cache | wc -l
find trees/db/vor-0.5.8/autom4te.cache -type f | wc -l
grep -n 'autom4te' diff-rq.txt
wc -c < trees/db/vor-0.5.8/configure
sed -n '/^# Generated by GNU Autoconf/p' trees/db/vor-0.5.8/configure | head -1
```

本窗实测：

| 路径 | `.orig` | tag 件 | 说明 |
|---|---|---|---|
| `configure` | **1**（166325 B，`# Generated by GNU Autoconf 2.69 for VoR 0.5.8.`） | **0** | 预生成脚本，与 `notes.md:22` 的字节数逐字对齐 |
| `aclocal.m4` | 1 | **0** | autoconf 宏展开产物 |
| `autom4te.cache/` | **1**（目录；内含 5 枚文件 `output.0`/`output.1`/`requests`/`traces.0`/`traces.1`） | **0** | 目录级读数走 `-type d` 口径（第 6 轮判决件称「清单只列常规文件、目录名不入列」⇒ 本件换口径）；`diff -rq` 第 3 行 `Only in trees/db/vor-0.5.8: autom4te.cache` 同判 |
| `Makefile.in` | 1 | 1 | 两侧同一枚（在 51 枚共同文件内） |
| `install-sh` | 1 | 1 | 两侧都有 ⇒ 非差异项 |
| `config.guess` / `config.sub` | 0 | 0 | 两侧都没有 ⇒ `conanfile.py:201-204` 的 isfile 跳过逻辑与本判据无关 |

即：**tag 件是 git-archive，不含任何 autotools 生成物**；`.orig` 是上游发布物，生成物齐备。

## 4. 两侧 `Makefile.am` 计数（automake 路也走不通）

```sh
find trees/db/vor-0.5.8 -name 'Makefile.am' | wc -l
find trees/gh/vor-0.5.8 -name 'Makefile.am' | wc -l
```

本窗实测：`.orig` = **0**、tag 件 = **0**（递归计数，非只看顶层）。⇒ 与 `notes.md:30-31` 一致：
`Makefile.in` 是手写的（`configure.ac` 只有 `AC_CONFIG_FILES([Makefile])`），上游从未走 automake，
所以「换到 tag 件后用 autoreconf 补齐缺件」这条路**没有 automake 输入可用**。

## 5. 缺 54 枚运行期 PNG 与再生工具链缺失

```sh
(cd trees/db && find vor-0.5.8 -name '*.png' | LC_ALL=C sort) > png-db.txt
(cd trees/gh && find vor-0.5.8 -name '*.png' | LC_ALL=C sort) > png-gh.txt
LC_ALL=C comm -23 png-db.txt png-gh.txt > png-missing.txt
wc -l < png-db.txt ; wc -l < png-gh.txt ; wc -l < png-missing.txt
find trees/gh/vor-0.5.8/data -type f | LC_ALL=C sort
find trees/db/vor-0.5.8 -name '*.pov' | wc -l ; find trees/gh/vor-0.5.8 -name '*.pov' | wc -l
grep -c '^data/.*\.png' trees/db/vor-0.5.8/gfx.mk ; grep -c povimg trees/db/vor-0.5.8/gfx.mk
sed -n '1,4p' trees/db/vor-0.5.8/povimg.sh
for c in povray pnmtopng pnmcrop; do printf '%s=' "$c"; command -v "$c" || echo NOT_FOUND; done
```

本窗实测：`PNG_DB=59`、`PNG_GH=5`、`PNG_MISSING=`**54**。tag 件的 `data/` 只有 7 枚
（`b_game.png`、`b_on.png`、`b_over.png`、`b_rockdodger.png`、`b_variations.png` + `bang.wav` +
`mph.xm`），`.orig` 的 `data/` 是 61 枚（59 PNG + 同两枚音频，与 `notes.md:180` 一致）。
`.pov` 源两侧各 **3** 枚、`gfx.mk` 与 `povimg.sh` 也都在共同 51 枚之内 ⇒ 换到 tag 件后
`make` 的 `data` 目标（`Makefile.in:77` = `data: $(graphics) build-dir-data-link`，
`Makefile.in:60` 的 `graphics := data/ship.png data/icon.png data/life.png data/font.png $(rocks)`）
会去跑 `gfx.mk` 那 **6** 条 `data/*.png` 再生规则（`grep -c povimg gfx.mk` = 7），而再生脚本本体
`povimg.sh:3` 是：

```
povray -D +A -O- +FP $* 2>/dev/null | pnmcrop | pnmtopng -transparent '#000000' -gamma .45 2>/dev/null
```

本窗一手读数：B 机 `command -v povray`、`command -v pnmtopng`、`command -v pnmcrop` **均 NOT FOUND**
⇒ 与 `notes.md:190-191` 与 `reports/failure-state-evidence.md:328` 同口径。
即便 make 因时间戳判定不需重建，装出来的包也只有 5 枚 PNG，与 `notes.md:207` 记的
「59 PNG 全部落 `share/vor/`」实物不符 ⇒ 运行期缺 54 枚资产。

## 6. 作者站 catch-all 页与 `releases` API

```sh
i=0
for P in "https://sametwice.com/vor" "https://sametwice.com/vor/" \
         "https://sametwice.com/vor/vor-0.5.8.tar.gz" "https://sametwice.com/vor/download" \
         "https://sametwice.com/vor/0.5.8" "https://sametwice.com/vor/releases"; do
  i=$((i+1))
  curl -sS -L -o "page$i.html" -w "HTTP=%{http_code} SIZE=%{size_download} EFF=%{url_effective}\n" "$P"
done
# 同长度/同族变体（看字节数是否只随路径长度变化）
for P in "https://sametwice.com/vor/vor-0.5.8.tar.gz" "https://sametwice.com/vor/vor-0.5.8.tar.bz2" \
         "https://sametwice.com/vor/vor-0.5.8.tar.xz" "https://sametwice.com/vor/vor_0.5.8.orig.tar.gz"; do
  curl -sS -L -o /dev/null -w "%{http_code} %{size_download} %{content_type} %{url_effective}\n" "$P"
done
head -c 2 page3.html | od -An -tx1        # gzip 魔数应为 1f 8b
diff page4.html page5.html                # /download 与 /0.5.8 两张页只差 3 行
curl -sS -H "Accept: application/vnd.github+json" -o rel.json \
  -w "HTTP=%{http_code} SIZE=%{size_download}\n" "https://api.github.com/repos/JasonWoof/vor/releases"
wc -c < rel.json
```

本窗逐条实测（HTTP 状态 / 字节 / `content_type`）：

| 路径 | HTTP | 字节 | 类型 |
|---|---|---|---|
| `/vor`（真主页，`<title>Variations on Rockdodger</title>`） | 200 | 8591 | text/html |
| `/vor/` | 200 | 1939 | text/html |
| `/vor/vor-0.5.8.tar.gz` | 200 | **1535** | text/html |
| `/vor/download` | 200 | 1511 | text/html |
| `/vor/0.5.8` | 200 | 1502 | text/html |
| `/vor/releases` | 200 | 1511 | text/html |
| `/vor/vor-0.5.8.tar.bz2` | 200 | 1538 | text/html |
| `/vor/vor-0.5.8.tar.xz` | 200 | **1535**（与 `.tar.gz` 同长 ⇒ 同字节） | text/html |
| `/vor/vor_0.5.8.orig.tar.gz` | 200 | 1550 | text/html |

机理已查实：这类页是作者站的 wiki「创建页面」表单——`<title>Edit "<路径>"</title>` +
`<p>edit "<路径>" below.</p>` + `<form action="<路径>" method="post">`，把请求路径回显了三处，
所以**字节数随路径长度变化**（两条同长度的候选名 `vor-0.5.8.tar.gz` 与 `vor-0.5.8.tar.xz`
实测同为 1535 B）。两枚页面对拉只差这 3 行：

```sh
diff page4.html page5.html   # /download 与 /0.5.8
```

无一例外是 HTML：`head -c 2` 读回 `3c 21`（即 `<!`），**不是** gzip 的 `1f 8b` ⇒ 作者站没有任一条
可直取的 tarball。真主页 8591 B 上唯一的下载链是 `vor-win-0.5.4-rc1.zip`（`grep -c` 命中 1，
`jasonwoof` 命中 3）⇒ 版本与平台都不对，这就是「前半段」结论的现取复核。
GitHub 侧：`api.github.com/repos/JasonWoof/vor/releases` 返回 **200 + 5 字节的空数组**
（GitHub 的 pretty-print 形态是 `[`、空行、`]`）⇒ 上游仓库**没有任何 release 资产**，
`0.5.8` 只有一个 git tag，tag 可达的发布件就是 §1 那枚 99326 B 的 git-archive。

> 口径精度（本窗据此改写了 PR 正文两处）：`notes.md:40` 与 `manifest.yaml:28-29` 原写作「三条候选
> 路径实测均只返回 **1535 字节**」，但 z75a 轮没把那三条路径名登记进任何落盘件 ⇒ 读者无法按名复算。
> 本表给出的口径是：**catch-all 是同一张 wiki「创建页面」模板、会回显请求路径**，与
> `vor-0.5.8.tar.gz` 等长的候选名恰为 1535 B，其余候选为 1502–1550 B 的同族变体，真主页 8591 B；
> 「只有 catch-all 页、没有任何可直取的 tarball」这一结论不变。两处正文已按本表改写并指回本件。

## 7. 后果链：为什么「换到官方 tag 件」走不通

1. 配方**直取**预生成 `configure`：`conanfile.py:109` 的 `source()` 只有
   `get(self, **self.conan_data["sources"], strip_root=True)`，`conanfile.py:229` 取
   `configure_script = os.path.join(self.source_folder, "configure")`、`:232` 直接
   `self.run('CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "%s" %s' % (configure_script, args), …)`。
   全件 `grep -c autoreconf` = 1，唯一命中是 `conanfile.py:27` 的 docstring「no source patching,
   no autoreconf run」⇒ **没有任何一步会生成 `configure`**。换到 §3 那枚不含 `configure` 的
   tag 件，起手就是 `sh: .../configure: No such file or directory`。
2. 补自举也不行：§4 两侧 `Makefile.am` 均 0 ⇒ automake 无输入；而 `INSTALL:13-16` 要求
   autoconf ≥ 2.63 的两条形路径是「从 git 构建」与「改动图形资产」（逐字见
   `reports/failure-state-evidence.md:323-325`），本包两条都不走（`notes.md:26-31`）。
3. 即使有 `configure`：§5 缺 54 枚运行期 PNG，`gfx.mk` 的再生规则又落在本机 NOT FOUND 的
   `povray`/`netpbm` 上 ⇒ 构建或运行期必有一处塌。
4. 披露面（本窗逐件 `grep -c` 复算）：`codeload` / `99326` / `491131` 三串在
   `archives/v/vor/0.5.8/` 的 `notes.md`、`manifest.yaml`、`conandata.yml`、`conanfile.py`、
   `test_package/conanfile.py`、`test_package/test.sh`、`test_package/MANIFEST.yml`、
   `archives/v/vor/commands.json`、草稿对两枚（`.kv`/`.md`）以及 `reports/` 原五件里**逐件 0 命中**；
   只有第 6 轮判决件 `reports/z75q-audit-result.json` 三串各 **1** 命中（那是判决叙述，不是取证）。
   ⇒ 「后半段没随 PR 走」在本件落库前的 HEAD 上仍是可复算事实。复算命令：

```sh
cd <仓根>/archives/v/vor/0.5.8
for f in notes.md manifest.yaml conandata.yml conanfile.py test_package/conanfile.py \
         test_package/test.sh test_package/MANIFEST.yml ../commands.json; do
  printf '%-32s %s %s %s\n' "$f" "$(grep -c codeload $f)" "$(grep -c 99326 $f)" "$(grep -c 491131 $f)"
done
grep -c codeload reports/z75q-audit-result.json   # 1
```

⇒ 官方 tag 件与本包所用 `.orig` **不等价**，且不存在一条可用的"换源"路径。所以 PF7 命中的
「非官方位」只能走**例外披露**（本件 + `notes.md` §2 与 §13），⛔ 不得改 `conandata.yml:18` 的
`url`：改 url ⇒ recipe revision 变 ⇒ `conan create` / conan-verify / W3 全套证据作废（第 6 轮
判决件的 `explicit_non_findings` 同判）。

**母本读数（他棒所留，只作可重复性旁证，不作本件依据）**：
`~/tmp/uc2/z75a-vor-close/probe/` 下同名件的 `wc -l` 现点为 `list-db.txt` 112、`list-gh.txt` 52、
`common.txt` 51、`diff-rq.txt` 58、`png-db.txt` 59、`png-gh.txt` 5，与 §0 的本窗现取值逐项相符。
第 6 轮判决件当时说「`autom4te.cache` 无法从清单证实」，是因为那份清单由 `find -type f` 生成、
目录名不入列；本件 §3 改用 `-type d` 计数 + `diff -rq` 第 3 行两种口径 ⇒ 该项现已可证。

## 8. 复算坐标与件数口径

- 设备侧原件目录：B 机 `~/tmp/uc2/z75z-vor-fix3/`（`dl/db.tar.gz`、`dl/gh.tar.gz`、
  `dl/page1.html`–`dl/page6.html`、`dl/rel.json`、`trees/db/vor-0.5.8/`、`trees/gh/vor-0.5.8/`、
  `list-db.txt` 112、`list-gh.txt` 52、`common.txt` 51、`only-db.txt` 61、`only-gh.txt` 1、
  `diff-rq.txt` 58、`png-db.txt` 59、`png-gh.txt` 5、`png-missing.txt` 54、`sum-compare.txt` 0 行）。
  ⚠ 该目录是设备侧一次性中间产物、**不随 PR**；本件 §0–§6 已把判决所需读数与命令抄全，读者不必上机。
- 随 PR 的 `archives/v/vor/0.5.8/reports/` 现共 **10** 枚（`git ls-files archives/v/vor/0.5.8/reports/ | wc -l` = 10）：
  原五件（`conan-create.log`、`conan-verify-report.md`、`failure-state-evidence.md`、`test-report.md`、
  `w3-local-ci.log`）+ 第 5 轮判决两件（`z75f-audit-result.json`、`z75f-w4-report.log`）+
  第 6 轮判决两件（`z75q-audit-result.json`、`z75q-w4-report.log`）+ **本件**。
  第 3 轮的 `reports/audit-result.json` 仍故意不入库（口径见 `notes.md:309-314`）。
- 本件的入库方式：`reports/` 整目录被仓根 `.gitignore` 的 `reports/` 规则挡住 ⇒ 新件一律
  `git add -f -- archives/v/vor/0.5.8/reports/pf7-source-equivalence-evidence.md`（逐件精确路径）。
