# conan-verify 人工补测报告 — libsbsms 2.3.0

> 被审 SHA: `c9c5fb32714eb222b399d53483a386a1654a9e72`
> 日期: 2026-09-16
> 采信轮形态: 清缓存干净轮（`tools/conan_verify_round.sh`）
> 依据: `notes/device-facts.md` §二.17 / §7.2 —— 报告的 `⏭️ 跳过` 行按显式 SKIPPED 对待
> （`✅ PASS` 与 `⏭️ 跳过` 并存时以跳过为准），跳过项必须人工补测

## 一、为什么要补测

采信轮的 `conan-verify-report.md` 里，**G4 与 L2/L4/L5 实际未执行**：

```
## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
```

这是工具已知的路径解析缺陷（程序包 ID 解析失败时整组静默跳过却并列打印 `✅ PASS`），
**必然命中而非偶发**。本包确实产出了 `lib/` 与 `include/`，不属于 header-only/application，
因此下面用独立命令把 G4/L2/L4/L5 逐项补回；跳过项**不计入 PASS**。

包 id `01d92cf349a0dd98ff915f4bd99a04430171517f` 的 settings/options：

```
arch=armv8  build_type=Release  compiler=clang  compiler.version=15
compiler.libcxx=libc++  compiler.cppstd=17  os=OHOS  os.version=6.0   options: shared=True
```

本 SHA 的**两轮独立构建目录**（后文 §5.3 的可复现性判据就用它们）。
下表的"证据行"一律取各轮日志里的 **`Package folder …` 行**（它就是"包目录"列的值），
行号按**抽取出的原始 `.log`** 计（入库的 `*-log.md` 在围栏块前另有 16 行表头，偏移恒为 +17）：

| 轮次 | 产出者 | 包目录 | 证据（原始 `.log` 行号 → 入库 `.md` 行号） |
|---|---|---|---|
| 第 1 轮 | 采信轮 `conan-verify` 的 G2 | `~/.conan2/p/b/libsb698b9c997c655/p` | `reports/conan-create.log` 第 176 行 → `reports/conan-create-log.md` 第 193 行 |
| 第 2 轮 | `finish` 内嵌 W3 的 `conan create` | `~/.conan2/p/b/libsbf2cff71db885c/p` | `reports/w3-local-ci.log` 第 260 行 → `reports/w3-local-ci-log.md` 第 277 行 |

> **定位口径（本轮踩过的坑）**：`conan cache path "<ref>:<pid>"` 返回的是 recipe 登记的那个
> 包目录（本例为第 1 轮），**不是"最新一轮"**；用它去取"第二轮"会取回同一个目录，等于自己跟
> 自己比。两轮目录必须从各自日志里取——`Package folder …/p` 行给出包目录本身，
> `Building your package in …/b` 行给出同一 cache 分片前缀（第 1 轮 raw:93、第 2 轮 raw:176）
> 但指向 `/b` 构建目录，引用时不要混用这两种粒度。

## 二、G4 产物完整性（补测）

`find "$PKG" -type f` 的完整清单（两轮一致）：

```
conaninfo.txt
conanmanifest.txt
include/sbsms.h
lib/cmake/sbsms/sbsmsConfig.cmake
lib/cmake/sbsms/sbsmsConfigVersion.cmake
lib/cmake/sbsms/sbsmsTargets-release.cmake
lib/cmake/sbsms/sbsmsTargets.cmake
lib/libsbsms.so.2.3.0
lib/pkgconfig/sbsms.pc
licenses/LICENSE.txt
```

符号链接（`find -type l`）：

```
lib/libsbsms.so   -> libsbsms.so.2
lib/libsbsms.so.2 -> libsbsms.so.2.3.0
```

与 `package_info()` 互证：

