# jose 14 适配笔记

## 编译环境
- 构建系统: meson（上游 `lib/meson.build` 用 `shared_library()`，不受 `default_library` 影响）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（`~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang`，`aarch64-unknown-linux-ohos`）
- 真机验证: 独立 `CONAN_HOME=~/work/psj/ch-jose`（只从 `~/.conan2` 拷 profiles/settings.yml/remotes.json，未写共享缓存）
- 状态: built（制品尚未上传制品仓，PR/CI 完成后按 R29 更新为 published）

## 源码坐标
- 上游 tag：`v14`（GitHub latchset/jose 确实有该 tag；任务版本键 `14` 与之对应）
- 取源 URL：codeload 形态 `https://codeload.github.com/latchset/jose/tar.gz/refs/tags/v14`
- sha256：`3ffb8ea9a0fa5194051499d96bfde957621fcd490ef7ed95effc699029d7ad3b`
  （本机分别 GET 两种 URL 落地对拍：`github.com/latchset/jose/archive/refs/tags/v14.tar.gz`
  与 codeload **字节同一**，同 sha256、同 843394 B；选 codeload 是因为真机直连 github.com 会
  `ConnectTimeout`，见「问题 7」）

## 编译步骤

```bash
# 配方验证（真机，独立 CONAN_HOME）
conan create archives/j/jose/14 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# build() 内部等价于：
meson setup build-release --native-file <conan_meson_native.ini> \
    -Ddocs=disabled -Dwerror=false -Db_ndebug=false -Dwrap_mode=nodownload
meson configure build-release -Db_ndebug=false     # 见「问题 1」
meson compile -C build-release
meson test  -C build-release --num-processes 1     # 上游 25 项
meson install -C build-release
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **上游 `meson test` 报 24/25，唯一失败 `jose:alg_comp` 被 SIGSEGV 打死，且崩溃前一个字符都没输出** | 不是平台缺陷，也不是签名/栈/内存：`b_ndebug` 是 meson 的 **built-in** 选项，写进 `MesonToolchain.project_options` 会被命令行 `--buildtype=release` 反推覆盖。真机 `meson introspect --buildoptions` 实测：`werror=False`、`docs=disabled`、`wrap_mode=nodownload`、`default_library=static` 全部生效，**只有 `b_ndebug = true`**。于是 `-DNDEBUG` 生效，而上游把测试的执行体本身写在 `assert(z->feed(...))` / `assert(z->done(...))` 里，整个套件的断言与其副作用被编译器整段删掉：其余 24 项变成「零断言的空跑绿」，`alg_comp` 则因为流被半初始化后直接崩溃 | `configure()` 之后补一次 `meson configure <build> -Db_ndebug=false`，再用 `meson introspect --buildoptions` 读回真实值并**硬断言**为 false，否则直接 raise（宁可 create 失败也不发「空跑绿」的通过率）。判值要按字符串比：meson 把 `b_ndebug` 报成字符串 `'false'`，而 `werror` 是真布尔 `False`，写成 `is not False` 会把已经生效的配置误判成失败 |
| 2 | 12 个 `tests/jose-*` shell 脚本 `mktemp -d` 失败 | 真机 `/tmp` 只读（`touch /tmp/x` → `Read-only file system`），且 meson 的 `test(env:)` 不自动继承父进程临时目录变量 | 在 `tests/meson.build` 里对上游的 `e` 环境对象补 `TMPDIR/TMP/TEMP` 三项，并把测试命令前也再导出一次；只换临时根目录，不跳测试不改断言 |
| 3 | `jose-jwk-pub` / `jose-jwk-thp` 两条 shell 测试失败 | 脚本 `#!/bin/sh -ex` 在真机是 mksh：`echo $var` 未加引号会做词分割 + 方括号 glob 展开，JSON 里 `key_ops` 的 `["..."]` 被拆坏，jose 收到的字节已经不是原文（同输入用 `-i FILE` 方式却通过 → 故障在 shell 管道层，不在库） | 把 6 处 `echo $var` 改成 `printf '%s' "$var"`（逐字节回灌，断言、向量、退出语义一字未动）；配方内做幂等字符串替换并回报命中数，实测 `pub:5 thp:1` |
| 4 | meson `dependency('libcrypto')` 探测失败 | PkgConfigDeps 按 conan 包名只生成 `openssl.pc`，而上游 `lib/meson.build` 要 `libcrypto`、`tests/issue-75` 要 `openssl` | 由生成的 `openssl.pc` 派生 `libcrypto.pc`/`libssl.pc`；派生时**必须保留原 Libs 里的 `-L`/rpath 搜索参数**，只写 `-lcrypto` 会在链接期报 `unable to find library -lcrypto` |
| 5 | 真机没有 meson | harmonybrew 装了 ninja 1.13.2 与 pkg-config，但没有 meson（CI worker 有） | `tool_requires("meson/1.11.0")`（制品仓已有 1.11.0 / 1.11.0.1），两侧统一 |
| 6 | meson 起不来 ninja | HarmonyOS 的 CPython 经 posix_spawn 起子进程不查 PATH，meson 按裸名字找 ninja 会 ENOENT | 生成期把 `NINJA` 定义成绝对路径写进 build 环境，并把 `llvm-ar/llvm-ranlib/llvm-nm/llvm-strip/ld.lld` 从 profile 编译器目录解析后注入 `tc.binaries` |
| 7 | `conan create` 重新取源时 `github.com` 连接超时 | 真机直连 github.com 常被墙（§3.2 已知） | conandata 用 codeload 单值 URL（本机实测与 github.com/archive 字节同一）；codeload 末段无 `.tar.gz`，故 `get()` 显式传 `filename="jose-14.tar.gz"`，否则按后缀猜成 zip 报 `BadZipFile` |
| 8 | 安装包里的 `jose` 一跑就报 `Error relocating ... json_*: symbol not found`（22 条专项断言里 20 条红） | `bin/jose` 与 `libjose.so.0` 的 `DT_NEEDED` 正确记了 `libjansson.so`，但打包件**没有 RUNPATH**（`readelf -d` 实测只有 `NEEDED libjose.so.0/libjansson.so/libc.so`），而 jansson 包只给无版本号的 `libjansson.so`，只能靠运行期 `LD_LIBRARY_PATH` 找到；构建树内的测试能过是因为 meson 给它加了含依赖目录的 RUNPATH | `package_info()` 里 `cpp_info.requires = ["jansson::jansson"]` 并把 jansson 的 lib 目录显式 `runenv_info` 导出；同时按实测把 openssl/zlib 标成 `visible=False`（两者制品仓只有静态库，已被吸收进 4.1 MB 的 `libjose.so.0.0.0`），否则 conan 会以「direct dependency openssl is not used by any requires」报错 |
| 8b | 补齐 8 之后，按名字 `jose` 仍然找不到（消费者 runenv 的 `PATH` 里没有包内 `bin/`） | conan 2.29 对 POSIX 目标不会把依赖的 `cpp_info.bindirs` 拼进 `PATH`（实测 runenv `PATH` 只有 harmonybrew、`/data/service/hnp/bin`、`/usr/bin` 等系统目录），而上游是带 CLI + man 页发包的 | `package_info()` 同时向 `runenv_info` 与 `buildenv_info` 导出包内 `bin/`；消费者测试两边都断言：包导出的绝对路径可执行 + 经 runenv `PATH` 能直接敲 `jose`（专项断言数由 22 增至 23） |
| 9 | 上游 `werror=true` + `warning_level=2` | clang 15 把 `-Wshadow`/`-Wstrict-prototypes` 等告警变成错误 | `-Dwerror=false`（只改告警处理，测试二进制仍真编真跑）；另外 `tests/alg_encr.c` 里只在 `assert()` 内使用的辅助变量加 `(void)` 兜底 |
| 10 | 无 a2x / 无 jq | 真机与 worker 都没有 asciidoc 的 `a2x` | `-Ddocs=disabled`；`jq` 上游标注为 unrequired，不影响 |

