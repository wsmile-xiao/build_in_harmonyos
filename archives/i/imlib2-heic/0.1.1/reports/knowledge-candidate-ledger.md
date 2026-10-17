# imlib2-heic 0.1.1 知识候选台账 + 七轴查重（R02 终态）

任务：imlib2-heic-0.1.1-r02-pc4-16-20260919T055418Z
阶段：R02 已完成依赖就绪后的**全部实际构建、测试、打包与交付门禁**（conan-verify G1-G4/L2/L4/L5 全过、
W2/W3 过、HOS 专项 + 消费者验证运行通过、commit 已入分支）。
本表在本轮真实证据上复核 R01 初判（path_a_no_knowledge），并登记 R02 新候选。

查重范围：正式知识（knowledge/graph/index.tsv E-entries）+ 图谱（index.tsv 行）+ doc/（E*.md）+ drafts/（DRAFT-*）。

## R01 候选复核（R02 实构建证据下）

### 候选 1：imlib2 依赖未发布 → 下游库被依赖门禁阻塞
- R02 复核：条件已解除——imlib2/1.9.1 已发布（revision 5d819e4fd242fc0ee250c554b7f43788，`conan download` 实测
  成功）；本库 G2 conan create 实构建通过。该候选是仓库调度状态事实，非编译模式知识，维持不建稿。
- 判定维持：`path_a_no_knowledge`（不构成 L1/L2 条目）。

### 候选 2：plain Makefile 项目被 conan-init 误判/回退为 autotools 模板
- R02 复核：本轮实际重写了 makefile 配方（build() `make -j1 -C {source_folder}` + 显式注入
  CC/CFLAGS/LDFLAGS + `-DX_DISPLAY_MISSING`；package() 从 source_folder 拷贝 heic.so 并完成 ELF 自签）。
- 查重：drafts/ 已有 ≥12 个 makefile→conan 配方草稿（DRAFT-cd-hit-4.8.1-make-conan-recipe、DRAFT-libcyaml-1.4.2-
  makefile-conan-env-cppflags、DRAFT-binn-3.0-raw-makefile-strip-musl-symbol、DRAFT-clthreads-makefile-stage-install-
  shadow 等），正式条目 E097/E108/E158/E156 亦覆盖自定义 Makefile 适配；`exact_duplicate`（触发/方案均被既有
  知识覆盖，无新增差异）。
- 判定维持：`path_a_no_knowledge`。

### 候选 3：imlib2 loader 插件打包模式（dlopen 插件/宿主 ABI/loaders 安装路径）
- R02 复核：本轮以真实证据验证了该模式——heic.so 经 `lib/imlib2/loaders/` 安装、loader ABI
  `char load(ImlibImage*, ImlibProgressFunction, char, char)`/`save`/`formats`（`void formats(ImlibLoader*)`）
  与 imlib2 1.9.1 宿主兼容；HOS 专项/消费者测试 dlopen + dlsym + formats() 注册 heic/heif 实测通过。
- 查重：E345（abi-matched-private-host-validation：loadable module/plugin/dlopen/runtime 验证）与
  E442（model-host-as-runtime-contract：host-loaded plugin、未解析宿主符号、ELF DYN、插件入口点）已覆盖
  loader 插件 ABI 与运行时验证核心；R01 判定 trigger_overlap + solution_overlap，本轮实测进一步确认
  无新增可跨库复用差异。
- 判定维持：`path_a_no_knowledge`。

## R02 新增候选（实构建排错产生）

### 候选 4（非噪声）：OHOS ELF 签名——未签名/无效签名 .so 在 OHOS 上 dlopen 报 EACCES 的修复路径
- 证据（本轮实测）：conan create（G2）首次产出 heic.so 后，package() 未签名；HOS 专项/消费者测试与
  test_package 对安装包内 heic.so 的 dlopen 全部报 `Permission denied`（EACCES），即使用例本身在
  普通 ELF 上正常。排错确认：llvm-readelf 显示 `.codesign` 段存在但签名**无效**（SDK 链接器自动插入占位段）；
  修复路径 = package() 内 `llvm-objcopy --remove-section .codesign` 后 `binary-sign-tool sign -inFile X
  -outFile Y -selfSign 1` 再 `chmod 755`；签名后 dlopen/HOS 测试/消费者测试/test_package 全部通过
  （RESULT: PASS，RC=0，证据见 reports/w3-local-ci.log 与 tests/run_ohos_tests.sh 复现脚本）。