| `cpp_info` 项 | 声明 | 实物 | 结论 |
|---|---|---|---|
| `libs` | `["sbsms"]` | `lib/libsbsms.so.2.3.0` (+2 符号链接) | ✅ 一致 |
| `libdirs`（默认） | `["lib"]` | `lib/` 有内容（库 + pkgconfig + cmake 配置） | ✅ 一致 |
| `includedirs`（默认） | `["include"]` | `include/sbsms.h` | ✅ 一致 |
| `bindirs`（默认） | `["bin"]` | 无 `bin/` | ✅ 库类型，符合预期（无 `commands.json`） |
| 许可文件 | `package()` 复制 | `licenses/LICENSE.txt` | ✅ 一致 |
| `cmake_file_name`/`cmake_target_name`/`pkg_config_name` | `sbsms`/`sbsms::sbsms`/`sbsms` | `lib/cmake/sbsms/sbsmsConfig.cmake` 等 4 件 + `lib/pkgconfig/sbsms.pc` | ✅ 一致 |

**结论：G4 PASS（人工）。**

## 三、L2 平台功能矩阵（补测）

**(a) 消费者程序在干净轮内真实构建并执行**（`reports/conan-create.log` 第 240–277 行）：

```
======== Testing the package: Executing test ========
libsbsms/2.3.0@ohpcd/stable (test package): RUN: ./test_sbsms
...
checks=26 failed=0
RESULT: PASS
```

**(b) 独立重建消费者并运行**（不依赖 finish 留下的构建产物，命令可复制执行）：

```console
$ PKG="$HOME/.conan2/p/b/libsbf2cff71db885c/p"
$ clang++ -std=c++17 -O2 -I"$PKG/include" \
    archives/l/libsbsms/2.3.0/test_package/test_sbsms.cpp \
    -L"$PKG/lib" -lsbsms -o /tmp/test_sbsms_consumer      # 设备 /tmp 只读，实际写 $TASK_DIR
$ LD_LIBRARY_PATH="$PKG/lib" ./test_sbsms_consumer | tail -3
  [ok]   output frequency Hz: got=439.574 want=440 tol=22
checks=26 failed=0
RESULT: PASS
```

**(c) 动态加载交付的 `.so`**：

```console
$ python3 -c "import ctypes,sys; ctypes.CDLL(sys.argv[1])" "$PKG/lib/libsbsms.so.2.3.0"
dlopen OK
```

**(d) W3 侧的破坏性反向测试（R34 兜底）**：`reports/w3-local-ci-log.md` 的 L1e 段

```
[step] L1e: Destructive negative test (R34)...
        [sabotage] lib/ moved away
        [sabotage] include/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on libsbsms
```

即：把交付的 `lib/` 与 `include/` 移走后测试不再通过 —— 测试确实链接并调用被测包，
不是 print-only 空壳。

**结论：L2 PASS（人工）。**

## 四、L4 静态安全扫描（补测）

### 4.1 交付的共享库 `lib/libsbsms.so.2.3.0`

```console
$ readelf -h  "$PKG/lib/libsbsms.so.2.3.0" | grep -E "Class:|Type:|Machine:"
  Class:                             ELF64
  Type:                              DYN (Shared object file)
  Machine:                           AArch64
$ readelf -lW "$PKG/lib/libsbsms.so.2.3.0" | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO      0x02fdc0 0x0000000000031dc0 0x0000000000031dc0 0x001458 0x002240 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0
$ readelf -dW "$PKG/lib/libsbsms.so.2.3.0" | grep -E "SONAME|FLAGS|BIND_NOW|NEEDED"
 0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
 0x000000000000000e (SONAME)             Library soname: [libsbsms.so.2]
 0x000000000000001e (FLAGS)              BIND_NOW
 0x000000006ffffffb (FLAGS_1)            Flags: NOW
```

| 判据 | 实测 | 结论 |
|---|---|---|
| `ELF type = DYN` | `DYN (Shared object file)` | ✅ |
| `GNU_STACK` 可读写、**不可执行**（NX） | `RW`（无 `E`） | ✅ |
| `GNU_RELRO` 存在 | 存在（`0x001458`） | ✅ |
| `FLAGS` 含 `BIND_NOW` | `BIND_NOW` | ✅ |
| `DT_NEEDED` 无绝对路径 / 不以 `../` 开头（L5b） | `libc++_shared.so`、`libc.so` 均为裸名 | ✅ |
| `DT_SONAME` 为相对路径（L5a） | `libsbsms.so.2` | ✅ |

### 4.2 消费者二进制（§3(b) 独立重建的那一个）

