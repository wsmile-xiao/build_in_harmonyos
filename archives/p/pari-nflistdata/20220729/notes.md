# pari-nflistdata 20220729 适配笔记

## 编译环境

- 构建系统: data（纯数据包，无编译）
- 构建日期: 2026-09-10
- 编译器: 无（数据包；lang-preflight 如实声明 `--lang other`）
- 宿主/交叉: OHOS aarch64 profile `ci/conan/profiles/ohos-aarch64`（os.version=6.0，clang 15）
- 状态: built（conan create rc=0，见「本地验证结果」）

## 这个包是什么

PARI/GP 的 nflist 数据库（上游 2022-07-29 发布）。官方包页原文：

> nflistdata.tgz (3.5 MB), Jul 29 2022 — Needed by nflist to list fields of small
> discriminant (currently needed by the single Galois groups A5 and A5(6)) or to
> list regular extensions of Q(T) in degree 7 to 15. **Require PARI/GP 2.14.0.**

上游 tarball 解出 `data/nflistdata/`，678 个非目录条目 / 8845045 字节：

| 类别 | 数量 | 说明 |
|------|------|------|
| `<degree>/<index>/QT` | 650 | Q(T) 上正则扩张的通用多项式，单行 GP list 字面量；度 2..15（12 度 301 个最多） |
| `5/4/0/{0..5}` | 6 | Jones–Roberts A5 表，r2=0，末片以哨兵 `[0,0]` 收尾（末条 524286） |
| `5/4/0cond/{0..9}` | 10 | Allombert–Page 表，r2=0，按 conductor 排序 |
| `5/4/2/0` | 1 | Jones–Roberts A5 表，r2=2（末条 10000，尾随 `[0,0]`） |
| `5/4/2cond/{0..9}` | 10 | Allombert–Page 表，r2=2 |
| `README` | 1 | 上游发布说明（含完备性边界与 GPL-2+ 声明） |

数据归属方（Jones/Roberts、Allombert/Page、Klüners/Malle、Dokchitser）是**来源声明**，
不是依赖。

## 依赖结论（W0 实测）

| 依赖 | 类型 | 结论 | 证据 |
|------|------|------|------|
| — | conan requires | **无**（`requirements()` 为空，与同族 pari-galdata/galpol/seadata 一致） | 上游无任何代码可编译；见下方入口清点 |
| Debian 运行期 | Depends | `${misc:Depends}`（解析为空） | `debian/control`：`Depends: ${misc:Depends}`、`Architecture: all`、`Multi-Arch: foreign` |
| pari-gp | Suggests（可选消费者） | 可消费：`pari/2.17.4.1` | `conan download pari/2.17.4.1 -r=ohpcd` rc=0；`conan install --requires=pari/2.17.4.1 -pr=ci/conan/profiles/ohos-aarch64 --build=never -d full_deploy` rc=0，取到 `bin/gp` + `libpari-gmp-tls.so.2.17.4`，package_id `4ab680a0ff306109f25f77cd4315ce7f1f9e5db0` |
| debhelper-compat (= 13) | Debian 构建期 | 不适用（conan 路线不跑 dpkg-buildpackage） | `debian/rules` 只用 dh_* 宏 |
| gzip | Debian install 期 | 不沿用（保留未压缩表，PARI 直读） | `debian/rules` 的 `-execdir gzip --no-name --best` |
| python3 | 校验器宿主 | 本机 3.12.9 rc=0 | test_package 与验证器用 `sys.executable` |

R36 前置：本包 `requires()` 为空，**不存在依赖绕过问题**；测试宿主 pari/2.17.4.1
由制品仓下载得到，未使用 `--build=missing`，未用本地缓存冒充。

## 构建/测试入口核验（清点命令与原始输出）

