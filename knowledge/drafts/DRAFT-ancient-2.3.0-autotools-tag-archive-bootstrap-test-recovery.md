# DRAFT-ancient-2.3.0-autotools-tag-archive-bootstrap-test-recovery

> 草稿知识项 — autotools 库以 tag/git-archive 归档发布（无预生成 configure）时配方内自举链
> + m4 宏随配方携带；上游测试被 `.gitattributes export-ignore` 排除发布时按源码测试入口
> 恢复规则从官方 tag 拉取重跑。
> 来源：ancient 2.3.0 Conan 配方化（feat/ancient-2.3.0，task ancient-2.3.0-r01-pc2-43，
> 2026-09-24）
> 同 stem 配对：`knowledge/drafts/DRAFT-ancient-2.3.0-autotools-tag-archive-bootstrap-test-recovery.kv`

## 问题（现象 / error_signature）

- **归档不含生成物**：`codeload refs/tags/v2.3.0.tar.gz` 等价 git-archive 快照，
  `autotools.configure()` 直接报
  `configure: error: cannot find required auxiliary files: config.guess config.sub ltmain.sh compile ar-lib missing install-sh`。
- **m4 宏缺失**：自举时 `configure.ac: error: possibly undefined macro: AC_SUBST/AC_DEFINE`；
  若忽略继续，`PKG_PROG_PKG_CONFIG(0.24)` 以字面量残留进 configure →
  `./configure: syntax error: unexpected '0.24'`。
- **测试被排除**：`tar -tzf | grep -c 'testing/'` = 0 → `make check` 只报 `# TOTAL: 0`，
  但官方 tag 源码（api.github.com git trees）实际含 `testing/test.cpp` + 210 个 test_files，
  且上游 CI（ubuntu-24.04-make.yml）用 `make -f Makefile.unix` + `./obj/test` 真实运行。

## 根因（root_cause）

1. 上游以 tag 归档发布时 = git-archive 快照：只有 `configure.ac`/`Makefile.am`，不含
   `configure`/`aclocal.m4`/`Makefile.in`/`ltmain.sh`/`build-aux` 全量辅助脚本。**这是官方发布
   形态，不是"开发版/打包不完整"**，E058/E059 的 use-stable-release 无解。
2. configure.ac 引用 autoconf-archive（AX_CXX_COMPILE_STDCXX/AX_CHECK_COMPILE_FLAG/
   AX_CXXFLAGS_WARN_ALL）与 pkg-config（PKG_PROG_PKG_CONFIG）宏，发布归档 `m4/` 只有
   libtool 宏；CI 沙箱无 `$HOME/.local/share/aclocal` → aclocal 找不到 ax_*/pkg.m4。
3. 上游 `.gitattributes` 声明 `testing export-ignore`：GitHub/codeload 归档整体剔除测试目录，
   但仓库内 Makefile.unix 的 `VPATH += testing` 与 CI workflow 仍实际运行它——发布物与
   上游 CI 口径不一致，仅凭 tarball 枚举会把真实测试误判为"无测试"。

## 可复用方案（rec_approach: tag-archive-recipe-bootstrap + export-ignore-test-tag-recovery）

### 1) 判归档，决定是否自举

```bash
tar -tzf ${SW}-${VER}.tar.gz | grep -E '/(configure|ltmain\.sh|aclocal\.m4)$'
# 无命中 → 配方内自举；命中（make dist 产物）→ 只 --disable-maintainer-mode（DRAFT-5982-gmime）
```

### 2) 配方内自举链 + tool_requires

```python
def build_requirements(self):
    self.tool_requires("automake/1.18")
    self.tool_requires("libtool/2.5.4")
```

build() 内（cwd=source_folder, env=conanbuild，完整 autoreconf -i 等价链）：

```bash
"${LIBTOOLIZE:-libtoolize}" --force --copy --install   # ltmain.sh + libtool.m4 系列
ACLOCAL_PATH="$PWD/m4:$ACLOCAL_PATH" "${ACLOCAL:-aclocal}" --force -I m4
autoconf -o configure configure.ac
"${AUTOMAKE:-automake}" --add-missing --copy --force-missing   # config.guess/sub/compile/...
```

