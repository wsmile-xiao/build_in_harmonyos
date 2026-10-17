# zsign 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游唯一构建入口 build/linux/Makefile，无 configure/cmake）
- 编译日期: 2026-09-21
- 编译器: clang / clang++（OHOS NDK，/data/service/hnp/bin/clang，与 ci/conan/profiles/ohos-aarch64 一致）
- 状态: built
- 源码目录: 发布包自包含（上游源码树内嵌 zlib + minizip，构建期一并编译静态入二进制）

## 源码溯源

- 权威源：上游 GitHub tag 归档 `https://github.com/zhlynn/zsign/archive/refs/tags/v1.1.1.tar.gz`
  （HTTP 200，gzip 魔术 1f 8b，顶层目录 `zsign-1.1.1/`，241 个文件），
  sha256 `5e1a24116ca6875d6786703a7fb129d6afde06822f6a859de47d44eff4ad7c05`（下载件实测一致）。
- 上游无 release 附件资产、无 PGP 签名；tag v1.1.1（2025-09，上游最新 release）即权威锚点。
- W0 依赖预检：唯一外部依赖 = openssl（选用仓内 `openssl/3.5.6`，117 个在用配方的共同选型）；
  依据：src/signing.cpp 无条件调用 `OSSL_PROVIDER_load`（OpenSSL 3.x API），1.x 头文件不兼容；
  zsign 只用 libcrypto（CMS/PKCS12/OCSP/X.509），不用 libssl。conan download + install 验证
  ohpcd 已发布 aarch64 静态二进制（libcrypto.a / libssl.a / include/ / openssl CLI）。

## 语言预检（R47）处置记录

`lang-preflight` 判 C++（.cpp/.cc 主体 + .mm 仅 2 个 macOS 专用入口），与任务语言 cpp 匹配，
milestone=lang_checked，无冲突出口，正常续行。

## 编译步骤

配方 `conanfile.py` 内联完成（零补丁、零源码修改）：

1. `source()`：conandata.yml 校验和下载解包（strip_root）。
2. `build()`：`make -C build/linux CC=… CXX=… VERSION=1.1.1 OPENSSL_INCLUDE=-I… OPENSSL_LIB="-L… -lcrypto" -j1`
   （R9：-j1；编译器取自 tools.build:compiler_executables，R33 无裸环境变量）。
3. `package()`：`<src>/bin/zsign` → `<pkg>/bin/`，LICENSE → `<pkg>/licenses/`。

关键读数（原生探索构建，与 conan create 同口径）：

- 上游 Makefile 特性：无 configure/cmake；CXXFLAGS 硬编码 `-std=c++11 -O3 -Wno-unused-result`；
  源码与输出全部经 `../../` 相对路径解析（`make -C build/linux` 是唯一正确调用位）；
  输出落 `<src>/bin/zsign`（`BINDIR=../../bin`）；`OPENSSL_INCLUDE/OPENSSL_LIB` 未设置时回退
  `pkg-config openssl`（必须覆盖传入，conan 环境无该回退路径）。
- **必须显式传 `VERSION=1.1.1`**：Makefile 用 `git describe` 取版本，release tarball 无 `.git`
  时回退 `0.0.0-dev`（实测不传则 `zsign -v` 输出 version: 0.0.0-dev）。
- 内嵌 zlib/minizip 与 libcrypto 静态链接：产物 `bin/zsign` 4.6MB（aarch64，`file` 确认
  ELF 64-bit ARM aarch64），运行时无 .so 依赖（ldd 无输出/静态段）。
- **HMDFS 怪癖**：`make -jN`（N>1）报 jobserver `mktemp: No such file or directory`（mkfifo
  失败族，knowledge_ref: E074 同族），`make -j1` 规避——与 R9 的 -j1 要求天然一致。

## R51 上游测试三步法（清点 → 分析 → 等价验证）

### 第一步：清点

- `test/` 下仅 3 个驱动脚本：`test/linux/test.sh`、`test/macos/test.sh`、`test/windows/test.ps1`
  （linux 版为唯一 Linux 入口，末位 `!!!OK!!!/!!!FAILED!!!` 口径）。
- 无 ctest / pytest / make check：`make -n check` 报 `No rule to make target 'check'`；
  Makefile 构建目标只有 release/debug/install/clean。
