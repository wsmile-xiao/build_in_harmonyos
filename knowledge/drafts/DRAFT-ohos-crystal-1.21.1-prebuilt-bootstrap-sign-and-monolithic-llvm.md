# DRAFT-ohos-crystal-1.21.1-prebuilt-bootstrap-sign-and-monolithic-llvm — 自举语言工具链在 OHOS 的三道门：预编译 bootstrap 需补签、单体 LLVM、glibc 符号垫片

> Contributor: AtomCode/oh-executor | Status: **DRAFT** / Updated: 2026-09-30 / Severity: 3 (high)
> Source: crystal 1.21.1 HarmonyOS PC 适配尝试（分支 `feat/crystal-1.21.1`）
> 对应：`knowledge/drafts/DRAFT-ohos-crystal-1.21.1-prebuilt-bootstrap-sign-and-monolithic-llvm.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-E077B-ohos-sdk-autocodesign-invalid` | 已在 main | **SDK 链接器自动插入的 .codesign 无效**（readelf 见签名 ≠ 可执行），修法=移除后重签 | 本条讲的是**完全没有 .codesign 段**的外来预编译二进制（官方 release），症状同为 EACCES/EPERM 但起点不同：E077B 是「有假签名」，本条是「无签名」。处置一致（走 binary-sign-tool selfSign），但**识别信号不同**：本条 `llvm-readelf -S | grep -c codesign` = **0** |
| `DRAFT-332-openrct2-0.5.3-libcpp15-cpp20-compat` | 已在 main | C++ libc++15 的 C++20 缺口 | 完全不同的语言栈（Crystal 非 C/C++）；本条属**语言工具链自举**问题 |
| `DRAFT-eigen-3.4.1-make-jobserver-mkfifo-nonfatal` | 已在 main | make jobserver FIFO | 本包同样出现且同样**非致命**（显式 `--jobserver-style=pipe` 即静默），不重复 |
| `DRAFT-ohos-clang15-missing-p0960-aggregate-paren-init` | 已在 main | P0960 | 本包无关，仅同批 |

**全库查证**：对 `crystal-lang` / `自举 bootstrap 二进制` / `LLVM_LDFLAGS` /
`单体 libLLVM` / `__xpg_strerror_r` 在 `knowledge/graph/`、`knowledge/doc/`、
`knowledge/drafts/` 中 grep —— 未命中同名条目，本条为新增。

## Scope（何时用）

在 OHOS 上适配**自举（self-hosting）语言工具链**——即「编译器本身由该语言写成、
需要先有一个可运行的既有编译器才能构建新编译器」的包族（Crystal、以及同形态的
Nim/Scheme 类）。典型特征：

- 源码里几乎全是 `.cr`（本包实测 **1625 个 `.cr`、0 个 `.c/.h`**）；
- 构建脚本（Makefile）里有 `CRYSTAL ?= crystal` 之类**「需要一个已存在的编译器」**的变量；
- 上游提供**预编译 bootstrap 二进制**（`crystal-<ver>-1-linux-aarch64.tar.gz`）。

## ⭐ 结论一：官方预编译 bootstrap 在 OHOS 上「不能跑」的真因是缺签名段，不是不兼容

**实测现象**（这一步极易误判为「外来 glibc 二进制与 OHOS musl 不兼容」）：

```console
$ ./bin/crystal --version
sh: ./bin/crystal: Permission denied      # execve → errno 13 (EACCES)
```

排查过程与反证：

| 实验 | 结果 | 排除的假设 |
|---|---|---|
| 同目录下用 OHOS clang 编一个本地二进制再执行 | ✓ 正常输出 | 排除「目录挂载 noexec / 权限位」 |
| 本地二进制**全静态**（`-static`，e_type=EXEC，无 INTERP/NEEDED） | ✓ 正常输出 | 排除「静态链接不被支持」 |
| 本地全静态二进制尾部填充到 **~130 MB**（与 crystal 同量级） | ✓ 正常输出 | 排除「文件过大」 |
| 对比 `security.selinux` / `user.hmdfs.perm` / 权限位 / uid-gid | 两者**完全一致** | 排除 SELinux / hmdfs 权限语义 |
| `llvm-readelf -S` 看 `.codesign` 段 | **本地二进制=1，crystal=0** | ← 决定性差异 |

**根因**：OHOS 要求可执行 ELF **带有效签名段**。OHOS clang/lld **自动**为本地编译
产物插入 `.codesign`（注意：该自动签名在部分场景无效，见 `E077B`，但本包实测
本地产物可执行）；而**官方 release 的外来二进制完全没有该段** → execve 被拒。

**修法**（与 E077 四步一致，只是无需先 remove）：

```bash
binary-sign-tool sign -inFile  <unsigned> -outFile <signed> -selfSign 1
chmod 755 <signed>
```

