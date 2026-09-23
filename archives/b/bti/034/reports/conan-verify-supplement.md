# bti 034 application 包人工补测（G4/L2/L4/L5）

bti 是 `package_type = "application"` 的纯可执行包：`conan-verify` 报告里
G4/L2/L4/L5 四项同时出现 `✅ PASS` 与 `⏭️ 跳过（无 cache 路径）`，按「并存时以跳过为准」
的口径视为 **SKIPPED**，因此按 application 判据人工补测。本文件是这次补测的逐字记录。

判据与结论：

- **G4 产物完整性**：`find <包目录> -type f` 得到 6 项，其中 `bin/` 下 2 个可执行产物
  （`bti`、`bti-shrink-urls`）、`share/man/man1/` 下 2 个 man page，无 `lib/`、无 `include/`；
  与 `conanfile.py` 的 `package_info()`（`bindirs=["bin"]`、`includedirs=[]`、`libdirs=[]`）互证一致。
- **L4 安全属性**（对 `bin/bti`）：`ELF64 / DYN`（PIE）、`GNU_STACK RW`（无执行位）、
  存在 `GNU_RELRO`、`FLAGS: BIND_NOW`、`FLAGS_1: NOW PIE` —— 五项判据齐全。
  `bin/bti-shrink-urls` 是 `#!/bin/sh` 脚本（非 ELF），按脚本判据做 `/bin/sh -n` 语法检查。
- **L2 消费者实测**：在包内真实制品上执行 `--version` / `--help` / 离线 `--dry-run`，
  以及直接执行 `bti-shrink-urls --help`（shebang 修复前该命令 rc=126）。
- **L5 产物基线**：同一提交两轮**独立清缓存**构建，6 个产物中 5 个逐字节一致
  （`bin/bti`、`bin/bti-shrink-urls`、`conaninfo.txt`、两个 man page）；唯一差异项
  `conanmanifest.txt` 的首行是打包时间戳，跨轮必然漂移，属已知预期（基线只对可复现子集给出）。

包目录一律用 `ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/bti*/p` 定位：2.29 缓存分片目录名是
「名前 5 字符 + hash」，`bti` 只有 3 个字符，实测两轮目录名不同
（`bti0101a9b803103` / `btif24c116cc97cf` / `btiae7ea0e121e21`），写死目录名下一轮即不可复核。

补充（W3 侧 L2 的同一现象）：finish 内嵌的 W3 本地 CI 也做了一次 smoke test，
日志逐字见 `reports/w3-local-ci-log.md`。该检查**不带 conanrun 环境**直接执行 `bin/bti`，
因此 `[warn] L2: bti --version/--help failed (non-blocking)`——原因是 bti 的 `DT_NEEDED`
是 `libcurl.so`/`libxml2.so.16`/`libjson-c.so.5`（无 RUNPATH），不设 `LD_LIBRARY_PATH` 时
加载器找不到它们；同一轮里 `[ok] L2: bti-shrink-urls --help OK`（脚本不依赖共享库）。
这是本仓非系统同名库的既定动态链接模型（依赖链由 Conan 管理，消费方 `conan install` 后
用 conanrun 环境运行）；真实消费路径由 `test_package` 证明——它用 `env="conanrun"`，
同一轮 `RESULT: 4/4 checks passed`，L1e 破坏性反向验证也确认测试确实依赖被测产物。

## 逐字证据

- 原始文件：`/storage/Users/currentUser/tmp/bti-034/evidence/supplement-transcript.txt`
- 原始字节数：4327
- 原始行数：92（`wc -l`，即换行符个数）
- sha256（原始文件逐字节）：`baaaa1bd7fc830dd1bbeec1993cf2c96fcd9bd6399e52d8788660284717e06c4`
- 抽取命令（块内含末尾换行，不额外剥除）：

````text
sed -n '/^```text$/,/^```$/p' conan-verify-supplement.md | sed '1d;$d' > supplement-transcript.txt
````

