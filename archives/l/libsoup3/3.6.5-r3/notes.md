# libsoup3 3.6.5-r3 适配笔记（依赖发布形态修复）

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-10
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 工具链）
- 状态: built（本地 conan create 通过，待 CI 发布）

## 背景与唯一目标

libshumate 1.6.3 适配链中，ohpcd 已发布的 libsoup3/3.6.5-r2 二进制把 gobject
**静态内嵌**进 libsoup-3.0.so.0（NEEDED 无 libgobject-2.0.so.0，自带
g_type_register_fundamental 强定义），而 gtk4/4.22.4 链接**共享**
glib/2.84.0.1.1（NEEDED libgobject-2.0.so.0）。任何同时加载两者的进程启动期
发生双 GObject 类型系统冲突（cannot register existing type 'gchar'，
gvaluetypes.c:453 SIGABRT），导致 libshumate 16 个上游测试全部 0/16。

本版本 3.6.5-r3 修复发布形态：声明 glib/2.84.0.1.1（shared）依赖（对齐 gtk4
链 r85/r86 硬约束），构建并交付链接共享 glib 的二进制，消除静态内嵌 gobject
副本。禁止使用原版本号 3.6.5 / r1 / r2 提交本次修复。

## 与 r1 配方的关键差异

| 项 | r1 | r3 |
|----|----|----|
| glib 依赖 | glib2/2.88.0（独立包，静态/共享不定） | glib/2.84.0.1.1 shared=True（gtk4 同链） |
| 发布形态 | r2 曾静态内嵌 gobject | libsoup-3.0.so.0 NEEDED 含 libgobject-2.0.so.0 |
| 系统库拼接 | test_package 拼 /usr/local/lib | 全部依赖 conan 共享包，不再拼接 |
| zlib override | 需要（glib2 拉 zlib/1.3.1） | 不需要（glib/2.84.0.1.1 已 pin zlib/1.3.1.1） |

## 编译步骤