```
$ curl -sS -I https://pari.math.u-bordeaux.fr/pub/pari/packages/nflistdata.tgz
  HTTP/1.1 200 OK / Last-Modified: Fri, 29 Jul 2022 11:34:07 GMT
  Content-Length: 3623252 / Content-Type: application/x-gzip
$ sha256sum nflistdata.tgz
  2c19a3e02afd3bba2af3071a7faa80924a75b00bb9713286c886b7fb460944bc
  ≡ 官方 packages.html 的 pin ≡ Debian 0.20220729-2.dsc 的 Checksums-Sha256（三值一致）

$ tar tzf nflistdata.tgz | grep -vE '/$' | wc -l
  678
$ tar tzf nflistdata.tgz | grep -icE "makefile|configure|cmakelists|\.c$|\.h$|\.py$|\.gp$|\.sh$"
  0                       ← 无构建文件、无源码、无脚本
$ grep -icE '(^|/)(Makefile|configure|CMakeLists.txt|setup.py|meson.build)$'   # 同口径
  0
$ dpkg-deb 侧（debian.tar.xz，sha256 c90498568ce86f4d…3490 与 dsc 一致）
  debian/ 文件清单: changelog control copyright dirs rules source/format upstream/signing-key.asc
                    ↑ 无 debian/tests/（无 autopkgtest）
  debian/rules  : build 目标只有 `dh_testdir; touch build-stamp`；install 只有
                  `dh_install nflistdata /usr/share/pari` + 大文件 gzip；**无 check/test 目标**
```

**真实功能入口**（本阶段实际执行，非引用）在消费方 gp：`nflist`。libpari 内实证
（`strings` 已发布的 `pari/2.17.4.1` 二进制）：

```
%s/nflistdata/%ld/%ld/QT          ← QT 正则扩张表寻址模板
%s/nflistdata/%ld/%ld/%ld%s/%ld   ← A5 分片寻址模板（"cond" 为该模板的 %s）
cond                              ← AP 表路径字面量
nflist / nflistQT / nflist_CL_worker(Fcond,bnf,ellprec): auxiliary.
datadir = "%s"                    ← gp 的 datadir 默认项
```

### 上游数据语义实证（本次实跑得出，非文档转述）

- `nflist([deg,idx],'t)` 返回 **t_POL**（不是向量）：`poldegree == deg`、`variable == x`。
- A5 表每行 `[[系数…],B]` 的 **B 是 sqrt(|disc|)**：表首行 `[[9,18,-5,-11,0,1],1762]`
  可被 `nflist("A5", 1762^2, 0)` 精确检索，返回
  `x^5 - 11*x^3 - 5*x^2 + 18*x + 9`（与表内系数逐项一致）。
- gp 对 r2=0 全表返回 **15184**，恰为 `5/4/0/{0..5}` 的 15185 行减去末片哨兵 `[0,0]`；
  r2=2 返回 **2336**，恰为 `5/4/2/0` 的 2337 行减哨兵。**表与函数返回值自洽**。
- 哨兵 `[0,0]` 只出现在两个 JR 表末片（`5/4/0/5`、`5/4/2/0`），末条边界值 524286 / 10000
  正是上游 README 声明的完备性上限（`disc ≤ 524286^2`、`disc ≤ 10^8`）；
  20 个 `*cond*` 表均无哨兵。
- `nflist("A5", [1,10^11])`（省略 s）报 `domain error in nflist(A5): sqrt(N) > 10000`；
  5 次域查询 s=1 返回空（度 5 无 r2=1 签名）。
- 群标识必须写名字或 `[n,k]` 向量：`nflist("8T1",'t)` 报 `unsupported group (8T1)`。

## 打包决策

沿用同族已合并的 **pari-galpol/20180625** 纯数据包范式（W0b：逐项比对遵循）：

- `package_type = "application"` + 软件级 `commands.json`（`binary: false`），
  确保 conan create 真正执行 `package()`，产物 `res/` 由 test_package 实质覆盖；
- `settings` 四项全声明（L0p 门禁）+ `package_id(): self.info.clear()` → noarch
  （否则 8.8 MB 数据按 profile 组合重复存储）；
- `build()` 跑 test_package 的同一验证器（`--source-root`），损坏下载在 create 中途即失败；
  用 `sys.executable` 而非裸 `python3`（R33：不依赖 shell 环境变量）；
- `package()`：`copy(self, "*", src=<src>/nflistdata, dst=<pkg>/res/pari/nflistdata)`
  —— **必须保留层级**（gp 按 `<datadir>/nflistdata/<deg>/<idx>/QT` 直接寻址）；
  这一点与扁平安装的 pari-galdata（`keep_path=False`）不同，是本包的关键差异；
- 许可证：上游 tarball 无独立 COPYING，但 `README` 内含 GPL-2+ 全文声明，
  随数据一并安装（不另造 licenses/COPYING，与 galpol 一致）；
