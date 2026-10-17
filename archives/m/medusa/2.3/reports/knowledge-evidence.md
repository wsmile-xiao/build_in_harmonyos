# medusa 2.3 知识提炼证据

本文件为 PR #13807（`【知识库扩展】`）的知识草稿提供可复现证据。草稿位于：

- `knowledge/drafts/DRAFT-medusa-conan-generate-dep-paths.{kv,md}`
- `knowledge/drafts/DRAFT-medusa-autotools-platform-triplet-and-probe.{kv,md}`

所有证据来自 HarmonyOS 真机隔离构建（HarmonyOS PC aarch64 / HongMeng Kernel 1.12.0 /
clang 15.0.4 / Conan 2.29.1 / profile `ohos-aarch64-localdevice`，独立 `CONAN_HOME` +
独立 `RUN_DIR`，入口 `ohos-test-runner.sh --mode heavy --try-lock`）。

---

## EVID-01 Conan `generate()` 中依赖包目录为 `None`

**判定方式**（配方内一次性探测输出）：

```text
DEBUG openssl attrs: [... 'package_folder', 'package_path', 'pref' ...]
DEBUG openssl: package_folder=None package_path=<assert failed> includedirs=['include'] libdirs=['lib']
AssertionError: `package_folder` is `None`
```

- 生成器侧后果（同一轮的另一份配方修订，实机 `conanbuild.conf`）：
  `configure_args = ... --with-ssl=None`，且 `config.log` 出现
  `checking None/include/openssl/ssl.h... not found`。
- 含义：`package_folder` 与 `cpp_info.location` 在 `generate()` 均为 `None`，
  而 `cpp_info.includedirs` 只有包相对路径 `['include']`。

**影响面统计**（在仓库 `archives/` 内静态统计）：

```bash
grep -rl 'package_folder' --include=conanfile.py archives/ | wc -l
```

本轮实测统计：`archives/` 下共有 **1304 个配方**在 `generate()` 方法内读取
`self.dependencies[...].package_folder`。

**修复后验证**：`medusa-2.3-conan20` / `conan21` / `final` 三轮
`conan create` 均 `Success: 1 / Failed: 0`。

---

## EVID-02 conftest 因继承的依赖 `LIBS` 运行失败（假阳性 "cannot run C compiled programs"）

**失败基线**：run `medusa-2.3-conan9`（`b10.log`）

```text
medusa/2.3: RUN: "<build>/configure" --prefix=/ ... >&5
checking whether we are cross compiling... configure: error: in '<build>':
configure: error: cannot run C compiled programs.
If you meant to cross compile, use '--host'.
```

**`<build>/config.log` 的 conftest 段（逐字）**：

```text
configure:4379: clang -o conftest ... -lgcrypt -lgpg-error -lssh2 -lpthread >&5
configure:4383: $? = 0
configure:4390: ./conftest
Error loading shared library libgcrypt.so.20: (needed by ./conftest)
Error loading shared library libgpg-error.so.0: (needed by ./conftest)
Error loading shared library libssh2.so.1: (needed by ./conftest)
configure:4394: $? = 127
configure:4403: error: cannot run C compiled programs.
```

编译与链接返回 0，失败只发生在运行 conftest：**不是编译器/工具链问题**，而是共享库加载路径问题。

**修复后**：run `medusa-2.3-conan20` 起，configure 全流程通过
（`checking build/host/target system type... aarch64-unknown-linux-ohos`）。

---

## EVID-03 `AutotoolsToolchain` 无 `extra_cppflags`

**失败基线**：run `medusa-2.3-conan4`

```text
medusa/2.3: Error in generate() method, line 124
	tc.extra_cppflags.extend(
	AttributeError: 'AutotoolsToolchain' object has no attribute 'extra_cppflags'
```

**修复**：include 路径改走 `extra_cflags` / `extra_cxxflags`（`extra_ldflags` 走 `-L`）。
真机 `config.log` 确认 CFLAGS 已带上四个依赖 include：

```text
ac_cv_env_CFLAGS_value='-O3 -I.../libgcrypt.../include -I.../libgpg-error.../include -I.../libssh2.../include -I.../openssl.../include'
```

---

## EVID-04 config.guess 插入分支缺 `echo/exit` → 穿透到失败路径

**失败基线**：run `medusa-2.3-conan7`

```text
configure: error: cannot guess build type; you must specify one
UNAME_MACHINE = "aarch64"
UNAME_SYSTEM  = "HarmonyOS"
```

同时 `grep -c HarmonyOS <build>/config.guess` = 1（补丁**已应用**却仍失败）。

**根因证据**：`scripts/patch-autotools-ohos.pl` 第 51–63 行插入块以
`"\tGUESS=\${MACHINE}-unknown-linux-ohos\n" . "\t;;\n\n"` 结束，只有赋值；
而 medusa 的 `config.guess` 中 `echo ... ; exit ;;` 形式出现 **230 次**，
主 `case` 之后即 `echo "$0: unable to guess system type" >&2` + `exit 1`。

**修复**：分支改为 `echo "${MACHINE}-unknown-linux-ohos"` + `exit ;;`。

**stub 验证（本机 MSYS，无需真机）**：

```text
config.guess (HarmonyOS stub)  → aarch64-unknown-linux-ohos     rc=0
config.guess (Linux stub)      → aarch64-unknown-linux-gnu      rc=0   （回归未破坏）
```

