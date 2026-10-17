# E430 — COIN-OR autotools 配方依赖发现方式决定 libtool 是否解析依赖包 .la（libdir='//lib' 无效路径）：显式 --with-*-lib 绝对 .a 注入是最稳路径

## 错误特征
- `libtool: link: '//lib/libClp.la' is not a valid libtool archive`
- 前导 `grep: //lib/libClp.la: No such file or directory` / `sed: …No such file`
- 直接后果：`make -j1` 链接 libCbc.la 失败（Error 1）→ ConanException Error 2 → `cbc/2.10.13 build failed`（CI 全新构建权威复现，PR #10898）
- 相关同族告警：`archive member 'libOsiClp.a' is neither ET_REL nor LLVM bitcode`（嵌套归档形态）

## 触发条件
- 构建系统: autotools + libtool（COIN-OR 家族：cgl/clp/cbc/coinutils/vol 等）
- 阶段: linking（make -j1 链接主库 .la）
- 前置条件: 配方 configure 仅传 `PKG_CONFIG_PATH + CPPFLAGS`、未传 `--with-*-lib` 显式绝对 .a 路径
- 环境: ohpcd 依赖包（clp/coin-or/coinutils/cgl/zlib）由 `configure --prefix=/` 构建，其 .la 内 `libdir='//lib'` 在设备上不存在
- 特性: CI 全新构建必现；本地增量构建复用旧对象可能不触发（R02 本地通过、CI 失败的教训）

## 根因分析
ohpcd 依赖包（clp/coin-or/coinutils/cgl/zlib）由 `configure --prefix=/` 构建，其 `.la` 内 `libdir='//lib'` 在设备上不存在。cbc 配方 configure 若仅传 PKG_CONFIG_PATH + CPPFLAGS（无 `--with-*-lib`），生成的 Makefile 用 `-lClp -lOsi -lz -lCoinUtils -lCgl -lOsiClp` 让 libtool 解析各依赖 `.la` → 执行 `grep/sed //lib/libClp.la` 均 No such file → 判定 `'//lib/libClp.la' is not a valid libtool archive` → libCbc.la 链接中断。

R02 曾因 osiUnitTest 段错误误判为 `--with-*-lib` 嵌套归档并移除注入（E430 初版方向相反），R03 恢复显式注入后修复：显式 `--with-*-lib` 传入绝对 `.a` 路径时 Makefile 直接引用可用归档，libtool 无需解析依赖 `.la`。

## 解决方案

### 推荐方案
`explicit-with-lib-absolute-archive-injection`：
configure 显式注入各依赖包的 `--with-*-incdir` 与 `--with-*-lib`，后者给出含传递依赖闭包的绝对 `.a` 列表，例如：
- `--with-coinutils-lib='<coinutils>/lib/libCoinUtils.a <zlib>/lib/libz.a -lm'`
- `--with-osi-lib='<osi>/lib/libOsi.a <coinutils>/lib/libCoinUtils.a <zlib>/lib/libz.a -lm'`
- `--with-clp-lib='<clp>/lib/libOsiClp.a <clp>/lib/libClpSolver.a <clp>/lib/libClp.a <osi>/lib/libOsi.a <coinutils>/lib/libCoinUtils.a <zlib>/lib/libz.a -lm'`
- `--with-osiclp-lib`、`--with-cgl-lib` 同构

同时保留 `PKG_CONFIG_PATH` 与 `osi.pc/osi-clp.pc` 兼容别名（E429）供上游 `AC_COIN_CHECK_PACKAGE` 探测。

### 禁止做法
- ❌ 仅传 PKG_CONFIG_PATH + CPPFLAGS 而省略 `--with-*-lib`（CI 全新构建必然触发 .la 解析失败）
- ❌ 依赖本地手工放置 .a 或增量缓存（本地通过≠CI 通过）
- ❌ 在配方内伪造/改写依赖包 `.la`（`libdir='//lib'` 是依赖包自身构建产物，不得修改依赖制品）

## 验证
```bash
conan create archives/c/cbc/2.10.13 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 期望 exit 0；日志中 grep -c 'is not a valid libtool archive' = 0
# libCbc.la 成功链接；cbc CLI 产出；p0033 冒烟 obj=3089；test_package 3/3 PASS
```

## 关联条目
- 相关: E429（osi.pc/osi-clp.pc pkg-config 兼容别名，前置条件之一）
- 相似: E236（.la 解析与嵌套归档同族告警）