- `package_info()`：`libs/includedirs/libdirs/bindirs` 全空、`resdirs=["res"]`、
  `set_property("pari:nflistdata_rel", "res/pari/nflistdata")`；下游把 gp 的
  `default(datadir,…)` 指到 `<pkg>/res/pari` 即命中（R49 同口径，不注入共享前缀）。

## OHOS 平台适配

纯数据包，**无需平台补丁、无 `__OHOS__` 宏、不改任何上游字节**（R8/R6 天然满足）：

- 平台适配点只有两处：① `validate()` 用 `in ("Linux","OHOS")`（R32）；
  ② 数据落 `res/`（OHOS 资源目录惯例）而非 Debian 的 `/usr/share/pari`，避免污染共享前缀（R49）；
- "打包零改动"有实证：同一 driver 分别对**上游原始解包目录**与**打包产物**跑
  685 项断言，逐用例 diff 为空（见「本地验证结果」）。

## 遇到的问题与解决方案

| # | 首个错误（原始输出） | 根因 | 修复 | 复验结果 |
|---|---------------------|------|------|---------|
| 1 | `lang-preflight` 默认口径 `exit_code=2`，自动落 `status=env_unsupported`、`detected_language=other`、`language_evidence.build_system=none` | 纯数据包无可统计源文件，而任务语言默认 `cpp` | 按协议 §4.6 用合法枚举 `--lang other` 重跑（同族 pari-galpol 问题#2 / pari-seadate-big 同口径），并如实保留默认口径证据 | `语言匹配: task=other, detected=other`，rc=0 |
| 2 | 验证器首跑 `FAIL concat_sha256_ALL got e3b0c44298fc1c14…b855`（空输入摘要） | `class_of()` 永不返回 `"ALL"`，循环取 `by_class["ALL"]` 得空集 | ALL 分类改为对**全部文件**拼接（`files if cls == "ALL"`） | 81/81 PASS，rc=0 |
| 3 | 验证器首跑 `FAIL a5_table_syntax_all 2 malformed, e.g. ["5/4/0/5:b'[0,0]\\n'", "5/4/2/0:…"]` | 数据本身合规：JR 表末分片以完备性哨兵 `[0,0]` 收尾，我的行正则未容纳 | 行校验容纳哨兵，并把哨兵**升格为断言**（`a5_jr_sentinel_*` 校验末行 `[0,0]` 且倒数第二行为 524286 / 10000；`a5_cond_tables_have_no_sentinel` 校验 20 个 cond 表无哨兵） | 81/81 PASS；哨兵断言真实命中 2 个文件 |
| 4 | 故障注入报 `exit_code=0`（篡改后仍显示 0） | 取了管道末端 `tail` 的退出码，非验证器本体退出码 | 单独执行重定向到文件后取 `$?`（同族 pari-galdata notes 问题#2 已记录该坑，本次遵循其口径） | 篡改 → rc=1（3 项 FAIL）；删除文件 → rc=1（8 项 FAIL）；完好 → rc=0（81/81） |
| 5 | gp 启动即 `Error loading shared library libpari-gmp-tls.so.9` + 上百条 `symbol not found`，`exit_code=127` | 该命令块忘了 `export LD_LIBRARY_PATH`（只设了变量未导出）——与同族 galpol notes 问题#4 同类 | 每次 gp 调用前显式导出 pari/lib 与 gmp/lib 两个目录 | 同一脚本立即 8/8 PASS，gp_rc=0 |
| 6 | 打包产物上 `a5_r2_0_full_table FAIL`、`a5_r2_0_subrange_monotone FAIL`（656/658 —— 该轮是 `--family all` 的 658 条 = 650 QT + 8 语义，不含 27 条归因） | **不是打包差异**：同一 `--family all` 脚本对上游原始解包目录跑，同样 2 FAIL。机制是在同一个 gp 进程内先跑 650 条 `nflist([d,i],'t)` 会污染 nflist 内部 A5 表状态，使 `#nflist("A5",[1,524286^2],0)` 不再等于 15184 | driver 改为 **U1 与 U2 各起一个 gp 进程**（`run-upstream-gp-sweep.py` 分 family 调用并合并统计）；生成器保留 `--family` 以便单独复现 | 打包产物 685 项：665 PASS / 0 FAIL / 20 SKIP，driver rc=0 |
| 7 | 首轮归因 20 个 `*cond*` 分片全部 `SKIP` | pari/2.17.4.1 的 nflist 未把 conductor 表暴露为可构造调用（libpari 里有 `cond` 字面量与 `nflist_CL_worker(Fcond,bnf,ellprec)`，入口需 bnf 级入参）。已尝试把探测集扩到 12 条（含带子域 F 的 `nflist("A5",[1,10^8],-2,x^2-5)` 等 3 种组合），移开 cond 文件后输出指纹逐位不变 | 不谎报覆盖：如实记 20 个 SKIP 并在 MANIFEST 写 `skip_explanation`；cond 表的**内容一致性**由 test_package 的字节级断言保证（分类拼接 sha256 覆盖 `A5_r2_0cond`/`A5_r2_2cond`） | 归因结果稳定复现：7 PASS / 20 SKIP，实验后基线指纹一致（副本未被改名实验破坏） |
| 8 | `nflist("8T1",'t)` 报 `unsupported group (8T1)`；`Polx`/`catch`/`substr` 报 `not a function in function call` | 该 gp 构建无这些原语，群标识只接受名字或 `[n,k]` 向量（同族 galpol notes 问题#6/#11 同类） | 生成器改用 `[deg,idx]` 向量形式；枚举与归因逻辑全放 Python 侧，GP 脚本只做读取与比较 | 650 条 QT 用例零 `***` 错误行 |