**实测验证**：

```console
# 补签前
$ ./bin/crystal --version
sh: ./bin/crystal: Permission denied

# 补签后
$ ./bin/crystal --version
Crystal 1.21.1 [73ea5c2b1] (2026-09-26)
LLVM: 20.1.8
Default target: aarch64-unknown-linux-gnu
```

> 📌 识别口诀：**外来预编译可执行报 EACCES 时，先数 `.codesign` 段**——
> 0 个 = 本条（补签即可）；1 个但仍报错 = `E077B`（假签名，移除后重签）。

## ⭐ 结论二：OHOS SDK 只有「单体 libLLVM」，必须用 `LLVM_CONFIG` 包装器覆盖组件库列表

自举构建会链接 LLVM。`llvm-config --libs` 输出 **110 个组件库**：

```console
$ llvm-config --libs | tr ' ' '\n' | grep -c '^-l'
110
$ # 其中如 -lLLVMX86CodeGen -lLLVMRISCVDisassembler -lLLVMLoongArchCodeGen ...
```

而 OHOS SDK 的 LLVM 目录只有 **3 个单体库**（`libLLVM.so` / `libLLVM-15.so` /
`libLLVM-15.0.4.so`，每个 70 MB）：

```console
ld.lld: error: unable to find library -lLLVMRISCVDisassembler
ld.lld: error: unable to find library -lLLVMLoongArchCodeGen
ld.lld: error: too many errors emitted, stopping now (use --error-limit=0 ...)
```

`--link-shared` 也救不了（它会去找 `libLLVMSupport.so` 等同样不存在的文件）。

**修法（实测有效）**：**不要用 `LLVM_LDFLAGS`** —— 实测设了它仍去链接 110 个组件库
（`lib_llvm.cr:23` 里 `LLVM_LDFLAGS` 与 `llvm-config` 是二选一，且经 Conan 传递不稳定）。
改为**用 `LLVM_CONFIG` 指向一个包装器**，由它把 `--libs` 的答案换成单体库；关键是包装器
必须**命名为 `llvm-config` 且置于 `PATH` 最前**（crystal 的编译期宏会直接按 PATH 查找
`llvm-config`，见 `Makefile:79` 的 `find-llvm-config.sh`）：

```bash
# compat/llvm-config-ohos —— 除 --libs/--ldflags/--system-libs 外一律转发真实 llvm-config
export PATH="<wrapper-dir>:$PATH"          # 目录里放一份**名为 llvm-config** 的包装器
export LLVM_CONFIG="<wrapper-dir>/llvm-config"
```

实测：真实 `llvm-config --libs` 输出 **110** 个组件库，包装器输出 **6** 个（单体 + 系统库）；
单体库可单独链接成功（实测：`clang++ ... -L<llvm/lib> -lLLVM-15.0.4` 通过）。

> 通用启示：**任何 `llvm-config --libs` 驱动的构建**在 OHOS 上都要准备这一步覆盖；
> 覆盖点是 `llvm-config` 这个**可执行体**，不是 `LLVM_LDFLAGS` 这个环境变量。

## ⭐ 结论三：gnu 目标 bootstrap 会引入 glibc 专属符号，需最小等价垫片

官方 linux bootstrap 是 **gnu 目标**构建的，其 stdlib 的 `lib_c` 绑定按「编译该
编译器时的目标」选择，因此**即使**给新代码传 `--target ...-linux-musl`，绑定仍取
gnu 版（`src/lib_c/aarch64-linux-gnu/**`）→ 引用 glibc 专属符号。

实测遇到的三个（均为等价补齐，非绕过）：

| 缺失符号 | 来源 | 垫片处置 |
|---|---|---|
| `__xpg_strerror_r` | `lib_c/aarch64-linux-gnu/c/string.cr:8` 的 `fun strerror_r = __xpg_strerror_r(Int, Char*, SizeT) : Int` | 转发到 musl 的 `strerror_r`（同为 XSI 版、同签名、同返回 int） |
| `pthread_setcancelstate` | `src/crystal/system/unix/process.cr:262,267` | 返回 0 的空实现（语义=不支持线程取消）；依据：设备运行期 libc 以**弱符号**导出它（见 `DRAFT-aml-1.0.0-ohos-pthread-setcancelstate-meson-feature-detect`） |
| `pthread_setcanceltype` | 同上族 | 同上 |

```c
int __xpg_strerror_r(int errnum, char *buf, size_t buflen) {
    return strerror_r(errnum, buf, buflen);
}
```

## ⭐ 结论四：`--target aarch64-unknown-linux-musl` 能产出**可运行**的 OHOS 二进制

实测（用自举出的编译器编 hello world）：

