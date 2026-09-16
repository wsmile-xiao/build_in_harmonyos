# libint2 2.7.2 知识库扩展举证说明

> **立项类型**：知识库扩展
> **软件/版本**：libint2 2.7.2
> **上游仓库**：https://github.com/evaleev/libint
> **分支**：`feat/libint2-2.7.2`
> **申报边界**：本文只覆盖本库的知识贡献与对应证据；不预先声明评审等级，不申报高难度挑战。

---

## 1. 为什么这次不是"把库编出来"就结束

libint2 2.7.2 的适配在"编过"之外暴露了三类**可复用**的打包/消费缺陷，其中一类是上游
真实缺陷（不是环境问题）：

| 类别 | 现象 | 是否上游缺陷 | 对应知识草稿 |
|------|------|--------------|--------------|
| 消费契约（pkg-config） | 安装出的 `libint2.pc` 前缀/版本为空，`pkg-config --cflags --libs` 返回 `-I -I/libint2 -L -lint2` 且 exit 0 | ✅ 是（`configure_file(@ONLY)` 渲染 autotools 模板） | `DRAFT-…-upstream-pc-template-unrendered-by-cmake` |
| 打包语义（库名） | 上游 `ARCHIVE_OUTPUT_NAME int2` → 产物 `libint2.a`，包名与库名不一致 | ✅ 上游行为，配方须如实映射 | `DRAFT-…-cpp-info-libs-must-use-upstream-output-name` |
| 打包语义（数据） | 运行期数据目录（基组 `.g94`）靠编译期宏 `DATADIR`/`SRCDATADIR` + `LIBINT_DATA_PATH` 定位，按名加载失败时**默认静默空基组** | ✅ 上游行为，配方须补 define | `DRAFT-…-compile-time-datadir-macro-for-runtime-data` |
| 运行期（已知，复用既有知识） | 测试二进制缺 `libc++_shared.so`（只在 SDK sysroot） | ❌ 平台特性 | 复用 `DRAFT-boost184-component-pack-static-libcxx-testbin` |

判定标准：**不是"编译耗时/补丁大小/CI 次数"，而是"换一个库还能不能复用这条诊断"**。

---

## 2. 知识贡献矩阵

### 2.1 新增（随本 PR 以 `draft:true` 提交，不修改正式 `index.tsv`）

| # | 草稿（KV+MD 配套） | 可复用判据（一句话） | 预审结论 |
|---|--------------------|----------------------|----------|
| 1 | `DRAFT-libint2-2.7.2-upstream-pc-template-unrendered-by-cmake` | 上游同时有 autotools + CMake 两条安装路径时，必须实测 `pkg-config --cflags --libs` 是否返回空路径；修复用 `${pcfiledir}` 重写、并在消费者侧留回归守卫 | create（新知；最高相似度 0.22） |
| 2 | `DRAFT-libint2-2.7.2-cpp-info-libs-must-use-upstream-output-name` | `cpp_info.libs` 一律以 `ls <pkg>/lib` 的产物名为准，不按包名猜；禁止用同名符号链接掩盖 | review-similar（灰区 0.30 → E511） |
| 3 | `DRAFT-libint2-2.7.2-compile-time-datadir-macro-for-runtime-data` | 运行期数据靠编译期宏/configure 期绝对路径定位时，检查 `package_info()` 是否补 define + 该 API 是否静默降级（须补负向断言） | create（新知） |

三条草稿均通过 `draft-review` 的质量预检（`signature=✅ root_cause=✅ rec=✅`）。

### 2.2 复用（引用既有条目，不重复入库）

| 既有条目 | 本库复用点 |
|----------|-----------|
| E480 | header-only 依赖 `eigen/3.4.0` 用 `transitive_headers=True` 传给消费者 |
| E216 | CMakeDeps 不传播依赖 include → 消费者侧 `'Eigen/Core' file not found` |
| E092 | CMake 4.1.2 不识别 HarmonyOS host 平台（`Platform/HarmonyOS` 缺失，仅提示） |
| E247 | 上游 `.pc` 元数据不完整（同类问题：字段缺失 vs 模板未渲染） |
| `DRAFT-boost184-component-pack-static-libcxx-testbin` | OHOS C++ 可执行文件运行期缺 `libc++_shared.so` → `-static-libstdc++` |

### 2.3 去重记录（体现"先查库再写"）

适配过程中先写过一条 `DRAFT-libint2-2.7.2-static-libcxx-for-test-binaries`，
经 `grep` 全量检索 + `draft-review` 比对后确认与既有草稿
`DRAFT-boost184-component-pack-static-libcxx-testbin` **同因同方案**，故在本 PR 中
**删除该重复草稿**（diff 中为 deleted），改为在 `notes.md` / `MANIFEST.yml` / `pr-body.md`
中以引用方式使用既有草稿。

