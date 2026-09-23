# dwarves 1.30 知识候选台账（knowledge_candidate_ledger）

任务: dwarves-1.30-r01-pc1-26 · 路径: 知识库扩展（路径 B 判定见文末）
查重范围: knowledge/doc/（正式 E###.md）、knowledge/graph/（E###.kv + index.tsv）、
knowledge/drafts/（草稿 .md/.kv）、SUMMARY.md 四范围

## R03 补充候选查重（2026-09-11）
### 候选 A：上游测试入口 /tmp 硬编码 → ${TMPDIR:-/tmp} 可配置适配
- 查重: **完全重复/复用** — E052（modify_tmpdir：临时目录适配）、E002（set-env-var /tmp 只读）、
  E223（secure tmp 0700 语义验证）已覆盖同根因与方案；R03 仅把它应用为上游测试入口的最小兼容修复，
  无新增跨库适配事实 → **reuse_existing**，不建新草稿
### 候选 B：musl 缺 glibc qsort_r，bpftool 构建需 glibc 兼容垫片
- 查重: **部分覆盖/复用** — E029、E151、E186、E211、E312 等覆盖 musl 缺 glibc 符号/功能类；
  qsort_r 属 musl 缺失 glibc 符号的一般模式，bpftool 是应用实例，根因与方案已被既有条目覆盖
  → **reuse_existing**，不建新草稿（bpftool 构建产物不入归档，仅测试临时目录工具）
### 草稿成对核对（R01 两对 + 本轮）
- DRAFT-dwarves-public-header-shim-transitive：.md/.kv 成对 ✅
- DRAFT-dwarves-ohos-cmake-soname-flag：.md/.kv 成对 ✅
- 本轮无新草稿（R03 两候选均复用既有条目），无新增草稿需要配对

## R02 补充候选（2026-09-11）：pre-download 正则误抓 conandata.yml 注释 URL 污染 sources.url
- 真实错误: W3 中 conan create 失败，sources.url 被改写为
  `https://gh-proxy.com/file://.../predl_cache/0baa4c3e_dwarves/archive/refs/tags/v1.30.tar.gz`（403 + NotADirectoryError）
- 根因: build_and_test.sh pre-download 正则从 conandata.yml 提取所有 `https?://` 串，
  注释行 `# 官方来源: https://github.com/acmel/dwarves` 被误抓为源码 URL，
  下载 7738B HTML（GitHub 仓库主页）存为 predl_cache/{hash}_dwarves；随后
  replace 把 sources.url 中同子串污染为 file:// 路径；
  R02-1 恢复官方 URL 后重跑 W3 仍复现 → 修复: 注释去掉 `https://` 前缀 + 清理陈旧 predl_cache 条目
- 验证: 注释改为 `github.com/...` 后 W3 通过（conan create rc=0，finish EXIT_CODE 0）
- 查重: **部分覆盖/同根因** — E333（pre-download 正则提取缺陷，连字符截断场景）已记录
  同脚本正则提取问题；E415（CI 镜像改写需恢复）相关。本轮是"注释 URL 误抓"新增触发场景，
  根因同 E333 的 pre-download 正则，修复方向同为规避正则误判 → **reuse_existing E333**，
  不新建草稿（新增差异不足以跨库独立复用；草稿 DRAFT-conan-downloader 亦已覆盖下载器语义）
- 恢复条件: 无（已就地修复）

## 候选 1：E091 sockaddr_storage 重定义（libbpf netlink.c/nlattr.c）
- 真实错误: `redefinition of 'sockaddr_storage'`，OHOS linux/socket.h 与 musl sys/socket.h 冲突
- 根因: OHOS 内核头无条件定义 struct sockaddr_storage，与 musl libc 重名
- 修复: include 期间 `#define sockaddr_storage __linux_sockaddr_storage` + `#undef`（define-guard）
- 验证: conan create 通过，libbpf 全部编译成功；W3 L0/L4 通过
- 适用范围: 任何包含 linux/netlink.h + sys/socket.h 链的 OHOS 源码
- 查重: **完全重复** — knowledge/doc/E091.md、knowledge/graph/E091.kv、index.tsv:317 已存在，
  trigger/root_cause/solution 逐项一致 → **reuse_existing**（复用 E091，不建新草稿）

## 候选 2：dwarves.h 公开头 include musl 垫片头（obstack/argp）与 elfutils 头
- 真实错误: 消费者仅 link dwarves::dwarves 时 `fatal error: 'obstack.h' file not found`（随后 dwarf.h）
- 根因: dwarves.h（公开头）第 14-16 行直接 #include <obstack.h>/<dwarf.h>/<elfutils/libdwfl.h>；
  OHOS-musl 下由 musl-obstack/argp-standalone/elfutils 提供；CMakeDeps 对传递依赖生成
  include 元数据为空（生成 data 中 INCLUDE_DIRS_RELEASE 空），消费者必须显式 requires+link
- 修复: 消费者（test_package）显式 `self.requires("musl-obstack/1.2.3")("argp-standalone/1.5.0")("elfutils/0.195")`
  + CMakeLists 显式 find_package 并 link 三个 target
