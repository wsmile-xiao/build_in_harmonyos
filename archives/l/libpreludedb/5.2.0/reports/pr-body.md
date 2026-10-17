## 三方库信息

- **三方库名称**：libpreludedb
- **上游版本**：v5.2.0
- **上游仓库地址**：https://github.com/Prelude-SIEM/libpreludedb
- **上游源码地址（conandata.yml 锁定）**：https://github.com/Prelude-SIEM/libpreludedb/archive/refs/tags/5.2.0.tar.gz
  `sha256: fdbfb75f3ae02e016f05881dabb6c2d588b1ae9896624cb46594e765f8b4b261`（558,322 字节，实测下载 + `sha256sum` 核验）
- **适配路径**：路径 A（基础适配）—— autotools 自举 + 依赖桥接 + OHOS 平台适配；复用仓内既有知识条目（E007 / E011）与同族包 `archives/l/libprelude/5.2.0` 的适配经验，本轮未沉淀新的知识草稿（新增经验记录在版本目录 `notes.md`，见「补充说明」）
- **使用知识库**：harmony-adapter（阶段一~六）；仓内知识条目 E007（`config.guess` 需注入 HarmonyOS 分支）、E011（HMDFS 下 `configure` 的 `umask 077` 临时目录不可写）；同族参考 `archives/l/libprelude/5.2.0`
- **适配路径（仓库内）**：`archives/l/libpreludedb/5.2.0/`
- **包类型**：C 库（`libpreludedb.so.7`；非 bash 补全脚本包、非 CLI 工具包）