**真机验证**：run `medusa-2.3-conan8` 起三元组三行全部为 `aarch64-unknown-linux-ohos`。

---

## EVID-05 config.sub 归一化把 `linux-ohos` 改写成 `linux-gnu-ohos`

**失败基线**：白名单补齐后

```text
$ ./config.sub aarch64-linux-ohos
aarch64-unknown-linux-gnu-ohos
```

**根因证据**（`config.sub` 通用规则，位于白名单检查之后）：

```sh
	-linux*)
		os=`echo $os | sed -e 's|linux|linux-gnu|'`
		;;
```

**修复**：在其前插入 `-linux-ohos*) os=-linux-ohos ;;`。

**验证**：

```text
$ ./config.sub aarch64-linux-ohos          → aarch64-unknown-linux-ohos
$ ./config.sub aarch64-unknown-linux-ohos  → aarch64-unknown-linux-ohos
$ ./config.sub x86_64-pc-linux-gnu         → x86_64-pc-linux-gnu          （回归）
```

---

## EVID-06 「假定式」降级探测静默禁用 SSH 模块

**失败基线**：run `medusa-2.3-conan19`（`log-conan19.log`）

```text
configure: checking for Libssh2 Library files...
checking for main in -lssh2... yes
configure: WARNING:  LIBSSH2 path not found. Assuming it was...
configure: WARNING:  No ldd detected. Unable to test whether Libssh2 was compiled to use libgcrypt. Assuming it was...
checking for gcry_control in -lgcrypt... yes
configure: checking for GnuTLS Library files...
checking for gnutls_handshake in -lgnutls... no
configure: WARNING:  *** GnuTLS required for installed version of Libssh2 ***
configure: WARNING:  The SSH2 module will NOT be built.
checking whether to enable SSH module... no
configure:     SSH             ** Disabled **
```

构建全程无 error、门禁 L0/L1/L5 正常，但产物缺 `ssh.mod`：**"构建成功"≠"功能完整"**。

**修复后**：run `medusa-2.3-conan20`（`log-conan20.log`）

```text
configure:     SSH             Enabled
[ok] ssh module loaded (libssh2 + libgcrypt)
[info] modules dlopen'ed successfully: 22
```

**兜底机制说明**：该缺口是被 `test_package` 的运行期断言
（`medusa -d` 统计 **dlopen 成功**的模块数——实现上先剔除上游 `listModules.c` 的
`Couldn't load` / `Invalid module` 两类失败行再计数，含 `ssh`）发现的，
不是被编译门禁发现的。

---

## EVID-07 附：`umask 077` / `config.status` 与 pthread 取消（已有条目覆盖，仅记录增量）

| 现象 | 既有条目 | 本轮处理 | 增量 |
| --- | --- | --- | --- |
| `./config.status: line 602: ./conf8OrVAv/subs1.awk: Permission denied`（run `conan13`） | **E011 / E060 / E112** 已充分覆盖根因（`drwx--S---` + UID 映射） | 补丁 0004 直接改 `configure` 中的 `umask 077`（源头一次修改同时作用于 configure 与生成的 config.status） | **方案增量**：不 sed 生成物、不预建目录、不搬 tmpfs，可作为一个 4 行 unified diff 随配方发布 |
| `ld.lld: error: undefined symbol: pthread_cancel / pthread_setcanceltype / pthread_setcancelstate`（run `conan17`） | **E085 / E127** 已覆盖"musl 未实现取消类接口" | 补丁 0007 用 `AC_CHECK_FUNCS([pthread_cancel])` 生成 `HAVE_PTHREAD_CANCEL`，补丁 0005 据此条件编译取消调用、无该能力时走协作关闭路径 | **替代实现模式增量 + R8 合规写法**：不是 `undef` 开关，也不是平台宏（首版曾用 `#ifdef __OHOS__`，AI 检视 P1 依 R8 判定不合规后改为能力探测；仓库内已有 `HAVE_PTHREAD_CANCEL` 先例） |
| `make: jobserver mkfifo: ... Operation not permitted` | E074/P020（FIFO 不受支持） | `autotools.make(args=["-j1"])` | 无新意，未单独成条 |
| `-lrt` 在 OHOS 上实测**可以链接**（链接器容忍缺失库） | knowledge 中通用做法为移除 `-lrt` | 仍保留补丁 0003（与既有做法一致） | **负面/存疑证据**：说明该移除并非必需的硬约束，留待后续按库验证 |

---

## 复现入口

```bash
# 真机（隔离 job）
. "$HOME/ohos-users/medusa/medusa-2.3-build/env.sh"
cd "$CI_REPO_ROOT"
sh "$HOME/bin/ohos-test-runner.sh" --user medusa --lib medusa \
  --task medusa-2.3-final --mode heavy --try-lock --workdir "$CI_REPO_ROOT" \
  -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"

# 单包 shadow CI
CI_PACKAGES="archives/m/medusa/2.3" zsh ci/conan/build_and_test.sh
```

最终 RUN_DIR：`$HOME/ohos-test-runs/medusa-medusa-medusa-2.3-final-20260929-170943-34668`
（`L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=skip` / `L4_RESULT=warn` / `L5_RESULT=pass`，
`Success: 1 / Failed: 0`）。
