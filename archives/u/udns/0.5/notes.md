# udns 0.5 适配笔记

## 编译环境
- 构建系统: 自研 autoconf 风格（configure + configure.lib + Makefile.in）
- 编译日期: 2026-09-30
- 编译器: OHOS 6.0 SDK clang 15（aarch64-unknown-linux-ohos-clang，交叉编译）
- 目标: HarmonyOS PC / OHOS 6.0 / aarch64 (armv8)
- 产物: libudns.a（静态库，86770 字节）+ udns.h + COPYING.LGPL
- 状态: built

## 编译步骤

```bash
# 1. 解压官方源（sha256 035bfc12...03c0）
tar xzf udns-0.5.tar.gz

# 2. 打补丁：修复上游 configure 的 inet_pton()/inet_ntop() 探测原型错误
#    （patches/0001-configure-fix-inet_pton-inet_ntop-probe-prototypes.patch）

# 3. configure（就地构建；udns configure 不接受 --prefix，仅支持 IPv6 选项）
sh ./configure --enable-ipv6

# 4. 构建静态库（不含示例工具，保持库级最小产物）
make staticlib -j1
# 产物: libudns.a（+ 构建期生成 udns_codes.c 与 config.h）
```

## ★ 关键问题与解决方案

### 1. 【本次适配的核心问题】上游 configure 的 inet_pton()/inet_ntop() 探测原型错误，导致 libudns.a 符号表与自身头文件不一致

**现象**：消费者只要调用 `dns_pton()` / `dns_ntop()`（udns.h 中声明、udns_resolver.c 内部也在用），链接必然失败：

```
ld.lld: error: undefined symbol: dns_pton
>>> referenced by test.c
>>> referenced by udns_resolver.c: udns_resolver.o:(dns_add_serv)
ld.lld: error: undefined symbol: dns_ntop
>>> referenced by test.c
>>> referenced by udns_resolver.c: udns_resolver.o:(dns_add_serv)
>>> did you mean: dns_dntop
>>> defined in: libudns.a(udns_dn.o)
```

**根因链**（逐环验证）：

1. `configure` 用一段探测程序判断 libc 是否提供 `inet_pton()`/`inet_ntop()`，0.5 的探测体写作：

   ```c
   int main() {
     char buf[64];
     long x = 0;
     inet_pton(AF_INET, &x, buf);                 /* long* 传给 const char* 形参 */
     return inet_ntop(AF_INET, &x, buf, sizeof(buf));  /* const char* 当 int 返回 */
   }
   ```

   这段代码本身是 ill-formed。clang 对 `incompatible pointer to integer
   conversion returning 'const char *' from a function with result type 'int'`
   报的是**硬错误**（不是可用 `-Wno-*` 降级的警告，实测 `-Wno-error
   -Wno-incompatible-pointer-types` 仍然报 error），因此探测必然失败。

2. 探测失败 → configure **不会**在 config.h 中写入 `#define HAVE_INET_PTON_NTOP 1`。
   实测生成的 config.h 只有：
   ```c
   #define HAVE_GETOPT 1
   #define HAVE_IPv6 1
   #define HAVE_POLL 1
   ```
   （注意 configure 退出码仍是 0 —— 探测失败被当成"该功能不可用"，**不报错**，
   这是本问题最隐蔽的地方。）

3. `udns_XtoX.c` 的结构是：
   ```c
   #ifdef HAVE_INET_PTON_NTOP
     const char *dns_ntop(...) { return inet_ntop(...); }
     int dns_pton(...) { return inet_pton(...); }
   #else
     #define inet_XtoX_prefix udns_
     #include "inet_XtoX.c"
   #endif
   ```
   宏缺失 → 走 `#else` 回退分支 → 实际产出的是 **`udns_ntop()` / `udns_pton()`**，
   而 udns.h 声明的、库内部 `udns_resolver.c` 调用的都是 **`dns_ntop()` / `dns_pton()`**。

4. 结果：`libudns.a` 的符号表与它自己随包发布的 `udns.h` 不匹配。任何消费者
   （CMake 目标也好、裸 `cc -ludns` 也好）链接都必然失败。

