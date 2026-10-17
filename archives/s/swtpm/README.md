# swtpm

swtpm 是 Stefan Berger 维护的**软件 TPM（Trusted Platform Module）模拟器**，基于 libtpms 实现 TPM 2.0 与 TPM 1.2 的功能仿真，为虚拟化、自动化测试与 CI 提供无需物理 TPM 芯片的可信计算环境。

## 功能概述

- `swtpm` — TPM 模拟器守护进程，支持 socket / chardev / cuse 等接口
- `swtpm_setup` — TPM 状态初始化与配置工具
- `swtpm_ioctl` — TPM 控制接口工具
- `swtpm_bios` — TPM BIOS 初始化辅助工具
- `swtpm_localca` — 本地 CA 与证书管理工具

### 典型用途

- **作为后端模拟器供测试框架消费**：GnuPG 的 `tests/tpm2dtests` 即通过
  `${SWTPM} socket --tpm2 ... --server type=tcp,port=2321 --ctrl type=tcp,port=2322`
  启动本工具，再让 `gpg-agent` 经 TPM 执行密钥操作。
- 虚拟机（QEMU/libvirt）的 vTPM 后端。
- 作为其他软件测试套件的 TPM 前置（本包即为此目的适配）。

## OHOS 适配

### 构建期

- **源码形态**：上游 GitHub 以 git archive 发布 tag 快照，**不含预生成的
  `configure`**，需在源码目录执行 `autoreconf --install --force`。
  构建期由 `tool_requires automake/1.18 + libtool/2.5.4` 提供工具链。
- **`config.guess` 不认 HarmonyOS**（关键坑）：autoreconf 会把 automake 自带的
  `config.guess` 复制进源码树，而 automake/1.18 的该文件**没有 HarmonyOS 分支**
  （`grep -c HarmonyOS` = 0）。在 HarmonyOS 上 `uname -s` 返回 `HarmonyOS`，该脚本
  直接报 `unable to guess system type`，进而 `configure` 报
  `cannot guess build type; you must specify one`。

  **注意**：此文件**不能**用 `conandata.yml` 补丁解决 —— 补丁在 `source()`
  阶段应用，而 `config.guess` 要等到 `build()` 里 autoreconf 之后才存在。
  本配方在 `build()` 内调用 `_patch_config_guess()` 就地插入
  `*:HarmonyOS:*:*` 分支（等价于本仓 `scripts/patch-autotools-ohos.pl`
  的 config.guess 部分）。

- **`config.sub` 无需处理**：实测 automake/1.18 自带的 `config.sub` 已能接受
  `aarch64-unknown-linux-ohos`（原样输出、rc=0），无需像老版本那样补
  `linux-ohos*` 白名单。
- **禁止 `--build`/`--host`（R1）**：不传三元组，改由 `config.guess` 自行识别。
  在 CI 上传 `--build=<gnu triplet>` 还会触发
  `C compiler cannot create executables`（psfex / weightwatcher / skymaker 同报）。
- **`-Werror` 后置生效**：上游 `configure.ac` 在 `CFLAGS` 末尾追加
  `-Wmissing-prototypes -Wall -Werror`，位置在工具链注入的 `-Wno-error` **之后**，
  故 `-Wno-error` 无法压制。本配方补丁从该行移除 `-Werror`。
- **裁剪不可用特性**：`--without-gnutls`、`--without-seccomp`、`--without-cuse`、
  `--without-selinux`（OHOS 缺对应库/内核接口）。
- **`--disable-hardening`**：规避 OHOS 上的链接器探测问题。
- **静态链接**：`--enable-static --disable-shared`，避免 RPATH 问题。
- **`-j1`**：E074 —— HMDFS 上 jobserver fifo `EPERM`，并行 make 失败。
- **`umask 077`**：E114 —— HMDFS 会强制目录 setgid，`umask 077` 下
  config.status 无法创建临时目录，构建期从生成的 `configure` 中移除。

### 打包期（重要，易静默失败）

- **install 产物在 HMDFS 上可能被截断且丢失 `.codesign`**：`conan create`
  端到端 **EXIT=0**，但 `bin/swtpm --version` 报 `Permission denied`。
  实测对照：

  | | 构建树 | 包内（截断） |
  |---|---|---|
  | 体积 | 7203328 | 1235968 |
  | `.codesign` 段 | 有 | **无** |
  | 可执行 | ✅ | ❌ EPERM |

  构建日志唯一线索：`ginstall: error deallocating '<pkg>/bin/swtpm': Permission denied`。
  命中三个**大体积**产物；小体积的 `swtpm_bios`/`swtpm_ioctl` 未受影响。

  本配方在 `package()` 内以 `_restore_binaries()` **从构建树回填** `bin/` 产物
  （先 `os.remove` 再 `copyfile`，直接覆盖无法修正截断内容）。

### 运行期

- **走 TCP 而非 AF_UNIX**：OHOS 对 AF_UNIX 路径名 socket 有域限制，而 swtpm
  支持 `--server type=tcp,port=2321 --ctrl type=tcp,port=2322`，规避该限制。
- **状态目录**：`--tpmstate dir=<可写目录>` 需可写（写入 `NVChip` 等状态文件）。

## 依赖关系

### 编译依赖（构建期）

- `automake/1.18`、`libtool/2.5.4` — autoreconf 工具链（tool_requires）

### 运行依赖

- `libtpms/0.10.2` — TPM 1.2/2.0 仿真核心库
- `glib/2.84.0` — 基础运行时
- `json-glib/1.6.6` — JSON 状态序列化
- `libtasn1/4.21.0` — ASN.1 编码
- `openssl/3.5.6` — 加密原语
- `gmp/6.3.0` — 大数运算

### 上游测试的额外依赖（仅 `--enable-tests` 时需要）

`configure.ac:396-440` 在 `--enable-tests` 分支内要求六项外部工具全部存在
（缺一即 `AC_MSG_ERROR` 中止 configure）：`netstat` 或 `ss`、`expect`、`gawk`、
`socat`、`base64`、`cp`。其中 **`socat` 已由本仓独立适配**（原为唯一阻断项）；
补齐后 `configure --enable-tests` 实测 **rc=0**，测试成功启用（68 项）。

## 可用版本

| 版本 | 状态 | 说明 |
|------|------|------|
| `0.10.1.1` | ✅ built | 当前版本。基于上游 0.10.1 的 OHOS 适配轮次（本仓 `.1` 惯例，如 gnupg `2.4.9.1`）；源码 URL 与产物自报版本均为 0.10.1 |
| `0.10.1` | failed | 不完整：`conandata.yml` 引用的补丁从未提交，`conan export` 直接失败；`manifest.yaml` 曾误声明 `status=published` 而 ohpcd 零发布 |

> **本包在下游依赖链中的位置**：`tpm2-tss` → **`swtpm`**（本包）→ `gnupg tests/tpm2dtests`。
> gnupg 以 `AM_CONDITIONAL(TEST_LIBTSS, [test -n "$SWTPM" ...])` 判定是否让
> `tpm2dtests` 进入 `SUBDIRS`。

## 参考资料

- 源码仓库：https://github.com/stefanberger/swtpm
- 依赖核心：https://github.com/stefanberger/libtpms
- 知识条目：**E007/E072/E268**（config.guess/sub 适配）、**E114**（umask 077 临时目录）、**E516**（OHOS libc omits `_res`/`__res_state`，socat 侧同源）、**E074**（HMDFS jobserver fifo）
