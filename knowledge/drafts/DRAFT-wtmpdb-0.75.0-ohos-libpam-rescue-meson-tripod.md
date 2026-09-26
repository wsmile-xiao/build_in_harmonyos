# wtmpdb 0.75.0 — OHOS 无系统 libpam 的 meson 救援三脚架（draft）

**Category**: ohos | pam | meson | conan | portability · **Severity**: 2 · **Tool**: meson|cc|conan

## 症状

需要 PAM 的 meson 包在 OHOS 上 configure 直接 fatal：

```
meson.build:94:12: ERROR: C shared or static library 'pam' not found
```

即使补了依赖，还会撞上 distro 式布局自检：

```
meson.build:88:8: ERROR: Problem encountered: Prefix is not below root prefix (now rootprefix=/usr prefix=/)
```

## 根因（三层）

1. **OHOS sysroot 与 harmonybrew 都没有 libpam**（全仓 find 为空）——`find_library('pam')` 上游是硬依赖。但**制品仓已发布 linux-pam/1.7.2**：`libpam.so/.so.0`、`include/security/*.h`、模块目录（testlog 环境里可见 `LINUX_PAM_MODULE_DIR=<pkg>/lib/security`），`conan install --build=never` 实测可用。
2. **meson `find_library()` 不吃 pkg-config**：PkgConfigDeps 只救 `dependency()`；find_library 走编译器链接行，conan 构建环境默认看不见依赖包目录 ⇒ 必须 `Environment(scope=build)` 前置 `LIBRARY_PATH`（链接探测）、`CPATH`（头文件）、`LD_LIBRARY_PATH`（meson test 运行期解析 PAM 模块的 DT_NEEDED）。
3. **conan meson 约定（`-Dprefix=/` + install 时 DESTDIR=package_folder）与上游 rootprefix 自检结构冲突**：显式 `-Dsplit-usr=true` 使 rootprefix='/' 与 prefix 相等即通过；rootlibdir 由 libdir 相对派生，pam 模块经 DESTDIR 落到 `package_folder/lib/security`。

## 验证（wtmpdb 0.75.0，HongMeng 1.12.0）

- 接线后 `conan create` G1–G4 全绿；`meson test` 6 注册 = **4 Ok + 2 上游自退 77**（tst-get_id 需 /var 可写、tst-varlink 需 root，均非移植缺陷，账本如实分类）；
- 关键读数：`dlopen() of "./pam_wtmpdb.so" succeeded` —— **PAM 模块在 OHOS 可构建、可加载**；
- 消费者 6/6：真调 `wtmpdb_login/logout/read_all/get_id` 断言 sqlite 记账（含 -2=无开放会话、-14=SQLITE_CANTOPEN 语义）。

## 适用边界

适用于一切 OHOS 上需要 PAM 的包（模块本体、pam_start 登录链、su/pam_* 工具）；第 2、3 脚（find_library 注入、split-usr 对表）与 libpam 无关，独立适用于任何用 find_library 消费 conan 依赖或带 distro 布局自检的 meson 包。

## 查重分界

| 条目 | 差异 |
|---|---|
| DRAFT-util-linux-login-2.42.2-…-pam-portability | autotools + GNU utmpx 符号路径；本条是 meson + find_library/布局路径，互补组网 |
| E394（LD_PRELOAD/PAM_WRAPPER fixture） | 本方案不经 pam_wrapper，直接 dlopen 真模块，签名与解法均不同 ⇒ 非 hit |
| E121（setutxent/pututxline 缺失） | wtmpdb 是 sqlite3 上的替代实现、非 utmpx 调用方；utmpx 命中 0 ⇒ 不适用 |