- 验证: test_package 编译链接运行通过（consumer: OK），W3 L1 pass
- 适用范围: 任何公开头传递 include 第三方库头文件的 Conan 2 library 消费者
- 查重: **部分覆盖** — DRAFT-conan2-cmakedeps-transitive-include-strip（pokerstove/boost 案例）
  已覆盖 CMakeDeps 传递 include 置空根因；本候选新增差异: musl 垫片头（obstack/argp）+ 库自身
  公开头链的具体场景与三 target 显式链接验证 → 建 dwarves 专属草稿（同 stem .md/.kv）

## 候选 3：/tmp erofs 只读导致上游测试平台阻塞
- 真实错误: `mktemp: /tmp/...: Read-only file system`（pfunct-btf-decl-tags.sh）
- 根因: OHOS /tmp 为 erofs 只读挂载；候选挂载点（HMDFS 2771、/、/dev/shm、/data）均不满足
  真实可写/0700 语义
- 修复: 按 SKILL 临时目录恢复规则枚举候选目录并 TMPDIR/TMP/TEMP 重跑，仍命中同一首错
  （mktemp 模板含 /tmp 绝对路径），记录平台阻塞计入分母
- 验证: 候选目录 stat 输出已记录（test-ledger.md），重跑命令与退出码完整
- 适用范围: 所有依赖 /tmp 可写的上游测试（OHOS 平台）
- 查重: **完全重复** — E002（set-env-var: /tmp erofs 只读 TMPDIR 方案）、E223
  （secure tmp 需联合验证 owner/mode/0700）已覆盖 → **reuse_existing**

## 候选 4：OHOS 无 CMake 平台模块导致 SOVERSION 不产出 DT_SONAME
- 真实错误: W3 L5a `libdwarves.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址`
- 根因: OHOS 无 CMake 平台模块（"System is unknown to cmake"），
  CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义，SOVERSION 不产出 DT_SONAME
- 修复: 配方 generate() 中 `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"`
- 验证: 产物 libdwarves.so.1/so.1.0.0 + DT_SONAME 出现（llvm-readelf 确认），W3 L5a pass
- 适用范围: 任何在 OHOS 上使用 CMake SOVERSION 的共享库配方
- 查重: **部分覆盖** — E274（create-soname-symlink，打包期符号链接缺失）、E316
  （copy-soname-entity，打包期实体缺失）覆盖"打包期"SONAME 问题；本候选是"构建期
  SOVERSION→DT_SONAME flag 未注入"，trigger_overlap 但 solution 新增（toolchain 变量注入）→
  建草稿（同 stem .md/.kv）

## 候选 5：GitHub release tarball 不含 lib/bpf 子模块
- 真实错误: CMakeLists `The submodules were not downloaded!` / btf.h 缺失 FATAL
- 根因: GitHub archive tarball 只含 git tree 快照，不含子模块内容
- 修复: conandata 记录 libbpf 锁定 commit（42a6ef6）+ source() 单独 get 到 lib/bpf
- 验证: conan create 全流程通过，libbpf 内嵌编译成功
- 适用范围: 任何内嵌子模块且以 GitHub tarball 为源的 C/C++ 库
- 查重: **部分覆盖** — DRAFT-rapidyaml-0.7.2-c4core-cmake-submodule-vendoring（rapidyaml/c4core
  案例）已覆盖同根因；本候选新增差异: 通过 conandata 记录锁定 commit + source() get 的方式，
  与 rapidyaml 的 export_sources 打包恢复不同实现 → 合并入候选 2/4 所在草稿组，不单独建草稿
  （solution_overlap 高，组合新颖性低）

## 七轴查重（对候选 2/4 两个将建草稿的候选）
| 轴 | 候选2（公开头传递） | 候选4（SONAME flag） |
|---|---|---|
| exact_duplicate | false（仅草稿，非正式条目） | false（E274/E316 为打包期场景） |
| causal_duplicate | false（根因同 DRAFT，但组合场景新增） | false（根因不同：构建期 flag vs 打包期实体） |
| trigger_overlap | true（fatal error: header not found） | false→partial（SONAME 相关但阶段不同） |
| solution_overlap | true（显式 requires 传递依赖） | partial（注入 flag vs 建 symlink） |
| combination_novelty | medium（垫片头三 target 组合验证） | medium（toolchain 变量注入 OHOS 场景） |
| boundary_novelty | true（公开头链依赖垫片头的新边界） | true（无 CMake 平台模块 → SONAME flag 缺失） |
| test_migration_novelty | false（复用同一 test_package 机制） | false |

## 路径判定
- **reuse_existing**: 候选 1（E091）、候选 3（E002/E223）— 完全重复，复用既有条目
- **new_draft（路径 B）**: 候选 2（dwarves 公开头 musl 垫片/elfutils 传递）与
  候选 4（OHOS SOVERSION→DT_SONAME flag）— 部分覆盖且有已验证、可跨库复用的新增差异
  → 建立 DRAFT-dwarves-public-header-shim-transitive 与 DRAFT-dwarves-ohos-cmake-soname-flag
  两对 .md/.kv 草稿，随 dwarves 归档同 PR 交付
- path_a_no_knowledge: 不适用（本任务为知识库扩展路径，已有可复用知识）