```console
$ readelf -h  test_sbsms_consumer | grep -E "Class:|Type:|Machine:"
  Class:                             ELF64
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           AArch64
$ readelf -lW test_sbsms_consumer | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO      0x0037d0 ... 0x0003b8 0x000830 R   0x1
  GNU_STACK      0x000000 ... 0x000000 0x000000 RW  0
$ readelf -dW test_sbsms_consumer | grep -E "FLAGS|NEEDED"
 0x0000000000000001 (NEEDED)             Shared library: [libsbsms.so.2]
 0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
 0x000000000000001e (FLAGS)              BIND_NOW
 0x000000006ffffffb (FLAGS_1)            Flags: NOW PIE
```

| 判据 | 实测 | 结论 |
|---|---|---|
| `ELF type = DYN` + `FLAGS_1` 含 `PIE` | `DYN (Position-Independent Executable file)` / `NOW PIE` | ✅ |
| `GNU_STACK` 不可执行 | `RW`（无 `E`） | ✅ |
| `GNU_RELRO` 存在 | 存在 | ✅ |
| `FLAGS` 含 `BIND_NOW` | `BIND_NOW` | ✅ |
| 消费者按 SONAME 寻址（不是路径） | `DT_NEEDED: libsbsms.so.2` | ✅ |

最后一行的意义：消费者记录的是**裸 SONAME**，而不是 `IMPORTED_LOCATION` 绝对路径或构建树相对路径，
说明 `CMAKE_SYSTEM_NAME=OHOS` 的平台修复在链接期真正生效（对照：不设平台名时产物无 `DT_SONAME`）。

**结论：L4 PASS（人工），库与消费者二进制两侧都达标。**

## 五、L5 产物基线（补测）

### 5.1 两条稳定聚合（聚合命令在包目录内用相对路径）

```console
$ PKG="$HOME/.conan2/p/b/libsbf2cff71db885c/p"
# ① 包内容聚合（排除 conan 元数据）
$ (cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
     | sed 's|^\./||' | sort | xargs sha256sum | sha256sum)
3254bf8f16e17d5b558b9dec7b1c3d1670d0a377868c7cd86a4c78409f6e2128  -
# ② 安装头文件树聚合
$ (cd "$PKG/include" && find . -type f | sed 's|^\./||' | sort | xargs sha256sum | sha256sum)
ede0a0a907be79503affe0c924f8cc7fbe7e1fde02f2348546e563d816a4c88c  -
```

### 5.2 逐产物 sha256（两轮相同）

| 产物 | sha256 |
|---|---|
| `include/sbsms.h` | `8901619970b44b178b85993ecb9e82e25595c174a5a5857aef6f04aa855d7575` |
| `lib/libsbsms.so.2.3.0` | `3880a1a88a4b64f0f36f7e9c91d4fafe7843a7812c983ac17e9a9202a1228f6a` |
| `lib/pkgconfig/sbsms.pc` | `4195c53dd5c871e324311090a5cda13779c76387d443c6a37a2a8a1083e00e79` |
| `lib/cmake/sbsms/sbsmsConfig.cmake` | `860d0eeb590861299e78ec4acd31e00d4e91bd62304ee4c4af3e498d7acc27d8` |
| `lib/cmake/sbsms/sbsmsConfigVersion.cmake` | `9923d1d62c2f4f0bdfb141c2e0112d3bf89b72f601118040410b1aa93ff4d9d2` |
| `lib/cmake/sbsms/sbsmsTargets.cmake` | `3b53d4975974fdaf693cd5851b0f88a8710d1052850809e3ae48a3cac0f63218` |
| `lib/cmake/sbsms/sbsmsTargets-release.cmake` | `c2456fb6656414d7a591182a5e9937dd58d0305d148c100af117392dd06194d5` |
| `licenses/LICENSE.txt` | `5fea475ad72d5d7cedec86d2dbfc02d2f8fcfb51a5c47ce155d64054b197e0b2` |

### 5.3 跨轮可复现性判别（同提交两轮独立清缓存构建）

```console
$ A="$HOME/.conan2/p/b/libsb698b9c997c655/p"   # 采信轮 conan-verify
$ B="$HOME/.conan2/p/b/libsbf2cff71db885c/p"   # finish 内嵌 W3
$ diff -u <(cd "$A" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
             | sed 's|^\./||' | sort | xargs sha256sum) \
          <(cd "$B" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
             | sed 's|^\./||' | sort | xargs sha256sum)
（无输出）
$ diff -r -x conaninfo.txt -x conanmanifest.txt "$A" "$B"
（无输出）
```

