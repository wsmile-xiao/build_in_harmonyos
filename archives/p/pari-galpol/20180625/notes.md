# pari-galpol 20180625 适配笔记

## 编译环境
- 构建系统: custom（**纯数据包，无任何构建系统**）
- 编译日期: 2026-09-06
- 编译器: N/A（无编译单元；profile 仍为 ohos-aarch64 / clang 15 / os=OHOS / armv8）
- 状态: built（conan-verify 全绿，未 upload）

## 这个包是什么
GALPOL 数据库 v4.0（发布日 2018-06-25 → conan 版本 `20180625`）：定义有理数伽罗华
扩张的多项式，覆盖阶 ≤ 143 的全部 3657 个抽象群、7194 个多项式，供 PARI/GP 的
`galoisgetpol` 读取。群编号按 GAP4 SmallGroups 库——**这是数据归属声明，不是依赖**。

## 版本与来源（R39 官方源，三方同一性实测）
| 分发形态 | URL | size | sha256 |
|---|---|---|---|
| 官方包目录 | `pub/pari/packages/galpol.tgz` | 10049371 | `562af283…16bb01b` |
| 上游 release | `galpol/releases/galpol-4.0.tar.gz` | 10049371 | 同上（逐字节一致） |
| Debian orig | `pari-galpol_4.0-2.dsc` Checksums-Sha256 | 10049371 | 同上 |

`galpol.tgz` FTP `Last-Modified: Mon, 25 Jun 2018 13:28:32 GMT`；Debian changelog
`pari-galpol (4.0-1) -- Mon, 25 Jun 2018 16:35:10` → 版本日期口径成立，
与同族 `pari-seadata/20090618` 一致。选 first-party URL，避开 PF7 Debian 重打包黑名单。

## 依赖结论（W0 前置，全新 conan 缓存实测，未用本地缓存/`--build=missing` 绕过）
- Debian `pari-galpol 4.0-2` control：`Build-Depends: debhelper-compat (= 13)`、
  `Architecture: all`、`Depends: ${misc:Depends}`（解析为空）、`Suggests: pari-gp`。
  → **无任何强制第三方库依赖**；`requires` 留空，R36 发布顺序不适用。
- 构建期工具 debhelper/make/gzip 属 Debian 打包侧，conan 配方用 `copy()` 直接落数据，
  不引入（保留上游未压缩文件，PARI 可直读）。
- 运行期消费者（软依赖，不进 requires）：`pari/2.17.4` 已在制品仓
  （`CONAN_HOME=<全新目录> conan download pari/2.17.4 -r=ohpcd --only-recipe` → rc=0，
  revision `b933064a7db703148fe548d36d0c0cb9`）；其自身闭包
  `gmp/6.3.0.1`、`readline/8.3`(→`ncurses/6.6`)、`ncurses/6.6` 同法均 rc=0。
- `gap/4.16.0` 在仓但**不需要**（见上，GAP4 仅数据归属）。

## 构建/测试入口核验（R51 三步法：清点 → 实跑 → 如实回填）
**包内清点（实证无自动化测试）**：官方 tarball 18483 条目全在 `data/galpol/` 下；
`Makefile|configure|CMakeLists.txt|setup.py|meson.build` 计数 **0**，
`.c|.h|.cpp|.gp|.py|.sh|test` 计数 **0**；文件仅 7 类：
3657 `real` + 3537 `complex` + 3657 `group` + 3657 `name` + 143 `nb` + 29 `non-wss`
+ 1 `README` = 14681，全部 ASCII，无任何扩展名。
Debian `debian/rules`：`build-stamp: touch build-stamp`（不编译）、install 仅
`dh_install galpol /usr/share/pari` + 对 real/complex/group `gzip`，**无 check/test 目标**；
`debian/` 文件清单里**没有 `debian/tests/`**（无 autopkgtest）。

**真实功能入口（本阶段实际执行）**：数据包的功能入口天然在消费方 gp 的 `galoisgetpol`。
用制品仓已发布的 `pari/2.17.4` 二进制（含 `bin/gp-2.17`，`conan install
--requires=pari/2.17.4 -r=ohpcd -pr:h=ci/conan/profiles/ohos-aarch64` → rc=0）执行：

- 生成器：`upstream-gp-sweep-generator.py`（枚举被测目录，用例集不硬编码）
- 打包产物运行：`upstream-test-cases.txt` → **7337 用例 / PASS 7337 / FAIL 0 / 跳过 0**，2.4s，rc=0
- 上游原始目录交叉验证：`本地 reports/upstream-gp-sweep-upstreamdir.log` → 7337 / 7337 / 0，rc=0
- 反向对照：`本地 reports/upstream-gp-sweep-negative-control.log` → datadir 指向空目录时
  gp 报 `galoisgetpol: error opening galpol file: '<datadir>/galpol/8/nb'`，
  证明上述 PASS 由本包数据驱动（gp 内建并不含这些数据）。

