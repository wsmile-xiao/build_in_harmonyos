# d0-blind-id 1.0 — 适配说明

## 这是什么

**d0_blind_id**（作者 divVerent，Xonotic 项目的身份系统）是一个**盲身份 / 匿名认证**
密码学库：给定一个 RSA 公钥，双方可以在**不暴露对方公钥指纹**的前提下协商出
"private ID"，并用它做匿名认证（挑战/应答）、消息签名（含 detached 变体）以及
Diffie-Hellman 会话密钥协商。附带的 `libd0_rijndael` 是一个独立的 AES 实现。

纯计算、无网络、无硬件、结果确定性 —— 很适合在无头 CI 上做端到端验证。

| 交付 | 内容 |
|---|---|
| `lib/libd0_blind_id.so*` | 盲身份协议 + RSA/大数（GMP 后端）+ SHA-2 |
| `lib/libd0_rijndael.so*` | AES（rijndael）实现，供协议内部与消费者使用 |
| `include/d0_blind_id/{d0_blind_id.h, d0.h, d0_rijndael.h}` | 公开头 |
| `lib/pkgconfig/{d0_blind_id.pc, d0_rijndael.pc}` | pkg-config 契约（prefix 已重写为 `${pcfiledir}/../..`） |
| `bin/blind_id` | 上游演示/基准程序（R38 申报见**源码树级** `archives/d/d0-blind-id/commands.json`） |
| `licenses/COPYING` | 上游 3-clause BSD 原文（`package()` 里 `copy()` 进来） |

唯一外部依赖：**`gmp/6.3.0`**（上游默认后端 `d0_bignum-gmp.c`；另有
openssl/tommath/tfm 后端，本包不用）。

## 关键适配决策

### 1. GitHub 归档不带 configure → autoreconf 引导（E178）

上游 tarball 只有 `configure.ac`/`Makefile.am`，没有 `configure`。CI worker 有
autoconf，但**没有 automake/aclocal/libtoolize**，所以：

```python
def build_requirements(self):
    self.tool_requires("automake/1.18")
    self.tool_requires("libtool/2.5.4")

def build(self):
    ... self.run("autoreconf --install --verbose", cwd=self.source_folder)
```
（仓库先例：enet/1.3.18、afuse、aircrack-ng、adcli —— 266 个配方用 autoreconf。）

### 2. E007：让 autotools 认识 HarmonyOS

autoreconf 生成的 `config.guess`/`config.sub` 不认识 OpenHarmony → 用仓库脚本
`scripts/patch-autotools-ohos.pl`（经 `CI_REPO_ROOT` 定位）打补丁；本地/脚本不可用时
走内联 Python 兜底（enet/1.3.18 同款）：config.guess 增加 `*:HarmonyOS:*:*` →
`<machine>-unknown-linux-ohos`，config.sub 增加 `ohos-linux` 三元组。

### 3. E011/E129：HMDFS 的 umask 077

生成的 `configure` 里有 `umask 077`（config.status 建临时目录用），在 HMDFS/SELinux
下会得到不可写的 0600 目录 → build() 里对**生成物**做 077→022（不修改源码）。

### 4. .pc 前缀重写

autotools 以绝对 `--prefix` 安装，`.pc` 里的 `prefix=` 会指向打包前缀 →
`package()` 改写成 `${pcfiledir}/../..`（unibilium/usbutils 先例），保证包可重定位。
同时删掉 libtool 的 `.la`（构建期包装，conan 自己管理链接）。

### 5. 包名带连字符 → CMake 目标名

`d0-blind-id` 含 `-`，CMakeDeps 生成的目标名非法 → `package_info()` 里显式
`cmake_file_name = "d0_blind_id"` / `cmake_target_name = "d0_blind_id::d0_blind_id"`。

## 测试证据（平台 rule12）

### ① 如实声明：上游没有测试套件

上游仓库只有 `main.c`（演示 + 基准），**没有** tests/ 目录，也没有
`make check`/`ctest`/`meson test` 目标。因此本包的做法是：

* **build() 内跑上游自带的演示程序**（**二进制未做任何修改**）：`timeout -s INT 120
  ./.libs/blind_id` —— 它的循环体在**上游
  自己的代码里**跑完 生成 RSA 私钥 → 私有 ID 模数/请求/应答/完成 → 公钥 ID 交换
  → 签名/验签 → 盲身份认证（挑战/应答/验证）→ DH 会话密钥双方一致 的全流程，
  并打印 `Generated key has ID: <base64>`。构建判据 = 日志出现该行 **且** 日志不含
  上游 errx 文案 ` fail`，否则 build 失败
  （输出 `HMBS_UPSTREAM_DEMO_RESULT rc=… full-protocol-round-ok signal_terminated=yes …`）。

  ⚠ **为什么必须用 SIGINT 结束**：上游 `main.c` 的 `quit` 是
  `volatile D0_BOOL quit = 0; mysignal()` + `signal(SIGINT, mysignal)` 置位的，
  **与 stdin 无关**；第二层 `while(!quit)` 是给交互式基准用的无限循环。
  早前版本写的 `echo quit | ./blind_id` 因此永远阻塞：本机复现 rc=124、日志 0 字节；
  OHOS worker 上实测**耗满 14400s 构建超时被 KILL**（CI 记「## CI 校验异常」，
  日志停在 `RUN: echo quit | ./blind_id > …` 之后）。`timeout -s INT` 就是模拟
  用户按 Ctrl-C（上游设计的结束方式），handler 置 quit 后进程走正常退出路径，
  stdio 缓冲才会 flush 落盘。
