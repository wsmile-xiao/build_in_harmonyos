# DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source — autotools 手写 Makefile.in（无 Makefile.am）out-of-source 构建下 install 规则裸名引用头文件失败 → 配方强制 in-source

> **Contributor**: pc2-34 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium | **Category**: build-system / autotools / conan / packaging / in-source
> **Audience**: 任何适配"发布 tarball 无 Makefile.am、install 规则以裸名引用头文件"的 autotools 库到 OHOS（或其它 out-of-source 构建环境）的工程师
> **Stem**: DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source（与同名 .kv 配对，字段逐一对齐）

## 问题（Symptom）

bc-ur 0.3.0（Blockchain Commons UR 库，C++ autotools）在 conan-verify G2 `conan create` 阶段，编译（make all）正常，但 package() 的 `make install DESTDIR=...` 报错：

```text
cd src && make install
install -d .../p//include/bc-ur
install bc-ur.hpp ur.hpp utils.hpp bytewords.hpp xoshiro256.hpp ... /.../include/bc-ur
install: bad 'bc-ur.hpp': No such file or directory
install: bad 'ur.hpp': No such file or directory
...
make[1]: *** [Makefile:93: install] Error 1
ERROR: bc-ur/0.3.0@ohpcd/stable: Error in package() method — autotools.install()
```

首跑还伴随 `make: jobserver mkfifo ...: Operation not permitted`（HMDFS 不支持 mkfifo，-j 并行降级为串行，非致命，E074 已覆盖）。

## 根因（Root Cause）

bc-ur 的发布 tarball 只含**手写 Makefile.in**（无 Makefile.am、无 automake 生成痕迹）。configure 从 Makefile.in 生成的 Makefile 虽然带 VPATH（因此 out-of-source 下 `make all` 能编译），但 src/Makefile 的 install 规则是：

```make
install: $(libname)
	install -d $(libdir)
	install $(libname) $(libdir)
	install -d $(includedir)
	install $(HEADERS) $(includedir)     # HEADERS = bc-ur.hpp ur.hpp ... （裸名，无 $(srcdir)/ 前缀）
```

GNU make 的 VPATH 只对**目标/依赖文件**的查找生效，**不会重写 recipe 里变量展开后的裸文件名**。conan 的 Autotools 默认 out-of-source 构建（basic_layout → `build-release/`），install 规则在 build 目录执行 `install bc-ur.hpp ...`，而头文件在源码目录 → `install: bad '<h>'`。automake 生成的 Makefile 会用 `$(srcdir)` 前缀引用头文件，因此**只有手写 Makefile.in 的库才会触发**。

## 方案（Solution）

在 conanfile.py 的 layout() 中把 build 目录折叠到源码目录，强制 in-source 构建：

```python
def layout(self):
    basic_layout(self)
    self.folders.build = "."   # 上游手写 Makefile 的 install 规则以裸名引用头文件，out-of-source 下 install 失败
```

bc-ur 0.3.0 实测：唯一此改动后 `conan create`（OHOS aarch64 profile，clang 15 / libc++）G1-G4/L2/L4/L5 全过，test_package 消费者 + 鸿蒙专项 2/2 通过。仓库内 abc/abduco/acpitool/adjtimex 等手写 Makefile 库已是同类做法。

备选方案（仅当项目强制 out-of-source 时）：conandata 补丁把 install 规则改写为 `install $(addprefix $(srcdir)/, $(HEADERS)) $(includedir)`，改动面更大。

## 适用边界与反例（Boundary & Counter-examples）

- **适用**：发布 tarball 无 Makefile.am（手写 Makefile.in）、install 规则以裸名引用头文件/源文件、且项目可接受 in-source 构建的 autotools 库。
- **反例（不适用）**：
  - automake 生成的 Makefile（含 `$(srcdir)` 前缀），out-of-source 正常（绝大多数常规 autotools 库）。
  - CMake 库（`install()` 规则自带完整源路径）。
  - 顶层 Makefile 完全无 VPATH 支持、out-of-source 下连 `make` 都找不到 makefile 的库——那是另一触发面（无 VPATH → makefile not found，见 DRAFT-audacious-buildsys-in-source-static-chain），本条目以"编译正常、仅 install 失败"为边界。

## 查重结论（四范围）

| 范围 | 命中 | 说明 |
|---|---|---|
| index.tsv ↔ graph/*.kv | E041（automake 版本不匹配/VPATH 重生成）、E514（install-sh 源内根，libtoolize aux dir）、E074（make jobserver FIFO）、E490（autotools 脚本执行位） | 无一覆盖"VPATH 可编译但 install 裸名头文件失败"签名 |
| knowledge/doc/ | 无命中 | — |
| knowledge/drafts/ | DRAFT-audacious-buildsys-in-source-static-chain（无 VPATH → makefile not found，同 in-source 方案不同触发面）、DRAFT-kytea-0.4.7-stale-shipped-configh-breaks-vpath（VPATH 时间戳）、DRAFT-ohos-makefile-explicit-toolchain-and-install-vars | audacious 草稿与本条同为"手写构建系统 + in-source"大类，但错误签名、触发 phase（make 找不到 makefile vs install 裸名）不同 |
| knowledge/operations/ | 无命中 | — |

**七轴查重**：
- exact_duplicate: false（无任何条目以 `install: bad '<h>'` 为签名）
- causal_duplicate: partial（audacious 草稿同属"手写构建系统 → in-source 要求"因果族）
- trigger_overlap: partial（audacious 触发于 make phase makefile-not-found；本条目触发于 packaging phase install 裸名；同为 out-of-source 域）
- solution_overlap: high（同一方案 `folders.build="."`；audacious 额外折叠 folders.source="."）
- combination_novelty: true（"VPATH 可编译 + install 裸名头文件"组合无既有条目）
- boundary_novelty: true（首次给出 automake `$(srcdir)` vs 手写裸名的差异边界）
- test_migration_novelty: true（bc-ur 实测 layout 改动后 conan create OHOS 全绿 + 消费者/鸿蒙专项 2/2，证据可跨库复用）

**关系字段**：`similar_to`: DRAFT-audacious-buildsys-in-source-static-chain；`caused_by`: 上游手写 Makefile.in 的 install 规则未使用 $(srcdir) 前缀；`prerequisite_of`: 无；`conflicts_with`: 无。

**路径判定**：**B（知识库扩展）** — 候选已验证（conan-verify 全绿）、可跨库复用（手写 Makefile.in 库族）、四范围查重部分覆盖且存在新增差异（install-phase 裸名触发面），建立同 stem .md/.kv 草稿对，随 bc-ur 归档同一 PR 交付。

## 验证（Verification）

1. `conan create`（OHOS aarch64 profile）未改 layout → package() `install: bad 'bc-ur.hpp'` Error 1（失败证据 2 次）。
2. `self.folders.build = "."` 后重跑 → G1-G4/L2/L4/L5 全过，exit 0。
3. test_package `test_bc-ur`（消费者）→ "bc-ur consumer test: ALL PASSED"；`test_bc-ur_ohos`（鸿蒙专项，-Werror）→ "bc-ur ohos test: ALL PASSED"。