**逐用例证据随 PR 入仓 + 可复算钉定**：7337 条 `用例名|PASS` 原样记录写在版本目录
`upstream-test-cases.txt`（213538 字节，随 PR 入仓）；用例名清单（升序、每行一个）
`sha256 = d02fab1954b2c24f788d7acb0bd14661485e6003d3e1627cc2e750d31e16f534`（与正文复算一致）；
分族数量与字典序首/末名见 `test_package/MANIFEST.yml` 的 `case_families`。
任何人用同目录的 `upstream-gp-sweep-generator.py` + 制品仓 pari/2.17.4 的 gp 即可重跑复现。

用例构成（每项都有独立名字，逐行 PASS/FAIL 记录在日志中）：

| 用例族 | 数量 | 断言内容 |
|---|---|---|
| `nb_count_<n>` | 143 | `readvec(<n>/nb)[1]` == 该阶下组目录数（索引自洽） |
| `roundtrip_real_<n>_<k>` | 3657 | `galoisgetpol(n,k,1) == read(<n>/<k>/real)` 且 `poldegree == n` |
| `roundtrip_complex_<n>_<k>` | 3537 | `galoisgetpol(n,k,2) == read(<n>/<k>/complex)` 且 `poldegree == n` |

**test_package 不替代上游统计**：它是 32 项字节级打包校验（见下），两侧数字分别申报。

## 基线指纹（官方源解包后按相对路径排序计算，test_package 断言基线）
- 条目 14681（含 README），数据字节 **28536355**（不含 README）
- 全部数据文件拼接 sha256：`08b4b31de8b040afe347f4af544d54216687ad4319140aabe7ed7aa2dbc8e52c`
- 分类拼接 sha256：real `f413d185…15129d`、complex `b6c9b12c…afef0e`、
  group `dc6cc331…3a0850`、name `6887e216…68b6fb`、nb `b819e599…b7b63e`、
  non-wss `e3b0c442…52b855`（29 个 0 字节标记）
- README `bd749aad…ac8e1a`；抽查 `8/1/real 3e33b762…572e047`、`143/nb 4355a46b…0dd865` 等 8 个
- 上游 tarball sha256：`562af28316ee335ee38c1172c2d5ecccb79f55c368fb9f2c6f40fc0f416bb01b`

## 打包决策
- `build()` 空操作（无代码可编，`apply_conandata_patches` 在无 patches 段时安全空转）。
- `package()`：`copy("*")` 把 `galpol/` 落到 `<pkg>/res/pari/galpol/`，与 Debian
  `dh_install galpol /usr/share/pari` 同位；**保留未压缩**（PARI 可直读，不为 gzip 引构建工具）。
- `package_type="application"` + 软件级 `commands.json`（`binary:false`）：与已入库
  `pari-seadata`/`ca-certificates` 同型，确保 conan create 真跑 `package()`（实测
  `package(): Packaged 14681 files`）。
- `package_id()` → `self.info.clear()`：28MB 数据与 arch/compiler/build_type 无关，
  单一 package_id（实测 `da39a3ee5e6b4b0d3255bfef95601890afd80709`），避免按 profile 重复存储。
- `package_info()`：`libs=[]`、`resdirs=["res"]`、`set_property("pari:galpol_rel",
  "res/pari/galpol")`（不用 1.x `user_info`）。**下游接线口径**：把 gp 的
  `default(datadir,…)` 指到 `<pkg>/res/pari` 即命中 `<datadir>/galpol/<order>/nb`。
