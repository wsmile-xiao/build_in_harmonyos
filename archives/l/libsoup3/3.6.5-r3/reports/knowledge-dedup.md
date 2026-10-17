# libsoup3 3.6.5-r3 知识候选台账与查重（R11）

## 候选 1：libsoup3 静态内嵌 gobject × 共享 glib 双副本 SIGABRT（发布形态修复）

- 本轮真实错误：libsoup3/3.6.5-r2 二进制把 gobject 静态内嵌进 libsoup-3.0.so.0
  （NEEDED 无 libgobject-2.0.so.0，自带 g_type_register_fundamental 强定义），
  与 gtk4/4.22.4 链接的共享 glib/2.84.0.1.1（NEEDED libgobject-2.0.so.0）
  同时加载时进程启动期双 GObject 类型系统冲突（cannot register existing type
  'gchar'，gvaluetypes.c:453 SIGABRT）→ libshumate 16 个上游测试 0/16。
- R11 修复：glib 依赖切换为 glib/2.84.0.1.1（shared=True, override，对齐 gtk4
  链 r85/r86），libsoup-3.0.so.0 NEEDED 含 libgobject-2.0.so.0，llvm-nm -D 无
  ' T g_type_register_fundamental' 强导出（取证见 reports/forensics/）。
- 生效范围：libsoup3 配方级（requirements/generate/package_info）+ test_package。

多轴查重（对照既有条目）：
| 轴 | 结论 | 说明 |
|---|---|---|
| exact_duplicate | false | 既有库内无 libsoup3 r3 同配方同版本条目 |
| causal_duplicate | false | 本连锁根因（静态内嵌 gobject）历史上未入库 |
| trigger_overlap | partial | 与 E444（GObject 显式 init，runtime-init）触发面有交集（同为 OHOS GObject 运行时），但 E444 是 .init_array 构造函数问题，本轮是动态链接形态冲突 |
| solution_overlap | partial | 与 E444 均为 glib/gobject 类方案，但 E444 是代码内 init，本轮是配方级依赖形态（shared glib），解决路径不同 |
| combination_novelty | true | "linked-shared-glib 配方对齐 + 双副本 SIGABRT"组合在 index.tsv 无同组合条目 |
| boundary_novelty | true | 适用边界：静态内嵌 gobject 的库与共享 glib 共存；反例：单一 glib 使用方无冲突 |
| test_migration_novelty | false（本轮无测试迁移成分） | 发布形态修复，非测试迁移 |

既有条目 E348/E444 均不覆盖"静态内嵌 gobject 与共享 glib 双副本"完整模式
（E444 为 .init_array 显式初始化，E348 为 pkg-config pc 转发）。
**路径决定：new_draft（路径 B，与既有 DRAFT-libshumate-libsoup3-static-gobject-dual-glib-sigabrt
同 stem 扩展 .md/.kv 成对草稿）——需确认既有草稿状态后决定 reuse or extend。**

## 候选 2：hsts/hsts-db g_uri_get_port(NULL) 断言 SIGTRAP 测试迁移（R11 核心）

- 真实错误：上游 tests/hsts-test.c:151-153、hsts-db-test.c:106-108
  rewrite_message_uri() 对 g_uri_get_port(https_uri) 无条件调用；OHOS 无
  glib-networking（GDummyTlsBackend supports_tls=0）→ tls_available=FALSE →
  https_uri 保持 NULL → glib 2.84 `GLib-FATAL-CRITICAL assertion 'uri != NULL'
  failed` → SIGTRAP exit 133。
- 修复：调用前判空守卫（https_uri != NULL ? 取端口 : 保持消息 URI 原样），
  只改 tests/hsts-test.c 与 tests/hsts-db-test.c，glib 2.84 语义，测试语义不变。
- 生效范围：上游测试代码迁移（补丁）、跨库可复用（任何在 glib 2.84+ 下调用
  g_uri_get_port 且可能传 NULL 的测试/代码）。

多轴查重（test_migration_novelty 轴为核心）：
| 轴 | 结论 | 说明 |
|---|---|---|
| exact_duplicate | false | 库内无 g_uri_get_port NULL 断言/该调用点条目 |
| causal_duplicate | false | 根因（glib 2.84 断言语义 + https_uri NULL）无既有条目表述 |
| trigger_overlap | partial | 与 E040（null pointer 系）/E259（NDEBUG assert）仅"NULL/断言"关键词重叠，机制完全不同（E040 是 man-db 内部 NULL；E259 是 assert 副作用） |
| solution_overlap | partial | 判空守卫属通用防御模式，但针对 glib 2.84 g_uri_get_port 语义的迁移无既有方案 |
| combination_novelty | true | "glib 2.84 g_uri_get_port NULL 断言 + OHOS 无 TLS 后端测试迁移"组合无既有条目 |
| boundary_novelty | true | 边界：TLS 后端不可用环境下的上游 https 测试；反例：有 TLS 后端环境不触发 |
| test_migration_novelty | true | 上游测试断言语义迁移（判空守卫）无既有成对草稿 |

**路径决定：new_draft（路径 B）——hsts g_uri_get_port(NULL) 测试迁移成对草稿。**

## 候选 3：brotli 测试迁移查重补做（R08 已做迁移，本轮补查重）

R08 迁移：brotli-decompressor-test 实跑 3/3 PASS（configured 33→34、passed
413→416、416/480=86.7%）。本轮补做查重：

| 轴 | 结论 | 说明 |
|---|---|---|
| exact_duplicate | false | 库内无 brotli 测试迁移条目 |
| causal_duplicate | false | 无 |
| trigger_overlap | false | brotli 测试依赖 brotli 压缩库可用性，与 hsts 不同触发 |
| solution_overlap | partial | 同为"上游测试纳入构建目标"通用做法，无条目标述 |
| combination_novelty | true | OHOS brotli 测试迁移组合无既有条目 |
| boundary_novelty | true | 边界：brotli 编译依赖满足即实跑；反例：无 brotli 依赖时禁用 |
| test_migration_novelty | true | R08 迁移 + 本轮查重，需成对草稿或并入本候选草稿 |

**路径决定：new_draft 或与候选 2 合建（同一测试迁移大类）；R08 未建草稿需补。**