**对照验证**（证明这是 0.5 特有、且是上游后来修掉的）：

| 版本 | configure 探测体 | config.h 得到 | libudns.a 导出 |
|------|------------------|---------------|----------------|
| 0.5  | `inet_pton(AF_INET, &x, buf); return inet_ntop(...)` | 无 `HAVE_INET_PTON_NTOP` | `udns_pton` / `udns_ntop`（错） |
| 0.6  | `inet_ntop(AF_INET, &x, buf, sizeof(buf)); inet_pton(AF_INET, buf, &x); return x;` | `#define HAVE_INET_PTON_NTOP 1` | `dns_pton` / `dns_ntop`（对） |

仓库内姊妹包 `archives/l/libudns/0.6` 之所以能过，正是因为它用的 0.6 源码探测已修好。

**解决方案**：`patches/0001-configure-fix-inet_pton-inet_ntop-probe-prototypes.patch`
把 0.5 的探测体替换为上游 0.6 修正后的版本。补丁后 `checking for inet_pton() &&
inet_ntop()... yes`，config.h 出现 `#define HAVE_INET_PTON_NTOP 1`，
`libudns.a` 导出 `T dns_ntop` / `T dns_pton`。

**反向证伪（证明补丁是真实门禁而非装饰）**：临时移除 `conandata.yml` 的 patches
段重新 `conan create`，构建立即失败，复现上述 `undefined symbol: dns_pton /
dns_ntop`；恢复补丁后 `conan create` 退出码 0。

**方法论教训**：编译探测（configure conftest / CMake try_compile）失败不总是
"该功能不可用"，也可能是**探测程序自己写错了**。因此看 configure 退出码为 0
是不够的，必须核对生成的 config.h 宏，以及最终归档的符号表是否与公开头文件一致。

### 2. udns 0.5 与 0.6 的真实 API 差异（影响消费者代码，测试必须按 0.5 原型写）

| API | 0.5 原型 | 0.6 原型 | 影响 |
|-----|----------|----------|------|
| `dns_ntop` | `const char *dns_ntop(int, const void *, char *, int)` | `... char *dst, unsigned size)` | 第 4 参数有/无符号不同 |
| `dns_dntop` | `int dns_dntop(dnscc_t *, char *, unsigned)` | 返回 `const char *` | 返回值类型变化 |
| `dns_free` | `void dns_free(struct dns_ctx *ctx)`，内部断言 `ctx != NULL && ctx != &dns_defctx` | `void dns_free(struct dns_ctx *ctx, void *result)` | 0.5 **不能** `dns_free(NULL)`（默认上下文下会 abort）；默认上下文的结果由 `dns_close(NULL)` 回收 |
| `dns_new` | `dns_new(const struct dns_ctx *copy)` 内部断言 `CTXINITED(copy)`（udns_resolver.c:457），**必须先有一个已初始化的上下文可复制** | 同左 | 0.5 直接 `dns_new(NULL)` 会 abort（实测 `Assertion failed: CTXINITED(copy)` + Signal 6）；正确姿势是先 `dns_init(NULL,0)` 再 `dns_new(NULL)` 派生独立上下文 |

后两点在首次运行时以真实崩溃暴露出来（`Assertion failed: ctx != NULL &&
ctx != &dns_defctx (udns_resolver.c: dns_free: 477)`），已按 0.5 原型修正测试代码，
并在测试注释中标注为版本适配点。

### 3. udns 自带 configure 不接受 `--prefix`/`--host` 等 GNU autoconf 选项

上游 configure 为自研脚本（configure.lib），仅支持 `--enable/--disable-ipv6`
与 `--help`（`--disable-*|--without-*|--no-*` 一律按 disable 处理）。因此不能
复用 `Autotools(self).configure()`，改为手动就地运行 configure。

### 4. `Makefile` 无 `install` 目标、且非 VPATH

