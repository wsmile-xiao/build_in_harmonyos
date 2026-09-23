# libcroco 0.6.13 知识候选台账（knowledge_candidate_ledger）

> knowledge_candidate_observation: required —— 本台账覆盖 GDPR 四范围查重（正式知识 doc/、图谱 index.tsv、草稿 drafts/、operations）、七轴查重与路径判定。

## 候选台账

### 候选1：config.sub 不识别 aarch64-linux-ohos 三元组
- 真实错误：`configure: error: Invalid configuration 'aarch64-linux-ohos'`（2018 版 config.sub 无 linux-ohos 候选）
- 根因：autoconf config.sub 校验逻辑未收录 HarmonyOS 平台名
- 修复：`0001-config.sub-ohos.patch` 在 KERNEL-OS 与 OS 列表中加入 `linux-ohos*`
- 验证：conan create 全流程通过；config.sub 复跑 `./config.sub aarch64-linux-ohos` 返回正常
- 适用范围：所有 autotools 库在 OHOS arm64 交叉编译
- 四范围查重：
  - 正式知识：E007（patch-autotools-script）、E072（invalid triplet ohos）、E122（add-linux-ohos-to-validation）—— 完全覆盖，同一机理
  - 图谱 index.tsv：E007/E072/E122 命中
  - 草稿：无新增草稿（沿用既有知识）
  - operations：build-systems.md §3.1 已有 config.guess/sub 处理说明
- 判定：exact_duplicate = true（与 E122 逐字同机理）

### 候选2：HMDFS 下 config.status 临时目录 Permission denied（E011）
- 真实错误：`./config.status: line 841: ./confHqrLU1/subs1.awk: Permission denied`
- 根因：HMDFS UID 映射导致 umask 077 创建的 0700 临时目录对当前进程不可写（实测 mktemp -d 成功但写入失败；umask 022 可写）
- 修复：`0002-configure-umask-ohos.patch`（umask 077 → 022，E011 推荐方法 2）
- 验证：patch 后 conan create 全流程通过
- 适用范围：所有 autotools 库在 HMDFS 挂载上的 configure
- 四范围查重：E011（edit-umask-in-configure）逐字命中；E052/E060/E110 同族；operations 无新增
- 判定：exact_duplicate = true

### 候选3：依赖包 .la 元数据不可搬迁导致 libtool 链接失败（E236）
- 真实错误：`libtool: error: '//lib/libpcre2-8.la' is not a valid libtool archive`（symbol pcre2 链）
- 根因：pcre2（glib 传递依赖）包内 libpcre2-*.la 记录 libdir='//lib'（conan 重定位后路径失效），libtool 递归打开失败
- 修复：配方内 E236 `scoped-la-free-static-archive-directory`——将依赖 .a/.so 复制到无 .la 的构建私有目录，CROCO_LIBS 指向它；包内 rm *.la
- 验证：conan create 全流程通过；test_package 消费者成功链接运行
- 适用范围：任意 autotools 库依赖带 .la 的 conan 包
- 四范围查重：E236 完全覆盖；E522 为同族复杂方案；图谱命中；无新增草稿
- 判定：exact_duplicate = true

### 候选4：glib/libxml2 CMakeDeps 组件 include 目录不传播（E216 同族，触发面略扩）
- 真实错误：test_package 消费者 `fatal error: 'glib.h' file not found`
- 根因：libcroco 头文件 #include <glib.h>；glib 作为传递依赖时 CMakeDeps 生成的数据文件 INCLUDE_DIRS 为空（作为直接依赖时非空，探针实证）
- 修复：test_package/conanfile.py 显式声明 glib/libxml2 直接依赖（AbiWord 插件 notes 同款先例）；消费者 include 使用 <libcroco/libcroco.h>
- 验证：conan create test_package 编译链接运行 exit 0
- 适用范围：glib 系 autotools 库的 CMake 消费者
- 四范围查重：E216 覆盖核心机理（components 传播失效 + glob fallback）；本候选是**触发面变体**：传递依赖 vs 直接依赖的 INCLUDE_DIRS 差异，方案的"显式声明直接依赖"在 AbiWord 插件 notes.md 已有记录，草稿/正式知识无独立条目
- 七轴：
  - exact_duplicate: false（E216 是 glob fallback 方案，本候选是显式 requires 方案）
  - causal_duplicate: true（同一根因：CMakeDeps 不传播组件 include）
  - trigger_overlap: true（同为 glib.h not found 触发）
  - solution_overlap: true（路径 A 已有 notes 先例，无需新知识）
  - combination_novelty: false
  - boundary_novelty: false（同为 OHOS+CMakeDeps+glib 边界）
  - test_migration_novelty: false

