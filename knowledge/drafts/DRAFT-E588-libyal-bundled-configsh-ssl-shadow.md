# DRAFT E588 — libyal 发布包内置 `common/config.h` 遮蔽 configure 新生成头（openssl/evp.h file not found）

- **软件**：libfvde 20240502（libyal 家族；同现象见 libbde/20240502 配方注释）
- **任务**：`feat/libfvde-20240502`（设备单端模式，OHOS aarch64 真机）
- **状态**：DRAFT（配对 `DRAFT-E588-libyal-bundled-configsh-ssl-shadow.kv`）
- **编号**：`E588`（`tools/knowledge_id.py --claim --task libfvde-20240502` 取号，建 PR 前 `--check E588 --fresh` 回查）

## 1. 现象

在 OHOS aarch64 上按常规（VPATH/out-of-source）方式 `conan create` 某个 libyal 加密类库时，构建在
`libhmac/`（或 `libcaes/`）阶段直接死于：

```
fatal error: 'openssl/evp.h' file not found
```

错误行落在 `libhmac/libhmac_md5_context.h` 之类被 `HAVE_LIBCRYPTO` / `HAVE_OPENSSL_EVP_H`
守卫的头文件里。形态极像"缺依赖"，于是很容易被误判成工具链问题去装包/改 profile——都不解决。

## 2. 根因（三层叠加）

1. **上游把生成物提交进了发布包**：release tarball 同时含
   `common/config.h`（维护者机器上用 `AC_CONFIG_HEADERS` 生成）与模板 `common/config.h.in`。
   libfvde 20240502 实测：

   | 文件 | 行 | 内容 |
   |---|---|---|
   | `common/config.h`（发布包内） | 239 | `#define HAVE_LIBCRYPTO 1` |
   | `common/config.h`（发布包内） | 419 | `#define HAVE_OPENSSL_EVP_H 1` |
   | `common/config.h.in`（模板） | 238 / 418 | `#undef HAVE_LIBCRYPTO` / `#undef HAVE_OPENSSL_EVP_H` |

   即：维护者机器**有** OpenSSL，这份陈旧头把 `HAVE_*` 钉成"有"。

2. **引号包含让源树副本永远优先**：`common/common.h:26` 是 `#include "config.h"`。
   C 预处理对引号包含**先查包含者所在目录**，所以只要编译工作目录在源树内（含
   `-I../common` 的 VPATH 构建，因为 `common.h` 本身来自源树），生效的永远是那份陈旧
   `config.h`；configure 在构建树里新生成的头根本轮不到。`-I` 顺序改不了这条规则。

3. **目标 sysroot 没有该头**：OHOS SDK 26.0.0.18 sysroot 下不存在
   `usr/include/openssl/evp.h`，于是被守卫的 `#include <openssl/evp.h>` 直接编译失败。

## 3. 设备可执行复现

```sh
TASK_DIR="$HOME/tmp/libfvde-20240502"; SRC="$TASK_DIR/src-check/libfvde-20240502"
grep -nE '^#define HAVE_LIBCRYPTO 1|^#define HAVE_OPENSSL_EVP_H 1' "$SRC/common/config.h"
grep -nE '^#undef HAVE_LIBCRYPTO|^#undef HAVE_OPENSSL_EVP_H'        "$SRC/common/config.h.in"
sed -n '20,30p' "$SRC/common/common.h"          # 期望 #include "config.h"
ls /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/openssl/evp.h
```

复现命令落 `$TASK_DIR`（设备 `/tmp` 只读，不能用作证据落点）。

## 4. 处置（libfvde 实测有效，两条同时用）

1. **in-source 构建**：在该源码目录内直接跑 `configure`/`make`/`make install DESTDIR=…`
   （conan 配方里 `cwd=self.source_folder`）。`config.status` 会把新的
   `common/config.h` 写回**源树同一路径**，从物理上覆盖陈旧副本。构建日志里的正面判据：

   ```
   config.status: creating common/config.h
   ```

2. **显式 `--with-openssl=no`**：让 libhmac / libcaes 走包内自带的本地实现
   （发布包里 `HAVE_LOCAL_LIBHMAC=1` / `HAVE_LOCAL_LIBCAES=1` 的本地目录都在），
   不引入制品仓未发布的声明外依赖，也不再受宿主机 libcrypto 有无头文件影响。

若必须 VPATH 构建：在 `build()` 开头删除源树的陈旧生成头
（`os.unlink(source_folder/common/config.h)`，libbde/20240502 的做法）；
或把源树 `config.h` 的两行改回 `#undef`、或把 `common.h` 的引号包含改成
`#include <config.h>` 并保证 `-I<builddir>/common` 在前（后两种要改上游文件，
须在 PR 说明理由）。

## 5. 边界与反例

- **不是缺依赖**：装 openssl 头、注入 `-lcrypto`、改 profile 都不解决，还会引入
  制品仓未发布的依赖（E412 同族）；包内本就有可用实现。
- **与 E412 的区别**：E412 是 configure **自动探测**到未声明的可选后端；
  本条是探测结果被**发布包内的陈旧生成物**整体遮蔽，configure 的结论根本没生效。
- **与 E284 的区别**：E284 是交叉编译时缺少/需要生成 target config header；
  本条是生成物**存在但是宿主机内容**。
- **与 `DRAFT-libfsntfs-release-archive-closure` 的分工**：那条管"组件目录与生成文件
  齐不齐、镜像身份是否可审计"；本条管"生成文件齐了但内容来自维护者机器"。

## 6. libyal 家族复用提示（同族 9 个待办任务）

同一发布包形态（自包含 tarball + 17 个内置 libyal 组件 + 预生成 Autotools 文件）
在 OHOS 上的配方骨架（libfvde/20240502 实机验证）：

- 用显式 GNU 三元组绕过不认 HarmonyOS 的 `config.guess/config.sub`（E007）；
- in-source + `umask 022`（E011）；脚本经解释器执行（E087）；
- `make check` 里 libtool 包装脚本要解析到 `.libs/`（E330 同族补丁形态）；
- `--disable-python --with-libfuse=no --enable-static-executables=no`；
- 上游测试计数：`tests/Makefile.am` 的 `check_PROGRAMS`（libfvde = 27）+ 默认 `TESTS`
  驱动（3 个，其中 `test_fvdeinfo.sh` 因发布包无 `tests/input` 按上游设计 exit 77 SKIP）。

## 7. 复现证据（本任务）

| 项 | 值 |
|---|---|
| 源码 | `libfvde-experimental-20240502.tar.gz`，sha256 `c2d22eca9f646a5a388c6c22d6920292832384800ebeb519c03907bd5003c49b` |
| 陈旧头 | `common/config.h:239` `#define HAVE_LIBCRYPTO 1`、`:419` `#define HAVE_OPENSSL_EVP_H 1` |
| 目标 sysroot | `.../sysroot/usr/include/openssl/evp.h` 不存在（实测 `No such file or directory`） |
| 正解判据 | `dev-build1.log` 中 `config.status: creating common/config.h`，libhmac/libcaes 全程无 `openssl/evp.h` 报错 |