上游 Makefile.in 仅含 all/static/staticlib/shared/sharedlib/dist/subdist/clean/
distclean/depend，无 install 目标；SRCS 为裸文件名，不支持 out-of-source 构建。
故 `build()` 中 `cd` 到源码目录就地构建（configure + make 均在 source_folder），
`package()` 手动 copy `libudns.a` 与 `udns.h`。

### 5. `self.run()` 中不能裸用 `${CC}`（R33）

configure 用 `$CC`/`$CFLAGS` 环境变量探测编译器，由 `AutotoolsToolchain` 生成的
conanbuild env 提供，`self.run(..., env="conanbuild")`。

### 6. 真机/受限环境的两类平台问题（沿用并保留上游 0.6 配方的处理）

- `[missing_build_tool]` 真机 make 位于 `/data/service/hnp/bin/make` 且不保证在
  子进程 PATH 上 → `build()` 用 `HMBS_MAKE` → `shutil.which("make")` → `"make"`
  三级解析。
- `[readonly_tmp]` OHOS `/tmp` 只读，configure/conftest/mktemp 默认写 `/tmp` 失败
  → 把 `TMPDIR/TMP/TEMP` 指到 HMBS 注入的可写 tmpdir（回退 build_folder/.tmp）。
- 不硬编码 HNP shell，改用 HMBS 注入的 `CONFIG_SHELL/SHELL`（真机 `/bin/sh`）。

### 7. Conan 2 要求 package_type="library" 必须声明 shared option

udns 上游只提供静态库构建（`make staticlib` → libudns.a），故声明
`options = {"shared": [True, False]}` 与 `default_options = {"shared": False}`，
无论取值均只构建静态库。

### 8. 上游无测试套件