- 0 补丁、0 平台宏（R8：无 patches/，conanfile 无 `-D__OHOS__`）；R32 用
  `os in ("Linux","OHOS")`；R49 不注入任何共享前缀（数据落包内 res/）；
  R40 不适用（非图形/UI/多媒体/底层类深度适配库）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan download … -r=ohpcd` 报 `ERROR: error:system acceleration policy not enabled.` rc=1 | cnb.cool 制品仓对**该 ref 不存在**的返回形态（对照：在仓的 pari/2.17.4、gap/4.16.0 均 rc=0；不在仓的 pari/2.17.3 同错） | 按 R35 用 `conan download` 判存在性，并用公开 API `probe_registry` 交叉标定错误语义，避免把"未发布"误读成网络故障 |
| 2 | `ohc-run.py lang-preflight` 默认口径 exit 2 → 自动写 `env_unsupported` 终态 | 本包无任何源文件可统计（`detected_language=other`、`build_system=none`），而任务语言默认 `cpp` | 按协议 §4.6 用合法枚举 `--lang other` 重跑（数据包如实声明，非"硬着头皮适配"：无任何 C/C++ 代码可编），rc=0；同时如实保留默认口径的 exit 2 证据 |
| 3 | `conan install --requires=pari/2.17.4` rc=6：`Invalid: 'settings.os.version' value not defined` | `conan profile detect` 生成的默认 profile 无 `os.version`，而 pari 配方 settings 含它 | 改用仓库 CI profile `ci/conan/profiles/ohos-aarch64`（`os.version=6.0`）→ rc=0，成功取到 `gp-2.17` |
| 4 | `gp-2.17: Error loading shared library libgmp.so.10` + 一串 `__gmpn_*` 未定义符号 | 只设了 pari 自身 lib 目录，未把**已部署的 gmp** lib 目录放进 `LD_LIBRARY_PATH` | `--deployer=full_deploy` 后同时导出 pari 与 gmp 两个 `Release/armv8/lib` → 版本横幅正常打印（2.17.4 / aarch64/GMP-6.3.0） |
| 5 | GP 脚本满屏 `not a function in function call`、`syntax error, unexpected ')'` | GP **不做** C 式相邻字符串字面量拼接（必须 `Str()`）；且 `for(…)` 体内多语句后不能写 `);` | 全部改 `Str()` 拼接、函数体用 `{}` 包裹、去掉多余 `;` |
| 6 | 自枚举驱动 `rchk` 报"不是函数"，整轮 0 用例却 rc=0（静默空跑） | 两个叠加原因：① `\\` 注释里有**行尾反斜杠**（命令示例续行符），GP 词法按续行合并注释，把后面的函数定义吃掉；② 该 gp 构建**没有** `file_exists`/`is_file`/`is_dir`/`wildcards` 文件探测原语，自枚举无从判存在性 | ①注释内禁用行尾 `\`（已在驱动脚本注释里写明此坑）；②改为 Python 生成器枚举被测目录 + 生成 straight-line GP 断言（`upstream-gp-sweep-generator.py`），gp 侧只做真实读取与比较 |
| 7 | 生成器首跑 36685 行 `read/readvec: error opening input file`，全用 baked-in 路径 | 生成脚本没写 `default(datadir,…)`，而这次也没在命令行传 `--default` → `dd` 取到 gp 编译期内置的 datadir | 生成器改为把 `default(datadir,"<root>")` 写进产物第 1 行（消除命令行脚枪），重跑 7337/7337 rc=0 |
| 8 | `init-build` 提示 `conanfile.py 模板不可用（autotools）` | 树内无任何构建文件，构建系统探测落到 autotools 默认值，模板选择随之落空 | 按 v12.21 无构建/打包族（`conanfile-headeronly.py.tmpl` 变体 B：数据资源）手写配方，conan create 实测通过 |

## 发现与知识

✅ GP 批处理脚本的注释行**不能以反斜杠结尾**：GP 词法把行尾 `\` 当续行，会让 `\\` 注释跨行合并、把紧随其后的用户函数定义吞进注释；症状是 `not a function in function call`，而批处理仍返回 rc=0 —— 测试静默退化为 0 用例（假绿）。已提草稿 `knowledge/drafts/E429-draft-5A6B.kv`。

✅ 制品仓发布的 `pari/2.17.4` 的 `gp` **没有 OS 文件层原语**：`file_exists`/`is_file`/`is_dir`/`wildcards` 均报 `not a function in function call`（`extern` 可用）。因此"自枚举被测目录"必须交给外部脚本（本包用 `upstream-gp-sweep-generator.py` 枚举 → 生成 straight-line 断言 .gp），gp 侧只做真实读取与比较。

✅ 任何"解释器 + 只看退出码"的测试驱动都必须断言**用例数 == 预期数**：本包三次假绿/半假绿（0 用例 rc=0、36685 行报错但 SUMMARY=0）都是靠对账用例数发现的。

✅ cnb.cool 制品仓对**不存在的 ref** 的返回形态是 `ERROR: error:system acceleration policy not enabled.` rc=1（不是 "Recipe not found"）；用同法对在仓的 `pari/2.17.4`、`gap/4.16.0` 得 rc=0、对不在仓的 `pari/2.17.3` 得同错，可据此标定 R35 探测语义，避免把"未发布"误判成网络故障。

✅ `lang-preflight` 默认口径对**纯数据包**必然 exit 2 并自动落 `env_unsupported` 终态（无任何源文件 → `detected_language=other`）。数据包适配须显式 `--lang other`（合法枚举值如实声明）；建议 SKILL 侧对 v12.21 的"无构建/打包族"给出显式语言口径。

✅ GP 不做 C 式相邻字符串字面量拼接：`print("a" x)` 直接语法崩，必须 `Str()`；`for()` 体内多语句以 `);` 收尾会报 `unexpected ')'`。写测试驱动前先按 GP 语法而不是 shell 语法来。

✅ PARI 数据包的功能入口都在消费方：galpol→`galoisgetpol`（本包）、`galdata`→`polgalois`（8–11 阶，另一包）。用 `polgalois` 测 galpol 会得到误导性的 `error opening galois file: '<datadir>/galdata/…'`。

✅ `conan profile detect` 生成的 profile 无 `os.version`，而 pari/gmp 等配方 settings 含它 → `conan install` rc=6 `Invalid: 'settings.os.version' value not defined`；一律改用仓库 CI profile `ci/conan/profiles/ohos-aarch64`。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify pari-galpol 20180625     # rc=0
G1 PASS / G0 跳过(构建系统 unknown) / G2 conan create PASS / G3 PASS(无系统同名库冲突)
G4/L2/L4/L5: 无 ELF 产物 → 跳过（数据包，符合预期）
$ grep "Packaged" 本地 reports/conan-create.log
pari-galpol/20180625@ohpcd/stable: package(): Packaged 14681 files
$ grep SUMMARY 本地 reports/conan-create.log                            # test_package 随 create 执行
SUMMARY checks=32 pass=32 fail=0 files=14681 bytes=28536355
$ tail -1 upstream-test-cases.txt                   # 上游功能入口实跑
SUMMARY pass=7337 fail=0 total=7337
```

