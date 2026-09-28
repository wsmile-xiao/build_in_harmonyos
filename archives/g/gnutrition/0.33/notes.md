# gnutrition 0.33 适配记录

## 基本信息
- 上游：https://ftp.gnu.org/gnu/gnutrition/（官方 GNU FTP）
- tarball：gnutrition-0.33.tar.gz，SHA-256 `470841a84180d8ec2b18cf73c66f216d9cdbb0063c710ac8eafe0994913b9b74`
- 构建系统：Autotools（configure.ac + Makefile.am），C99（-std=c99 -D_POSIX_C_SOURCE=200809L）
- 产物：单个 GUI 应用 `gnutrition`（GTK3）+ 数据 `food.db`
- 依赖（PKG_CHECK_MODULES 硬性）：sqlite3、gtk+-3.0、gio-2.0（glib 提供）、libm
- 制品仓依赖（ohpcd，均已有预编译包）：gtk/3.24.43、sqlite3/3.49.1

## 适配修改
1. **数据路径运行时覆盖（核心适配）**：main.c 原用编译期 `GNUTRITION_DATADIR` 拼 food.db
   绝对路径（`//share/gnutrition/food.db`），OHOS 上包内数据在 conan prefix 下不可解析。
   补丁：支持 `GNUTRITION_DATADIR` 环境变量覆盖（空则回退编译期默认）。该补丁在
   conanfile.py build() 内联应用（与 aris E007 同款模式）。
2. **config.guess/config.sub 替换（E007）**：预生成的 configure 内置脚本不识别 OHOS，
   build() 中替换为自包含 OHOS-aware 版本。
3. **HMDFS 适配（E011）**：configure 的 ac_pwd 探测加 `$PWD` 回退；config.status
   umask 077→022（HMDFS setgid 目录 077 下连 owner 也不可写）。
4. **执行位恢复（E490）**：configure/config.guess/config.sub/install-sh 等 chmod 755。
5. **运行时库路径**：generate() 中把 glib libdir 的 `-L`/`-lintl` 加入 LDFLAGS 并注入
   LD_LIBRARY_PATH（GTK 图内代理 libintl，configure conftest 需要）。

## 上游测试台账（R51，枚举清点）
gnutrition 0.33 上游**无任何测试入口**，证据：
- 源码树 `find -name 'test*' -o -path '*/tests/*'`：零匹配
- Makefile.am 无 `TESTS/check_PROGRAMS/check_SCRIPTS`（grep rc=1）
- configure.ac 无 `AC_CONFIG_TESTDIR/--enable-tests`
- `make check` 无目标可运行
→ 上游声明总数 `0`；configured_executable_total 上游 `0`；无未运行/未实例化项。

## 鸿蒙专项测试（新增，真实运行）
- `test_package/harmonyos_specific_test.c`：3 用例全部通过——
  A) 有效 GNUTRITION_DATADIR + broadway：sqlite3 数据层通过（无 cannot open database），
     到达 GTK 显示依赖边界（OHOS PC 无原生显示，按 E471 display-dependent 纪实分类）；
  B) 无效目录：错误信息含覆盖路径（环境变量覆盖生效）；
  C) 未设置：回退编译期默认路径。
- `test_package/test.c`（消费者验证）：真实启动已安装 gnutrition 产物 + 包内 food.db，
  断言数据层加载成功，纪实分类 headless 显示边界。PASS。

## 消费者验证（硬门禁）
- 消费者源文件：`test_package/test.c`、`test_package/harmonyos_specific_test.c`
- 构建/运行：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
  （test_package 由 CMake 构建 + ctest 执行），cwd=archives/g/gnutrition/0.33
- 退出码：conan create rc=0；ctest 2/2 Passed（test_gnutrition + harmonyos_specific_test）
- 使用的公开产物：安装的 `bin/gnutrition` 可执行文件 + `share/gnutrition/food.db` 数据
- 验证结果：数据层加载成功；headless 显示依赖按 E471 分类记录（非库缺陷、不伪造运行成功）

