# DRAFT: autotools OHOS 平台判定的三处缺口

> **结构化数据**：[DRAFT-medusa-autotools-platform-triplet-and-probe.kv](DRAFT-medusa-autotools-platform-triplet-and-probe.kv)
> **严重度**：🔴 high | **分类**：autotools-config / ohos / platform-detection
> **来源**：medusa 2.3 原生 OHOS 适配（PR #13807）

本条目由三处**互不相关但都会让平台判定失败**的缺口组成，它们都在同一轮适配里被逐一实测确认。

---

## 缺口一：仓库标准脚本插入的 config.guess 分支不会输出

### 现象

```text
configure: checking build system type
uname -m = aarch64
uname -r = HongMeng Kernel 1.12.0
uname -s = HarmonyOS
configure: error: cannot guess build type; you must specify one
```

`config.guess` 明明已经"包含 HarmonyOS"，`grep -c HarmonyOS config.guess` 返回 1，却依然报无法识别。

### 根因

`scripts/patch-autotools-ohos.pl` 第 51–63 行插入的块是：

```perl
"\tesac\n" .
"\tGUESS=\${MACHINE}-unknown-linux-ohos\n" .
"\t;;\n\n";
```

而 config.guess 的每个 case 分支**必须自己负责输出**。同一文件里 `echo "$x"; exit ;;` 形式出现 **230 次**（如 `echo "$timestamp" ; exit ;;`），主 `case` 结束后紧跟的就是失败路径：

```sh
esac

echo "$0: unable to guess system type" >&2
...
exit 1
```

所以只赋值不打印的分支会**直接穿透到失败路径**。

### 修复

```diff
-	GUESS=${MACHINE}-unknown-linux-ohos
-	;;
+	echo "${MACHINE}-unknown-linux-ohos"
+	exit ;;
```

**这条特别值得回写**：P001 的建议就是"使用 `patch-autotools-ohos.pl`"，也就是说按仓库推荐做法去做的项目都会踩到；它属于**工具链缺陷**，不是某个库的问题。

### 验证（stub uname，不需要真机）

```bash
# HarmonyOS stub
UNAME_SYSTEM=HarmonyOS sh ./config.guess   → aarch64-unknown-linux-ohos
# Linux 回归
UNAME_SYSTEM=Linux      sh ./config.guess   → aarch64-unknown-linux-gnu   （不能被破坏）
```

---

## 缺口二：只给 config.sub 加白名单不够，三元组会被归一化成 `linux-gnu-ohos`

### 现象

白名单补齐后：

```text
$ ./config.sub aarch64-linux-ohos
aarch64-unknown-linux-gnu-ohos      ← 多出 -gnu
```

### 根因

2018 版 `config.sub` 里有一条通用重写规则，位于白名单检查**之后**：

```sh
	-linux*)
		os=`echo $os | sed -e 's|linux|linux-gnu|'`
		;;
```

它会把已经正确识别为 `linux-ohos` 的 OS 再改写成 `linux-gnu-ohos`。只补 `linux-ohos*` / `-linux-ohos*` 白名单无法阻止这一步。

### 修复

在通用规则**之前**插入专用分支：

```diff
 	-linux-dietlibc)
 		os=-linux-dietlibc
 		;;
+	-linux-ohos*)
+		os=-linux-ohos
+		;;
 	-linux*)
 		os=`echo $os | sed -e 's|linux|linux-gnu|'`
 		;;
```

### 验证

```text
$ ./config.sub aarch64-linux-ohos            → aarch64-unknown-linux-ohos
$ ./config.sub aarch64-unknown-linux-ohos    → aarch64-unknown-linux-ohos
$ ./config.sub x86_64-pc-linux-gnu           → x86_64-pc-linux-gnu        （回归）
```

---

## 缺口三：「假定式」降级探测静默禁用功能（构建全绿，能力已丢）

### 现象

构建一切正常，`Build Summary` 全绿，但产物里少了一个模块：

