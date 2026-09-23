# cracklib 2.9.8 — 适配笔记

## 概要

- 上游: https://github.com/cracklib/cracklib (tag v2.9.8, commit d9e8f9f47718539aeba80f90f4e072549926dc9c)
- 构建系统: autotools（官方 release tarball 预生成 configure）
- 类型: 纯 C 库（libcrack.a），零第三方运行时依赖（--without-zlib 关闭可选 gz 支持）
- 版本号: 首次适配，取上游版本 2.9.8

## OHOS 适配要点（沿 2.10.3 已验证经验 W0b 比对）

1. `--build/--host=aarch64-unknown-linux-gnu` 原生构建（build==host，跳过 config.guess 写盘探针）
2. `--without-python --disable-nls --without-zlib` 裁剪 python 绑定、NLS 与可选 zlib
3. 顶层 `make SUBDIRS="lib util"` 裁剪 po/doc/python/dicts
4. TMPDIR 指到 build 目录可写子目录（HMDFS 权限受限）
5. configure 内 `umask 077 → 022`（config.status 的 confXXXXXX/subs*.awk Permission denied 根因，CI #43775）
6. 消费者测试用 `FascistCheck`（其内部 getpwuid 在 OHOS 无 passwd 条目恒失败 → 与缺失字典路径一致，契约断言稳定）
7. 构建期 L1 语义断言必须用 `FascistCheckUser`（CI #43915：FascistCheck 对任何密码返回 "not registered in the password file"）

## 上游测试双口径台账（R03 完整重枚举）

### 源码声明总数 source_declared_total = 14

可复制枚举（官方 tag v2.9.8 源码树 `.oh-ut/scratch/src`）：

1. **util/Makefile.am 第 3 行 `check_PROGRAMS = testlib testnum teststr`** → 3 个 C 独立用例（stdin 交互驱动）
2. **python/test_cracklib.py `class TestModuleFunctions` 11 个 unittest 方法**
   （`grep -c "def test_" python/test_cracklib.py` = 11）：
   test_VeryFascistCheck / test_palindrome / test_same / test_case_change / test_similar /
   test_simple / test_simple_lower / test_simple_upper / test_simple_digit / test_simple_other /
   test_simple_combinations → 11 个独立用例（python 绑定用户用例；
   受 `python/Makefile.am` `if BUILD_PYTHON` 条件宏控制）
3. **顶层 Makefile.am `test:` target** = `util/cracklib-check < test-data`（工具链入口，
   非独立用例，单列不计入独立用例分母）
