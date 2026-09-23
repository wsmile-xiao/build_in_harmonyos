# conan-verify 人工补测报告 — digup 0.6.57

采信轮：`conan-verify` 在**修掉知识草稿与配方注释表述后的 SHA**（`dac8d333` 之后的修复轮，
先清 `~/.conan2/p` 下 digup 分片目录与 `p/cache.sqlite3`（含 `@ohpcd/stable` 形态 ref）后重跑）执行，
工具报告 `archives/d/digup/0.6.57/reports/conan-verify-report.md`。
该报告的 **G4 / L2 / L4 / L5 四行为 `✅ PASS` 且下一行为 `⏭️ 跳过（无 cache 路径）`**，
按 workflow 第 7.2 节以跳过为准，故在此人工补测并留证。

跳过原因：本包以 `--user=ohpcd --channel=stable` 形态构建，工具按裸 ref 形态的
`p/<首字母>/<名字前5字符><hash>/p` 规律未命中 OHOS 缓存实际布局
（`p/b/<名字前5字符><hash>/p`），属已登记的 `conan-verify` 缓存与定位缺陷，
不是包问题。

包目录一律用 glob 定位（缓存目录名每轮重建，不写死）：

```sh
PKG="$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/digup*/p | head -1)"
```

本轮采信日志副本：`$HOME/tmp/digup-0.6.57/conan-create-<SHA前7>.log`，
与 `reports/conan-create.log` 的 sha256 一致（`b7251daca6d48982a0afa46f61a57f3a80e088c6749da91173647f072df0a284`，33645 字节）。

## G4 产物完整性

`find "$PKG" -type f | sort`：

```
./bin/digup
./conaninfo.txt
./conanmanifest.txt
./licenses/COPYING
./share/man/man1/digup.1
```

与 `package_info()` 声明一致：`cpp_info.libs = []`、`cpp_info.bindirs = ["bin"]`，
包内无 `lib/`，`bin/digup` 为唯一可执行产物；另有上游 `make install` 安装的
man page 与配方显式安装的 GPL 许可证。`readelf -h` 显示 `Type: DYN`、`Machine: AArch64`。

## L2 消费者真实行为

不使用构建树副本，直接用**包内** `bin/digup` 驱动真实命令行为（工作目录为任务私有临时目录 `$HOME/tmp/digup-0.6.57/<轮次>/data`，用后即弃；下表为准）：

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| 版本自报 | `"$PKG/bin/digup" -V` | `digup 0.6.57` |
| 生成摘要文件 | `"$PKG/bin/digup" -b -u -t sha256` | rc=1（首次扫描全部为 new，符合上游语义），写出 3 条记录 |
| 全量校验 | `"$PKG/bin/digup" -b -c` | rc=0；`one.txt matched.` / `two.txt matched.` / `three.bin matched.`（matched 行数 = 3） |
| 篡改后校验 | 追加内容后 `-b -c` | rc=1；`one.txt CHANGED.`，未改动文件仍匹配 |

摘要值独立复算（Python `hashlib` 对包内 digup 写出的摘要文件逐行比对）：

```
one.txt      digup=b6a98d9ce9a2d9149288 python=b6a98d9ce9a2d9149288 MATCH
three.bin    digup=ae9a6306a205417afddd python=ae9a6306a205417afddd MATCH
two.txt      digup=f2c82decdd7181cf9894 python=f2c82decdd7181cf9894 MATCH
records compared: 3
```

`conan create` 的 `test_package` 另有 21/21 断言（`HMBS_TEST_SUMMARY discovered=21 passed=21 failed=0 skipped=0`，
见 `reports/conan-create.log`），覆盖 md5/sha1/sha256/sha512 四种摘要类型与用法错误路径。

## L4 安全属性

对包内 `bin/digup`（PIE 可执行文件）：

```sh
readelf -h  "$PKG/bin/digup" | grep -E 'Class|Type|Machine'
readelf -lW "$PKG/bin/digup" | grep -E 'GNU_STACK|GNU_RELRO'
readelf -dW "$PKG/bin/digup" | grep -E 'FLAGS|NEEDED'
```

```
Class: ELF64 ; Type: DYN (Position-Independent Executable file) ; Machine: AArch64
GNU_RELRO  0x0119e0 0x00000000000139e0 0x00000000000139e0 0x000550 0x000620 R 0x1
GNU_STACK  0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW 0
 (NEEDED)  Shared library: [libc.so]
 (FLAGS)   BIND_NOW
 (FLAGS_1) Flags: NOW PIE
```

判据全部满足：`DYN` + `GNU_STACK RW`（无执行位）+ `GNU_RELRO` + `FLAGS BIND_NOW` + `FLAGS_1 PIE`。

## L5 产物基线

```sh
# 包内容聚合（排除 conaninfo.txt / conanmanifest.txt —— conanmanifest.txt 首行为打包时间戳，含它跨轮必漂移）
(cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt | sort | xargs sha256sum | sha256sum)
```

```
包内容聚合（排除 conaninfo/conanmanifest）: 94eb204fda03f9a4c0fcaf99c196c8574d72cd9a051387c725c07fe2f589bd5d
bin/digup                                 : f75a242b8ea56a31d2916302fddcda4fc8482a82fd48b118c811c0198e7bfe66
share/man/man1/digup.1                    : bb4772a4badb04386f5c3c7593a42836b3652eb242d501e3ba89812164797535
licenses/COPYING                          : 8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903
```

## 结论

G4/L2/L4/L5 四项经人工补测全部满足要求，无未覆盖的验证缺口；
工具报告中的 `⏭️ 跳过` 不构成失败，也不改变 G0–G3 的 PASS 结论。

上述四个哈希与上一轮（修复配方注释前的干净轮）逐字节相同，说明本轮文档/注释级修改
没有改变任何构建输入的实际产物；`conan create` 的两轮日志在
`Apply patch` ×3、`checking build/host system type... aarch64-unknown-linux-ohos`、
`checking whether we are cross compiling... no`、`make check` 的 `# TOTAL: 3` /
`# PASS:  3`、`HMBS_TEST_SUMMARY discovered=21 passed=21 failed=0 skipped=0`
各处完全一致。