## 交付物

**入 PR 的文件（`git status -uall` 实测 10 个）**：
`archives/p/pari-galpol/{manifest.yaml,README.md,commands.json}` +
`20180625/{conanfile.py,conandata.yml,manifest.yaml,notes.md}` +
`20180625/test_package/{conanfile.py,test_verify.py,MANIFEST.yml}`。
另有 `knowledge/drafts/E429-draft-5A6B.{kv,md}` 随 PR（R16 草稿形态）。
下表 `reports/`、`packaging/` 与 `.` 点开头的运行时标记均被仓库 `.gitignore` 排除
（`reports/`、`packaging/`、`.ci-result.json`、`.staging-verified` 等），是**本地留档**，
不入 PR——因此上游测试的统计与命令都在本笔记与 `test_package/MANIFEST.yml` 内自证。

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 数据配方（application / package_id cleared / resdirs） |
| `conandata.yml` | 官方源 URL + sha256 + 三方同一性证明 |
| `test_package/conanfile.py` | R34 实质校验：`self.run` 跑打包内容校验 |
| `test_package/test_verify.py` | 32 项检查（计数/nb 自洽/总字节/整体+分类+抽查 sha256/GP 语法/无 gzip 混入） |
| `test_package/MANIFEST.yml` | 上游测试申报（包内 0 + 消费方入口 7337 + test_package 32） |
| `upstream-gp-sweep-generator.py` | 上游功能测试用例生成器（枚举被测目录，随 PR 入仓） |
| `upstream-test-cases.txt` | 7337 行逐用例名 + PASS/FAIL 原始记录（随 PR 入仓） |
| `本地 reports/*.log`（conan-create / w3-local-ci / upstreamdir 交叉验证 / negative-control / staging-verify） | 运行日志，`.gitignore` 排除不入 PR |
| `本地 reports/conan-create.log`、`本地 reports/conan-verify-report.md` | 真实构建与门禁日志 |
| `../{manifest.yaml,README.md,commands.json}` | 软件级元数据（数据包无二进制） |

## 注意事项
- **不要 `make install`/`dh_install` 式地把数据装进共享 `/usr/local/share/pari`**：
  由下游按 conan 包目录拼 `res/pari` 传给 gp 的 `datadir`（R49 同口径，避免污染共享前缀）。
- `polgalois()` 对 8~11 阶另需**独立**数据包 `galdata`（实测报
  `error opening galois file: '<datadir>/galdata/COS8_50_47'`），那是另一个包的范围，
  不要拿它当 galpol 的测试。`galoisgetpol` 才是本包的功能入口。
- GP 2.17 已无 `galoisgetpolnumber`/`galoisgetpolname`（实测 `not a function`），
  别照旧文档写断言；`galoisgetpol(n,k,1)`→real、`(n,k,2)`→complex、`flag=0` 非法。
- 包内数据未压缩（28MB / 14681 小文件）：Debian 会 gzip `real/complex/group`，
  我们保持原样以免引入构建期工具；若下游在意体积，应在消费侧处理。
- 语言预检：本包 `detected_language=other`（纯数据）。若按默认 `cpp` 口径跑
  `lang-preflight` 会 exit 2 并自动落 `env_unsupported` 终态——数据包适配须显式
  `--lang other`（建议 SKILL 侧对"无构建/打包族"给出显式口径，避免误判）。
---

**编译结束**: 2026-09-07 14:21
**最终状态**: built