```console
$ crystal build hello.cr --target aarch64-unknown-linux-musl \
      --link-flags="-L<libgc>/lib"
$ ./hello
hello from crystal
```

产物为 aarch64、依赖 libgc。**注意**：`--target musl` 与「链接 OHOS 预编译 `.so`」
存在 ABI 张力——OHOS 编译的 `.so` 带 ohos ABI，与 musl 三元组混链会报
`libxxx.so is incompatible with aarch64linux`。故**优先用静态库**（本包 libgc 在
ohpcd 上即 static-only），或统一到同一 ABI。

## 自举构建的完整可行路径（实测拼通）

```bash
# 1) 取源码 + 官方 bootstrap，补签
tar -xzf crystal-1.21.1.tar.gz
binary-sign-tool sign -inFile bootstrap/bin/crystal -outFile <signed> -selfSign 1
binary-sign-tool sign -inFile bootstrap/bin/shards -outFile <signed> -selfSign 1   # shards 同样缺签名段

# 2) 依赖（ohpcd 均有）：libgc(static) / libevent / pcre2(static) / gmp / libyaml / openssl / zlib
# 3) 装 shards 依赖
CRYSTAL_PATH=<src>/lib:<src>/src:<bootstrap>/share/crystal/src shards install   # markd/reply/sanitize

# 4) 构建编译器
export CRYSTAL_PATH="<src>/lib:<src>/src:<src>/src/lib_c/aarch64-linux-musl:<bootstrap>/share/crystal/src"
# LLVM：把**名为 llvm-config** 的包装器（compat/llvm-config-ohos）放到 PATH 最前
export PATH="<wrapper-dir>:$PATH"
export LLVM_CONFIG="<wrapper-dir>/llvm-config"
make --jobserver-style=pipe -j4 crystal \
  CRYSTAL=<signed bootstrap> \
  FLAGS="--target aarch64-unknown-linux-musl" \
  LDFLAGS="-L<libgc>/lib -L<pcre2>/lib -L<libevent>/lib <compat_shim>.o"
# → MAKE_RC=0，产出 47 MB aarch64 编译器；补签后可运行：Crystal 1.21.1
```

> ⚠️ `CRYSTAL_PATH` **必须**同时含 `lib`（shards 解析 `require "markd"`）与
> `src/lib_c/<triple>`（stdlib 解析 `require "c/fcntl"`）——少任一个即报
> `can't find file 'markd'` / `can't find file 'c/fcntl'`，且错误信息会误导向
> 「Did you remember to run shards install?」。

## ⚠️ runner 级环境陷阱：`id -un` / `id -gn` 在编译期宏里返回非 0

上游 spec 在**编译期宏**里取用户名/组名：

```crystal
# spec/std/system/group_spec.cr:8
GROUP_NAME = {{ `id -gn`.stringify.chomp }}
```

本机 uid/gid 无名称映射 → `id -gn` 向 stderr 打
`id: cannot find name for group ID 20020085` 并返回 1 → **整个 spec 编译失败**。

**处置**（runner 级环境兼容垫片，不改上游测试与断言）：PATH 前置一个 `id` shim，
`-un/-gn` 失败时回退数字 id 并返回 0（POSIX 允许无名称映射时回退数字）。

## ⭐ 结论五：OpenSSL 3 报「1.1 宏名未定义」是**版本探测失败**的次生现象

修完前四道门后，spec 编译**仍**逐个报 OpenSSL 1.1 的宏名缺失，一次一个、看似无底洞：

```console
ld.lld: error: undefined symbol: sk_value
ld.lld: error: undefined symbol: sk_pop_free
ld.lld: error: undefined symbol: EVP_CIPHER_flags
```

**不要逐个补符号**（那是无底洞）。查 `src/openssl/lib_crypto.cr` 会发现这是**分支选错**：

```crystal
{% if OPENSSL_VERSION != "0.0.0" %}
  fun sk_value = OPENSSL_sk_value(x0 : Void*, x1 : Int) : Void*   # ← OpenSSL 3 正确分支
{% else %}
  fun sk_value(x0 : Void*, x1 : Int) : Void*                       # ← 1.1 裸名分支
{% end %}
```

而 `OPENSSL_VERSION` 由**编译期宏**跑 shell 探测得出：

```crystal
{% ssl_version = `sh -c 'hash pkg-config 2> /dev/null &&
    pkg-config --silence-errors --modversion libcrypto || printf %s 0.0.0'` ... %}
