# libsecret 0.21.7 适配笔记

## 编译环境
- 构建系统: meson 1.12.0 + ninja 1.13.1
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. W0 依赖核验（制品仓 R35 探测）
conan install --requires=glib/2.84.0.1 -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
conan install --requires=libgcrypt/1.11.0 -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64

# 2. 探索构建（签名 wrapper 方案，见下方问题1）
meson setup builddir --default-library=shared \
  -Dcrypto=libgcrypt -Dintrospection=false -Dvapi=false \
  -Dmanpage=false -Dgtk_doc=false -Dbash_completion=disabled \
  -Dpam=false -Dtpm2=false -Ddebugging=false
ninja -C builddir

# 3. 上游测试（本地 OHOS 实测）
meson test -C builddir libsecret:test-hex libsecret:test-secmem \
  libsecret:test-dh libsecret:test-hkdf libsecret:test-attributes \
  libsecret:test-value libsecret:test-file-collection libsecret:test-secret-tool.sh

# 4. conan create（CI 同款）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson sanity check 失败（clang 产物不可运行） | OHOS ELF 需签名才能执行（E077） | 探索阶段用 clang-wrapper（编译后 binary-sign-tool 自签）；配方里 CI 用 conan profile 的环境（conan create 机器原生构建可运行） |
| 2 | `Program //bin/gdbus-codegen found: NO` + `Dependency 'gio-2.0' tool variable 'gdbus_codegen' contains erroneous value: '//bin/gdbus-codegen'` | glib 包 .pc 文件 prefix=/（DESTDIR 安装），gdbus_codegen=${bindir}/gdbus-codegen 解析为 //bin/... | 配方 generate() 里复制 glib 全套 .pc 到 generators 目录并重写 prefix 为真实包路径（accountsservice/GOA 模式） |
| 3 | `error: call to undeclared function 'getpass'` + `-Wint-conversion` | OHOS musl libc 有 getpass 符号（系统 musl loader 导出）但 SDK unistd.h 无声明 | 补丁 0001：secret-tool.c 加 `extern char *getpass(const char *);`（glib/2.84.0 patch 0002 同款） |
| 4 | 链接 `undefined symbol: getpass` | SDK sysroot libc.so 无 getpass 符号；只有系统 musl（/lib/ld-musl-aarch64.so.1）有 | 链接参数 `-L/lib -l:ld-musl-aarch64.so.1`（glib 配方 _MUSL_LINK_ARGS 同款） |
| 5 | test-file-collection 失败：`egg_tests_create_scratch_directory: code should not be reached` | 硬编码 `/tmp/scratch-*`，OHOS /tmp 只读（E002），g_mkdtemp 返回 NULL | 补丁 0002：改用 g_build_filename(g_get_tmp_dir(), ...)（遵循 TMPDIR） |
| 6 | gio-2.0 pc 解析缺 libpcre2-8/libffi/zlib | glib 的 .pc Requires.private 引用传递依赖 pc | pkg_config_path 注入全部依赖包的 lib/pkgconfig（配方 _inject_pkg_config_paths） |

## 上游测试定性（N 申报口径）

上游 meson 注册 **16 个测试目标**（g_test_add 子用例合计 195）：

| 测试目标 | 子用例 | 状态 | 定性 |
|---|---|---|---|
| test-hex | 4 | ✅ 通过 | egg hex 编解码 |
| test-secmem | 7 | ✅ 通过 | egg 安全内存 |
| test-dh | 8 | ✅ 通过 | DH 密钥交换（libgcrypt） |
| test-hkdf | 7 | ✅ 通过 | HKDF（libgcrypt） |
| test-attributes | 12 | ✅ 通过 | schema 构建/校验 |
| test-value | 11 | ✅ 通过 | SecretValue 生命周期 |
| test-file-collection | 7 | ✅ 通过 | 文件后端读写加解密 |
| test-secret-tool.sh | 6 | ✅ 通过 | secret-tool 端到端（file 后端） |
| test-prompt | 12 | ⛔ 豁免 | 需要 python D-Bus mock service |
| test-service | 12 | ⛔ 豁免 | 同上 |
| test-session | 6 | ⛔ 豁免 | 同上 |
| test-paths | 20 | ⛔ 豁免 | 同上 |
| test-methods | 25 | ⛔ 豁免 | 同上 |
| test-password | 15 | ⛔ 豁免 | 同上 |
| test-item | 20 | ⛔ 豁免 | 同上 |
| test-collection | 27 | ⛔ 豁免 | 同上 |

豁免证据（实测报错原文）：
```
ModuleNotFoundError: No module named 'dbus'
libsecret:ERROR:../libsecret-0.21.7/libsecret/test-prompt.c:46:setup:
assertion failed (error == NULL): Remote closed the output (g-io-error-quark, 0)
```
mock service（libsecret/mock/service.py）需要：python3 `dbus`/`dbus.glib` 模块
+ `gi.repository`（PyGObject）+ D-Bus session bus（dbus-daemon）。OHOS 无
dbus-daemon，python3 亦无 dbus/gi 模块（本地实测 pip 装 dbus-python 后仍缺
gi + 无 session bus 可连）。属环境类豁免，逐项见上表。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.84.0.1 | ohpcd 制品仓（libffi/3.4.4、pcre2/10.45、zlib/1.3.1.1 传递） |
| libgcrypt | 1.11.0 | ohpcd 制品仓（libgpg-error/1.55 传递） |

## 验证结果

```bash
# 上游测试（8 可运行目标）
$ meson test ...  → Ok: 8 / Fail: 0（62 子用例全 ok，0 not ok）
# secret-tool 冒烟
$ secret-tool --help   → 正常打印 usage
# test_package
$ ./test_package       → PASS (version/schema/value APIs)
# secret-tool file 后端端到端（test_package test()）
$ SECRET_BACKEND=file secret-tool store/lookup/clear → PASS
```

## 产物清单

- libsecret-1.so / libsecret-1.so.0 / libsecret-1.so.0.0.0
- secret-tool（bin/）
- include/libsecret-1/libsecret/*.h
- lib/pkgconfig/libsecret-1.pc / libsecret-unstable.pc
