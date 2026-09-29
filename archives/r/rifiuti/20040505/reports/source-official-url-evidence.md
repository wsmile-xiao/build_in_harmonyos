# 取源官方直链证据 — rifiuti/20040505（第 6 轮整改，棒 z75m）

- **一句话结论**：第 5 轮 W4 审计否证的"无官方发布物"前提成立与否已本棒一手复测 —— `.dsc` 声明的官方主页
  `sf.net/projects/odessa` 的 `files/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz` **确实一手可取**
  （HTTP 200 / `application/x-gzip` / **2823 字节** / sha256 `3694cf6811c7be96412934ee1f378cf74003472d1a62dc642e2229f4ad5073cc`
  与 `conandata.yml` 现声明值逐字相等），且与 Debian 池内 `.orig` 是**字节级同一枚发布物**（`cmp` 相同、解包树
  `diff -rq` 零差异）⇒ 取源已按框架处方的首选路径 (a) 换成官方直链，**PF7 命中由 2 归 0**，不写例外说明、不用 `--no-preflight`。
- 机/时：B 机（HarmonyOS aarch64，`curl 8.8.0-DEV (aarch64-linux-ohos) libcurl/8.8.0-DEV OpenSSL/3.0.12 zlib/1.3.1`），
  2026-09-27 08:39–09:04（设备本地 +08:00）。
- 环境：`export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem" PATH="$HOME/usr/local/bin:$HOME/.local/bin:$PATH"`。
- **本件所有网络与哈希读数为本棒现取**（未沿用审计窗数字）；审计窗的同一批读数只在 §5 作交叉对照列出。
- 工作目录：`~/qzy/主理-75-rifiuti-20040505`；基线 `48d9cee684`；整改前 HEAD `04e90158e72ca1e88478832671e29e7b225a31be`。

## 1. 四种 URL 形态的现取读数与 302 链

命令模板（本棒实际执行件：`~/tmp/uc2/z75m-rifiuti-fix6/probe3.sh`，日志 `probe2.log`）：

```sh
curl -sS -L --max-redirs 8 --connect-timeout 20 --max-time 180 \
  -o <落盘> -D <头存档> \
  -w 'code=%{http_code} type=%{content_type} dl=%{size_download} eff=%{url_effective} redir=%{num_redirects}\n' \
  <URL>
```

| # | URL 形态 | 现取读数 |
|---|---|---|
| V-a | `https://sourceforge.net/projects/odessa/files/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz/download` | `code=200 type=application/x-gzip dl=2823 redir=2`；`wc -c`=2823；sha256=`3694cf68…`；`gzip -t` rc=0；`tar tzf` 列出 `rifiuti_20040505_1/{bin/,CHANGES,Readme.txt,src/,src/Makefile,src/rifiuti.c}` |
| V-b | `https://downloads.sourceforge.net/odessa/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz` | `code=200 type=application/x-gzip dl=2823 redir=1`；2823B；同哈希 |
| V-c | `…/projects/odessa/files/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz`（不带 `/download`） | `code=200 type=application/x-gzip dl=2823 redir=4`（301→301→302→302→200）；2823B；同哈希 |
| **V-d（采用）** | `https://downloads.sourceforge.net/project/odessa/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz` | `code=200 type=application/x-gzip dl=2823 redir=1`；2823B；同哈希；`gzip -t` rc=0；tar 列表同 V-a |

**302 链逐字**（V-a 的头存档 `h`/`v*.hdr`）：

```
HTTP/1.1 302 Found   location: https://downloads.sourceforge.net/project/odessa/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz?ts=gAAAAAB…&use_mirror=master&r=
HTTP/1.1 302 Found   location: https://master.dl.sourceforge.net/project/odessa/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz?viasf=1&fid=d3e93a1758799649&e=1790556056&st=<令牌>
HTTP/1.1 200 OK      Content-Type: application/x-gzip   Content-Length: 2823
                     content-disposition: attachment; filename="rifiuti_20040505_1.tar.gz"
```

⇒ 跳转终链 `master.dl.sourceforge.net/…?viasf=1&fid=…&e=<过期时戳>&st=<令牌>` **每次请求新签**（V-a/V-b/V-c/V-d 四次实测
`e=` 分别为 1790556056 / 1790556057 / 1790556060 / 1790556062）⇒ 终链不可写进配方；`use_mirror=master` 是服务端选的镜像名，
也不写。配方只写稳定路径，镜像回退由框架追加。