4. **test-data**（87 字节密码样本输入，`make test` 的输入文件）→ 非独立用例
5. **dicts/**（词表数据源 cracklib-small，54763 词；任务正文称 words/，2.9.8 实际目录为
   dicts/）→ 非测试分类
6. **po/**（翻译目录）→ 非测试分类

| 入口 | 类型 | 驱动方式 | 独立用例? | 互斥分支/条件 |
|---|---|---|---|---|
| util/testlib.c | check_PROGRAM | stdin 逐行输入密码 → FascistCheck | 是（交互驱动） | 无 |
| util/testnum.c | check_PROGRAM | stdin 输入词编号 → GetPW | 是（交互驱动，PWOpen(NULL)） | 无 |
| util/teststr.c | check_PROGRAM | stdin 输入词 → FindPW | 是（交互驱动，PWOpen(NULL)） | 无 |
| python/test_cracklib.py 11 方法 | unittest | python3 unittest 驱动 | 是 | `if BUILD_PYTHON`（配方 `--without-python` 默认裁剪） |
| `make test`（cracklib-check < test-data） | 工具链入口 | shell | 否（工具验证入口） | 依赖已建字典 |
| test-data | 输入文件 | — | 否 | — |
| dicts/（cracklib-small） | 词表数据源 | — | 否 | — |
| po/ | 翻译 | — | 否 | — |

### 配置可执行数 configured_executable_total = 14

- util 3 个 check_PROGRAM：`make testlib testnum teststr -C util` 全部编译链接成功（R02 保留）
- python 11 个 unittest：R03 最小纳入尝试成功——启用 BUILD_PYTHON 构建 _cracklib 绑定，
  python3 3.12.9 可导入并实例化 11 个用例（详见下文恢复条件）

### 实测执行与结果（R03 返工后：14/14 全部真实运行）

| 入口 | 运行命令 | cwd | 退出码 | 结果 |
|---|---|---|---|---|
| testnum | `printf '0\n1\n5\n100\n25000\n' \| ./testnum`（字典以字面 `(null)` 前缀安装于 cwd） | .oh-ut/run-null | 0 | 真实词条：`(word 0) '007bond'`、`(word 100) 'aback'`、`(word 25000) 'ibxnsm'`，语义正确（R02 证据） |
| teststr | `printf 'abc\nadoration\nbawled\nzznotaword\nXk9#mQ2$vL8p\n' \| ./teststr` | .oh-ut/run-null | 0 | 典内命中 `adoration: 999`、`bawled: 4999`；非词 `zznotaword: **** NOT FOUND ****`，语义正确（R02 证据） |
| testlib | `LD_PRELOAD=.../libpwuid_shim.so printf 'abc\nadoration\nbawled\n007bond\nXk9#mQ2$vL8p\n' \| ./testlib` | .oh-ut/run-null | 0 | `abc: WAY too short`、典内词拒绝、强密码 ok，语义正确（R02 证据） |
| python 11 unittest | `LD_PRELOAD=.../libpwuid_shim.so python3 -c "unittest.TestCase.assertEquals=unittest.TestCase.assertEqual; import test_cracklib; test_cracklib.run(verbosity=2)"`（PYTHONPATH=.../python） | .oh-ut/scratch/src | 0 | **Ran 11 tests, OK（failures=0 errors=0 skipped=0）**（R03 实测） |

证据日志（绝对路径 + SHA-256，均在任务 worktree .oh-ut/evidence/）：
- `./testnum.log` sha256=5281bd1829cc77bf5375e28dac26a6b2e54590b9b3491c98ce841b3879351aef
- `./teststr.log` sha256=1d6885ffa01a4bb22d16491f2c0efaa6afb53899914c86fd6fa3e882d15a761b
- `./testlib.log` sha256=f5d2c6b385431e869041015cbca914089a3dcc744cc798894ca92ed075b94943
- `passwd-writability.log`（/etc/passwd 只读证据）sha256=e82f978fb02957bfe930c41804e58011f835ff34776e9a5b57fdaf0ce744941e
- `gates/py-configure2.log`（BUILD_PYTHON 启用 configure，python3.12/Python.h=yes）
- `gates/py-unittest-shim.log`（python 11/11 unittest 实测日志）

恢复条件实测（R02/R03，全部已解决）：
- testnum/teststr 的 `PWOpen(NULL)`：packlib.c 用 snprintf("%s.pwd", NULL) 把空前缀
  格式化为字面 `(null)` 相对路径（musl 行为）→ 把 cracklib-packer 建好的真实字典以字面
  `(null)` 前缀装入运行 cwd（`.oh-ut/run-null/(null).pwd/.pwi/.hwm`）即成功；无需特权路径。
- testlib 的 `FascistCheck(NULL)`：用 `--with-default-dict=<testdict>` 重建 scratch 库后
  字典装载成功；其内部 `getpwuid(getuid())` 需当前 uid 的 passwd 条目——设备 /etc/passwd
  只读（追加实测 "Read-only file system"，见 passwd-writability.log），以 LD_PRELOAD
  getpwuid shim（nss_wrapper 同方式，等效 nss 来源）按进程 uid 提供条目后语义全部正确。
- python unittest（R03 新增）：①AM_PATH_PYTHON 用 `sys.version[:3]` 截断得 "3.1" 导致
  `python3.1/Python.h` 探测失败 → configure 以缓存变量 `am_cv_python_version=3.12` 覆盖后
  `python3.12/Python.h` 探测 yes，BUILD_PYTHON 生效；②配方 `--disable-shared` 只产
  `_cracklib.a`，python import 需共享模块 → 补建
  `clang -shared -fPIC -o python/_cracklib.so python/_cracklib.o lib/.libs/libcrack.a -lpython3.12`；
  ③上游 2.9.8 测试用 `assertEquals`（Python 3.12 已移除）→ 运行时注入
  `unittest.TestCase.assertEquals = unittest.TestCase.assertEqual` 兼容 shim（不改上游文件）；
  ④FascistCheck 内部 getpwuid 同 testlib，LD_PRELOAD getpwuid shim 覆盖。
  设备 python3 3.12.9 + Python.h + libpython3.12.so 均已实测存在。

### 等效覆盖（配方 build() 内 L1，实测 PASS，另列不计入上游通过数）

用上游 cracklib-packer 把 dicts/cracklib-small（54763 词）打成 testdict，
`FascistCheckUser` 4 条语义断言：典内词 adoration 拒绝（dictionary word）/ 典内词 bawled 拒绝 /
过短 abc 拒绝（WAY too short）/ 强密码 Xk9#mQ2$vL8p 通过。实测 `PASS test_cracklib_build`。
另 test_package 消费者测试（FascistCheck 到达字典路径契约断言）实测 `PASS test_cracklib`。

### 通过率（R03 返工后双口径，消除少报）

- 源码声明总数 source_declared_total = **14**（util 3 个 C check_PROGRAMS +
  python/test_cracklib.py 11 个 unittest 方法）
- 当前配置可执行数 configured_executable_total = 14（3 个 C 编译链接成功 +
  11 个 python unittest 经最小纳入构建绑定成功并实例化）
- 实际执行并通过 executed_passed_total = **14**，fail = 0，unrun/uninstantiated = 0
- **全量通过率 = 14/14 (100%)**；`make test` 工具入口与 test-data 非独立用例单列，不计入分母
- 逐项映射：源码声明（util/Makefile.am check_PROGRAMS + python/test_cracklib.py
  TestModuleFunctions）-> 构建目标（util/testlib、util/testnum、util/teststr、
  python/_cracklib.so）-> 注册项（util 为 make 目标；python 为 unittest.TestSuite 注册 11 项）
  -> 实际执行日志（.oh-ut/evidence/gates/py-unittest-shim.log + testlib.log / testnum.log /
  teststr.log，退出码 0）
- 说明：配方对 OHOS 目标保持 `--without-python`（python 绑定不随库交付），11 个 python
  用例为设备侧最小纳入实测（BUILD_PYTHON 互斥分支），不作为 CI 默认构建路径；审计口径
  以源码声明 14 为准，审查实测 N=11 已被 14 ≥ 11 覆盖，不再少报。

## 知识候选台账与查重（路径 B 决定）

任务类型：知识库扩展。本适配产生 1 项非噪声候选。

### 候选 1：发布包无自动化 check 脚本 + 交互式 check_PROGRAMS + python unittest 互斥分支 → 建典+passwd 条目构造后全量 14/14 真实运行（配方以 FascistCheckUser 作 CI 等效覆盖）

- 真实错误：`make check` 不可直接运行（check_PROGRAMS 交互驱动；testnum/teststr 的 PWOpen(NULL)
  把空前缀格式化为字面 `(null)` 相对路径；testlib 的 FascistCheck 依赖 getpwuid GECOS，CI #43915）；
  python/test_cracklib.py 11 个 unittest 受 BUILD_PYTHON 条件宏控制，R01/R02 台账漏枚举（少报）
- 根因：上游发布 tarball 无自动化测试脚本（2.9.8 未声明 both-endian.sh/checkdict.sh）；
  交互式驱动需环境构造后才能在干净环境自动化；FascistCheck 依赖 getpwuid GECOS 检查；
  python 入口另有 AM_PATH_PYTHON `sys.version[:3]` 截断（3.12→"3.1"）、Python 3.12 移除
  `assertEquals`、FascistCheck getpwuid 三个前置条件
- 修复（R02 3/3 + R03 python 11/11）：cracklib-packer 建 testdict + 以字面 `(null)` 前缀装入
  运行 cwd 使 PWOpen(NULL) 成功（无需特权路径）；LD_PRELOAD getpwuid shim（nss_wrapper 同方式，
  等效 nss 来源，/etc/passwd 只读）使 FascistCheck 内部 getpwuid 返回条目（sort -u 收敛绕 toybox
  gzip -cdf，CI #43836；--with-default-dict=<testdict> 重建装载字典，R01 已证）；python 11 个
  unittest 最小纳入：`am_cv_python_version=3.12` 覆盖版本截断（→ python3.12/Python.h=yes、
  BUILD_PYTHON 生效）、补建 `_cracklib.so` 共享模块（--disable-shared 只产 .a）、运行时注入
  `assertEquals` 兼容 shim + 同一 getpwuid shim → 实测 11/11 OK
- 验证：全量 14 真实运行 14/14（util 三入口 stdin 管道驱动退出码 0 语义正确 + python 11/11
  unittest OK，见双口径台账）；配方 build() 内 L1 FascistCheckUser 4 断言作 CI 等效覆盖；
  conan create / test_package / 消费者用例全过；W3 本地 CI exit 0
- 适用范围：发布 tarball 无自动化测试、check_PROGRAMS 交互驱动的 autotools 库；
  PWOpen 空前缀按 libc 格式化为字面 `(null)` 的库；OHOS 上调用依赖 getpwuid 的公开 API 的库；
  带 BUILD_PYTHON 条件宏且测试用 assertEquals 旧别名的 python 绑定（Python 3.12+ 兼容）
- 正式知识查重：无 cracklib 相关 E 条目（E093 是 getpass 缺失、E402 是 gzip 长选项，均不同面）
- 图谱查重：index.tsv 无 cracklib / dist-missing-check 相关行
- 草稿查重：main 的 knowledge/drafts/ 无 cracklib 条目；2.10.3 远程分支草稿
  DRAFT-cracklib-2.10.3-dist-missing-check-scripts 覆盖同源问题但存在新增差异（见七轴）

### 七轴查重（对照 2.10.3 草稿与既有 E 条目）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false —— 2.9.8 是"无声明脚本"、2.10.3 是"声明未分发"，测试声明数不同（14 vs 5） |
| causal_duplicate | 部分 —— 同为"发布包内上游 make check 不可用"，根因同类 |
| trigger_overlap | 部分 —— error_signature 有交集（enter dictionary words），但 2.9.8 新增 PWOpen(NULL)/(null).pwd 字面路径模式与 python unittest 入口 |
| solution_overlap | 高 —— 同为 cracklib-packer 建典 + FascistCheck 语义断言（方案同源） |
| combination_novelty | 有 —— R02 新增"字面 (null) 前缀字典 + LD_PRELOAD getpwuid shim（等效 nss 来源）三入口 3/3 真实运行"组合；R03 新增"AM_PATH_PYTHON 版本截断覆盖 + _cracklib.so 补建 + assertEquals 兼容 shim"python unittest 11/11 纳入组合，2.10.3 草稿均未覆盖 |
| boundary_novelty | 有 —— 明确"PWOpen 空前缀 → libc 格式化为字面 (null) 相对路径"边界（cwd 装入即成功，无需特权路径）；R03 新增"BUILD_PYTHON 互斥分支下 python unittest 仍可按环境构造纳入实测"边界（设备 python3+Python.h 存在时 11/11 可运行），2.10.3 草稿未覆盖 |
| test_migration_novelty | 有 —— 双口径台账 14/14 (100%) 的可复制枚举/环境构造/恢复条件流程（含 python 入口） |

### 覆盖/新增差异

- 既有条目（E093/E402/E011 等）覆盖部分：getpwuid 系 libc 行为、gzip 长选项、umask 平台陷阱
- 本轮新增部分：cracklib 测试结构真相（util 3 交互驱动 + python 11 unittest + make test 工具
  入口分类）、PWOpen 空前缀格式化为字面 `(null)`、FascistCheck vs FascistCheckUser 在 OHOS 的
  差异、LD_PRELOAD getpwuid shim 作等效 nss 来源（/etc/passwd 只读时的 getpwuid 构造方法）、
  sort -u 收敛绕 toybox gzip、AM_PATH_PYTHON `sys.version[:3]` 截断陷阱（am_cv_python_version
  覆盖）、Python 3.12 移除 assertEquals 的兼容 shim、--disable-shared 下 python 绑定补建 .so
- 适用边界/反例：完整发行环境安装默认字典后 testnum/teststr 以真实路径可运行（R02 以
  字面 (null) 前缀装入 cwd 等价达成）；有 passwd 条目或 nss 等效来源的环境 testlib 可作
  字典语义验证；python 11 个入口需设备具备 python3.12+Python.h+libpython3.12.so 并按三前置
  构造后实测；无任何构造时三入口仍不可直接自动化（保持边界描述）

### 关系字段

- similar_to: DRAFT-cracklib-2.10.3-dist-missing-check-scripts（远程分支草稿，方案同源）
- caused_by: cracklib 上游 dist/test 设计（autotools 交互式 check_PROGRAMS + BUILD_PYTHON 条件宏）
- prerequisite_of: 无
- conflicts_with: 无

### 路径决定

- reuse_existing: false —— 既有知识未覆盖 PWOpen(NULL) 字面路径/LD_PRELOAD nss shim/sort -u/
  python unittest 纳入组合差异
- new_draft: true —— 已建 knowledge/drafts/DRAFT-cracklib-2.9.8-dist-missing-check-scripts.kv/.md（R03 已同步更新完整枚举/纳入证据与边界，保持 .md/.kv 同 stem 成对）
- path_a_no_knowledge: false
- 路径判定：**路径 B（知识库扩展）**——候选已由本轮真实日志验证、可跨库复用（交互式
  check_PROGRAMS + 字面 (null) 前缀 + getpwuid 依赖 + BUILD_PYTHON unittest 互斥分支模式），
  查重为部分覆盖且存在新增差异
---

**编译结束**: 2026-09-17 08:56
**最终状态**: built