源码审计确认 Makefile 无 check/test 目标、无 tests/ 目录、无测试框架、无 CI 配置
（详见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`，含
`upstream_test_total: 0`）。`test_package` 承担全部实质性验证。

## 源码修改（补丁）

| 补丁 | 类型 | 说明 |
|------|------|------|
| `patches/0001-configure-fix-inet_pton-inet_ntop-probe-prototypes.patch` | portability | 修复上游 configure 的 inet_pton()/inet_ntop() 探测原型错误（采用 0.6 已修正的探测体），使 config.h 得到 `HAVE_INET_PTON_NTOP`、libudns.a 导出头文件声明的 `dns_ntop()`/`dns_pton()` |

除该补丁外，udns 0.5 源码在 OHOS clang 上可直接编译，无需 config.guess/config.sub
或平台宏适配（POSIX socket/网络接口齐全，IPv6 由 configure 探测启用）。

## 测试（三层，真实执行）

| 层 | 目标 | 用例数 | 结果 |
|----|------|--------|------|
| 1 | `test_udns`（CMakeDeps 消费者 udns::udns） | 12 | 12/12 通过 |
| 2 | `test_static_link`（裸 `-ludns` 直连 libudns.a） | 8 | 8/8 通过 |
| 3 | `test_udns_ohos`（鸿蒙特有，rule12 本地应答器端到端回环） | 1 | 通过（A = 127.0.0.1，与期望值一致） |
| | **合计** | **21** | **21/21**（层3 为端到端门，计 1 项） |

执行方式：aarch64 目标经 profile 的 `CMAKE_CROSSCOMPILING_EMULATOR`
（`/root/ohpc/bin/ohos-qemu-aarch64`，qemu-aarch64-static + 真机 musl 运行根）
执行；另以 `-static` 静态链接后直接经 qemu 运行复核，与真机口径一致。

关键输出：

```
test_udns: RESULT 12/12 checks passed (udns 0.5)
E2E_DNS_RESULT={"status":"passed","host":"localhost","nrr":1,"first":"127.0.0.1"}
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_udns","discovered":12,"passedCount":12}
test_static_link: RESULT 8/8 checks passed
OHOS_E2E_RESULT={"status":"passed","host":"localhost","nrr":1,"first":"127.0.0.1","elapsed":0}
HMBS_UPSTREAM_TEST_RESULT={"status": "no_tests", ...}
```

离线容错：层 1 的端到端回环与层 3 在无 DNS 可达性的环境（沙箱/CI）会如实输出
`status=skipped` 并给出原因，退出码 0 但**明确不计为通过**；层 1 的 12 项离线
确定性断言与层 2 的 8 项在任何环境都必须 100% 通过。

## 依赖版本

- **无外部依赖**：纯 C 库，仅依赖系统 libc 与 POSIX socket/arpa/inet 接口。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（自研 autotools，就地构建静态库，手动打包） |
| conandata.yml | 官方源 URL + sha256 + patches 注册 |
| patches/0001-...patch | 修复 configure inet_pton/ntop 探测原型（本轮核心修复） |
| test_package/ | 三层消费者测试（test.c / test_static_link.c / test_udns_ohos.c） |
| test_package/MANIFEST.yml | 上游测试审计（upstream_test_total: 0）+ 测试清单 |
| manifest.yaml | 版本级 manifest |
| notes.md | 本笔记 |

## 注意事项

1. 只打包 `libudns.a` 与 `udns.h`，示例工具 `dnsget`/`rblcheck`/`ex-rdns` 不打包
   → 无 bin/，无需 commands.json（R38）
2. 版本号 0.5（不加后缀，R37）
3. `settings.os` 判断用 `in ("Linux", "OHOS")`（R32）
4. `build()` 不依赖未定义 shell 环境变量（R33），编译器来自 AutotoolsToolchain
   conanbuild env
5. **补丁不可移除**：`patches/0001` 是库可用性的前提，移除后消费者 100% 链接失败

## 真机验证（DAYU200 · 规则 12 消费者端到端证据）

设备：润和 DAYU200-RK3568 · OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)
序列号：`450100445634303332018f3e7d2dba00`
执行器：`bash /mnt/d/OHDev/automation/device_runner.sh run <job> <dir> <cmd>`
二进制：`aarch64-unknown-linux-ohos-clang -static`（ELF64 / AArch64 / EXEC，设备无运行库依赖）

### 三层结果（真机实测，均 exit_code=0）

| 层 | 作业名 | 命令 | 结果 | evidence |
|----|--------|------|------|----------|
| 1 | `udns_offline` | `./test_udns` | 12/12 通过 | `offline_evidence.json` exit_code=0 |
| 2 | `udns_static` | `./test_static_link` | 8/8 通过 | `static_evidence.json` exit_code=0 |
| 3 | `udns_ohos_e2e` | `./test_udns_ohos` | 端到端回环通过 | `ohos_e2e_evidence.json` exit_code=0 |

层 3 真机输出：

```
libudns 0.5 OHOS 端到端解析闭环
== [B] 本地 UDP DNS 应答器回环 ==
  本地应答器: 127.0.0.1:56974
  已配置 nameserver 127.0.0.1:56974
  dns_sock=4 server=127.0.0.1
  [cb] A[0] = 127.0.0.1