**采用 V-d 而非 V-a 的理由见 §3**（V-a 页面式形态在 `conan create` 的一手失败）。两枚 URL 均不在
`scripts/ohc/preflight.py:356-362` 的 `_PF7_MIRROR_HOSTS` / `_PF7_DEBIAN_HOSTS` 里 ⇒ 直调
`_pf7_classify()` 对二者返回 `None`（本棒现取：`CD_CLASSIFY None` / `MF_CLASSIFY None`）。

## 2. 与 Debian 池内 `.orig` 的字节级同一性（池址降级为旁证）

命令与现取读数（实际执行件 `probe4.sh`，日志 `probe4.log`）：

```sh
curl -sS -L … -o pool.orig.tar.gz https://deb.debian.org/debian/pool/main/r/rifiuti/rifiuti_20040505.orig.tar.gz
#   code=200 type=application/x-gzip dl=2823   wc -c=2823   sha256=3694cf6811c7be96412934ee1f378cf74003472d1a62dc642e2229f4ad5073cc
cmp sf.tar.gz pool.orig.tar.gz          # ⇒ CMP_TARBALL=identical（两枚 tar 逐字节相同）
tar xzf … -C xsf ; tar xzf … -C xpool   # ⇒ 顶层目录同为 rifiuti_20040505_1
diff -rq xsf xpool                      # ⇒ DIFF_RQ_RC=0，differ 行数 0（日志文件 0 字节）
```

逐文件 sha256（sf 侧 / pool 侧，四对全 SAME）：

| 文件 | sha256（两侧相同） |
|---|---|
| `CHANGES` | `ee4bb8756777e09c526bf753384a4ff646ce39e2bf74a36bf835378972a126c9` |
| `Readme.txt` | `f637218edfbcb6405f278b43ec86bd249ae122bfcf06933fd4f906740c44002f` |
| `src/Makefile` | `f3bb073249cc2ff9ec009db96fda1cb9a9485004a9a4c9bbb871d23e73ba2000` |
| `src/rifiuti.c` | `2d75a10c19aa85872135ec944aec31c6ed391411d19185792c5e87c23f200945` |

本包构建实际消费的那枚缓存件（未跟踪，不入 PR）：
`.build-cache/predl_cache/49d722b2_rifiuti_20040505.orig.tar.gz` = 2823B / sha256 `3694cf68…` ⇒ **同一枚**。

⇒ 换源**不动哈希、不动解包树、不动产物面**；`conandata.yml` 文本变 ⇒ recipe revision 变 ⇒ 门禁必须重跑（§4）。

## 3. URL 形态是门槛，不是风格（第 6 轮 G2 一手失败现场）

先按页面式 V-a 换源（提交 `d0a4261308610d0d4fb26b1f772d9f1818dc6d34`）后跑 `conan-verify` ⇒ **G2 FAIL**：

```
$ python3 scripts/ohc-run.py conan-verify rifiuti 20040505     # 2026-09-27 08:56:57，rc=1
❌ 配方验证失败: G2
reports/conan-verify-report.md:3  **Verdict**: FAIL   Date :6 = 2026-09-27T08:56:57.938189
reports/conan-create.log:86-93（逐字）
  rifiuti/20040505@ohpcd/stable: Calling source() in …/p/rifiu0357bb25574ac/s
  … WARN: The requested URL(s) are not listed in backup-sources metadata for this SHA256 cache entry. … Re-downloading to verify.
  … WARN: file '…/tmp/ch/dlcache/s/3694cf68…' already exists, overwriting
  … Sources correctly downloaded from https://sourceforge.net/projects/odessa/files/Rifiuti/20040505_1/rifiuti_20040505_1.tar.gz/download
  … Uncompressing download to .
  ERROR: rifiuti/20040505@ohpcd/stable: Error in source() method, line 83
        get(self, **self.conan_data["sources"], strip_root=True)
        BadZipFile: File is not a zip file
```

⇒ **下载成功、解包失败**：conan 按 URL 末段推归档类型，末段 `download` 无扩展名 ⇒ 落到 zip 分支。
该轮两份判决件已被通过轮按名覆盖，逐字件已在本棒整改前快照：
`failed-g2/conan-create.log` sha256 `642ff403a6babab2b2d3996e6256e0928e538460ffb761ea66ce9a98ea78291d`、
`failed-g2/conan-verify-report.md` sha256 `721d7397e1463f4f055cfd5c69a76f3c492f309b4396bec9d0c090ee38595d9e`
（在 `~/tmp/uc2/z75m-rifiuti-fix6/`，非随 PR 件；本件 §3 的引文即其逐字内容）。

