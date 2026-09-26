# DRAFT-dnstap-ldns-0.2.1-protoc-pregen-pkgconfig-name：ohpcd protobuf-c 制品无 protoc-c 工具，autotools 消费方作者期预生成 .pb-c 绑定并 patch 掉构建期工具依赖（附 pkg-config 模块名边界）

> Contributor: pc4-23 | Status: Draft | Updated: 2026-09-25
> Source: dnstap-ldns 0.2.1 第一轮适配（HarmonyOS PC，autotools + protobuf-c/ldns/fstrm）
> 对应：`knowledge/drafts/DRAFT-dnstap-ldns-0.2.1-protoc-pregen-pkgconfig-name.kv`

## 现象

autotools 库消费 protobuf-c 时，构建期需要 `protoc-c`（protobuf-c 的 C 代码生成器）把
`.proto` 编译成 `.pb-c.c/.pb-c.h`。在 HarmonyOS PC 上：

```console
configure: error: The protoc-c program was not found. Please install the protobuf-c compiler!
```

即使 `protobuf-c/1.5.1` 已从 ohpcd 正确安装（`libprotobuf-c.a`、头文件齐全），configure
依然失败——**缺的不是运行库，是构建期工具**。

## 根因

ohpcd 发布的 `protobuf-c/1.5.1` 配方 `package()` 里显式 `shutil.rmtree(bin/)`：
`protoc-c` 与 `protoc-gen-c` 都不随制品发布（配方把它当纯库包处理）。因此：

1. `configure.ac` 的 `AC_PATH_PROG([PROTOC_C], [protoc-c])` + `AC_MSG_ERROR` 直接失败；
2. `Makefile.am` 的 `.proto.pb-c.c` 后缀规则（`@PROTOC_C@ "--c_out=..."`）在构建期无工具可用；
3. 上游 tag archive 通常**不带**生成物（`.pb-c.c/.h` 是 BUILT_SOURCES，dist 会删），
   无法直接复用上游产物。

> 附带边界：已发布制品的 pkg-config 模块名可能与上游探测名不一致。ohpcd 的
> `ldns/1.9.0` 只装 `ldns.pc`（无 `libldns.pc` 别名），而上游 `configure.ac` 探测
> `PKG_CHECK_MODULES([libldns],[libldns])` → `No package 'libldns' found`。当制品无
> 对应别名 `.pc` 可复制时（区别于既有 DRAFT-ohos-pkgconfig-name-alias 的别名复制
> 场景），需修正 `configure.ac` 探测名。

## 方案（主方案，作者期预生成）

### 1. 作者期用官方生成器预生成绑定

用 protobuf-c 1.5.1 自带的 `protoc-gen-c` 插件（配合 `protoc`）从官方 `.proto` 一次性生成：

```bash
protoc --plugin=protoc-gen-c=$GEN --c_out=$OUT -I $PROTO_DIR $PROTO
# 产出 $OUT/dnstap.pb-c.c 与 $OUT/dnstap.pb-c.h（"DO NOT EDIT" 头为生成器产物证据）
```

配方侧：

```python
def export_sources(self):
    export_conandata_patches(self)
    copy(self, "dnstap.pb-c.c", src=..., dst=os.path.join(self.export_sources_folder, "generated"))
    copy(self, "dnstap.pb-c.h", src=..., dst=os.path.join(self.export_sources_folder, "generated"))

def build(self):
    copy(self, name, src=<export_sources>/generated, dst=<source_folder>/dnstap.pb)
    apply_conandata_patches(self)
    autotools = Autotools(self)
    if not os.path.isfile(<source_folder>/configure):
        autotools.autoreconf()          # GitHub archive 无 configure
    autotools.configure()
    autotools.make(args=["-j1"])        # E074：HMDFS jobserver fifo EPERM
```

### 2. patch configure.ac：去掉 protoc-c 硬依赖

```diff
-AC_PATH_PROG([PROTOC_C], [protoc-c])
-AS_IF([test -z "$PROTOC_C"],
-  AC_MSG_ERROR([The protoc-c program was not found. Please install the protobuf-c compiler!]))
+AC_SUBST([PROTOC_C], [true])
```

### 3. patch Makefile.am：直接用预生成源，移除重生成规则

```diff
-SUFFIXES = .proto .pb-c.c .pb-c.h
-
-.proto.pb-c.c:
-	$(AM_V_GEN)@PROTOC_C@ "--c_out=`pwd`" -I$(top_srcdir) $<
-
-.proto.pb-c.h:
-	$(AM_V_GEN)@PROTOC_C@ "--c_out=`pwd`" -I$(top_srcdir) $<
-
 PROTOBUF_SOURCES = dnstap.pb/dnstap.pb-c.c dnstap.pb/dnstap.pb-c.h
-BUILT_SOURCES += ${PROTOBUF_SOURCES}
 CLEANFILES += ${PROTOBUF_SOURCES}
```

### 4. 附带：修正 pkg-config 探测名（制品无别名可复制时）

```diff
-PKG_CHECK_MODULES([libldns], [libldns])
+PKG_CHECK_MODULES([libldns], [ldns])
```

变量前缀 `libldns` 保留，`Makefile.am` 里的 `${libldns_CFLAGS}/${libldns_LIBS}` 引用
不受影响。

## 验证

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：通过
  （configure 无 protoc-c 报错、`checking for ldns... yes`、make -j1 编译预生成源、
  install 成功）
- 消费者用例（test_package）：`dnstap-ldns -x` 解码真实 dnstap protobuf
  （`7801721008011001180122047f00000130353835` = AUTH_QUERY/INET/UDP/127.0.0.1:53），
  quiet 输出含 `AQ 127.0.0.1 UDP`、YAML 输出含 `AUTH_QUERY/127.0.0.1/UDP`，退出码 0
- W3 本地 CI：JC/KC/L0/L1/L4/L5 全 pass，Pass rate 100%

## 适用边界

- 适用：autotools 且 `.proto` 在构建期生成 C 绑定、上游 tag 不带生成物、
  ohpcd protobuf-c 剥离 bin/ 的消费方库
- 反例：上游已带 `.pb-c` 生成物（如 cdogs-sdl → 直接复用，见 E447）；
  构建机有 protoc-c 工具（无需预生成）；PkgConfigDeps 生成名 ≠ 期望名且制品带可复制
  `.pc`（走别名复制，见 DRAFT-ohos-pkgconfig-name-alias）

## 关系

- similar_to: DRAFT-ohos-pkgconfig-name-alias（.pc 名不一致家族，边界互补）、
  E447（SDL2/nanopb c_out 语境，上游自带生成物 vs 本条作者期生成）
- caused_by / conflicts_with / prerequisite_of: 无