```bash
curl -fL -o libsoup-3.6.5.tar.xz \
  https://download.gnome.org/sources/libsoup/3.6/libsoup-3.6.5.tar.xz
sha256sum libsoup-3.6.5.tar.xz   # 6891765aac3e949017945c3eaebd8cc8216df772456dc9f460976fbdb7ada234

conan create archives/l/libsoup3/3.6.5-r3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | r2 静态内嵌 gobject 与 gtk4 共享 glib 双副本 SIGABRT | libsoup3 链接了非共享 glib 副本 | r3 强制 glib/2.84.0.1.1 shared=True，NEEDED 含 libgobject-2.0.so.0 |
| 2 | meson 探测 gmodule-no-export-2.0/gio-unix-2.0 | PkgConfigDeps 只生成 glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gthread-2.0.pc | 复制 glib 包内 lib/pkgconfig 的 .pc 并修 prefix 进 pc-fix 目录 |
| 3 | gnome.mkenums/gdbus-codegen 缺工具 | conan 生成的 glib-2.0.pc 无 glib_mkenums 变量 | 从 glib 包 bin 目录 pin 工具绝对路径进 meson native file [binaries] |
| 4 | AR=llvm-ar 等环境变量坏 | PATH 无 llvm-ar | generate() 里 os.environ.pop + shutil.which 定位真实工具 |
| 5 | OHOS loader 校验 .codesign | meson install 清理 DT_RUNPATH 改写 .so 内容 | package() 用 builddir 原始链接产物覆盖被改 .so |

## 发布形态取证（任务必查）

```bash
# 修复后（r3）：NEEDED 必须含 libgobject-2.0.so.0
llvm-readelf -d libsoup-3.0.so.0 | grep NEEDED
# 修复后（r3）：不得再强定义导出 g_type_register_fundamental
llvm-nm -D libsoup-3.0.so.0 | grep ' T g_type_register_fundamental'   # 无命中
# 进程级复验：链接 libsoup 的小程序/test_package 启动无 'cannot register existing type' 报错
```

## 验证结果

```bash
conan create ... --build=missing   # 成功，test_package L1 通过
conan list "libsoup3/*"            # libsoup3/3.6.5-r3@ohpcd/stable 在缓存
```

## 注意事项

- libsoup3 下游（gssdp/gupnp/libshumate）必须消费 3.6.5-r3 或更新的共享 glib 形态
- 运行 test 二进制时需 export LD_LIBRARY_PATH 覆盖全部依赖 libdirs（r3 已全 conan 包）

## 上游测试完整枚举台账与双口径统计（2026-09-10 实测）

### 枚举规则（可复制）
- 源：官方 tag libsoup-3.6.5.tar.xz `tests/*-test.c`
- 枚举命令：`grep -cE 'g_test_add_func|g_test_add_data_func|g_test_add *\\(' tests/*-test.c`
- 独立用例定义：用户测试源中的 g_test 注册调用点（每个注册点=1 独立 TEST_CASE）；
  框架内部宏、宏前缀命中、SECTION 子节、样例/基准不计入独立用例。

### source_declared_total
- 38 个测试源文件，392 个注册调用点（明细见下方文件清单）
- 条件注册排除：auth(28)/connection(12)/range(2)/proxy(5, 需 apache have_apache=false) 未注册
  → 当前 OHOS 配置实际注册的测试可执行 = 34 个（meson tests 数组 32 + unix-socket 1 + brotli-decompressor 1）

### configured_executable_total
- 34 个测试可执行目标（tests/*-test）在当前 OHOS 配置全部构建成功（ninja BUILD_EXIT=0）
  （R08 测试迁移补丁：brotli/1.2.0.1 已发布（revision 79807221），配方 requirements 声明
  brotli + generate() brotli=enabled + brotli 真实 .pc 注入，brotli-decompressor-test 恢复注册）
- 其中 http2-test(35 注册点) 因 `if (!tls_available) return 0;`（OHOS GDummyTlsBackend
  无 TLS 后端）注册后 0 用例执行；unix-socket-test(1) 因平台禁止绑定 unix socket 无法运行

### executed_passed_total = 416
实际运行 30 个测试二进制（纯单元+本地 server 测试），全部 exit=0，TAP ok 行合计 416：
date 66, websocket 55, sniffing 38, redirect 29, multithread 21, ntlm 21, misc 18,
server 18, request-body 18, samesite 16, cookies 14, server-auth 12, continue 12,
coding 11, header-parsing 8, cache 7, ssl 7, session 6, logger 6, forms 5,
multipart 4, uri-parsing 4, streaming 4, timeout 4, http2-body-stream 3,
brotli-decompressor 3, context 2, tld 2, chunk-io 1, no-ssl 1

### 失败/未运行（计入分母，不计通过）
| 入口 | 注册点 | 结果 | 首错 | 阻塞归属 |
|------|-------|------|------|---------|
| hsts-test | 25 | exit 133 SIGTRAP | GLib-FATAL-CRITICAL: g_uri_get_port assertion 'uri != NULL' failed | 测试内 uri 为 NULL（server 未成功提供 base_uri），glib 断言 abort |
| hsts-db-test | 3 | exit 133 SIGTRAP | 同上 | 同上 |
| unix-socket-test | 1 | exit 1 | Unable to bind unix socket: Operation not permitted | 平台沙箱禁止 unix socket 绑定 |
| http2-test | 35 | exit 0, 0 用例执行 | if (!tls_available) return 0（GDummyTlsBackend） | 平台无 TLS 后端，TLS 类用例整体未实例化 |

### 汇总
- 上游统计：416/392 注册点口径已超 100% 系循环注册展开所致（如 websocket close_clean_tests
  循环按数据表展开注册），以 TAP 实际执行数为准
- 通过率：416 通过 / (416 + 25 + 3 + 1 + 35 失败/未运行) = 416/480 = 86.7%
  （R08 brotli 恢复后：brotli-decompressor 3 注册点由"未注册"转为"已实例化并运行通过"，
  分母相应 +3；auth/connection/range/proxy 47 注册点因 apache 基础设施缺失仍保留未注册）
## 知识候选台账与七轴查重（2026-09-10）

### 候选
- 标题：libsoup3 发布形态修复——静态内嵌 gobject → 共享 glib/2.84.0.1.1（配方级修复方案）
- 真实错误：libsoup3/3.6.5-r2 二进制静态内嵌 gobject，与 gtk4 链共享 glib 双副本导致
  cannot register existing type 'gchar' SIGABRT（libshumate 16 测试 0/16）
- 根因：r2 配方未对齐 gtk4 链的共享 glib 依赖，链接进非共享 glib 副本
- 修复：r3 配方 requirements 用 glib/2.84.0.1.1 options={"shared": True}（gtk4 同链）；
  generate() 用官方 glib-2.0.pc 覆盖 PkgConfigDeps 生成版补 -lintl（soup-init 引用
  g_libintl_bindtextdomain）；剥 Requires.private（libpcre2-8 不在本包 PkgConfigDeps 输出）
- 验证：NEEDED 含 libgobject-2.0.so.0；nm -D 无 ' T g_type_register_fundamental'；
  test_package/ohos 专项进程级无 gchar 冲突；上游测试 413 例通过
- 适用范围：任何"静态内嵌 gobject 的发布二进制需要与共享 glib 链共存"的 OHOS 库配方

### 七轴查重（对照 DRAFT-libshumate-libsoup3-static-gobject-dual-glib-sigabrt）
- exact_duplicate: false — 既有草稿记录问题识别+阻塞上报+恢复条件（分析端发布共享 glib 变体）；
  本候选是该恢复条件的**配方级实现**（依赖侧修复），内容不同
- causal_duplicate: false — 因果链相关（同根因）但本候选是修复实现而非重复报告
- trigger_overlap: true — 触发面重叠（libsoup3 × gobject 双副本主题）
- solution_overlap: partial — 既有草稿 Rec 只写"分析端发布共享 glib 变体"无配方细节；
  本候选给出完整可执行配方（requires shared 对齐 + pc 覆盖 + 取证命令），为增量方案
- combination_novelty: true — 新组合：共享 glib 依赖对齐 + 官方 glib-2.0.pc 覆盖补
  -lintl + Requires.private 剥除 + NEEDED/符号取证方法
- boundary_novelty: true — 新增边界：gssdp 单副本方案在含 gtk4 链时不可用 → 改为
  **依赖侧修复**（库自身链接共享 glib），消费者即可正常加载；恢复条件命中即本修复
- test_migration_novelty: true — 验证方式迁移：libshumate 0/16 阻塞 → 本修复后
  libsoup3 自身上游测试 413 例实测通过 + 进程级 gchar 冲突消除取证

### 路径决定
- reuse_existing: false（既有草稿是问题报告，本候选是修复方案，非完整重复）
- new_draft: true（配方级修复方案可跨库复用 → 路径 B：知识库扩展）
- 建立同 stem 草稿：DRAFT-libsoup3-shared-glib-release-form-fix.{md,kv}
- PR 前缀按任务规则：仅 new_draft 且 .md/.kv 配对通过时用【知识库扩展】；
  默认 initial_pr_prefix 为【依赖项】——本任务建 new_draft 后改用【知识库扩展】
---

**编译结束**: 2026-09-11 13:55
**最终状态**: built