- **上游测试语料被 .gitignore 有意排除**：`test/ipa/`、`test/assets/`（test.ipa、test.p12、
  test.mobileprovision）不在 tarball 内；`test/dylib/bin/demo1.dylib、demo2.dylib` 为上游
  自带的真实 arm64 Mach-O 样本（可直接用）。此为 R51 关键证据：上游自身交付的 Linux 测试
  开箱即不可运行。

### 第二步：test.sh 字面执行分析

脚本参数（`-q -i -U -k ../assets/test.p12 -m ../assets/test.mobileprovision ../ipa/test.ipa`）
的三重环境依赖：

1. **语料依赖**：`../ipa/test.ipa`、`../assets/test.p12`、`../assets/test.mobileprovision`
   需按 README 手工置备（上游 .gitignore 排除）——本机已按上游文档重建全套语料
   （openssl 3.5.6 自签证书 + CMS 签名 provisioning profile + python zipfile 打包 IPA，
   TeamId `Z5IGNTEAM1D`）。
2. **设备依赖**：`-i` 结尾调用 `ideviceinstaller install` 把签名包装机到 USB 连接的 iOS
   设备；src/zsign.cpp `InstallSignedIpa()`（Linux 分支）对子进程退出码非 0 返回 false →
   `main()` 返回 -1。**任何无 iOS 设备的 Linux 环境该步必然失败**（与平台无关）。
3. **/tmp 依赖**：脚本未传 `-t`，zsign 默认把待签 IPA 解压到 `ZFile::GetTempFolder()`
   （/tmp）；鸿蒙 HMDFS 挂载的 /tmp 只读（knowledge_ref: E002 族），解压步即失败。

字面执行实录（语料重建后、`test/linux/` 目录内）：`../ipa/test.ipa: !!!FAILED!!!`。

### 第三步：因子实验 + 等价验证

因子实验（均从 `test/linux/` 目录、重建语料、`-t` 指定可写临时目录）：

| 因子 | 参数 | 结果 |
|------|------|------|
| A | 保留 `-i`、不传 `-p`（脚本原样，p12 已重建为空密码） | rc=255，签名步成功、装机步 `ideviceinstaller install failed`（无设备）→ `InstallSignedIpa` false → main -1 |
| B | 去 `-i`、不传 `-o`（脚本同参数去安装步） | rc=255，`>>> Use -o option to specify the output file.`（`-i` 隐含临时输出路径，脚本参数把 `-o` 的存在也绑在 `-i` 上） |
| C | 去 `-i`、补 `-p 123456`（密码版 p12）+ `-t` | rc=0，完整重签成功（TEST-3，见下） |

结论：字面 FAILED = ①/② 设备因素（上游固有语义，无 iOS 设备的 Linux 均如此）+ ③ /tmp 只读
平台因素（鸿蒙特有，可经 `-t` 完全规避）。签名核心功能不含任何鸿蒙特有障碍。

**功能等价验证清单（重建语料 + `-t` 可写临时目录，7/7 通过）**：

| # | 场景 | 结果 |
|---|------|------|
| 1 | adhoc 签上游样本 demo1.dylib（`-a -f`） | ✅ rc=0 |
| 2 | `-l` 注入 dylib（demo2 → demo1 注入） | ✅ rc=0，LC_LOAD_DYLIB 写入 |
| 3 | 完整 IPA 重签（p12 密码 + provision + `-t`）：解压→替换签名→回包，产物含 embedded.mobileprovision + _CodeSignature/，TeamId/SubjectCN 解析正确 | ✅ rc=0（**必须 `-t`，/tmp 只读下无 `-t` 即 `Unzip failed`**） |
| 4 | `-C` 证书信任链检查（自签证书，无 OCSP 响应端） | ✅ 路径正确执行，rc=255 为上游对自签证书的固有语义（如实记录） |
| 5 | `-x -o` 提取已签 IPA 元数据（JSON） | ✅ rc=0 |
| 6 | bundle 元数据编辑（`-b`/`-n`/`-M`） | ✅ rc=0，Info.plist 修改生效 |
| 7 | 文件夹直接签名（.app 目录形态） | ✅ rc=0 |

## 平台适配知识（跨版本沉淀）