**8 个交付产物逐字节一致，目录树逐字节一致**；两条聚合值两轮相同：
包内容 `3254bf8f…`、头文件树 `ede0a0a9…`。因此基线可复现。

#### 为什么这一条此前不成立、以及它的根因已被修掉

第一版采信轮（SHA `bd3463fb`）在同一判据上是**7/8**：唯一不一致的是
`lib/pkgconfig/sbsms.pc`——上游 `CMakeLists.txt` 用 `configure_file(sbsms.pc.in)` 生成它，
把 `CMAKE_INSTALL_PREFIX`（即当轮的 Conan 包目录）写死在 `prefix=` 行里，于是同一配方两轮构建
会得到 `prefix=…/libsb1c34e470bb7c5/p` 与 `prefix=…/libsbf2993eb2c96e4/p` 两个不同文件，
包内容聚合也随之不同（`f94e649b…` vs `c76f3c36…`），只有头文件树聚合稳定。

本条已在本 SHA 的配方里**根治**：`package()` 的 `_make_pkgconfig_relocatable()` 把该行改写为
`prefix=${pcfiledir}/../..`（pkg-config 会展开 `${pcfiledir}`，`../..` 从任意安装位置都解析到包根），
既不指向 Conan 缓存绝对路径，也不再随轮次漂移。改写后的实测内容与 pkg-config 解析：

```console
$ head -1 "$PKG/lib/pkgconfig/sbsms.pc"
prefix=${pcfiledir}/../..
$ PKG_CONFIG_PATH="$PKG/lib/pkgconfig" pkg-config --cflags --libs sbsms
-I<包根>/include -L<包根>/lib -lsbsms
```

> 说明：本节第一版曾把「两轮逐字节一致」写成结论，而当时实际是 7/8；原因是取"第二轮"目录时
> 用了 `conan cache path "<ref>:<pid>"`，它返回的仍是第一轮的包目录，等于拿同一目录自比。
> 独立审计实测两个真实包目录后证伪。现已按 §5.3 的口径（从各自日志取目录）重测，并给出
> 上表的真实数值。

**结论：L5 PASS（人工），基线为两轮一致的包内容聚合 `3254bf8f…` 与头文件树聚合 `ede0a0a9…`。**

## 六、W3 本地 CI 结果（同一 SHA，`reports/w3-local-ci-log.md`）

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
```

说明：W3 的 L2 `skip: no bin/ dir` 与 L4 `pass: patches clean` 是本包形态的预期结果
（纯库无命令行工具、零补丁），**不是**「解析失败导致的静默跳过」，故不构成第 1 节的缺陷面；
真正需要补测的是采信轮报告里 G4/L2/L4/L5 的「无 cache 路径」跳过，已在上文逐项完成。

## 七、补测结论汇总

| 门禁 | 采信轮报告 | 人工补测结论 |
|---|---|---|
| G4 产物完整性 | ⚠️ 无法找到程序包 ID（却并列 ✅ PASS） | ✅ PASS —— 10 个文件 + 2 个符号链接与 `package_info()` 互证 |
| L2 平台功能矩阵 | ⏭️ 跳过 | ✅ PASS —— 干净轮内消费者 26/26 通过 + 独立重建消费者重跑 + dlopen + W3 L1e 反向测试 |
| L4 静态安全扫描 | ⏭️ 跳过 | ✅ PASS —— 库与消费者二进制均 DYN/RELRO/NX/BIND_NOW，消费者 PIE |
| L5 产物基线 | ⏭️ 跳过 | ✅ PASS —— 两条稳定聚合 + 8 个产物与整树跨轮逐字节一致 |
| L5a SONAME | 未输出 | ✅ PASS —— `SONAME: libsbsms.so.2`，消费者 `DT_NEEDED` 记裸 SONAME |
| L5b DT_NEEDED 路径 | 未输出 | ✅ PASS —— 仅 `libc++_shared.so` / `libc.so` 裸名 |

**没有把任何跳过项当作 PASS 记账；以上四项均为独立命令实测。**