## 依赖版本

- jansson/2.15.1.1（公开依赖：头文件 + DT_NEEDED）
- openssl/3.5.8.1（私有，静态吸收，`visible=False`）
- zlib/1.3.1.1（私有，静态吸收，`visible=False`；制品仓里 1.3.1.1 是 -fPIC 静态构建）
- meson/1.11.0（tool_requires）

## 上游测试台账

统计口径（可复跑）：

```bash
# tests/meson.build 的两个列表 + issue-75 子目录
python3 - <<'PY'
import re
s=open('tests/meson.build').read()
print('progs  =', len(re.findall(r"'([a-z_0-9]+)'", re.search(r'progs = \[(.*?)\]', s, re.S).group(1))))
print('scripts=', len(re.findall(r"'([a-z_0-9-]+)'", re.search(r'scripts = \[(.*?)\]', s, re.S).group(1))))
PY
# 真机上注册数自证：meson test --list 行数 = 25
```

| 口径 | 数量 | 说明 |
|------|------|------|
| 源码声明（C 可执行） | 8 | `progs`：alg_hash, alg_sign, alg_encr, alg_wrap, alg_comp, api_b64, api_jws, api_jwe |
| 源码声明（shell） | 16 | `scripts`：jose-{alg,fmt,b64-enc,b64-dec,jwk-eql,jwk-exc,jwk-gen,jwk-pub,jwk-use,jwk-thp,jws-fmt,jws-ver,jws-sig,jwe-fmt,jwe-dec,jwe-enc} |
| 源码声明（子目录） | 1 | `tests/issue-75/issue75`（`dependency('openssl')` 命中时注册；本配方命中） |
| **meson 注册（实跑分母）** | **25** | `meson test --list` 行数 |
| 真机实跑结果 | **Ok 25 / Fail 0 / Skipped 0 / Timeout 0** | `b_ndebug=false` 生效后的结果，见问题 1 |