修法取舍：`conanfile.py:83` 的 `get()` 未给 `target=`/`filename=` ⇒ 加参数可救，但**本棒红线不改 `conanfile.py`**
（且那是构建输入、再动一次 rrev）⇒ 改用末段带 `.tar.gz` 的官方直链形态 V-d。**该坑与既有条目 E392 同族**
（`knowledge/doc/E392.md:11` 签名含 `BadZipFile`），本包是其"URL 形态"变体。

## 4. 换源后的门禁复跑读数（一手）

| 步 | 命令 | 读数 |
|---|---|---|
| 准入 | `sh ~/tmp/uc2/gate.sh --light` | `GATE_PASS:probe=clang MemAvailable=6113MB`（W0 前）/ `5114MB`（finish 前，编译器进程 1、RSS 78MB）；rc=0 |
| 槽位 | `sh ~/tmp/uc2/build-slot.sh --kind short --wait 1800 --mem 2500 -- <cmd>` | 开工 `SLOT_STATUS: 本机长杆 0/2 · 机动 1/3（总 5 槽）`；`SLOT_OK 09:00:59 cmd=…conan-verify…`、`SLOT_OK 09:01:42 cmd=…finish…`；verify 轮收尾 `SLOT_DONE:ok MemAvailable=5237MB` |
| W0 | `bash ci/scripts/preflight_check.sh rifiuti/20040505` | rc=**0**，`[OK] 预检通过（无依赖需要检查）` |
| PF7 | `python3 scripts/ohc/preflight.py <worktree> origin/main HEAD` | `PF_RC=1`；**`PF7_HITS=0`**（`grep -c PF7`）；findings 共 1 条且不含 PF7 = `PF9 分支/路径闸…archives/r/rifiuti/README.md, commands.json, manifest.yaml`（第 5 轮审计记 P3 的仓级结构性互斥，本棒按指令未处置） |
| verify | `python3 scripts/ohc-run.py conan-verify rifiuti 20040505` | rc=**0**；三一致 = 正文 `✅ 配方验证通过: rifiuti 20040505` + `reports/conan-verify-report.md:3` `**Verdict**: PASS` + rc 0（`Date :6` = 2026-09-27T09:01:11.445013，全文 44 行）；G0/G1/G2/G3 全 PASS，其中 **G2（conan create）换源后 PASS** |
| finish | `python3 scripts/ohc-run.py finish rifiuti 20040505 built` | 包装 rc=2（红项 `失败步骤: step5b, step8`，见下）；判据按 `:123` `║ EXIT_REASON: finish_success` + `:124` `║ EXIT_CODE: 0` + `.ci-result.json exit_code=0` ⇒ **通过**；`:125 STEP_FAILED: Step6` 是 `finish.py:538` 非阻塞分支写死的字面量 |
| W3 真伪 | `reports/w3-local-ci.log` | mtime 09:03（晚于本轮起点 09:01:36）、14960B / 296 行（上轮 14240B / 291 行）、判决标记数 `grep -c -E 'RESULT=\|SUMMARY'` = **9** > 0；`:282-286` L0 pass / L1 pass / **L2 skip** / L4 pass / L5 pass，`:291-293` Total 1 / Success 1 / Failed 0，`:266` `SUMMARY total=22 pass=22 fail=0` |
| 归档判决 | `archives/r/rifiuti/20040505/.ci-result.json`（gitignore，不随 PR） | `timestamp=2026-09-27T09:03:45.125275`、`exit_code=0`、`step=W3_local_ci`、`integrity_hash=b5ebda842cb8d1d5`、`log_sha256=235f30e33262d94c9cdc3c85651461aee9da4ccfc76c9387de069896d453dd02`；本棒按 `finish.py:251-252` 复算 `sha256("2026-09-27T09:03:45.125275:rifiuti:20040505:0")[:16]` = `b5ebda842cb8d1d5`（**match True**），按 `:263-267` 复算 `sha256(reports/w3-local-ci.log)` = `235f30e3…`（**match True**） |
| CKG | `python3 scripts/ohc-run.py check-knowledge-gap rifiuti 20040505` | `notes.md: total=0 extracted=0 pending=0 failed=0`、`manifest.yaml: knowledge_count=4 `**`unreferenced=0`**、`✅ 知识完整性检查通过`、RC=**0**（整改前同命令 = `unreferenced=4` / RC=3）；finish 内嵌的那次同样 `unreferenced=0`（`finish6.log:96-97`） |

