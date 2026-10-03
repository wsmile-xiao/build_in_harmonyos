# 真机运行时人工取证 — john-jumbo 1.9.0

> 消费者探针（test_package）之外的补充实机证据。所有命令均在 OHOS 真机
> （192.168.43.14，aarch64）对 conan 打包产物执行。
> 产物：`john-jumbo/1.9.0@ohpcd/stable`（2026-10-02 整改后进行两次 clean 全量
> 重建——第二次为 test_package 修复后复跑；两次产物 bin/john sha256 完全一致
> `d52716e5…`，构建确定性成立。package 目录分别为 `.../p/b/john-601019d4d149e/p`
> 与 `.../p/b/john-e00d6f44a332d/p`；§1/§3/§4/§5 样例取自重建产物——两次产物
> 逐字节相同，故样例对两次重建产物均成立）。

## 1. 二进制、版本与安全属性（readelf 取证）

> 注：真机 readelf 经 `command -v readelf || command -v llvm-readelf` 解析后调用。

```
$ bin/john --help | head -3
John the Ripper 1.9.0-jumbo-1 [linux-arm64le]
Copyright (c) 1996-2019 by Solar Designer and others
Homepage: http://www.openwall.com/john/

$ bin/john --list=build-info | grep -E "Version|Build|Arch"
Version: 1.9.0-jumbo-1
Build: linux-arm64le

$ readelf -d bin/john | head -6          # 节选
Dynamic section at offset 0x57b020 contains 25 entries:
  Tag        Type                         Name/Value
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
 0x000000000000001e (FLAGS)              BIND_NOW
 0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE

$ readelf -lW bin/john | head -1
Elf file type is DYN (Position-Independent Executable file)

$ readelf -lW bin/john | grep -E "GNU_STACK|GNU_RELRO"    # 节选
  GNU_RELRO      0x54ffc0 0x0000000000551fc0 0x0000000000551fc0 0x02d880 0x02e040 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0

$ sha256sum bin/john
d52716e593c686df43727e758665f78140d4aa9bf0bd800b1922b41959c4a7b5  john
```

- aarch64 ELF（T1 探针 magic+e_machine 校验通过）；Elf type DYN（PIE）
- 动态依赖仅 `libc.so`（唯一 DT_NEEDED）——openssl/zlib 两依赖制品仓包均为纯静态库，已静态链入
- 安全属性：BIND_NOW + NOW PIE、`GNU_RELRO` 段存在（Full RELRO）、`GNU_STACK` 无执行位（NX）
- 产物 sha256 已记录为基线（L5 等效，见 §5）

## 2. 格式注册表

```
$ bin/john --list=formats | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -c .
259
```

含 descrypt/bcrypt/scrypt/LM/raw-md5/md5crypt/sha256crypt/sha512crypt/NT/PKZIP/
RAR5/7z/PDF/Office/SSH 等 259 个注册格式（重建产物 T3 探针实测 259，见 conan-create.log）。

## 3. 7 格式自检（--test 内置向量，含依赖路径）

逐格式 `bin/john --test --format=<fmt>` 全部 rc=0、无 "Self test failed"、
Benchmarking 行存在（探针 T4 七个具名测试用例全过，见 conan-create.log）。
依赖路径两例（PKZIP→zlib、openssl-enc→OpenSSL "enc"/libcrypto）样例：

```
$ bin/john --test=1 --format=PKZIP
Benchmarking: PKZIP [32/64]... DONE
Many salts:	9499K c/s real, 9595K c/s virtual
Only one salt:	6077K c/s real, 6139K c/s virtual

$ bin/john --test=1 --format=openssl-enc
Benchmarking: openssl-enc, OpenSSL "enc" encryption (AES-128, MD5) [32/64]... DONE
Many salts:	1351K c/s real, 1351K c/s virtual
Only one salt:	1503K c/s real, 1518K c/s virtual
```

基础 5 例（Raw-MD5/md5crypt/sha256crypt/sha512crypt/NT）同样全过，md5crypt 样例：

```
$ bin/john --test=1 --format=md5crypt
Benchmarking: md5crypt, crypt(3) $1$ (and variants) [MD5 32/64 X2]... DONE
Many salts:	10788 c/s real, 10788 c/s virtual
Only one salt:	10528 c/s real, 10634 c/s virtual
```

## 4. E2E 破解闭环（5 组哈希，向量由 PC 端 openssl 3.5.5 生成）

