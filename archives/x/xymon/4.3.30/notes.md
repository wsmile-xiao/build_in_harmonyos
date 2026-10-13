# xymon 4.3.30 适配笔记（HarmonyOS PC / OpenHarmony aarch64）

## 编译环境
- 构建系统: xymon 自带 `configure.server`（非 autoconf，交互式 shell 脚本）+ `build/Makefile.Linux`
- 编译日期: 2026-10-11
- 编译器: clang 15（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标: os=OHOS / arch=armv8 / build_type=Release
- 状态: built

## 编译步骤

1. 下载上游 tarball（`xymon-4.3.30.tar.gz`，sha256 见 `conandata.yml`），Python `tarfile` 解包并去掉顶层目录。
2. 物化 tarball 中的符号链接——上游 31 个符号链接全部是 `xymond/webfiles/*_footer -> stdnormal_footer`，HMDFS 上符号链接创建不可靠，因此提取时按目标文件内容写成普通文件。
3. `build/*.sh`、`configure`、`configure.server` 删除首行 `#!/bin/sh`（OHOS 不支持 shebang），后续统一用 `<hnp>/bash` 显式调用。
4. 用 stdin 重定向非交互执行 `configure.server --server --fping xymonping ...`（依赖 include/lib 路径全部传 Conan 包目录）。
5. 在生成的顶层 `Makefile` 中 `include build/Makefile.rules` **之前**注入 Conan 工具链与依赖变量块。
6. 执行 `build/genconfig.sh` 生成 `include/config.h`，然后 `make`（串行）。
7. `make install INSTALL=/bin/install` 安装到 `package_folder`；上游用符号链接建立的 `$(XYMONHOME)/{bin,etc,ext,tmp,web,www}` 在 HMDFS 上创建失败（上游规则带 `|| true`，静默失效），改为把真实安装目录拷贝进 `server/` 复现同一视图。
8. 对整个包内所有 ELF（`bin/`、`cgi-bin/`、`cgi-secure/`、`server/bin/` 等）做 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 自签名；签名在拷贝之前完成，`server/` 下的副本因此继承有效签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 挂起 / 无法非交互 | `configure.server` 是交互式脚本，会逐个提问 | 用 `stdin.txt`（`y\ny\n` + 若干空行）重定向喂入默认答案 |
| 2 | `configure.server: unexpected EOF while looking for matching '` | 把 `` XYMONHOSTOS=`uname -s \| tr '[A-Z]' '[a-z]'` `` 只替换了前半段，尾部残留反引号与引号导致整个脚本引号不配对 | 必须整串替换为 `XYMONHOSTOS=linux`，不要做前缀式替换 |
| 3 | `bash: ../build/merge-sects: No such file or directory`（make install 阶段） | 误判 merge-sects/merge-lines 为 shell 脚本而删除其编译规则；实际它们是 `build/Makefile` 编译出的 ELF 辅助工具（`all: $(TOOLS)`），install 会直接调用 | 保留 `build/Makefile` 的编译规则，并在 xymond/client/xymonnet 的 Makefile 中**只**给真正的 shell 脚本（`bb-commands.sh`、`convert-bbservices`）加 bash 前缀 |
| 4 | `xymonnet` 链接期 `undefined symbol`（`deptest_failed`、`validity`） | `build/Makefile.Linux` 在 `PKGBUILD` 未定义时设置 `RPATH = -Wl,--rpath,`；空 rpath 让链接器把紧随其后的 `xymonnet.o` 当作 rpath 参数吞掉 | 注入 `PKGBUILD = yes` 且显式 `RPATH =` / `RPATHOPT =`，并从 link 行移除 `$(RPATHOPT)` |
| 5 | `#error "Endianness is UNDEFINED"` | `lib/Makefile` 用反引号命令替换执行交叉编译产物 `./test-endianness`，OHOS 上无法运行 | 把 `` `./test-endianness` `` 整体替换为 `-DXYMON_LITTLE_ENDIAN`，并从 `all:`/`client:` 依赖中移除 test-endianness |
| 6 | `showgraph.c` 报 `too few arguments to function call, expected 8, have 5` | rrdtool 1.9 的 `rrd_graph()` 已是 8 参数 API | 注入 `RRDDEF = -DRRDTOOL12` |
| 7 | 探测程序 `build/test-*.c`、`build/lfs.sh` 交叉编译后无法运行 | 交叉编译产物不能在构建机上执行 | 把探测结论直接写入 `include/config.h`（`PATH_MAX`、`SHUT_RD/WR/RDWR`）并重写 `lfs.sh` 直接输出结论 |
| 8 | 平台判定错误 | xymon 用 `uname -s` 选择 `build/Makefile.<平台>` | 将平台判定钉死为 `build/Makefile.Linux`，`XYMONHOSTOS=linux` |
| 9 | `rpc/rpc.h` 找不到 | OHOS 用 libtirpc，头文件在 `<tirpc/rpc/rpc.h>` | 为 xymonnet 追加 `-I<libtirpc>/include/tirpc` |
| 10 | `getrpcbyname` 未定义 | OHOS libc 未提供该函数 | 在 `xymonnet.c` 内用 `#ifdef OHOS` 提供 `return NULL` 的静态内联桩并宏替换 |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1.1 | HTTP 压缩 |
| pcre | 8.45 | 正则 |
| libtirpc | 1.3.7 | RPC 头/库（替代 glibc sunrpc） |
| openssl | 3.5.8.1 | TLS |
| c-ares | 1.34.6 | 异步 DNS |
| openldap | 2.6.7 | LDAP |
| rrdtool | 1.9.0 | 图形/趋势数据 |