**step5b / step8 仍红的归属（如实记录，不处置）**：CKG 半区已绿，step5b 的剩余红项是**仓级** W5
知识图谱完整性检查（`finish6.log:80-94`：`字段缺失: E219.kv/E253.kv/E305.kv root_cause 为空、E305.kv rec_approach 为空`
＋`发现 1397 个草稿待审` ⇒ `❌ 知识图谱完整性检查发现 1 类问题`），与 `finalize-archive 有警告 (RC=2)`
（`packaging/` 目录、release/debug tar.gz 缺失）；step8 = submit 就绪预检缺
`reports/test-report.md` / `packaging/` / `.staging-verified`（`finish6.log:104-108`）⇒ 即第 5 轮审计记 P3 的
"PF9 分支/路径闸 × 软件级三件套"互斥家族，非本包缺陷。另披露：`finish6.log:73` 的"状态不一致: notes=published…"
回显把本包 notes §7.2 表格里的**引用文字**当成了状态行 ⇒ 框架启发式误读，非本包状态字段冲突（`manifest.yaml:8` `status: built`）。

## 5. 与第 5 轮审计窗读数的交叉对照

| 项 | 审计窗（z75n） | 本棒现取（z75m） | 是否一致 |
|---|---|---|---|
| `/download` 端点 | 302→200、2823B、`application/x-gzip` | 200、2823B、同类型（2 跳） | 一致 |
| sha256 与 `conandata.yml` | 逐字相同 | 逐字相同（`3694cf68…`） | 一致 |
| 两棵树 `diff -rq` | 零差异 | 零差异（differ 行数 0）＋ `cmp` 逐字节相同 | 一致 |
| 四个文件 sha256 | `ee4bb875…`/`f637218e…`/`f3bb0732…`/`2d75a10c…` | 同上四枚 | 一致 |
| `www.foundstone.com` | TCP 443 超时 `rc=28` | 同（`code=000`、15s 超时） | 一致 |
| `mbsd.evolvis.org` | 可达但无本包树（404/319B） | 未重测（本棒只补 `www.mirbsd.de` catch-all 一项） | — |
| **URL 形态可被 conan 直接消费** | 未跑 `conan create` 验证 | **页面式 `/download` 在 G2 报 `BadZipFile`** ⇒ 采用末段带 `.tar.gz` 的 V-d | **本棒新增，审计建议的形态不可直接用** |
| 取源探针的 UA | 未记 | 自加浏览器 UA ⇒ `403 + text/html 5929B`（`uatrap.bin`）；默认 curl UA ⇒ 200/2823B | 本棒新增 |

## 6. 反例读数（判"可取"为什么不能只看 HTTP 码）

```sh
curl -sS -o ca.bin -D ca.hdr -w 'code=%{http_code} type=%{content_type} dl=%{size_download}\n' <URL>
```

| URL | 读数 |
|---|---|
| `https://www.mirbsd.de/` | `200` / `text/html; charset=utf-8` / **28339 字节** / sha256 `0bea0fc36a7d277ad53839bb4a0ba372816366826f6782d94d41b5477de2233f` |
| `https://www.mirbsd.de/MirOS/dist/mir/rifiuti/rifiuti_20040505_1.tar.gz`（虚构深路径） | **同样 `200` / `text/html` / 28339 字节 / 同一 sha256** ⇒ catch-all 首页，不是发布物 |
| `https://www.foundstone.com/` | `curl: (28) Failed to connect … port 443 after 15002 ms: Timeout` ⇒ `code=000` |
| 页面式 `/download` + 浏览器 User-Agent | `403` / `text/html; charset=UTF-8` / 5929 字节 / sha256 `470feadd89e633c0…` ⇒ 反爬拦截，与"发布物不存在"无关 |

⇒ 判定口径：**状态码 + `Content-Type` + 字节数 + sha256 四项同时核**，缺一项就可能把 catch-all 首页或反爬页当成发布物。

## 7. 落点（本件支撑的三处改动）

- `archives/r/rifiuti/20040505/conandata.yml:20`（url）/ `:21`（sha256）/ `:3-18`（取源叙述与陷阱注释）
- `archives/r/rifiuti/20040505/manifest.yaml:19`（url）/ `:20`（sha256）
- `archives/r/rifiuti/20040505/notes.md` §一（取源叙述换官方直链口径 + 形态失败现场）与 §七 7.3 / §十 10.4（本轮门禁读数）