* **协议正确性的强证据来自消费者用例**（见下），其中 AES 部分用**外部权威 golden 数据**。

### ② 完整消费者用例（35 项，全绿）

`test_package/test_d0_blind_id.c`（只用交付的库与头）：

1. **NIST FIPS-197 官方 AES 测试向量**逐字节比对（本地实测输出）：

   | 向量 | 期望密文 | 结果 |
   |---|---|---|
   | FIPS-197 C.1 AES-128 | `69c4e0d86a7b0430d8cdb78070b4c55a` | ✓ 一致 + 解密往返 |
   | FIPS-197 C.2 AES-192 | `dda97ca4864cdfe06eaf70a0ec0d7191` | ✓ 一致 + 解密往返 |
   | FIPS-197 C.3 AES-256 | `8ea2b7ca516745bfeafc49904b496089` | ✓ 一致 + 解密往返 |

2. **盲身份协议全流程**：`d0_blind_id_INITIALIZE` → new ×2 → 1024 位 RSA 私钥 →
   公钥 64 位指纹/序列化/读入 → 私有 ID 模数 → `generate_private_id_start/request`
   → `answer_private_id_request`（以 RSA 私钥签发）→ `finish_private_id_request`
   → 公钥 ID 序列化/读入 → 签名（`sign_with_private_id_sign`）→ 验签
   （`..._verify`，`status=TRUE` 且还原出 `"hello world"`）；
3. **盲身份认证**：`authenticate_with_private_id_start` → `..._challenge`
   （前置签名校验通过）→ `..._response` → `..._verify`（`status=TRUE` + 消息还原）；
4. **DH 会话密钥**：两端 `sessionkey_public_id` 得到的会话密钥完全一致（本地 64 字节）；
5. **负例**：篡改签名 → 判为无效；篡改认证应答 → 判为无效。

本地实测：`d0-blind-id 消费者用例结果：35 项检查，0 项失败`。

### ③ 适配自检（M = 17 条，非上游用例）

`test_package/test_layout.py`：两个库都是 ELF `ET_DYN`、`include/d0_blind_id/` 三个公开头、
两个 `.pc` 且 prefix 已重写、`bin/blind_id`、**R38 申报**（`commands.json` 是源码树级
文件，脚本按其自身位置向上找软件级/版本级两处候选并校验 name/type/ref/commands）、
`licenses/COPYING`（上游 3-clause BSD 原文）、无 `.la`/构建残留、无隐藏文件（JC5）。
本地实测 17/17 通过。

> 教训（CI 实证）：`commands.json` 属于**源码树**交付物（仓库 2096 个软件级先例 + 平台
> L0k 与 `ci/conan/hooks/pre-commit` 都只看软件级），**不**装进 conan 包目录；而
> `licenses/COPYING` 恰恰相反，必须由 `package()` 拷进包（仓库 1500+ 配方同款）——
> 自检脚本原先把它写成"包根目录下的 commands.json"，属检查写错；许可原件漏拷属配方 bug。

## 版本与来源

* 上游：<https://github.com/divVerent/d0_blind_id>，tag **v1.0**
  （`configure.ac` 里 `AC_INIT` 版本号仍是历史值 0.5，上游未随 tag 更新）
* 平台任务版本字段为单字符 `1`；Conan 版本正则要求 ≥2 字符 → 版本目录 **`1.0`**
  （仓库先例：`5` → `5.0`）
* tarball：`https://github.com/divVerent/d0_blind_id/archive/refs/tags/v1.0.tar.gz`
* sha256：`e9edcc55af1b322a5e51832f4a95b456a368d527b34ff31ebe88340728eca5a1`
  （49110 字节；双校验 sha256 + `tar tzf | wc -l` = 26）
* 许可：**3-clause BSD**（上游根目录 `COPYING`：`Copyright (c) 2000-2001, Aaron D. Gifford`
  / `Copyright (c) 2010, Rudolf Polzer`；早先配方里写 `MIT` 是错的，已按原文改成
  `license = "BSD-3-Clause"`，并把 `COPYING` 拷进包的 `licenses/`）