> ⚠️ **上游源变更说明（必读）**：libpreludedb **原项目官网域名已被劫持失效**
> （`prelude-labs.org` / `www.prelude-siem.org`），官网发布页上的
> `libpreludedb-5.2.0.tar.gz` 全部 **404 不可用**，既无法下载也无法校验（与同族
> libprelude 情况相同）。因此本次改用 **Prelude-SIEM 官方 GitHub 组织的 tag 归档**
> 作为上游源码（R39 官方托管源，非镜像、非个人 fork），并锁定该归档的 sha256。
> 该归档是 autoreconf 的**输入**（上游未把 `configure`、`Makefile.in`、`config.h.in`
> 提交进版本库），这也是本 PR 必须在配方里做 autotools 自举的直接原因。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游本包**没有**自己的 `tests/` 目录（顶层 `Makefile.am` 为 `SUBDIRS = m4 libmissing src plugins bindings docs`），即上游未提供 libpreludedb API 级单元测试 |
| 集成测试 | 0 | 需要真实 SQL 后端 + Prelude manager 运行环境，上游未提供 |
| 其他测试 | 44 | 来源：随树发布的 **vendored gnulib** `libmissing/tests/Makefile.am` 的 `TESTS`（automake parallel-tests），内部共 230 处 `ASSERT (` |
| **合计** | **44** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游本包自身无 API 级单元测试，未新增也未删除 |
| 其他测试（vendored gnulib） | 44 | 不变 | 全部保留、全部实跑；已集成进 `conanfile.py` 的 `build()`（`cd libmissing/tests && make check`），`conan create` 即门禁 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c`（Conan L1 消费者测试，9 条 CHECK）：以下游使用者视角经 CMakeDeps 链接 `libpreludedb::libpreludedb`，实调 `preludedb_check_version`（含「过高版本必须拒绝」反向断言）、`preludedb_selected_path_new_string`（真实走 lex/yacc 生成的路径解析器，合法路径必须解析、非法路径必须报错）、libprelude 的 `idmef_message_new/destroy`；任一断言失败即非 0 退出 |
| **合计** | **45** | **+1**（新增消费者冒烟测试） | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**

补充说明（为「不改一行上游测试」而做的**构建侧**调整，均非测试代码改动）：

1. **`cd libmissing/tests && make check`，而非 `make -C libmissing/tests check`**
   - 从父目录 `-C` 进入时，libtool wrapper 的 `getcwd()` 反查在 HMDFS 上失败，
     44 项会全部假失败（同族 libprelude 的 9 项测试有同样现象，已沉淀为历史结论）。
2. **E007 / E011 只修 autoreconf 生成物，不碰上游源码**
   - `config.guess` 注入 HarmonyOS 分支（E007，禁止用 `--build/--host` 伪造三元组，
     那会跳过全部 `AC_RUN_IFELSE` 探测）；`configure` 内 `umask 077` → `022`（E011）。
   - 二者均为**构建期生成物**，`patches/` 目录为空 —— 本包 **0 个源码补丁**。
3. **未删除、未跳过、未替换任何上游测试程序或断言**（44/44 全绿，无 XFAIL/SKIP）。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游**本包自身无 API 级测试**（只有随树发布的 gnulib 自检），适配后补全了消费者视角测试

> 说明：上游 `libmissing/tests` 的 44 项是 gnulib 的 libc/内核能力自检，**不覆盖**
> libpreludedb 的对外契约；因此本 PR 按 Conan 强制要求（R34 / PF3 / CI L0c）补全 1 个
> 真实编译执行的消费者测试。

- **补全的测试范围**：库的对外契约面 —— 头文件布局与包含路径（`include/libpreludedb` +
  依赖头 `<libprelude/…>` 的传递可见性）、导出符号、`libpreludedb.so.7` 与其
  `libprelude.so → libgnutls/libgcrypt` 依赖链在 OHOS 上的**可加载性**、以及
  lex/yacc 生成的路径选择解析器在运行期的真实行为。
- **补全原因**：上游树内测试无法覆盖「安装后的包 + 下游消费者」这条路径；本包运行期依赖
  `libprelude.so.28` 能否被加载，只有消费者视角测试能暴露回归。
- **新增测试文件清单**：
  1. `archives/l/libpreludedb/5.2.0/test_package/test.c` — 9 条 CHECK 的消费者冒烟测试
  2. `archives/l/libpreludedb/5.2.0/test_package/conanfile.py` — 直接运行二进制并用
     `env="conanrun"` 注入运行环境（不用 `cmake.test()`，避免失败细节被 ctest 吞进日志）
  3. `archives/l/libpreludedb/5.2.0/test_package/CMakeLists.txt` — `find_package(libpreludedb)`
  4. `archives/l/libpreludedb/5.2.0/test_package/MANIFEST.yml` — 上游 44 项测试清单申报（CI L0e；
     YAML 条目按同类用例合并书写，合计仍为 44）

---

## 验证结果（OHOS aarch64 实测）

- **编译状态**：通过（`conan create` 成功；`conan-verify` G0 预扫 / G1 配方完整性 /
  G2 干净构建 / G3 系统同名库隔离 / G4 产物完整性 全部 PASS；`conan-verify` 的
  L2/L4/L5 为「跳过式 PASS」（该层无 cache 路径），L2/L4/L5 的**实跑**结论见
  `reports/w3-local-ci.log`：L2 `skip: no bin/ dir`（纯库包）、L4 `pass: patches clean`、
  L5 `pass: lib/ has content`）
- **上游测试用例通过率**：**44/44（100%）**
  （`Testsuite summary for libpreludedb 5.2.0`：# TOTAL 44 / # PASS 44 / # SKIP 0 / # XFAIL 0 / # FAIL 0 / # ERROR 0，构建期强制执行）
- **新增测试用例通过率**：**1/1（100%，内含 9 条 CHECK）**
  （输出 `libpreludedb 5.2.0 consumer test: OK`）
- **W3 本地 CI 模拟**：通过（`bash ci/conan/setup.sh` + `build_and_test.sh`，日志
  `archives/l/libpreludedb/5.2.0/reports/w3-local-ci.log`；L0 `pass: all checks passed` /
  L1 `pass: upstream tests + test_package executed` / L2 `skip: no bin/ dir`（纯库包，符合预期）/
  L4 `pass: patches clean` / L5 `pass: lib/ has content`，Build Summary 1/1 100%；
  `.ci-result.json` 由 finish 写入并含日志 SHA256，未手工改动）
- **依赖发布核验（W0）**：`libprelude/5.2.0`、`automake/1.18`、`libtool/2.5.4` 均
  `conan download -r=ohpcd --only-recipe` → EXIT 0（另含传递闭包 gnutls/libgcrypt/libgpg-error/
  libtasn1/nettle/libunistring/gmp 全部 EXIT 0）
- **产物**：`lib/libpreludedb.so.7.4.1`（SONAME `libpreludedb.so.7`，来自 `configure.ac` 的
  `-version-info 11:1:4` → libtool 计算 current-age=7）+ `include/libpreludedb/*.h`
  + `lib/libpreludedb/plugins/formats/classic/classic.so`（上游默认安装的 dlopen 插件）
  + `share/aclocal/libpreludedb.m4`；剔除 `bin/`（`preludedb-admin`、`libpreludedb-config`）、
  `share/man` 与全部 `.la`

---

## 补充说明

### 1. 真实构建问题的「首个错误 → 根因 → 最小修复」（三轮，均有日志）

| # | 首个真实错误 | 根因 | 最小修复 |
|---|---|---|---|
| 1 | `configure: error: Cannot find libprelude: Is libprelude-config in the path?`（此前输出 `*** The test program compiled, but did not run`） | 上游 `m4/libprelude.m4` 的 `AM_PATH_LIBPRELUDE` 只认 `libprelude-config` 脚本并用 `AC_TRY_RUN` **运行**探测程序；而 ohpcd 的 libprelude 制品按 R38 只交付库（`bin/` 已剔除），且配方用 `Environment.append()` 注入的 `LD_LIBRARY_PATH` 被 Conan 以**空格**连接，动态链接器无法解析 | `generate()` 生成最小 `libprelude-config` 兼容层 + 改用 `append_path()`（`os.pathsep`）注入 `PATH`/`LD_LIBRARY_PATH` |
| 2 | `test_package` 编译失败：`fatal error: 'libprelude/idmef.h' file not found` | libpreludedb 的**公开头文件**直接 `#include <libprelude/prelude-inttypes.h>` / `<libprelude/idmef.h>`，而 Conan 对非直接依赖默认 `headers=False/libs=False`，CMakeDeps 会清空传递依赖的 `INCLUDE_DIRS/LIBS` | `self.requires("libprelude/5.2.0", transitive_headers=True, transitive_libs=True)`（仓库内 461 个配方同一约定） |
| 3 | CI L0m：`版本目录 '5.2.0' 与 conanfile.py version='{version}' 不一致` | CI 判据为 `^\s*version\s*=\s*["']…` 取 `conanfile.py` 的**第一处**匹配，命中了配方内 shell 模板里的占位赋值 | 模板中去掉行首 `version=` 赋值，版本值内联 |

> 其余为既有知识直接套用：E007（`config.guess` 注入 HarmonyOS 分支）、E011（`umask 077`）、
> in-tree 布局（上游 `src/Makefile.am` 以 `-I$(srcdir)/include` 引用生成头
> `preludedb-version.h`，VPATH 构建必失败）。**源码补丁 0 个**。

### 2. 关于 `--no-preflight`（本地 PF9 误报）的说明

本地对变更清单实跑仓内 `scripts/ohc/preflight.py`（PF1–PF9 + R52）结果：

| 闸 | 结果 |
|---|---|
| PF1 单包 / PF2 制品 / PF3 测试实质性与结构 / PF4 依赖发布 / PF5 平台宏（补丁+配方）/ PF6 前缀 / PF7 源 URL / PF8 配方静态 | **全部 0 命中** |
| PF9 分支/路径闸 | **1 命中**：`archives/l/libpreludedb/README.md`、`archives/l/libpreludedb/manifest.yaml` 被判「变更路径缺版本目录层」 |

PF9 的判据是 `len(path.split('/')) < 5`，会把**软件级**交付物一并拦下；而

- 归档规范 `knowledge/ARCHIVE-SPEC.md` §2.1 明确规定软件级 `manifest.yaml` / `README.md`
  **必须**位于 `archives/{letter}/{name}/`（与 `commands.json` 同级，无法下调到版本目录）；
- 已合并的同批积分赛 PR 形态一致（如 dbab/1.6.1、libcrypto3/3.5.7 均携带软件级
  `manifest.yaml`/`README.md`）。

即：对「全新软件包」而言 PF9 与归档规范互斥，属框架门禁的存量误报。**本 PR 因此对
`create-pr` 使用 `--no-preflight`，未跳过任何构建/测试/审计步骤**：W3 本地 CI 模拟
（`reports/w3-local-ci.log`，L0/L1/L4/L5 全 pass）、`.ci-result.json`（工具生成，含日志 SHA256）、
conan-verify 8 道门禁、上游 44/44 测试与 test_package 均为真实通过。**请评审人工复核目录合规。**

> 建议框架侧处理：`check_branch_and_paths()` 对
> `archives/<字母>/<包>/{README.md,manifest.yaml,commands.json}` 予以豁免
> （按 W2 铁律，本 PR 不修改 `scripts/`）。

### 3. 已知限制 / TODO

- `preludedb_init()` 会访问编译期常量 `FORMAT_PLUGIN_DIR`（`configure` 时 prefix=/ →
  `/lib/libpreludedb/plugins/formats`），该路径只有部署到设备根后才存在，因此 `test_package`
  不调用它（避免误报），改以 `preludedb_check_version` / 路径选择解析器 / libprelude 对象 API 验证。
- MySQL / PostgreSQL / SQLite3 后端插件由上游 `AX_LIB_*` 探测决定，本次未探测到
  （上游未提供 `--without-*` 开关），故制品只含 classic 格式插件；如需启用 SQL 后端，
  需要先在制品仓补齐 libmysqlclient/libpq/libsqlite3。