---

## 3. 每条新知识的落地实证

### 3.1 `.pc` 重写（草稿 1）

**修复前**（上游安装产物，实测）：

```console
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --cflags --libs libint2
-I -I/libint2 -L -lint2          # exit 0，静默失败
```

**修复后**（`package()` 用 `${pcfiledir}/../..` 重写）：

```console
$ pkg-config --cflags --libs libint2
-I<pkg>/include -I<pkg>/include/libint2 -L<pkg>/lib -lint2
```

**回归守卫**（consumer 入口 4，conan create 自动执行）：

```console
libint2/2.7.2@ohpcd/stable (test package): RUN: /data/service/hnp/bin/clang -std=c11 \
  -I<conan-cache>/p/libincc8068153c85b/p/lib/pkgconfig/../../include \
  -I<conan-cache>/p/libincc8068153c85b/p/lib/pkgconfig/../../include/libint2 <src>/test_pkgconfig.c \
  -o <build>/test_pkgconfig \
  -L<conan-cache>/p/libincc8068153c85b/p/lib/pkgconfig/../../lib -lint2
[PASS] pkg-config consumer: C API 可用 (need_memory_eri(1) = 14133)
```

### 3.2 库名与数据目录（草稿 2、3）

```console
$ ls <pkg>/lib          → libint2.a       （库名 int2，cpp_info.libs = ["int2"]）
$ ./test_basis          → sto-3g nbf=7 / 6-31g* nbf=19 / cc-pvdz nbf=24 / aug-cc-pvdz nbf=41
                          未知名（默认）→ nbf=0；strict → 异常信息含 <pkg>/share/libint/2.7.2/basis/
failures = 0
```

负向断言（strict 模式的异常信息包含真实数据目录）是关键：只做正向断言时，
"数据目录其实指向源码树"这类错误配置也能通过。

---

## 4. 验证与门禁（与知识条目绑定的可复现证据）

| 项 | 结果 | 证据位置 |
|----|------|----------|
| 上游 CTest | 12/12 通过（100%） | `reports/w3-local-ci.log` / `reports/test-report.md` |
| 消费者入口 | 4/4 通过（38 断言，`failures = 0`） | `reports/w3-local-ci.log` |
| conan-verify | G0/G1/G2/G3/G4 PASS | `reports/conan-verify-report.md` |
| W3 本地 CI | `JC_RESULT=pass`（涉及软件数 1）/ `KC_RESULT=pass` / `L0_RESULT=pass` / `L1_RESULT=pass` | `reports/w3-local-ci.log` |
| 配方硬闸（PF1-PF9 子项） | 单包 / 无二进制 / 无平台宏补丁 / 无共享前缀注入 / 源URL 官方 / settings 齐全 / 测试源与 MANIFEST 齐全 / 依赖在制品仓 | 本文件 §5 |
| 知识库校验 | `graph validate` 通过；新草稿 `draft-review` 质量预检全绿 | `knowledge/drafts/` |

---

## 5. 最终变更集与证据摘要

### 5.1 证据摘要（SHA256 前 32 位，2026-09-13 本轮验证）

| 对象 | SHA256（32 位） |
|------|-----------------|
| `archives/l/libint2/2.7.2/conanfile.py`（配方，含 `.pc` 重写与两处适配） | `4494873de8f010d99f7689f1a3863857` |
| `archives/l/libint2/2.7.2/test_package/conanfile.py`（4 入口编排 + pkg-config 探针） | `e39204cdc8b97e79da4c34f3ca473d49` |
| `archives/l/libint2/2.7.2/test_package/test_c_api.c` | `ec9cd5285ddf70fd0bf5b17fa542d8a3` |
| `archives/l/libint2/2.7.2/test_package/test_basis.cpp` | `89f26ee60d1aa66fae8cb0cfae3ab3a7` |
| `archives/l/libint2/2.7.2/test_package/test_pkgconfig.c` | `35c500d04298709f1066bb6ab7928f80` |
| `archives/l/libint2/2.7.2/reports/w3-local-ci.log`（W3 完整日志） | `162aee25f1895a0f605189ca9af0ad04` |
| `archives/l/libint2/2.7.2/reports/test-report.md` | `bb0e312f0e067c2fae0d025239b5c30d` |
| `knowledge/drafts/DRAFT-…-upstream-pc-template-unrendered-by-cmake.kv` | `682fe1be4c061e0983450d2944b45cf1` |
| `knowledge/drafts/DRAFT-…-cpp-info-libs-must-use-upstream-output-name.kv` | `36719dfd7519237303b0ab6e7ff61d34` |
| `knowledge/drafts/DRAFT-…-compile-time-datadir-macro-for-runtime-data.kv` | `5ad8728070644efc9c14c1680bd5f4bb` |