## 上游测试三步法申报表（R51，适配前清点）

| 清单项 | 实测值 | 清点命令 |
|--------|--------|-----------|
| `tests/` 目录数（上游 tarball 内） | **0** | `tar tzf nflistdata.tgz \| grep -ciE '(^|/)tests?/'` → 0 |
| ctest 注册数 | **0**（无 CMakeLists.txt，`enable_testing()/add_test()` 均无） | `tar tzf nflistdata.tgz \| grep -c CMakeLists.txt` → 0 |
| pytest 注册数 | **0**（无 `.py` 文件、无 `setup.py/pyproject.toml`） | `tar tzf nflistdata.tgz \| grep -cE '\.py$\|pytest.ini\|tox.ini'` → 0 |
| `make check` 目标 | **0**（无 Makefile/am，Debian rules 无 check/test 目标） | `grep -nE '^(check\|test)' debian-src/debian/rules` → 无匹配 |
| Debian autopkgtest | **无**（`debian/` 下无 `tests/`） | `ls debian-src/debian/` → changelog control copyright dirs rules source format upstream |
| **上游包内自动化测试合计** | **0**（附以上清点证据，符合 R51"确无测试须附证据"） | — |
| 真实功能入口（消费方） | gp 的 `nflist`（上游 README 自述 + 官方页样本命令 `nflist("A5")`） | 见「构建/测试入口核验」 |
| 适配后实际执行 | **685 项**（650 QT + 8 A5 语义 + 27 分文件归因），665 PASS / 0 FAIL / 20 SKIP | `run-upstream-gp-sweep.py`，逐用例 `upstream-test-cases.txt` |

第二步"可运行环境实际运行"已达成（OHOS aarch64 真机 + 制品仓 gp 二进制），未使用"没环境"作为理由；
第三步回填即上表末行与 `test_package/MANIFEST.yml` 的 `consumer_functional_test`，无占位符。

## 上游测试统计（实际执行）

命令（宿主为制品仓 pari/2.17.4.1 的 gp，被测对象为 conan create 的打包产物）：

```
$ conan install --requires=pari/2.17.4.1 -r=ohpcd \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
      --deployer=full_deploy                                    # rc=0
$ python3 run-upstream-gp-sweep.py <pkg>/res/pari \
      --gp  full_deploy/host/pari/2.17.4.1/Release/armv8/bin/gp \
      --lib full_deploy/host/pari/2.17.4.1/Release/armv8/lib \
      --lib full_deploy/host/gmp/6.3.0.1/Release/armv8/lib \
      --out-cases upstream-test-cases.txt                       # rc=0，10s
  TOTAL=685 PASS=665 FAIL=0 SKIP=20
```