```text
configure: checking whether to enable SSH module... no
configure:     SSH             ** Disabled **
```

### 根因（逐行）

medusa 的 libssh2 判定链在其 `configure` 中是这样走的：

```text
checking for Libssh2 Library files...
checking for main in -lssh2... yes                       ← 库找得到
configure: WARNING:  LIBSSH2 path not found. Assuming it was...
configure: WARNING:  No ldd detected. Unable to test whether Libssh2
                     was compiled to use libgcrypt. Assuming it was...
checking for gcry_control in -lgcrypt... yes             ← 依赖也满足
configure: checking for GnuTLS Library files...
checking for gnutls_handshake in -lgnutls... no
configure: WARNING:  *** GnuTLS required for installed version of Libssh2 ***
configure: WARNING:  The SSH2 module will NOT be built.
checking whether to enable SSH module... no
```

链条：**`ldd`/`otool` 缺失 → 退化为"假定 libssh2 是 libgcrypt 版" → 据此额外要求 gnutls → OHOS 未发布 gnutls → 整个模块被静默关闭**。

而制品仓里 libssh2 实际是 OpenSSL 后端，这个"假定"在本平台**事实错误**。

### 修复

两条路，按依赖可得性选择：

1. **优先**：若假定出来的依赖确实已发布，就把它补进 `requirements()` 并给上 `-I`/`-L`——让探测诚实地通过。
   （medusa 的 `libgcrypt` 就是这样提供的，`checking for gcry_control in -lgcrypt... yes`。）
2. **假定事实错误 / 依赖不可得时**：让探测对 `*ohos*` 目标跳过该兜底分支，而不是让功能被静默关闭：

```diff
-    if test -f "`which ldd`"; then
+    if test "$target" != "${target%ohos*}"; then
+      check_libgcrypt="false"
+    elif test -f "`which ldd`"; then
       LDD="ldd"
```

修复后同一份构建日志变为：

```text
checking whether to enable SSH module... yes
configure:     SSH             Enabled
...
[ok] ssh module loaded (libssh2 + libgcrypt)
[info] modules loaded: 22
```

### 教训（本条最有价值的部分）

**"构建成功 + 门禁全绿"不能证明功能完整。** 这类探测降级的唯一可靠兜底是**运行期断言**——medusa 的 `test_package` 执行 `medusa -d` 并统计 dlopen 成功的模块数，正是靠这一步才发现少了一个模块；如果只依赖 `configure` 摘要或 CI 的 L0/L1/L5，这个缺口会一路带到制品仓。

---

## 与既有知识的关系（增量说明）

| 既有条目 | 覆盖内容 | 本条增量 |
| --- | --- | --- |
| **E007** | config.guess 无法识别 HarmonyOS，建议用 `patch-autotools-ohos.pl` | 指出**该脚本插入的分支缺 `echo/exit`**，会穿透到失败路径；给出 stub uname 的自检方法 |
| **E072** | config.sub 不接受 `ohos` 三元组 | 指出**通用 `-linux*)` 会把 os 改写成 `linux-gnu`**，专用分支必须插在它之前 |
| E011 / E112 | `umask 077` 目录不可写导致 `config.status` 失败 | 本条不重复（仅注意：同轮适配用"改 configure 源头"的补丁形态解决，可作 E112 的方案增量） |
| E085 / E127 | musl 未实现 pthread 取消类接口 | 本条不重复；但补一条**合规写法**约束：R8 规定 `patches/` 不得引入 `__OHOS__` 平台宏，本库首版补丁即因该写法被 AI 检视判 P1 阻塞，改为 `AC_CHECK_FUNCS([pthread_cancel])` → `HAVE_PTHREAD_CANCEL` 能力探测后通过（仓库内已有 `HAVE_PTHREAD_CANCEL` 先例） |

全库检索 `config.status`（除 E011/E060/E112）、`ldd`（E137/E173 为 Perl 场景）、`libgcrypt`、`gnutls`、`-lrt`：缺口一、二、三的表述均无既有条目覆盖。
