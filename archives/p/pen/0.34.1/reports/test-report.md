# pen 0.34.1 测试报告

> **项目**: pen 0.34.1（tcp/udp 负载均衡器）
> **测试日期**: 2026-09-28
> **测试环境**: HarmonyOS / OpenHarmony PC，aarch64（armv8），clang 15.0.4，libc++
> **测试类型**: 上游测试入口实测（make check）+ 新增鸿蒙消费者用例（真实数据面/控制面）

---

## 一、测试摘要

### 1.1 上游测试（`make check`，R51 第二步实测）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 0 | — |
| 通过 (PASS) | 0 | — |
| 失败 (FAIL) | 0 | — |
| 跳过 (SKIP) | 0 | — |

`make check` 退出码 0、无任何输出。**这不是失败也不是跳过**：上游 `Makefile.am` 未注册任何
`TESTS`/`check_PROGRAMS`，automake 的 `check` = `check-am` = `all-am`，没有任何测试程序
被构建或运行。清点证据见 `reports/upstream-test-inventory.log`，执行证据见
`reports/upstream-test-run.log`。

> → **上游确无自动化测试入口**（无 `tests/` 目录、无测试程序注册）。因此"上游测试通过率"
> 无分母可算，如实申报为 0 用例，并以下节新增的鸿蒙消费者用例承担回归保护。

### 1.2 新增鸿蒙消费者用例（本仓库新增，非断言型）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总用例数 | 4 | 100% |
| 通过 (PASS) | 4 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**消费者用例通过率**: ✅ **100%（4/4）**

原始输出：`reports/ohos-consumer-test.log`

---

## 二、测试结论

### 2.1 总体评价

✅ **适配成功**：零补丁交叉编译通过，packaged 的 5 个可执行文件在鸿蒙 PC 上完成真实负载均衡
数据往返（UDP 数据面、TCP 数据面、TCP 控制面、统计面全部跑通），OpenSSL 静态链入，
运行期零外部依赖。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游无自动化测试 | 回归保护 | 🟡 由新增 4 条消费者用例覆盖 |
| GeoIP 功能未启用 | 统计页国家字段 | 🟢 制品仓无 libgeoip |
| DSR 模式未启用 | Direct Server Return | 🟢 OHOS 无 netmap |

### 2.3 可用功能清单

```
✅ TCP 负载均衡（含客户端会话保持、后端故障转移）
✅ UDP 负载均衡（-U）
✅ TLS 前端/后端（--with-ssl，OpenSSL 3.5.8.1 静态链入；构建期已验证 -lssl/-lcrypto/EC_KEY 探测命中、
   ssl.c 参与编译、产物 DT_NEEDED 仅 libc.so；运行期 TLS 会话未纳入本次 4 条用例）
✅ 运行期控制面（-C + penctl：查询服务表/在线管理）
✅ 日志聚合链路（penlog → pen(转发) → penlogd → 落盘）
✅ 离线日志合并（mergelogs）
✅ HTML 状态页（-w + SIGUSR1）
✅ 事件后端自动选择（epoll / poll 命中）
⚠️ GeoIP 国家统计（--without-geoip，制品仓无依赖）
❌ DSR / Direct Server Return（--without-dsr，OHOS 无 netmap 实现）
```

### 2.4 已知限制

1. GeoIP 不可用：`libgeoip` 未适配/未发布到 ohpcd，`--with-geoip` 关闭。
2. DSR 不可用：依赖 `net/netmap_user.h`，OHOS 无对应实现，`--with-dsr` 关闭。
3. 上游无测试，后续回归保护依赖本 PR 新增的 4 条消费者用例。
4. TLS 路径当前只有**构建期证据**（configure 探测命中 + `ssl.c` 参与编译 + 产物仅 `DT_NEEDED libc.so`），
   4 条消费者用例走的都是明文 TCP/UDP，未发起 TLS 会话；运行期 TLS 若需回归保护应另补一条用例。

---

## 三、测试详情

### 3.1 通过的上游测试

无（上游无测试）。

### 3.2 通过的新增鸿蒙消费者用例

| 用例 | 场景 | 命令（实测） | 观察到的结果 | 结果 |
|------|------|--------------|--------------|------|
| OHOS-T1 | UDP 数据面 | `penlog 127.0.0.1 17140`（→ `pen -U 17140 127.0.0.1:17141` → `penlogd 17141 -l log`） | 日志行 82 字节原样落盘：`198.51.100.9 - - [...] "GET /pen-ohos-t1 HTTP/1.0" 200 42` | ✅ PASS |
| OHOS-T2 | TCP 控制面 | `penctl 127.0.0.1:17142 servers` | `0 addr 127.0.0.1 port 17141 conn 1 max 0 hard 0 weight 0 prio 0 sx 0 rx 0` | ✅ PASS |
| OHOS-T3 | TCP 数据面 | `penctl 127.0.0.1:17143 servers`（pen A 数据口 → pen B 控制口） | 转发结果与直连 pen B 控制口**完全相同**：`0 addr 127.0.0.1 port 17146 conn 0 ...` | ✅ PASS |
| OHOS-T4 | 统计面 | `pen -w stats.html ...` + `kill -USR1 <pid>` | 生成 HTML 状态页 1564 字节，含 `Pen status page` / `1 servers` / 后端地址 | ✅ PASS |