W3 结果文件 `.ci-result.json`：`exit_code=0`，`log_sha256=162aee25f1…befcf693`（与上表 W3 日志一致）。

### 5.2 变更集

相对基线 `525d915cc4`，本 PR 的**净变更集 = 23 个新增/修改文件、0 删除**（17 个 `archives/l/libint2/**`
归档文件 + 6 个 `knowledge/drafts/DRAFT-libint2-2.7.2-*` 知识草稿文件）。

去重记录（见 §2.3）里的重复草稿 `DRAFT-libint2-2.7.2-static-libcxx-for-test-binaries.{kv,md}`
是**在本分支内部创建后即删除**的（`b8cb803ec3` 加入 → `6548212c0b` 删除），因此在 `base..HEAD`
净 diff 中既非新增也非删除，**不存在于 PR 内容中**；去重结果体现为 `notes.md` / `MANIFEST.yml` /
`pr-body.md` 中对既有草稿 `DRAFT-boost184-component-pack-static-libcxx-testbin` 的**引用**。

核验命令与结果（只读）：

```console
$ git diff --name-status 525d915cc4 -- archives/l/libint2 knowledge/drafts   # 23 行，全部为 A
$ git diff --diff-filter=D --name-only 525d915cc4                           # 输出为空（无删除）
```

不含任何框架文件（`SKILL.md`/`scripts/`/`ci/`/`templates/`/`knowledge/graph/index.tsv` 均未改动）。

### 5.3 W4 审计 P3 项处置

W4 独立审计（verdict=pass，P0/P1/P2=0，P3=3）的 3 条非阻断项处置：

| P3 项 | 处置 |
|---|---|
| §5.2 变更集计数与净 diff 不一致 | **已修正**（本节，按净变更集 23 新增/0 删除 + 分支内自建自删的说明重写） |
| 软件级 `manifest.yaml` 偏离 `templates/manifest-software.yaml`（缺 display/license/build_system/ohos_adaptation，以 website 代 homepage） | **已修正**（补齐 `display`/`license`/`build_system`/`homepage`/`ohos_adaptation`，版本索引改为 `status`/`build_date`/`packaging`/`notes` 形态） |
| `package_type="static-library"` 与 `options.shared` 并存 | **保留并说明**：与仓库既有 `archives/c/ceres-solver/2.2.0` 及 `templates/conanfile-cmake.py.tmpl` 的写法一致；`package_type` 优先，`shared` 选项仅保留统一形态，不影响产物（R26 静态库、G1 PASS） |

---

## 6. 申报边界

1. **不申报高难度挑战**：本库为单依赖（header-only）、零源码补丁、纯静态数学库，
   不具备该路径举证范式所需的运行时/多目标动态语义；本次按"知识库扩展"如实申报。
2. **未修改上游测试**：`tests/**` 与上游 CTest 注册未改动（`patches/` 为空）；
   新增的 4 个消费者入口全部位于 `test_package/`。
3. **不重复计数**：上游 12 个 CTest 用例按唯一入口计；新增消费者入口按 4 个唯一入口计，
   不把入口内部的 38 条断言拆成更多用例。
4. **不夸大消费契约**：C ABI 入口断言的是内核分发表/内存契约/生命周期，
   数值正确性归属上游 `tests/unit/c-api.c` 与入口 1/3，本文不重复声称为 C 入口的成果。
5. **不把已知平台限制写成通过**：Fortran 绑定与 MPFR 高精度测试在本 PR 中显式关闭，
   已在 `reports/test-report.md` 的"已知限制"中列出。
6. **工具侧观察（供框架维护者参考）**：`ci/conan/build_and_test.sh` 在构建前把
   `conandata.yml` 的 `sources.url` 改写为「镜像（`gh-proxy.com`）+ 官方」列表
   （`build_and_test.sh:1050-1054` 规则），而**该改写没有还原路径**——紧随其后的 `file://`
   预下载改写带 `trap _restore_conandata EXIT`，但它备份并还原的是"已注入镜像"那一版
   （`build_and_test.sh:1166-1188`），且脚本没有关闭注入的开关。后果：
   ① W3/CI 构建态与"按 R39/PF7 要求提交的官方单源态"必然不一致（实测 recipe revision
   `b2e10dacf339…` vs `19f04f48d434…`，差异仅 `sources.url` 一行，源码 sha256 固定值相同）；
   ② 若 AI 随后 `git add archives/` 直接提交，镜像 URL 会流入 PR（仓库中已有 372 个
   conandata 含 `gh-proxy`、72 个含 `ghfast`，属存量违规，PF7 会拦新建 PR）。
   建议框架侧：给镜像改写加还原（或提供 `OHC_NO_MIRROR=1` 开关），使"所测 = 所提"。
   本 PR 的处理：提交前人工复原为官方单源（PF7 PASS），并在 `reports/pr-body.md` 中显式披露。