`autoheader` 在 configure.ac 无 `AC_CONFIG_HEADERS` 时报
`error: AC_CONFIG_HEADERS not found`——无害（ignore_errors=True）。

### 3) m4 宏随配方携带 + ACLOCAL_PATH 注入

```python
def export_sources(self):
    export_conandata_patches(self)
    copy(self, "m4/*.m4", src=self.recipe_folder, dst=self.export_sources_folder)

def generate(self):
    if os.path.isdir(os.path.join(self.source_folder, "m4")):
        self.buildenv_info.append_path("ACLOCAL_PATH", os.path.join(self.source_folder, "m4"))
    VirtualBuildEnv(self).generate()   # 必须先 append 再 generate
```

归档 `m4/` 放：ax_cxx_compile_stdcxx.m4、ax_check_compile_flag.m4、ax_append_compile_flags.m4、
ax_append_flag.m4、ax_require_defined.m4、ax_cxxflags_warn_all.m4、pkg.m4。

### 4) OHOS 等值三元组

```python
tc.configure_args.append("--build=aarch64-linux")
tc.configure_args.append("--host=aarch64-linux")
```

真机原生构建 build==host，保留 AC_RUN_IFELSE（同 DRAFT-5982-gmime）。

### 5) export-ignore 测试恢复 + 双口径台账

```bash
git clone --depth 1 --branch v${VER} https://github.com/${OWNER}/${SW}.git ${SW}-git-tag
cp -r ${SW}-git-tag/testing ./testing
make -f Makefile.unix CXX=clang++ CC=clang obj/test   # 上游 CI 同方式
./obj/test                                             # 201/201 exit 0
```

台账双口径：`source_declared_total`（官方 tag 源码按可复制枚举）与
`configured_executable_total`（当前配置实例化）分别列，全量通过率 = 通过数/全量发现数。

## 验证结果（ancient 2.3.0 实测）

- conan-verify G2（conan create ohos-aarch64）全绿；W3 本地 CI L0 全过；
  上游 obj/test 201/201 = 100%（`reports/upstream-test-ledger.md`）；
  test_package 实质依赖 + 鸿蒙专项双测试 Passed；消费者用例 SHA-256 与官方 raw 一致。

## 适用边界 / 反例

- **反例（release tarball 自带生成物）**：`make dist` 产物含 configure/Makefile.in/aclocal.m4/
  ltmain.sh → 不得加 automake/libtool tool_requires（DRAFT-5982-gmime forbid 规则），
  只 --disable-maintainer-mode。
- **反例（真实交叉构建）**：build≠host 时等值三元组不可用，须 patch config.guess/sub
  （E268/E205 patch-autotools-ohos.pl）。
- **反例（测试不在 git / submodule-only）**：tag 拉取恢复不可行 → 保留 uninstantiated 并
  记录恢复条件（双口径分母计、不计通过）。
- **限制**：自举链需 automake/1.18 + libtool/2.5.4 已发布制品仓；configure.ac 引用的
  ax_* 宏版本需与配方携带的 m4 一致（版本不匹配时以 configure.ac 声明为准）。

## 关系

- similar_to: DRAFT-5982-gmime-3.2.15-release-tarball-native-run-probe（release tarball 免自举 / 等值三元组）
- caused_by: 上游以 tag/git-archive 归档发布（不含生成物）；.gitattributes export-ignore 剔除测试
- prerequisite_of: 双口径上游测试台账（source_declared_total 需 tag 源码枚举）
- conflicts_with: E058/E059 use-stable-release（tag 归档即官方形态，无更"稳定"版本可换）

## 恢复条件

- automake/libtool 制品仓不可达 → 无法自举，报 dependency_missing（需先发布工具链包）
- 官方 tag 不可访问（网络/仓库迁移）→ 测试恢复不可行，保留台账为 uninstantiated 并附证据