### 候选5（观察项）：上游 test-output-refs 参考输出陈旧（2003-2004 生成）与 0.6.13 修复后行为不一致
- 真实证据：test2.1/test2.2/test4.1 三个输出对比 diff；gitlab API 实证参考文件最后提交 2003-04-04/2004-03-04；ChangeLog 记载 Bug 381040（浮点固定 3 位小数）、Bug 314831/394294（转义计算）修复在参考生成之后；cr-num.c 最后修改 2014-08-05
- 根因：上游修复行为后未重新生成 test-output-refs（非回归参考陈旧）
- 修复/处置：不做库行为回退（不伪造测试）；台账如实记录 13/16 通过，3 项差异归属 upstream 参考陈旧，附恢复条件（上游 testctl ref 重生成）
- 验证：字节级 diff + gitlab API 提交时间 + ChangeLog 三证据互证
- 适用范围：任何携带 20 年以上 test-output-refs 的老 autotools 库
- 四范围查重：正式知识无此主题（E365 是 MPI test oracle 另一主题）；图谱未命中；草稿无；operations 无
- 七轴：exact_duplicate=false; causal_duplicate=false（知识库无同因条目）; trigger_overlap=false; solution_overlap=false; combination_novelty=false; boundary_novelty=false; test_migration_novelty=false（唯一证据属库自身，不是跨库可复用解决方案——已在台账记录，不满足"已验证且可跨库复用并存在新增差异"路径 B 门槛）

## 路径判定

- 候选1/2/3：**reuse_existing**（E122/E011/E236 完全覆盖，无新增差异）
- 候选4：**reuse_existing**（根因与 E216 causal_duplicate；方案先例在 notes；无独立知识价值）
- 候选5：**path_a_no_knowledge**（观察已入本台账，无跨库可复用新方案；不建草稿）
- final_path = path_a_no_knowledge：本库为常规适配（虽标【高难度挑战】，但知识层面全部命中既有条目），
  无需新建 knowledge 草稿；任务前缀仍按任务头保持【高难度挑战】

---

## R02 复核（2026-09-10，upstream reference remediation 返工）

### 变化：候选5 升级为可跨库复用知识，建立 E543 草稿对

R02 实际完成"上游测试参考输出陈旧"的完整处理并全量通过（16/16），证明该
方法论（三证据证明链 + 配方管理最小补丁）已验证且可跨库复用（任何携带
2003-2004 年冻结 test-output-refs 的老 autotools 库都适用）——满足 R02 任务
"任一已验证、可跨库复用新增差异必须建立同 stem .md/.kv 草稿对"：

- 草稿：`knowledge/drafts/E543-draft-4CD6.kv` + `knowledge/drafts/E543-draft-4CD6.md`
  （同 stem 配对；.kv 含 error_signature/root_cause/rec_approach/verification；
  .md 含错误特征、触发条件、根因、三证据证明链方案、禁止做法、验证命令）
- 状态：Draft（未建正式条目、未入 index.tsv——R02 任务要求草稿不建正式条目或索引）
- 候选1-4 结论不变（reuse_existing）

### R02 最终路径判定

- 候选1/2/3：reuse_existing（不变）
- 候选4：reuse_existing（不变）
- 候选5：**new_draft（E543）**——三证据证明链 + 配方管理补丁更新陈旧参考，
  可跨库复用、查重未命中既有条目（草稿区无同主题；DRAFT-ccfits-2.7-stale-pc-prefix-regen
  为另一类"陈旧资产"：依赖 .pc prefix，非测试参考）
- 七轴复核：exact_duplicate=false; causal_duplicate=false; trigger_overlap=false;
  solution_overlap=false; combination_novelty=true（"三证据证明链 + 配方管理
  参考补丁"为独立组合方案）; boundary_novelty=true（老 autotools 库 OHOS 适配
  的参考陈旧处理边界）; test_migration_novelty=true（参考输出由冻结资产转为
  配方管理补丁维护的迁移路径）
- 最终决定：路径 A 基础 + 新增 E543 草稿对（R02 要求），PR 前缀仍为【高难度挑战】