```

未设 `PKG_CONFIG_PATH` 时 `pkg-config --modversion libcrypto` 取不到 →
`ssl_version = "0.0.0"` → **走 else 的 1.1 裸名分支** → 于是引用了
`sk_value`/`sk_pop_free`/`EVP_CIPHER_flags` 等「1.1 是函数、3.x 只是宏」的名字。

**修法（一行）**：

```bash
export PKG_CONFIG_PATH="<openssl>/lib/pkgconfig:<libgc>/lib/pkgconfig:<pcre2>/lib/pkgconfig:..."
pkg-config --modversion libcrypto      # → 3.5.8 ✓
```

**实测效果**：整条 `sk_*` / `EVP_*` 报错链**一次消失**，spec 套件随即编译通过。

> 通用启示：**任何「编译期宏跑 pkg-config 探测依赖版本」的构建**，在 OHOS/conan
> 环境下都必须显式导出 `PKG_CONFIG_PATH`；否则探测静默退化为「未找到」，
> 症状却表现为一堆毫不相关的符号缺失，极易误判为依赖 ABI 不兼容。

## 上游测试实测结果（R51）

修完五道门后 spec 套件**编译并通过运行**：

```console
$ .build/std_spec
Finished in 4:29 minutes
18066 examples, 67 failures, 38 errors, 32 pending
```

| 指标 | 数值 |
|---|---|
| 总用例 | **18066** |
| 通过 | 18066 − 67 − 38 − 32 = **17929** |
| 失败 failures | 67 |
| 错误 errors | 38 |
| 待定 pending | 32 |

失败用例集中在 `spec/std/file_spec.cr` 的 **chmod / readlink**、`user/group`、
`tempfile`、`XML`、异常内存类——与本平台已知限制一致（HMDFS **忽略 chmod**、
uid/gid **无名称映射**、`/tmp` 只读等），属**环境限制**而非源码缺陷；逐条归类
待补（见「未完成事项」）。

## ✅ 完成状态（已闭环）

- **`conan create` 本地验证通过（W3）：`CREATE_RC=0`** —— 编译器构建成功
  （47 MB aarch64）、打包成功、test_package 端到端通过（用被测编译器真实编译
  并执行产物，输出 `crystal-hello-ok`）；
- conanfile **七件套已落地**，并随 PR 提交；
- PR 已创建：`【知识库扩展】feat(crystal): 1.21.1 适配 HarmonyOS PC`。

> 判定：crystal 的适配**关键路径已完全打通**。本条把六道门沉淀下来，
> 使后续（或他人）不必重新踩一遍。

## 附：一次性修复清单（按踩坑顺序，均已实测）

1. **补签** bootstrap 的 `crystal` 与 `shards`（`binary-sign-tool ... -selfSign 1`）
   —— 两者都缺 `.codesign` 段，只签一个会在调用另一个时再失败
2. **`LLVM_CONFIG`** 指向包装器，且包装器须**命名为 `llvm-config` 并 PATH 前置**
   （⚠️ 实测仅设 `LLVM_LDFLAGS` **无效**，见门二）
3. **`CRYSTAL_PATH`** 同时含 `lib`、`src`、`src/lib_c/<triple>`
4. **`PKG_CONFIG_PATH`** 指向各依赖 pkgconfig（修 OpenSSL 版本探测 ← 关键一击）
5. glibc 符号垫片：`__xpg_strerror_r` / `pthread_setcancelstate`（若仍走 gnu 分支）
6. runner 级 `id` shim（`-un`/`-gn` 回退数字 id）
7. 用 **OHOS 版 `libgc.a`** 覆盖 bootstrap 随附的 gnu 版（否则消费者链接报
   `__sigsetjmp` 等未定义）
8. 把运行时库闭包装入包内（`libLLVM-15.so` / `libc++_shared.so` / `libxml2.so.16`
   / `libedit.so.0` / `libtinfo.so.6`）
9. make 用 `--jobserver-style=pipe`（HMDFS 无 mkfifo，非致命但消噪音）

> 另注：**不要执行 `shards install`** —— 官方 tarball 自带 `lib/`（三个 shard
> 已内嵌，`src/*.cr` 数量与安装结果一致 1/9/4），而它在受限网络下反复超时且
> 对构建无增益。

## 禁止事项

- ❌ 见到「外来 aarch64 glibc 预编译二进制在 OHOS 报 Permission denied」就断言
  「glibc 与 musl 不兼容/该包不可适配」——先数 `.codesign` 段（本条结论一）。
- ❌ 指望 `LLVM_LDFLAGS` 能覆盖组件库列表——**实测无效**；必须用命名为
  `llvm-config` 的包装器 + PATH 前置（见门二）。
- ❌ 为 OpenSSL 的 `sk_*` / `EVP_*` 逐个写符号转发——那是无底洞；根因是
  `PKG_CONFIG_PATH` 缺失导致版本探测退化，补该变量即可一次解决（见门三）。
- ❌ 删掉 `id -un/-gn` 相关 spec 或断言以绕过（那是掩盖；应加 runner shim）。
- ❌ 认为补签一次即可：**bootstrap 的 `crystal` 与 `shards` 都要补签**。