```text
# application 包人工补测逐字记录（final SHA 7e93f24b / T3 重验轮）
$ PKG=$(ls -d ${CONAN_HOME:-$HOME/.conan2}/p/*/bti*/p | head -1)
/storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p

## G4: 包内容清单 vs package_info() 的 bindirs
$ find "$PKG" -type f | sort
bin/bti
bin/bti-shrink-urls
conaninfo.txt
conanmanifest.txt
share/man/man1/bti-shrink-urls.1
share/man/man1/bti.1
$ find "$PKG" -type f | wc -l
6
# package_info() 声明 bindirs=['bin']、includedirs=[]、libdirs=[]；
# 实测 bin/ 下 2 个产物、share/man/man1/ 下 2 个 man page，无 lib/ 与 include/ —— 与声明一致
$ ls "$PKG/lib" "$PKG/include" 2>&1
ls: /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p/lib: No such file or directory
ls: /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p/include: No such file or directory

## L4: 对 bin/ 下每个产物核对 ELF 属性（application 判据）
$ head -c4 bin/bti | od -c   # ELF 魔数；bin/bti-shrink-urls 为脚本
bti: 0000000 177   E   L   F
bti-shrink-urls: 0000000   #   !   /   b
$ llvm-readelf -h bin/bti | grep -E 'Class|Type|Machine'
  Class:                             ELF64
  Type:                              DYN (Shared object file)
  Machine:                           AArch64
$ llvm-readelf -lW bin/bti | grep -E 'GNU_STACK|GNU_RELRO'
  GNU_RELRO      0x01b2e0 0x000000000001d2e0 0x000000000001d2e0 0x000948 0x000d20 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0x0
$ llvm-readelf -dW bin/bti | grep -E 'FLAGS|NEEDED'
  0x0000000000000001 (NEEDED)       Shared library: [libcurl.so]
  0x0000000000000001 (NEEDED)       Shared library: [libxml2.so.16]
  0x0000000000000001 (NEEDED)       Shared library: [libjson-c.so.5]
  0x0000000000000001 (NEEDED)       Shared library: [libc.so]
  0x000000000000001e (FLAGS)        BIND_NOW 
  0x000000006ffffffb (FLAGS_1)      NOW PIE 
$ head -1 bin/bti-shrink-urls
#!/bin/sh
$ /bin/sh -n bin/bti-shrink-urls; echo rc=$?
rc=0

## L2: 在包内真实制品上执行真实命令（LD_LIBRARY_PATH=Conan 依赖 lib 目录）
$ LD_LIBRARY_PATH=<conan deps lib dirs> "$PKG/bin/bti" --version
bti - version 034
rc=0
$ "$PKG/bin/bti" --help | head -4
bti - send tweet to twitter or identi.ca
Version: 034
Usage:
  bti [options]
rc=0
$ printf 'hello bti' | "$PKG/bin/bti" --debug --dry-run --account=someuser --password=somepass --host=identi.ca --action=update
bti: main: account = someuser
bti: main: password = somepass
bti: main: host = 2
bti: main: action = 0
bti - version 034
bti: main: tweet = hello bti
bti: main: config file = 
bti: main: host = 2
bti: main: action = 0
bti: send_request: user_password = someuser:somepass
bti: send_request: data = status="hello bti"
bti: send_request: proxy = (null)
rc=0
$ /bin/sh "$PKG/bin/bti-shrink-urls" --help | head -3
bti-shrink-urls - convert URLs to a shorter form using a web service

    /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p/bin/bti-shrink-urls [--escaped] [<url>]
rc=0
$ "$PKG/bin/bti-shrink-urls" --help   # 直接执行（shebang 修复后）
bti-shrink-urls - convert URLs to a shorter form using a web service

    /storage/Users/currentUser/.conan2/p/b/btibc745e33f236f/p/bin/bti-shrink-urls [--escaped] [<url>]
rc=0

## L5: 两轮独立清缓存构建的产物 sha256（roundA vs roundB，同一 final SHA 7e93f24b）
$ cd "$PKG" && find . -type f | sed 's|^\./||' | sort | xargs sha256sum   # roundB
05f69237f5a8319f5cc77888ac14eba306bb5751ab22e9d5d50b30a86917ed5e  bin/bti
bc93da20735cbc142cd1ffbd17fe05088da1f9085e0a54cb2605363e90ac4004  bin/bti-shrink-urls
cb6f144c7bd9ac49001753cf6675846195b7ffa54bc5c2e010e94e34891bbb80  conaninfo.txt
282592bd7f67e75817e11e38550050a9b15026aeff1e20a677d3a8bc7e253cb2  conanmanifest.txt
aea2e1e7e0ae10a274ca8aa4afdd181dbc7d1686ccdef31a80c97203e01d3228  share/man/man1/bti-shrink-urls.1
5a7077b8e07832b256c72336a0c93042e49f2a561cf887460b008acab592545e  share/man/man1/bti.1
$ diff roundA-sha256.txt roundB-sha256.txt
4c4
< 8541b56b7e505321d757a4b274506796d3164f6652d6a2439b1bb2ea5f3bf557  conanmanifest.txt
---
> 282592bd7f67e75817e11e38550050a9b15026aeff1e20a677d3a8bc7e253cb2  conanmanifest.txt
# 结论：6 个产物中 5 个逐字节一致；conanmanifest.txt 首行为打包时间戳，跨轮必然漂移（W§7.2 已记录）
```
