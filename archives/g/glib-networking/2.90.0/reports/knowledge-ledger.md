# glib-networking 2.90.0 知识候选台账与七轴查重

## 知识候选

候选 1（非噪声，具跨库复用性）：**OHOS 上 GLib 的 TLS 后端仅有 GDummyTlsBackend
（空实现），导致依赖 glib TLS 的库（libsoup3 http2 等）上游测试注册后 0 执行
（`if(!tls_available) return 0;`）→ 以 glib-networking（GLib 官方 TLS 后端 GIO
模块桥接 OpenSSL）提供真实 TLS 后端**。任何依赖 `g_tls_backend_get_default()`
返回真实后端的库（libsoup3、curl、libxml2 等）均可复用。

- 真实错误：libsoup3 3.6.5-r3 http2 上游测试 35 项注册后 0 执行；`if(!tls_available)
  return 0;`；OHOS 上 g_tls_backend_get_default() 仅返回 GDummyTlsBackend。
- 根因：glib 自带 GDummyTlsBackend 为空实现（不支持任何 TLS）；OHOS 缺 GLib 官方
  TLS 后端模块（glib-networking 的 gioopenssl.giognutls GIO 模块）。
- 修复：适配 glib-networking 2.90.0（Meson 构建，openssl 后端），将 gioopenssl.so
  GIO 模块安装到 glib 的 giomoduledir；消费进程加载模块后
  g_tls_backend_get_default() 返回 GTlsBackendOpenssl。
- 关键约束：glib 必须以 shared 形式存在（ohpcd 已发布 glib/2.88.3 shared），
  否则 GIO 模块 dlopen 与消费进程双份静态 glib → "cannot register existing type"。
- 验证：test_package 断言 10/10 通过（GTlsBackendOpenssl + 进程级 TLS 握手真实错误
  "wrong version number"）；libsoup3 http2 测试恢复执行。
- 适用范围：OHOS 上所有依赖 glib TLS API（GTlsConnection/GTlsCertificate/
  g_tls_backend_get_default）且需要真实 TLS 能力的库或应用。

## 七轴查重

检索范围：knowledge/graph/index.tsv（正式知识图谱 423+ 条目）与 knowledge/drafts/
（草稿，含 E550/E563/E464/E285 等）。

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无既有条目描述"glib TLS 后端缺失→glib-networking 桥接" |
| causal_duplicate | false | 同类根因（"默认空后端"）在音频域有 E285（openal-soft Null backend），但域不同、库不同，非同一因果链 |
| trigger_overlap | false | E464（mygui dummy resource）、E527（gtk broadway display backend）同为"空后端/显示后端 fallback"，但触发语言（运行时资源注册 / GTK 显示后端）与本次（GIO TLS 后端）不同；E550（gupnp）触发为**链接期** undefined symbol，与本次**运行时** TLS 缺失不同阶段 |
| solution_overlap | false | E550（ar 提取最小补链归档）、E285（禁用外部后端保留 null loopback）与本次（安装真实 TLS 后端 GIO 模块）方向相反：本次是"补上真实后端"，非"绕过空后端" |
| combination_novelty | true | "shared glib + GIO TLS 模块 + OpenSSL 后端"在 OHOS 上的组合适配为新增；依赖组合（glib/2.88.3 shared + openssl/3.5.8.1 + glib-networking 模块）无既有条目 |
| boundary_novelty | true | 适用边界清晰：任何调用 g_tls_backend_get_default() 且 libsoup3 http2 式测试依赖真实 TLS 的库；反例：仅用 G_DUMMY 后端可满足的库不需要此方案 |
| test_migration_novelty | true | "上游测试因 tls_available=false 0 执行 → 安装真实 TLS 后端后恢复执行"的迁移路径是新增的，可跨库复用于 libsoup3/curl 等任意 GLib TLS 依赖库 |

## 查重关系字段

- similar_to：E285（audio Null backend 默认空实现导致测试受限——同为"默认空后端限制上游测试"，但领域与解法均不同）
- caused_by：GLib 在 OHOS 上缺少官方 TLS 后端模块（glib-networking 未适配/未安装）
- prerequisite_of：libsoup3 http2 上游测试恢复（35 项从 0 执行恢复为真实 TLS 执行）
- conflicts_with：无

## 路径判断

七轴查重显示 exact/causal/trigger/solution 四轴均未命中既有条目，combination/
boundary/test_migration 三轴为新增差异，且已由本轮真实日志验证（test_package 10/10、
GTlsBackendOpenssl、进程级 TLS 握手错误、122 项次上游测试）并可跨库复用
（libsoup3/curl 等依赖 glib TLS 的库）→ 决定：**new_draft（路径 B），创建成对
.md/.kv 草稿，PR 前缀改用【知识库扩展】**。

（口径说明：任务头 initial_pr_prefix 为【依赖项】，但知识候选经完整多轴查重确认
属新增差异且可跨库复用，依任务 "仅 new_draft 且 .md/.kv 配对通过时改用【知识库扩展】"
规则生效。）