- zsign 默认临时目录 /tmp 在鸿蒙只读：所有 IPA/文件夹签名场景必须 `-t` 指定可写目录
  （E002 同族；上游 test.sh 未传 `-t` 属上游脚本对常规 Linux 的假设）。
- make -jN jobserver mkfifo 失败（HMDFS），-j1 规避（E074 族）。
- Makefile 工程取版本号依赖 git describe：tarball 构建必须显式传 VERSION。
- openssl 3.5 的 PKCS12 密码错误报 `mac verify failure` 且错误队列连带 legacy provider
  噪声（现代 p12 导出实际不需要 legacy.so）——排查 p12 问题先核对密码再看 provider 噪声。

## 检视意见修复复测（对话 #2，2026-09-21）

PR #11678 检视修复（conandata.yml 删 gh-proxy 镜像前缀 / test_zsign.sh 补 `set -euo pipefail`）后，
本机全量复测（conan create + test_package 4/4 PASS + 上游 test.sh 字面重跑 + 7/7 等价重跑）。
本次实测比历史记录更精确的两条新发现：

1. **字面执行失败点在解压步而非装机步**：无 `-t` 时 zsign 把 IPA 解压到 /tmp，
   HMDFS 只读（E002）在 `>>> Unzip failed!` 即死（rc=255），根本走不到签名/装机步。
   历史因子 A 的“签名步成功+装机步失败”是在加了 `-t` 的变体下观察到的；字面（无 -t）
   卡点更早。两次实测一致。
2. **p12 需携带 issuer 证书链（zsign 1.1.1 新校验）**：单叶证书 p12 报
   `Unknown issuer hash 0x...! No embedded WWDR intermediate matches and the p12
   carries no usable CA chain`（openssl.cpp GenerateCMS：p12 CA 链须含叶子 issuer，
   否则查内嵌 WWDR 表）。用二级链（Root CA 签发叶子 CN=Z5IGNTEAM1D + p12 带 [叶子，Root]）
   解决；叶子带 codeSigning EKU。另：运行时 CMS 路径需 OPENSSL_MODULES 指向 legacy.so
   （静态 libcrypto 仍会 dlopen provider 模块；默认路径指向构建时 conan 包目录，包被清后失效）。
   -C 证书检查对自签链输出 `OCSP: Error`（无 OCSP 响应端，上游固有语义，非平台回归）。

### 本次 7/7 等价实测读数（openssl 3.5.6 同源 CLI 重建语料，二级证书链）

| # | 场景 | 结果 |
|---|------|------|
| 1 | adhoc 签上游 demo1.dylib | ✅ rc=0 Signed OK |
| 2 | `-l` dylib 注入（demo2→demo1） | ✅ rc=0 Signed OK |
| 3 | 完整 IPA 重签（p12 链+provision+-t+-o） | ✅ rc=0，输出 59544 字节 |
| 4 | `-C` 证书信任链检查 | ✅ Expires/Algorithm/Issuer 全解析（Issuer=Z5IGN Root CA）；OCSP Error 为自签固有 |
| 5 | `-x <目录>` 元数据提取（配合 -o） | ✅ metadata.json 193 字节（AppName/Version/BundleId/AppSize 全对） |
| 6 | bundle 编辑 `-b`/`-n`/`-M` | ✅ Info.plist 实测改为 testapp2/TestApp2/12.0 |
| 7 | 文件夹直接签名 | ✅ rc=0 Signed OK |

（勘误：历史 TEST-4/5 的参数口径为准——`-C` 的 p12 作位置参数且不带 `-m`；
`-x` 接输出目录而非 `-o` 文件。）

## 对话记录

### 对话 #1（2026-09-21）

- W0 依赖预检 → W1 基线同步（main 42a8cc8fd8，zsign 无历史归档，全新适配）→ R47 语言预检通过。
- 探索构建：零源码修改编译通过（bin/zsign 4.6MB，libcrypto 静态链接）。
- R51 三步法完成（清点/字面分析/因子实验 + 7/7 等价验证，详见上文）。
- 配方固化（conanfile.py + test_package 4/4 PASS）、manifests 回填、finish、推送 feat/zsign-1.1.1。
---

**编译结束**: 2026-09-21 08:26
**最终状态**: built
