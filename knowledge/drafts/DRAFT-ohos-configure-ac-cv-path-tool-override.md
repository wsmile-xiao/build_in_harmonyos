# DRAFT-ohos-configure-ac-cv-path-tool-override — autotools configure 工具探测命中系统 curl-config 的 ac_cv_path__* 覆盖

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: 🟡 medium | **Category**: configure / autotools / tool-probe / cache-variable

## 相关既有条目（同族差异化定位）

本 skill 与既有"工具链/依赖探测"类条目共享 configure 探测背景，但拦截面是
**autoconf 缓存变量的用户覆盖**，与既有条目（都是具体库的编译报错）非重复；
申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 同族点 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E272**（arm-none-eabi-binutils） | 正式收录 | 上游库编译报错场景 | 非本题——E272 是 LD_PRELOAD tmpfile shim；本条目是 configure **探测阶段**的缓存变量覆盖，问题层不同 |
| **E005**（-fPIC/relocation） | 正式收录 | 链接期 | 非本题 |
| **E079**（HMDFS 硬链接） | 正式收录 | 文件系统 | 非本题 |
| **asterisk-pgsql（PR #7331）** | main 已收录配方 | 同 asterisk 变体模式，用 pg_config shim + `--with-postgres` | 本条目新增 **`ac_cv_path__libcurl_config` 缓存变量覆盖**（pgsql 未用 ac_cv_path——它靠 `--with-postgres` 指向 ${PGSQL_DIR}/bin） |

> index.tsv 查证（2026-09-02）：`ac_cv_path` 命中 0 条正式条目、`curl-config` 命中 0 条、
> `AST_MODULE_SELF_SYM` 命中 0 条——无正面撞车；`E272` 仅同族 LD_PRELOAD 背景。

## Scope（何时用）

在 HarmonyOS PC（或任何 PATH 中同时存在系统工具与 conan 私有 prefix 工具）上
适配 autotools 库时，若出现：

- configure 日志 `checking for curl-config... /usr/local/bin/curl-config`
  （或 `pg_config`/`xml2-config` 等同类工具命中系统路径）；
- 生成的 makeopts 里 `CURL_INCLUDE=-I/usr/local/include`（该目录无 `curl/curl.h`）；
- 模块/库编译报 `curl/curl.h: No such file or directory`；
- 若又覆盖了 menuselect.makeopts 快照，还会叠加
  `Externally compiled modules must declare AST_MODULE_SELF_SYM.`

典型实例：asterisk-curl（res_curl/func_curl/res_config_curl 模块）。

## Symptom

```text
configure: checking for curl-config... /usr/local/bin/curl-config
# makeopts: CURL_INCLUDE= -I/usr/local/include   （无 curl/curl.h）
make -C res res_curl.so
→ [CC] res_curl.c -> res_curl.o
→ include/asterisk.h:235:2: error: "Externally compiled modules must declare AST_MODULE_SELF_SYM."
→ res_curl.c:45:10: fatal error: 'curl/curl.h' file not found
```

## Root Cause

1. asterisk 的 `AST_EXT_LIB_CHECK([CURL], curl, curl_easy_init, curl/curl.h, curl-config)`
   经 `AC_PATH_TOOL` 按 `PATH` 顺序探测 `curl-config`——系统
   `/usr/local/bin/curl-config` 存在且排在前，configure 命中它；
2. 系统 curl-config 的 `--cflags` 报 `-I/usr/local/include`，该目录**没有 curl/curl.h**；
   `--libs` 报 `-L/usr/local/lib -lcurl`（系统库）——两者都指向非期望位置；
3. autoconf 把探测结果缓存进 makeopts 的 `CURL_INCLUDE`/`CURL_LIB`，模块编译按此
   找头文件 → file not found；
4. 额外坑：若复制其他 asterisk 变体（如 pgsql）的 menuselect.makeopts 快照覆盖，
   快照把 curl 模块标 `MENUSELECT_DEPSFAILED` → make 不定义 `AST_MODULE_SELF_SYM`
   → 双重报错。

## Recommended Solution

**主方案：私有 prefix 注入 curl-config shim + `ac_cv_path__libcurl_config` 缓存变量覆盖。**

1. `_ensure_libcurl(prefix, ...)`：把 libcurl 包的 include/lib 复制进私有 prefix，
   `_fix_pc_prefix` 改写 `libcurl.pc` 的 `prefix=`；
2. `_ensure_curl_config_shim(prefix)`：在 `prefix/bin/curl-config` 放 shim——
   `--cflags` 报 `-I<prefix>/include`、`--libs` 报 `-L<prefix>/lib -lcurl`；
   若 libcurl 包自带 curl-config（`_ensure_dep_present` 会复制 include/lib 与 bin），
   shim 仅在包内缺失时兜底；
3. configure 命令行显式传
   `ac_cv_path__libcurl_config=<prefix>/bin/curl-config`——autoconf 缓存变量
   **支持用户覆盖**，configure 直接使用该路径，跳过 PATH 探测；
4. **不要**覆盖 configure 生成的 menuselect.makeopts（只注入 menuselect.makedeps
   声明模块依赖）——让 configure 检测到 CURL 后自然把模块标记为启用，
   `AST_MODULE_SELF_SYM` 与 `CURL_INCLUDE` 一并正确。

```sh
./configure --prefix=/ --host=aarch64-unknown-linux-ohos \
  CPPFLAGS=-I<prefix>/include LDFLAGS=-L<prefix>/lib \
  PKG_CONFIG_PATH=<prefix>/lib/pkgconfig \
  --with-curl=<prefix> \
  ac_cv_path__libcurl_config=<prefix>/bin/curl-config \
  ac_cv_prog_cc_works=yes
```

**回退方案**：若无法用缓存变量覆盖（configure 版本不支持），只注入
menuselect.makedeps、保留 configure 生成的 makeopts，再对 makeopts 里空的
`CURL_INCLUDE=`/`CURL_LIB=` 做字符串替换兜底指向 prefix。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **asterisk-curl/22.10.1** | 主验证（本 PR） | ✅ 覆盖前 `CURL_INCLUDE=-I/usr/local/include` → res_curl.o 编译失败；覆盖后 `CURL_INCLUDE=-I<prefix>/include`，res_curl/func_curl/res_config_curl 三模块编译链接成功，conan create 通过 |

## 测试覆盖边界

- shim 只影响 configure **探测结果**（头文件/库路径），不进入 package 产物，
  不改变库行为；
- 声明通过率时：以 conan create 全流程（含 test_package R34 校验）为实证；
  curl 模块无专属上游测试，按 rule 1.2 如实声明"上游无测试"（非跳过）。
