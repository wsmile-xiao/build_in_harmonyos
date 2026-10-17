# exifprobe 2.0.1 适配笔记

## 编译环境

- 构建系统: makefile（纯 Makefile，无 configure/autotools）
- 编译日期: 2026-09-21
- 编译器: clang 15（OHOS aarch64，`/data/service/hnp/bin/clang`）
- 状态: published
- 目标平台: HarmonyOS PC (aarch64, musl, libc++)

## 编译步骤

```bash
# init-build（github.com 直连超时，经 ghfast.top 镜像拉取官方 tag 2.0.1，SHA-256 核验一致）
python3 scripts/ohc-run.py init-build exifprobe 2.0.1 --url=https://github.com/hfiguiere/exifprobe

# 语言预检：task=cpp, detected=c (兼容族)
python3 scripts/ohc-run.py lang-preflight exifprobe 2.0.1 --src $BUILD_SRC_DIR

# 手工编译（Makefile 默认 CC=cc 不可用，必须显式 make CC=clang）
make CC=clang CFLAGS="-DCOLOR -O2"        # → exifprobe 二进制
make install PREFIX=$TEST_PREFIX           # staging 安装

# 配方验证（conan create + G1-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify exifprobe 2.0.1

# 收尾（W3 本地 CI 单包口径：JUNK_PR_DIFF=pr.diff 规避 main 上其他库基线垃圾误拦）
JUNK_PR_DIFF=pr.diff python3 scripts/ohc-run.py finish exifprobe 2.0.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 超时 | 本机直连 GitHub 不可达（TCP 超时），ghfast.top 镜像可达 | 经 ghfast.top 拉取官方 tag 归档，SHA-256 与官方一致后放入 `$TMPDIR/builds/` 缓存，init-build 跳过下载 |
| 2 | conanfile build() 中 `self.conf.get("tools.build:compiler_executables:c", ...)` 报错 | Conan conf 读取子键路径 `.c` 不存在；`tools.build:compiler_executables` 是字典，须整读后取 `c` | `compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 再 `compilers.get("c", "clang")`（E307 部分覆盖，见知识台账 C2） |
| 3 | package() 中 `copy(..., keep_perm=True)` 报 `TypeError: copy() got an unexpected keyword argument 'keep_perm'` | Conan 2 `conan.tools.files.copy` 无 `keep_perm` 参数 | 去掉 `keep_perm=True`，直接 `copy(self, "exifprobe", src, bin_dir)`（保留执行位靠源文件权限）（知识台账 C1，新建草稿） |
| 4 | W3 本地 CI junk_check full 模式拦截 main 上其他库垃圾（cloog/kics `.staging-verified`、`.build-closed`） | full 模式整仓扫描 git ls-files，扫到其他库历史遗留空文件 | 基线隔离复验：记录路径+隔离前 SHA-256（均 e3b0c44... 空文件）→ 临时移出 → 复跑 junk_check（Junk Files: 0）→ 原样恢复 → 核对 post SHA-256 一致；同时用 `JUNK_PR_DIFF=pr.diff` 单包口径跑 W3 |
| 5 | 上游无测试（无 tests/ 目录、无 check/test make 目标、无 ctest/gtest） | 上游为 2005 年纯 Makefile 项目，官方源码不含测试用例 | 台账记录 source_declared_total=0；test_package 自建 6 项消费者断言（生成真实 EXIF JPEG → exifprobe -V/-L 验证版本与 Make 标签解析） |

## 源码修改

无（纯配方适配，无源码补丁；patches/ 为空）

## 依赖版本

无外部依赖（仅 libm，系统库）

## 验证结果