说明：4 条用例均为**真实数据往返**，脚本中不含 `assert` 语句，判据取自实际观察到的
字节内容 / 命令输出（见 `test_package/test.sh` 中每条用例的 `observed` 行）。

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无。上游 0 用例，故无 SKIP 项。

### 3.5 test_package 其他门禁（本机实跑，与 CI 同源）

| 门禁 | 内容 | 结果 |
|------|------|------|
| conan create | 从干净源码交叉编译（隔离 CONAN_HOME，依赖现取 ohpcd） | ✅ exit 0 |
| 包内容基线 | `bin/` 5 个可执行 + man + doc + licenses | ✅ |
| ELF 属性 | ELF64 AArch64，PIE（`Type: DYN`），`DT_NEEDED` 仅 `libc.so` | ✅ |
| `--version` / `--help` 冒烟（CI L2 口径） | pen / penctl / penlogd / mergelogs / penlog 均立即返回、无挂起 | ✅ |
| R34 破坏性反向验证等价检查（移除 bin/ 后用例必须失败） | 用例首先 `command -v pen` 校验可执行文件存在，缺失即 `exit 2` | ✅ |

---

## 四、关键问题分析

### 问题1: 官方源 siag.nu 在 conan 中下载必然失败

**现象**：

```
pen/0.34.1: WARN: network: Download failed, check server, possibly try again
Transfer interrupted before complete: 686080 < 184622
ERROR: pen/0.34.1: Error in source() method
```

**根因分析**：

官方站由 Loopia 托管代理提供，响应头 `Content-Encoding: x-gzip`、`Content-Length: 184622`
（压缩件尺寸），但实际下发的 body 是**解压后的 tar 流**（686080 字节）。Conan 的
`conan/internal/rest/file_downloader.py:138` 只把字面量 `"gzip"` 视为"尺寸不可知、可容忍"的
编码，`x-gzip` 不在此列 → 尺寸比对失败即抛 `Transfer interrupted`。
`curl` 不要求自动解压，拿到原始 184622 字节（sha256 与官方一致），因此 CI 的 curl 预下载
（`ci/conan/build_and_test.sh` Pre-download 段）不受影响，受影响的是本地 `conan create`。

**解决方案**：

`conandata.yml` 采用 conan 支持的 **url 列表**（首个为主源、其余自动回退）：
官方源 + OpenBSD ports distfile + NetBSD pkgsrc distfile。三者 sha256 两两一致
（`2b640795…1e864`）即逐字节相同，`sha256:` 校验对任一源都成立。本地实测：
`pen/0.34.1: Trying another mirror.` → `Sources correctly downloaded from
https://ftp.openbsd.org/pub/OpenBSD/distfiles/pen-0.34.1.tar.gz`。

### 问题2: `penlogd` 日志不可立即读到（非缺陷，已按正确语义设计用例）

**现象**：向 `penlogd` 发数据后立刻 `cat` 日志文件为 0 字节，容易误判成"转发失败"。

**根因分析**：`penlogd` 用 `fopen(..., "a")` 写日志；OHOS musl 下即使传 `-b`（unbuffered），
数据仍在 stdio 缓冲里，直到进程关闭文件才落盘（`penlogd.c` 主循环退出后 `fclose(logfp)`）。

**解决方案**：用例先 `kill -TERM`（触发 SIGTERM handler → `loopflag=0` → 优雅退出 → `fclose`）
再读日志。同时用 `penctl ... servers` 的 `conn 1` 作为"数据确实到达过 pen"的即时旁证。

### 问题3: 未携带 config.guess/config.sub 的 released tarball

**现象**：普通 `./configure` 需要 build 三元组；若让其自行猜测会因 `uname -s = HarmonyOS` 失败。

**根因分析**：上游 tarball（74 文件）未包含 autoconf 辅助脚本 `config.guess`/`config.sub`，
而 `configure` 里 `ac_config_guess="$SHELL $ac_aux_dir/config.guess"` 仍指向它们。

**解决方案**：显式 `--build=aarch64-linux-ohos`（并伴随 conan 下发的 `--host`），
`_AC_CANONICAL` 不再调用猜测脚本 → 零补丁通过（与 `archives/n/ngircd/28` 同法）。

---

## 五、测试环境

```
软件: pen 0.34.1 (https://siag.nu/pen/)
源码 sha256: 2b640795029df9d1672e17202c109cc5d42538f6754a6070dc27da640881e864
目标平台: os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ build_type=Release
编译器: /data/service/hnp/bin/clang (clang version 15.0.4)
依赖: openssl/3.5.8.1 (ohpcd, 静态包 package_id=4b977264131a1c74e82bd6bb51b63cc9aadc4cfa)
configure: --with-ssl --without-geoip --without-dsr --disable-debugging --build=aarch64-linux-ohos
补丁: 无 (0 个)
产物: bin/{pen,penctl,penlog,penlogd,mergelogs} + share/man/man1/*.1 + doc/pen/* + licenses/COPYING
```

测试脚本与日志：

| 文件 | 说明 |
|---|---|
| `test_package/test.sh` | 4 条消费者用例实现（`conan create` 时自动执行） |
| `test_ohos/run_ohos_test.sh` | 本机独立运行入口（`bash run_ohos_test.sh <prefix>`） |
| `reports/upstream-test-inventory.log` | 上游测试入口清点证据 |
| `reports/upstream-test-run.log` | 上游 `make check` 实测输出与退出码 |
| `reports/ohos-consumer-test.log` | 4 条消费者用例完整输出 |

---

*报告生成时间: 2026-09-28*