## W3 / conan-verify
- conan create（干净构建）rc=0，G0-G4/L2/L4/L5 全通过，报告见 reports/conan-verify-report.md
- 系统同名库隔离（G3）：产物仅 bin/gnutrition 与 share 数据，无同名 .so 冲突

## 知识候选台账（knowledge_candidate_ledger）

### 候选 1：GUI 应用编译期绝对数据路径（PKGDATADIR）在 OHOS conan 包内不可解析
- 真实错误：`gnutrition: cannot open database '//share/gnutrition/food.db': unable to open database file`
  （configure --prefix=/ 把 GNUTRITION_DATADIR 编成 //share/gnutrition，包内数据在
  <package_folder>/share/gnutrition）
- 根因：main.c 用编译期宏 + snprintf 拼绝对数据路径；应用（无 cpp_info 消费者）没有
  defines/runenv 注入点，库侧方案（E546 runenv_info.define_path / libint2 cpp_info.defines）不适用
- 修复：应用内 `getenv("GNUTRITION_DATADIR")` 覆盖 + 空值回退编译期默认（conanfile.py build()
  内联补丁 + patches/0001-main.c.patch）
- 验证：test_package/harmonyos_specific_test.c 三用例（有效/无效/未设置）3/3 PASS（OHOS aarch64）
- 适用范围：带数据文件、编译期 PKGDATADIR/DATADIR 宏拼接路径的 GUI/CLI 应用（GTK/Qt 等）

### 四范围查重结果
| 范围 | 命中 | 结论 |
|---|---|---|
| 正式知识（graph/*.kv + index.tsv） | E546（gupnp-av GUPNP_AV_DATADIR，库侧 runenv 注入）、E6344（bison BISON_PKGDATADIR，工具侧）、libint2 草稿（编译期 DATADIR 宏，库侧 defines） | 触发类高度重叠；方案为库/工具侧，未覆盖应用侧 in-app 补丁 |
| 知识图谱 index.tsv | 无应用侧数据路径条目 | 未命中 |
| 草稿 drafts/ | DRAFT-libint2-2.7.2-compile-time-datadir-macro-for-runtime-data、E6344-draft-zimpl-bison-pkgdatadir-redirect、E546-draft-3BD6-gupnp-av-xsd-datadir | 同类触发已记录，应用边界未覆盖 |
| 本候选（新） | DRAFT-gnutrition-0.33-app-datadir-env-override.kv/.md | 应用侧 getenv 补丁 + 默认回退 + 三用例探针 |

### 七轴查重
| 轴 | 结论 |
|---|---|
| exact_duplicate | NO（无应用侧同条） |
| causal_duplicate | NO（触发类同，修复载体不同：库 defines/runenv vs 应用 in-app 补丁） |
| trigger_overlap | YES（E546/E6344/libint2：编译期数据目录在 conan 包内断裂） |
| solution_overlap | PARTIAL（env 覆盖方向一致；注入点不同——应用无 cpp_info 消费者，必须改源码） |
| combination_novelty | NO（无新组合） |
| boundary_novelty | YES（应用边界：in-app getenv + 空值回退，既有条目未覆盖） |
| test_migration_novelty | YES（三用例运行探针：有效/无效/未设置双向语义验证，可跨库复用） |

### 关系字段
- similar_to: E546（gupnp-av xsd datadir，库侧）、DRAFT-libint2（编译期 DATADIR 宏，库侧）
- caused_by: 无（平台固有）
- prerequisite_of: 无
- conflicts_with: 无

### 路径判定
- **path_b_new_draft**：新增差异（应用侧 in-app 补丁 + 默认回退 + 三用例探针）已由本轮真实日志验证
  （harmonyos_specific_test 3/3 + consumer test）且可跨库复用（同类 PKGDATADIR GUI/CLI 应用）；
  查重为部分覆盖 → 走路径 B，草稿已建（.kv/.md 配对），与归档文件同一 PR。
- reuse_existing: E007（config.guess OHOS）、E011（umask HMDFS）、E490（执行位）、E471（显示分类）、
  E472（stub_test_method/self.run）均按既有条目复用，未新建草稿。
---

**编译结束**: 2026-09-27 02:27
**最终状态**: built