```
$ printf '%s\n' '$6$ohos$i/vdZ.UMCx3QF2ADd7uvoMkfu800FtigdeZKuf1kEU.alAWhhXtDSvB.51RQYiPSFlWW256Dw2DtQteIAoDwN.' > h.txt
$ printf '%s\n' 'harmonyos123' 'decoy-one' 'decoy-two' > wl.txt
$ bin/john --nolog --pot=pot --format=sha512crypt --wordlist=wl.txt h.txt
Using default input encoding: UTF-8
Loaded 1 password hash (sha512crypt, crypt(3) $6$ [SHA512 64/64])
Cost 1 (iteration count) is 5000 for all loaded hashes
Press 'q' or Ctrl-C to abort, almost any other key for status
harmonyos123     (?)
1g 0:00:00:00 DONE (2026-10-02 16:22) 50.00g/s 150.0p/s 150.0c/s 150.0C/s harmonyos123..decoy-two
Use the "--show" option to display all of the cracked passwords reliably
Session completed

$ cat pot
$6$ohos$i/vdZ.UMCx3QF2ADd7uvoMkfu800FtigdeZKuf1kEU.alAWhhXtDSvB.51RQYiPSFlWW256Dw2DtQteIAoDwN.:harmonyos123

$ bin/john --nolog --pot=pot --format=sha512crypt --show h.txt
?:harmonyos123

1 password hash cracked, 0 left
```

5 格式（md5crypt/sha256crypt/sha512crypt/Raw-MD5/NT）pot 文件均含明文
`harmonyos123`（探针 T5 五个测试用例在重建产物上全过，见 conan-create.log；
上例为 sha512crypt 于该产物的现场复跑，2026-10-02 16:22）。

## 5. 官方 conan-verify 八门禁（如实口径）

`python3 scripts/ohc-run.py conan-verify john-jumbo 1.9.0`（2026-10-02 整改后干净重建）：

```
✅ 配方验证通过: john-jumbo 1.9.0
   可标记 status: published
```

逐门禁如实记录（原文见 conan-verify-report.md）：

- **G0 ✅** 预构建评估——工具未识别构建系统（"📦 构建系统: unknown"），跳过预查询后 PASS（配方实际以 Makefile.legacy 构建，不依赖该识别）
- **G1 ✅** 配方完整性（方法/补丁/依赖声明、conandata、test_package 齐备）
- **G2 ✅** conan create 干净重建成功 + test_package **19/19**
- **G3 ✅** 系统同名库隔离（R26）
- **G4 ✅** 产物完整性（⚠️ 工具同时报"无法找到程序包 ID"——conan-verify 在 Conan 2.29 下 conan list 输出 schema 兼容问题，工具侧已知限制；产物打包校验实际由 G2 环节完成）
- **L2 / L4 / L5**：报告中标注 ✅ 但实际为 **"⏭️ 跳过（无 cache 路径）"——不视为已测**；已以等效手动探测补齐（重建产物实测）：
  - L2 等效（功能矩阵）：`--help` rc=0、`--list=build-info` rc=0（§1）；7 格式 `--test` 自检全过（§3）
  - L4 等效（安全属性）：readelf 实证——DT_NEEDED 仅 libc.so、BIND_NOW + NOW PIE、GNU_RELRO（Full RELRO）、GNU_STACK 无执行位（NX）（§1）
  - L5 等效（基线）：bin/john sha256 = `d52716e593c686df43727e758665f78140d4aa9bf0bd800b1922b41959c4a7b5`（2026-10-02 两次 clean 重建结果一致，构建确定性已实证，供后续对比）

> 报告整体 Verdict=PASS（可标记 published）；上表如实标注了其中被工具跳过、并经手动探测补齐的三项。

## 6. 上游 unit-tests

37 个测试函数、43,067,484 次检查全部通过，退出码 0（详见 upstream-test-run.md）。

## 7. test_package 无 od 回退分支实证（2026-10-02）

`is_aarch64_elf()` 在无 od 环境走 dd 字节比较回退分支。真机自带 od（该分支
代码路径在真机不可自然触发），故以与之等价的独立命令对同一重建产物实测：

```
$ p=/storage/Users/currentUser/.conan2/p/b/john-e00d6f44a332d/p
$ m3=$(dd if=$p/bin/john bs=1 skip=1 count=3 2>/dev/null | tr -d "\0"); [ "$m3" = "ELF" ] && echo FALLBACK-M3-OK
FALLBACK-M3-OK            # 跳过 0x7f 魔数首字节，后 3 字节 = "ELF"
$ m1=$(dd if=$p/bin/john bs=1 skip=18 count=1 2>/dev/null | tr -d "\0"); [ "$m1" = "$(printf "\267")" ] && echo FALLBACK-M1-OK
FALLBACK-M1-OK            # e_machine 首字节 = 0xB7（LE aarch64）
$ dd if=$p/bin/john bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d " \n"
7f454c46                  # magic 原文（0x7f + "ELF"）
$ head4=$(dd if=$p/bin/john bs=1 count=4 2>/dev/null | tr -d "\0"); [ "$head4" = "ELF" ] && echo OLD-OK || echo OLD-CODE-FAIL-expected-bug
OLD-CODE-FAIL-expected-bug   # 旧回退写法对合法产物恒假（0x7f 保留致比较失败）——缺陷复现并已修复
```