| 族 | 用例数 | PASS | FAIL | SKIP | 逐用例日志 |
|----|--------|------|------|------|-----------|
| U1 `qt_<deg>_<idx>` | 650 | 650 | 0 | 0 | `upstream-test-cases.txt` |
| U2 `a5_*`（语义） | 8 | 8 | 0 | 0 | 同上 |
| U3 `a5_read_<path>`（分文件归因） | 27 | 7 | 0 | 20 | 同上 |
| **合计** | **685** | **665** | **0** | **20** | 用例名升序 sha256 `14ca8540e254e1ef3aef18f7859dc2022f13bf316e4a917295f29b56ea9791d8` |

20 个 SKIP 逐项为 `a5_read_5_4_0cond_{0..9}` 与 `a5_read_5_4_2cond_{0..9}`，
根因见问题表 #7（**不是**失败，也不是"没测"：已按 #7 的修复扩大探测调用集复跑一次）。

反向对照（证明 PASS 由本包数据驱动）：

```
同一 650 条 QT 用例、datadir 指向不含任何表的空目录 →
  PASS=52  FAIL=598   （52 条 = 度 2..7 的全部索引 36 条 + 度 8..15 每度末两个索引 16 条，
                       逐条清单见 test_package/MANIFEST.yml 的 builtin_case_list；
                       这些用例在空 datadir 下仍返回满足断言的 t_POL ⇒ 不依赖本包数据）
```
交叉验证：同一 driver 对上游原始解包目录重跑 → `685/665/0/20`，与打包产物
逐用例 diff 为空（⇒ 打包零改动）。

## 本地验证结果

| 步骤 | 命令 | rc | 关键输出 | 日志 |
|------|------|----|---------|------|
| 下载/解包 | `ohc-run.py init-build pari-nflistdata 20220729 --url=…` | 0 | 基线指纹: 678 个文件；errors=0 warnings=3 | 本地 `.ci_logs`/`reports/` |
| 语言预检 | `ohc-run.py lang-preflight … --lang other` | 0 | `语言匹配: task=other, detected=other` | `reports/`（默认口径 exit 2 证据亦留档） |
| conan create | `conan create archives/p/pari-nflistdata/20220729 -pr:h=… -pr:b=…` | 0 | `Packaged 678 files`；build 校验 `TOTAL=81 PASS=81 FAIL=0`；test() `TOTAL=81 PASS=81 FAIL=0`；package_id `da39a3ee5e6b4b0d3255bfef95601890afd80709`（noarch） | `reports/conan-create.log` |
| 上游测试 | 见上表 | 0 | `TOTAL=685 PASS=665 FAIL=0 SKIP=20` | `reports/upstream-test-cases.raw.txt{,.gp-raw.log}` |

## 复现说明

随 PR 入仓的文件足以离线复算全部结论：

| 文件 | 作用 |
|------|------|
| `conanfile.py` / `conandata.yml` | 配方与源 pin（R39 官方 URL + sha256） |
| `test_package/test_pari_nflistdata.py` | 81 项字节/结构/语法断言（`--source-root` 与 `--package-root` 双模式） |
| `upstream-gp-sweep-generator.py` | 由被测目录枚举生成 GP 断言（含 `--cases-from` 供反向对照复用同一用例集） |
| `run-upstream-gp-sweep.py` | 三族上游测试驱动（分进程 + 归因 + 缺失即 FAIL 的核对） |
| `upstream-test-cases.txt` | 685 行逐用例名与结果 |
| `test_package/MANIFEST.yml` | 上游测试申报（含实证命令、断言定义、SKIP 根因、故障注入） |

任何人用制品仓的 `pari/2.17.4.1` gp + 上述脚本即可重跑复现。

## 知识沉淀（W5）

| 条目 | 内容 | 状态 |
|------|------|------|
| `knowledge/drafts/E543-draft-B5C8.kv` / `.md` | gp 单进程内 `nflist` 表状态污染：前序 650 条 `nflist([d,i],'t)` 会改变后续 A5 精确计数断言结果（15184 变小），须按断言族**分进程**执行；判据是上游树与打包产物表现一致 ⇒ 非打包差异 | 草稿（待人工 promote，R30/R31） |
| 复用同族既有结论 | `lang-preflight` 对纯数据包必须 `--lang other`（pari-galpol 问题#2 同口径）；gp 无 `catch`/`file_exists`/`Polx` 等原语（E429 同族记录）；故障注入退出码不得用管道取（pari-galdata 问题#2） | 已在问题表 #1/#8/#4 逐项比对遵循 |
---

**编译结束**: 2026-09-11 17:33
**最终状态**: built