```bash
# 真实 EXIF 解析（构造 JPEG/APP1/TIFF, Make=OHOS-TEST）
./exifprobe test-exif.jpg   # → File Type = JPEG/APP1/TIFF, Make = 'OHOS-TEST\0'
# test_package 消费者 6/6
bash test_package/test.sh   # 6/6 functional checks PASS
# W3 门禁
.coni-result.json  # exit_code=0, log_sha256=9d77eb6fae0baa02ada0edb80975b0b1e55fc3633bb6b2703a6dcde5cc483e77
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 配方（Makefile CLI 工具） |
| conandata.yml | 官方 GitHub tag 2.0.1 + SHA-256 |
| commands.json | R38 CLI 声明（archives/e/exifprobe/commands.json） |
| test_package/ | 消费者测试（6 断言） |
| knowledge/drafts/DRAFT-exifprobe-2.0.1-conan2-copy-keep-perm.{kv,md} | 知识草稿（路径 B） |

## 注意事项

- Makefile 硬编码 `CC=cc` 与 `CFLAGS=-DCOLOR -O`，配方必须显式传 `make CC={cc} "CFLAGS=-DCOLOR -O2"`（R33）
- 构建依赖 `/bin/sh`（makebyteorder.sh / mkcomptime）；HMDFS 环境注意 shell 临时文件配额
- 该设备共享文件数配额紧张（/storage/Users tmpfs, total≈48M, 一度 free≈5000），conan create 前可用 `conan cache clean -b` 释放陈旧构建目录

## 知识候选台账（knowledge_candidate_ledger）

每个候选记录真实错误、根因、修复、验证、适用范围及正式知识/图谱/草稿四范围查重结果。

| 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 正式知识(index.tsv/doc) | 图谱(.kv) | 草稿(drafts) | 判定 |
|---|---|---|---|---|---|---|---|---|---|
| C1: copy() keep_perm | `TypeError: copy() got an unexpected keyword argument 'keep_perm'` (conan create package()) | Conan 2 copy() 无 keep_perm 参数 | 去掉 keep_perm=True 直接 copy | conan-verify G2 由 FAIL→PASS，bin/exifprobe 可执行位保留 | 所有用 conan.tools.files.copy 打包可执行/脚本/带模式文件的 Makefile CLI 工具配方 | 未命中 | 未命中 | 未命中 | **new_draft**（路径 B） |
| C2: compiler_executables 子键 | `Error in build() method` 读取 conf 失败 | `tools.build:compiler_executables:c` 子键路径不存在，须整读字典 | `get("tools.build:compiler_executables", default={}, check_type=dict)` 再 `.get("c")` | conan-verify G2 PASS | 所有从 Conan profile 读编译器的 build() | E307 部分覆盖（rec_command 同构） | 命中 E307 | 未命中 | **reuse_existing**（E307 已含方案，不新建稿，避免与 E307 重复） |
| C3: W3 full 模式误拦其他库基线垃圾 | junk_check JC1/JC5 拦截 cloog/kics `.staging-verified`/`.build-closed` | full 模式整仓扫 git ls-files；其他库历史空文件已提交在 main | 基线隔离复验（记录 SHA-256→隔离→复跑 Junk Files:0→恢复→post SHA 一致）+ `JUNK_PR_DIFF=pr.diff` 单包口径 | W3 L0/L1/L4/L5 全 pass，.ci-result.json exit_code=0 | 所有依赖归档与整仓历史垃圾并存的本地 W3 场景 | 未命中 | 未命中（本仓基线噪声规程属 SKILL 而非图谱） | 未命中 | **path_a_no_knowledge**（SKILL/规程既有处理方式，非新增知识） |
| C4: 上游无测试（source_declared_total=0） | make -n check 为空、无 tests/ctest 注册 | 上游 2.0.1 纯 Makefile 项目不含测试 | 台账据实记录 0 项；test_package 自建 6 断言消费者验证 | test_package 6/6 PASS | 无测试上游的 R51 台账口径 | 未命中（R51 规程已覆盖） | 未命中 | 未命中 | **path_a_no_knowledge**（规程口径，非新增知识） |

### 路径 B 七轴查重（仅 C1 进入 new_draft 判定）

- exact_duplicate: false（四范围均无 keep_perm 条目）
- causal_duplicate: false（无其他条目由同根因产生）
- trigger_overlap: 低（E307 是 test_package 缺 CMake 直编场景，触发面不同）
- solution_overlap: 部分（E307 也涉及 conf dict 读取，但 copy() 参数问题无重叠）
- combination_novelty: true（Conan 2 copy() 参数签名 + Makefile CLI 打包组合，语料未覆盖）
- boundary_novelty: true（明确"仅 package() 拷贝路径、install() 族不受影响"边界）
- test_migration_novelty: false（无测试迁移内容）

### 路径决定

- **reuse_existing**: C2（E307 覆盖）
- **new_draft**: C1 → `knowledge/drafts/DRAFT-exifprobe-2.0.1-conan2-copy-keep-perm.{kv,md}`（同 stem 配对，路径 B 【知识库扩展】）
- **path_a_no_knowledge**: C3、C4（SKILL/规程既有处理，无新增库级知识）

---

**编译结束**: 2026-09-21 16:04
**最终状态**: published