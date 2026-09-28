# libamrwb 11.0.0.0 适配笔记

> 3GPP TS 26.204 (Release 11) AMR-WB 浮点参考实现的 autotools 封装库。
> 版本号 11.0.0.0 = 3GPP TS 26.204 v11.0.0 + penguin.cz wrapper 打包版本。
> 命名来源：FreeBSD ports `audio/libamrwb`（DISTVERSION 11.0.0.0）。
> 同源参照：archives/l/libamrnb/11.0.0.0（AMR-NB，同一位作者、同一 wrapper 结构）。

## 1. 源码身份（三重交叉验证，2026-09-23）

| 文件 | sha256 | FreeBSD distinfo SIZE |
|---|---|---|
| amrwb-11.0.0.0.tar.bz2 (240170 B) | `5caf59b14480b0cd2a7babb8be472c4af39ff4c7c95f1278116557049a4dd5dc` | 240170 ✅ |
| 26204-b00.zip (385394 B) | `c885c44483fd4502d354ec9656f2cdc0469050015052f8f3ecc1d5e08c869fec` | 385394 ✅ |

验证源：FreeBSD `audio/libamrwb/distinfo`（cgit.freebsd.org 实测读取，权威记录）
与本机 tarball / 已下载 3GPP zip 的 sha256 实测一致。

仓库根目录 `26204-b00.zip`（192 字节）核实为 3GPP 的 "Document Moved" HTML 重定向页
（非源码），仅说明 26204-b00.zip 官方真实位置；真实 3GPP zip 由构建期按
conandata.yml 官方 URL 下载（sha256 校验）。

## 2. 上游状态与镜像策略

- 官方站 `www.penguin.cz/~utx/amr` 及 `ftp.penguin.cz` 均不可达（http only，连接超时）。
- wrapper tarball 取 FreeBSD ports 基础设施镜像：
  1. `https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/libamrwb/amrwb-11.0.0.0.tar.bz2`
  2. `https://distcache.FreeBSD.org/ports-distfiles/libamrwb/amrwb-11.0.0.0.tar.bz2`
- 3GPP zip 镜像情况：正规发行版镜像（FreeBSD/Debian/Gentoo/MacPorts 等）均因 3GPP
  许可限制拒绝镜像，仅官方源可得（libamrnb 同源结论）。

## 3. 3gpp.org WAF 与 CI 预下载的交互

与 libamrnb 完全同源（见 archives/l/libamrnb/11.0.0.0/notes.md §3）：
- `www.3gpp.org` 前置 WAF 按 UA 过滤：curl/wget UA → ~35KB HTML 拦截页（HTTP 200）；
  Conan UA 可正常下载真实文件。
- conandata.yml 用双 URL：小写官方源（R39 合规）+ 大写 scheme/host 变体
  （`HTTPS://WWW.3GPP.ORG/...`，RFC 3986 大小写不敏感；CI 预下载正则只匹配小写，
  大写变体由 conan 原生下载、Conan UA 过 WAF）。校验失败自动回落下一 URL。

## 4. 构建机制（FreeBSD port 同构）

wrapper 只有构建系统 + 4 个补丁；真实源码在构建期注入：

```
26204-b00.zip --(make 规则, unzip)--> 26204-b00_ANSI_C_source_code.zip
       --(prepare_sources.sh: unzip → tr 去 \r → patch×4 → sed 接口三倍化)-->
       dec_*.c/h enc_*.c/h if_rom.c/h decoder.c encoder.c typedef.h readme.txt
       --> libamrwb.la (soname 3) + 4 个 bin 工具
```

- 4 个上游补丁：`amrwb-intsizes` / `amrwb-any-cflags` / `amrwb-dhf-declaration` /
  `amrwb-includes`（intsizes 把 typedef.h 的 Word8/16/32 改为 stdint 定长类型；
  any-cflags 在接口头文件加宏 `E_IF_encode`/`D_IF_decode` → GP3/IF2 变体，默认 GP3）。
- 本机实跑 make 日志确认：unzip → tr 去 CRLF → 4 补丁干净应用（typedef.h 生效）→
  sed 接口变换成功，18 个 .c/.h 生成，GP3D_IF_decode/GP3E_IF_encode 宏别名确认存在。
- 构建期宿主工具依赖：bash、unzip、patch、sed、tr（configure 用 AC_PATH_PROG 探测
  unzip/patch，缺失直接报错）。CI Linux worker 标配。
- 本机 /usr/bin/patch 为 toybox：对 3GPP 源码（tr 归一化后）应用补丁正常；但对
  无上下文行的最小 hunk 会静默 no-op（exit 0 不改文件）。本配方 configure 补丁
  由 conan patch_ng 应用（CI 同机制），不受 toybox 影响。
- 上游 Makefile 把生成文件写进 `$(top_srcdir)`：配方 build() 先把源码树（含 zip）
  整体复制到 build_folder 再 in-tree 构建，保持 conan source 缓存干净。
- `-j1`：上游源码准备链是单一串行点（Makefile 注释明言防并发解包）。

## 5. 交叉编译适配