- 查重：
  - E077（post-install-script）：已正式条目，完整覆盖"ELF 必须含有效 .codesign 才能被加载；binary-sign-tool
    无法覆盖已有签名段，必须先移除旧签名再重签；签名后权限归零需重 chmod"四步流程——`solution_overlap` 完全一致。
  - DRAFT-E077B（ohos-sdk-autocodesign-invalid）：草稿，精确覆盖"SDK 链接器自动插入的 .codesign 占位段对内核不可用，
    readelf 见签名 ≠ 可执行"——与本轮 EACCES 现象逐字吻合，`trigger_overlap` + `causal_duplicate`。
  - DRAFT-7939（gpgmepy-python-ext-selfsign-hmdfs）：草稿，覆盖"Conan copy() 破坏签名后须 objcopy 去段 + 自签 +
    chmod"同一修复动作。
  - DRAFT-binary-sign-tool-buildenv-ldlibrarypath：草稿，覆盖 binary-sign-tool 在 conan buildenv 下的签名前环境处置。
- 七轴（候选 4）：
  | 轴 | 判定 |
  |---|---|
  | exact_duplicate | 否（各草稿散点覆盖，无单一完整条目比本轮更全） |
  | causal_duplicate | 是（E077/DRAFT-E077B 同根因：签名无效 → 加载拒绝） |
  | trigger_overlap | 是（E077/DRAFT-E077B 完全重叠） |
  | solution_overlap | 是（E077 四步流程逐字一致） |
  | combination_novelty | 否（无新组合） |
  | boundary_novelty | 否（E077 已含 dlopen/插件边界） |
  | test_migration_novelty | 否（dlopen 验证方式 E345/E442 已覆盖） |
- 判定：`path_a_no_knowledge`——既有知识（E077 正式 + 3 个签名草稿）已完整覆盖根因与修复，本轮只是正确应用；
  不建草稿、不改知识库。

### 候选 5（观察记录，不建稿）：无 X11 环境编译 imlib2 系代码需 `-DX_DISPLAY_MISSING`
- 证据（本轮实测）：imlib2/1.9.1 以 --without-x 构建，其 Imlib2.h 用 `#ifndef X_DISPLAY_MISSING` 守卫 X11/Xlib.h；
  本库编译 loader 与两类测试均须定义该宏才能通过（G2 首错 `X11/Xlib.h not found`，加入 `-DX_DISPLAY_MISSING` 后通过）。
- 查重：该知识已由 **imlib2-1.9.1 库自身**登记并建稿（imlib2 1.9.1 先例 reports/knowledge-candidate-ledger.md 候选 C1
  判定 new_draft，草稿 DRAFT-imlib2-1.9.1-x-display-missing-consumer-macro.md/.kv 已随 imlib2 库交付；E527/E530/E533
  亦相关）。本库作为 imlib2 的消费者**复用该已知知识**，不重复建稿；imlib2 包 recipe 已通过 package_info
  cflags 注入该宏，下游无需再注入。
- 判定：`reuse_existing`（复用在先例已交付的知识，不新增）。

## 七轴查重汇总（候选 1-4，逐轴口径）

| 轴 | 候选1 | 候选2 | 候选3 | 候选4 |
|---|---|---|---|---|
| exact_duplicate | 否（状态事实） | 是 | 否 | 否 |
| causal_duplicate | 否 | 是 | 是（E345/E442） | 是（E077/DRAFT-E077B） |
| trigger_overlap | 弱（E277） | 是 | 是 | 是 |
| solution_overlap | 否 | 是 | 是（E442） | 是（E077 四步） |
| combination_novelty | 否 | 否 | 否 | 否 |
| boundary_novelty | 否 | 否 | 否 | 否 |
| test_migration_novelty | 否 | 否 | 否 | 否 |

关系字段：候选 3 similar_to: E345, E442；候选 4 similar_to: E077, DRAFT-E077B, DRAFT-7939,
DRAFT-binary-sign-tool-buildenv-ldlibrarypath；候选 2 similar_to: E097/E108/E158/E156 及 ≥12 个 DRAFT
makefile 配方条目。其余候选无 caused_by / prerequisite_of / conflicts_with 关系。

## 路径决定（R02 复核终态）

- `reuse_existing`：**是**（候选 5 复用 imlib2 已交付知识；候选 1-4 复用既有条目，未改知识库）。
- `new_draft`：**否**（无任一候选形成"已验证、可跨库复用且查重为未命中或部分覆盖并存在新增差异"的新知识；
  本轮全部为既有知识（E077/E345/E442/E097 家族 + imlib2 loader/dlopen/签名草稿群）的正确应用）。
- `path_a_no_knowledge`：**是**（唯一决定，**复核维持 R01 初判**；高难度挑战标注保留不降级——Path C 的
  "具体高难证据"由本轮真实构建/测试/交付证据支撑：私有 loader ABI 对齐 + OHOS ELF 自签 + dlopen 消费者验证）。
- 未新增/修改任何 knowledge/graph、knowledge/doc、knowledge/drafts 文件（除本台账记事文件 reports/ 外）。