OHOS_E2E_RESULT={"status":"passed","mode":"local-responder","server":"127.0.0.1:56974","nrr":1,"first":"127.0.0.1","expected":"127.0.0.1"}
libudns OHOS 端到端回环通过：A = 127.0.0.1（与应答器写入的期望值一致）
```

### ★ 为什么用"本地应答器"而不是外部 DNS

实测该 DAYU200 **完全无网络**：`ifconfig` 显示 `wlan0`/`eth0`/`eth1` 的 RX/TX 包数全为 0，
`ping 8.8.8.8` 返回 `ping: sendto: Network unreachable`（`/etc/resolv.conf` 里虽配了
114.114.114.114 / 8.8.8.8 但根本不可达）。

若 rule12 用例只依赖外部 DNS，在这种设备上只能输出 SKIP —— 那等于**放弃端到端验证**。
因此 `test_udns_ohos.c` 内置一个最小 UDP DNS 应答器线程（绑定 127.0.0.1 临时端口，
回一条合法 A 记录应答报文），再通过 `dns_add_serv_s()` 把解析器指向它，从而**确定性**
走通 libudns 的真实链路：

```
查询报文编码 → sendto → 应答接收 → DNS 报文解析 → RR 解码(dns_rr_a4)
→ 回调派发 → dns_ntop 渲染 → dns_close
```

这条链路覆盖了库的核心解析逻辑，且不依赖任何外部网络。

### 反向证伪（证明断言不是空壳）

把应答器写入的 RDATA 由 `127.0.0.1` 改成全 0 后重新构建运行：

```
libudns OHOS 端到端回环失败：期望 127.0.0.1，实际 "0.0.0.0"
OHOS_E2E_RESULT={"status":"failed","mode":"local-responder","expected":"127.0.0.1","got":"0.0.0.0","nrr":1}
NEG_EXIT=1
```

即用例确实在断言**解析结果的值**，而不只是"有应答"。这条反向测试还顺带修掉了两个
真实的测试缺陷（见下）。

### 开发过程中发现并修复的测试缺陷

1. **`dns_init(&ctx, 0)` 用法错误导致 SIGSEGV**：udns 所有 API 的 `ctx` 参数传 `NULL`
   即表示内置默认上下文 `dns_defctx`，`dns_init()` 的返回值只是成败、**不会回写指针**。
   写成二级指针会把栈上的野指针当上下文用，真机直接 `Signal 11`。
2. **`dns_add_serv(ctx, "127.0.0.1:53")` 返回 EINVAL**：0.5 的 `dns_add_serv()` 只接受
   **裸 IP**（内部走 `dns_pton`），带 `:port` 会失败；指定端口必须用
   `dns_add_serv_s(ctx, const struct sockaddr *)`（端口需网络字节序）。
3. **断言过弱 + 错误回退掩盖故障**：最初只断言 `nrr > 0`，且本地回环失败后会回退到
   系统解析器。实测把 RDATA 破坏成全 0 时，回退让系统解析器把测试**重新判成 passed**，
   完全掩盖了本地解码故障。已改为：断言必须等于期望值 `127.0.0.1`，且本地回环是
   **权威**路径，未达期望值即判 failed、退出码 1，不回退。

---

**编译结束**: 2026-09-30
**真机验证**: 2026-10-01（DAYU200 / OpenHarmony 6.0.0.47）
**门禁的可复核性（构建期强制）**:

- `build()` 在 `apply_conandata_patches()` 之后**不信任其返回值**，而是直接断言
  `configure` 的 inet_pton/ntop 探测程序已被改写、且 `config.h` 含
  `HAVE_INET_PTON_NTOP`。原因：实测 patch_ng 的语义是"只要有一条 hunk 命中就
  整体返回成功"（干净源码 → True；已完整应用后重打 → **True 且静默 no-op**；
  部分已应用 → False 硬失败），源码树状态不同会导致结果不同，而源码树一旦被
  污染，"补丁是否真的生效"就没有独立证据。该断言使这一前提成为构建期门禁。
- `test()` 的每一层在执行后都会把输出 tee 到日志，并断言该层的**证据标记**确实
  出现（层1 `HMBS_TEST_PACKAGE_RESULT`、层2 `RESULT 8/8 checks passed`、
  层3 `OHOS_CTX_RESULT` + `OHOS_E2E_RESULT`），缺失即抛 `ConanException`。
  这样"这层真跑了"由运行日志证明，而不是依赖"能否编译链接"这一实现细节 ——
  仓库 CI 的 L1e 破坏性反向验证（移走 lib/include 后重跑、期望失败）因此
  不再把语义寄托在编译失败上，失败信息也不会指向错误的层。
- 可执行性判定统一用 Conan 的 `can_run(self)`，**不比较 -pr:h/-pr:b 的 settings**：
  仓库 CI 用的是 `-pr:h="$PROFILE_FILE" -pr:b="$PROFILE_FILE"`（同一个 profile），
  两者 settings 恒等，任何"比较两个 profile"的自造 cross 判据都会恒为
  "非交叉"而绕过保护。

**最终状态**: built（三层测试 21/21 通过（12+8+1）；本地 qemu 复核通过；
**真机 DAYU200 三层全部通过**，含 rule12 本地应答器端到端回环）