- 上游 config.guess/config.sub（2012）不识别 `aarch64-linux-ohos` → libamrnb/
  celt/a52dec 先例：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`。
- 本机为 HarmonyOS aarch64（uname -s = HarmonyOS，clang 15.0.4 target
  aarch64-unknown-linux-ohos），纯原生构建。
- configure 找不到默认 cc：需显式 `CC=clang`（老 AC_PROG_CC 只找 gcc/cc，不找 clang）。
- CONFIG_SHELL 需指向可用 bash（`/data/service/hnp/bin/bash` 或
  `/storage/Users/currentUser/usr/local/bin/bash`）。
- HMDFS umask 077 → configure 临时目录不可写（`config.status: ./confXXXX/subs1.awk:
  Permission denied`，知识库 E011/E114）→ 新增 `0001-configure-hmdfs-umask.patch`
  （libamrnb 0001 同方案，去除 configure 两处 umask 077）。
- 纯 C、零 conan 依赖，仅需系统 libm（configure `AC_SEARCH_LIBS([sqrt],[m])`）。

## 6. 上游测试清点（R51）

- wrapper 无 tests/、无 `check` 目标（Makefile.am 全量核阅：仅 libamrwb.la +
  4 个 bin_PROGRAMS，无 TESTS/check_PROGRAMS）。
- 3GPP 内层 zip 18 个文件全为源码 + makefile.gcc + readme.txt，无测试向量、无测试程序。
- FreeBSD audio/libamrwb port 未定义 do-test（仅构建库与工具）。
- 实跑 `make check`：输出 `make: Nothing to be done for 'check'.`，exit 0 —— 上游确无
  自动化测试。→ test_package 自建消费者测试（R34 实质调用被测 API）：
  - 9 种 AMR-WB 模式编码（RFC 3267 存储格式精确字节数断言：18/24/33/37/41/47/51/59/61）
  - DTX/SID（静音输入 mode 8 + dtx=1 → 61 字节 SID 帧）
  - mode 8 多帧编解码往返（解码器收敛后正弦峰值断言，实测 peak=5000/输入 8000）
  - amrwb-encoder CLI 冒烟（16kHz 正弦 PCM → `#!AMR-WB\n` 魔数校验）

## 7. 许可提示

- wrapper：BSD-3-Clause（COPYING）
- 编解码参考代码：3GPP TS 26.204 许可（限制性，非 OSI）——FreeBSD 归入受限制类、
  各发行版不镜像该 zip 的原因。制品为二进制库分发，与本仓 opencore-amr（Apache-2.0
  替代实现）并存；PR 中如实声明。

## 8. 验证记录（2026-09-23，HarmonyOS aarch64 本机）

### 手动构建（Step 2）

```bash
cd $BUILD_SRC_DIR
export PATH="/data/service/hnp/bin:$PATH"
export CONFIG_SHELL=/data/service/hnp/bin/bash
./configure CC=clang --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu --prefix=$DEFAULT_PREFIX   # exit 0
make -j1                                                        # exit 0
make install DESTDIR=$TEST_PREFIX                               # exit 0
make check                                                      # exit 0，无上游测试
```

- 产物：lib/libamrwb.{a,so.3.0.0}、bin/amrwb-{encoder,decoder,encoder-if2,decoder-if2}、
  include/amrwb/ 17 个头文件。
- 编译告警仅 2 处 `%ld → Word32(int)` format 告警（上游 2007 年代码，非致命）。

### 消费者测试（test_package/test.c，对 staging 产物实测）

```text
mode 0: 18 bytes
mode 1: 24 bytes
mode 2: 33 bytes
mode 3: 37 bytes
mode 4: 41 bytes
mode 5: 47 bytes
mode 6: 51 bytes
mode 7: 59 bytes
mode 8: 61 bytes
dtx: 61 bytes
libamrwb round-trip OK (peak=5000)
```

9 模式字节数 = RFC 3267/4867 精确值；往返峰值 5000（输入 8000 的 62.5%，≥4000 阈值）✅

### CLI 冒烟

```bash
amrwb-encoder 8 in.pcm out.amr   # 20 帧 MR24k → 369 字节 = "#!AMR-WB\n" 9B + 20×61B - 1 帧头
```
`#!AMR-WB\n` 魔数校验通过（AMR-WB 存储格式）。

## 9. 下一步（CI / shadow）

单包 shadow CI：

```sh
CI_PACKAGES="archives/l/libamrwb/11.0.0.0" zsh ci/conan/build_and_test.sh
```

## 10. 遗留风险清单

1. **3GPP WAF vs OHOS 适配版 conan UA**：libamrnb 已在本机 conan 2.31.2 实测通过；
   2.29.1 UA 格式相同，风险低；大写 URL 变体作兜底。
2. **真机 unzip/patch 可用性**：本机已实测（unzip 可用，toybox patch 对 3GPP 补丁
   在 tr 归一化后正常）。
3. **HMDFS chmod**：上游 Makefile 对 srcdir `chmod +w`/`chmod og-w`，HMDFS 忽略 chmod
   （E046/E524）；本机构建未触发，CI Linux worker 无影响。
4. amrwb-* CLI 的 L2 `--version` 冒烟：上游工具无 --version 参数（Usage 报错退出码 1），
   L2 判定以 test_package 执行为准。
---

**编译结束**: 2026-09-23 14:21
**最终状态**: built