注意：**v15 的 `tests/` 比 v14 多一个 `api_mem.c`**（所以已合入的 15 记的是 26 项），v14 是 25 项，不是少跑。

## 与已合入配方的关系（不作重复适配使用）

- `archives/l/libjose/14`（PR #10324，作者 `gcw_6a3w2yXz`）与本任务是**同一上游同一 tag**，但 conan 包名不同（`libjose` vs `jose`）；`archives/j/jose/15`（PR #10808）是同包异版本。本 PR 填的是 `jose` 包的 14 号版本位（制品仓与 main 的 `archives/j/jose/` 都没有 14，不触发 L0j/R37）。
- 配方主体与两份范本都不同：问题 1 的 `b_ndebug` 生效与自证、问题 8/8b 的 `visible=False` +
  runenv `LD_LIBRARY_PATH`/`PATH` 导出，都是本轮在真机量出来的（两份范本里都没有）；
  test_package 也完全不复用——消费者测试改为「只依赖 jose + jansson」的真实处境，
  并新增 23 条针对**安装包**（不是构建树）的 CLI 与 ELF 断言。

## 真机终态证据（独立 CONAN_HOME=~/work/psj/ch-jose，日志 ~/work/psj/jose-ch1.log）

```
CREATE_EXIT:0
Full package reference: jose/14#519a5f59afef1f84924e8c95070c907b
                                  :9777232a5082d15a293637ac36353a49b4b7b9f9   # 包 ID
                                  #2b2c2dc4b2e0b6a8096d02fd908e74af           # 包 rev
JOSE_MESON_OPTION buildtype = 'release'
JOSE_MESON_OPTION b_ndebug = 'false'          # 硬断言通过（问题 1）
JOSE_MESON_OPTION werror = False
JOSE_UPSTREAM_ADAPTATIONS=["tmpdir", "pub:5", "thp:1", "alg_encr:1"]
JOSE_UPSTREAM_TEST_RESULT={"status":"passed","executed":25,"passed":25,"failed":0,"skipped":0,"timeout":0}
JOSE_REIGNED_ELF=2/2
TOTAL=11 PASS=11 FAIL=0   (test_jose       —— 公共 <jose/b64.h> API)
TOTAL=23 PASS=23 FAIL=0   (test_jose_ohos  —— 安装后的 CLI、runenv PATH、打包 ELF 身份)
bin/jose            sha256 2aea411e4fab0e2eed05f99c0f6223ce66f4e06795dec171a5c1800a7398f58e  (109120 B)
lib/libjose.so.0.0.0 sha256 f17be6ca05ed04fb249ba4edd2b38b197c30825c24d01c7e9b23f2b90cd8c98b
                     SONAME libjose.so.0, NEEDED = libjansson.so + libc.so
od -An -tx1 -j18 -N2 bin/jose  ->  b7 00            # EM_AARCH64
包内清单：bin/jose, include/jose/*.h(8), lib/libjose.so.0.0.0(+.so/.so.0 符号链接),
          lib/pkgconfig/jose.pc, licenses/COPYING, share/licenses, share/man/man3/*.3(7)
```

依赖解析侧：`jansson/2.15.1.1`、`openssl/3.5.8.1`、`zlib/1.3.1.1`、`meson/1.11.0` 全部命中
制品仓预编译包（日志 `Already installed!`），真机只编了 jose 自己。
`openssl/3.5.8.1` 包内只有 `libcrypto.a`/`libssl.a`（静态），zlib 同理，故被吸收进
`libjose.so.0.0.0`；jansson 提供 `libjansson.so`，是唯一的运行期共享依赖。