## 验证结果

```bash
# conan create 全链路（source → configure → build → package → test_package）
conan create archives/x/xymon/4.3.30 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → Package '8ec5c6e6a7cc65552c058983ef4c7f265a64d9c5' created

# 已安装二进制可执行（conanrun 环境）
xymon --version        # → Xymon version 4.3.30
bbcmd --version        # → Xymon version 4.3.30
xymondigest md5 file   # → md5:900150983cd24fb0d6963f7d28e17f72
```

产物统计（`package_folder` 内实测）：`bin/` 67 个文件、`cgi-bin/` 26 个 + `cgi-secure/` 6 个 CGI 包装器、`www/` 80 个 `.html`、`etc/` 15 个 `.cfg`、`share/man/` 69 个手册页，合计 1025 个文件，其中 170 个 ELF 全部已用 `binary-sign-tool -selfSign 1` 自签名（`llvm-readelf -S` 可见 `.codesign` 与 `.note.ohos.ident` 段）。

## make check
- 状态: 不适用
- 原因: 上游 xymon 4.3.30 无单元测试套件（无 `tests/` 目录、无 `check:`/`test:` 目标）。
  仅有的 `build/Makefile.test-*` 与 `lib/test-endianness.c` 是 configure 阶段的编译/运行特性探测，
  不是测试套件。清点证据见 `test_package/MANIFEST.yml`。

## G0 干净构建验证
- 状态: built（conan create + test_package 全绿，conan-verify G1-G3 全 PASS）
- 方式: `conan create` 从干净源码（每次重建 source 目录）完整重建并执行 test_package

## 已知限制
- 交叉编译场景下无法在构建机执行 aarch64 探测程序，主机字节序固定按小端处理（目标平台 aarch64 恒为小端，结论正确）。
- `xymon` 服务端运行时需要 `xymon` 系统用户与 `/var` 目录结构；本包仅提供安装产物，未创建系统用户（OHOS 无该用户），配置由使用方按需设置。
- `fping` 探测在 OHOS 上以 `xymonping`（内置 ICMP 实现）替代外部 fping。
### 对话 #1（2026-10-11 ~ 2026-10-12）
- 用户指令：将 xymon 4.3.30 编译适配到 HarmonyOS PC（aarch64），遵循完整适配流程（源码核验 → OHOS 适配 → 真实构建 → 上游测试 → test_package → conan create → conan-verify → finish → W2/W3 → PR 原子性检查），上游测试实际执行并单独汇报，commit/push/PR 前停止等待确认。
- 关键决策与结论：上游无测试套件（证据清点于 test_package/MANIFEST.yml）；test_package 提供断言自由的鸿蒙特有端到端测试（xymondigest md5/sha256）+ 三 bin 树覆盖负面测试支撑（R34/L1e）；依赖 7 项全部经 conan download 验证可消费；最终 conan create 全链路 RC=0，conan-verify G1-G3 PASS，W3 全绿（JC/L0/L1/L1e/L2/L4/L5 pass），W2 原子性 PASS。
- 遗留事项：gen_summary（Step 8）失败由 qpdf 既有 manifest 重复键触发（仓库级问题，与本包无关）；软件级 README.md 与 git index 修复在收尾轮完成。
---

**编译结束**: 2026-10-12 00:43
**最终状态**: built
