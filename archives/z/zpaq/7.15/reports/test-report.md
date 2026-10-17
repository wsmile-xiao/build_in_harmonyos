# zpaq 7.15 测试报告（OHOS aarch64）

- 包引用：`zpaq/7.15@ohpcd/stable`
- Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd 17）
- 构建方式：上游 `Makefile` 的 `zpaq` 目标 + OHOS 参数覆盖（`-Dunix -DNOJIT -O3 -DNDEBUG -static-libstdc++`）
- 执行日期：2026-09-25

---

## 0. 测试汇总（机器可读）

| 项 | 数量 |
| 总测试数 | 1 |
| 通过 PASS | 1 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

| 鸿蒙特有（test_package） | 数量 |
| 总测试数 | 7 |
| 通过 PASS | 7 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

---

## 1. 上游测试（R51 第 1-3 步）

### 1.1 清点（第 1 步）

| 项 | 结论 | 证据 |
|----|------|------|
| 测试目录 | 无 | 解包目录 8 个文件，无 `tests/`、无 `test/` |
| 构建系统注册的测试入口 | 1 个 | 顶层 `Makefile:32-36` 的 `check` 目标 |
| ctest / pytest / meson test 注册 | 无 | 上游无 CMake/Meson/Python 测试配置 |
| `make -n check` | 4 行命令 | `add` → `extract -to` → `cmp` → `rm`；断言仅 `cmp` 一条 |

```
$ make -n check
./zpaq add archive.zpaq zpaq
./zpaq extract archive.zpaq zpaq -to zpaq.new
cmp zpaq zpaq.new
rm archive.zpaq zpaq.new
```

**上游注册用例总数 N = 1。**

### 1.2 实际运行（第 2 步）

命令（适配机 aarch64 OHOS 实跑）：

```bash
make check CXX=clang++ CPPFLAGS="-Dunix -DNOJIT" \
           CXXFLAGS="-O3 -DNDEBUG" LDFLAGS="-static-libstdc++"
```

关键输出：

```
clang++ -Dunix -DNOJIT -O3 -DNDEBUG -o zpaq.o -c zpaq.cpp -pthread
clang++ -Dunix -DNOJIT -O3 -DNDEBUG -o libzpaq.o -c libzpaq.cpp
clang++ -static-libstdc++ -o zpaq zpaq.o libzpaq.o -pthread
./zpaq add archive.zpaq zpaq
zpaq v7.15 journaling archiver, compiled Sep 25 2026
100.00% 0:00:00 [1..37] 2214620 -method 14,103,0
1 +added, 0 -removed.
0.000000 + (2.214464 -> 2.214464 -> 0.930681) = 0.930681 MB
0.170 seconds (all OK)
./zpaq extract archive.zpaq zpaq -to zpaq.new
0.303 seconds (all OK)
cmp zpaq zpaq.new          # 无输出 = 字节一致
rm archive.zpaq zpaq.new   # ← 本机 rm 被沙箱 shim 拦截（127），与 zpaq 无关
```

**实测 N′ = 1 / 1，通过率 100%（1/1）。** 唯一失败的是收尾清理命令 `rm`：
本机 `rm` 被沙箱安全 shim 接管且 shim 的 `#!/bin/bash` 解释器不存在（OHOS 无 `/bin/bash`），
错误码 127 —— 属于执行环境问题，与 zpaq 行为无关（`cmp` 已在此之前成功）。

### 1.3 如实回填（第 3 步）

上游无跳过的用例，无被修改的上游用例，无「没环境」的用例。
`test_package` 的 7 项消费者断言为**鸿蒙特有测试**，不计入上游分母。

---

## 2. 本地构建验证（conan create，W3 同源）

```
$ conan create archives/z/zpaq/7.15 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
...
zpaq/7.15@ohpcd/stable: RUN: /data/service/hnp/bin/clang++ -O3 -DNDEBUG -Dunix -DNOJIT -static-libstdc++ zpaq.cpp libzpaq.cpp -pthread -o zpaq > ".../zpaq-build.log" 2>&1; rc=$?; cat ".../zpaq-build.log"; exit $rc
zpaq/7.15@ohpcd/stable: Package '6b129b068851896169fae42d399fa922d239ce8a' built
zpaq/7.15@ohpcd/stable: package(): Packaged 2 files: zpaq, COPYING
```

配方走**单次直接编译调用**（等价上游 `Makefile:32-36` 的 `zpaq` 目标：`zpaq.o` +
`libzpaq.o` → `zpaq`），不经过 `make` 层：本机实测，`/system/bin/sh` 作 recipe shell 时
编译器 stdio 直连 harness 捕获管道会**静默退出 1（零诊断）**，stdio 落到普通文件即恢复
（见 notes.md 表格 #4）。日志随后 `cat` 回显，`exit $rc` 保证失败仍能传播。

`conan-verify` 结论（逐字见 `reports/conan-verify-report.md`）：**G0-G3 通过；
G4/L2/L4/L5 为 SKIPPED（工具未执行）**，按「PASS 与 SKIP 并存时以 SKIP 为准」的口径
不计入通过 —— 这四项由 `reports/conan-verify-supplement.md` 的人工补测覆盖
（G4 产物清单、L2 消费者实测、L4 ELF 安全属性、L5 两轮独立清缓存构建复现基线）。

---

## 3. test_package 消费者断言（鸿蒙特有，7 项）

对 `conan create` 安装出来的 `bin/zpaq` 真实执行（`test_package/test.sh`），
`conan create` 内置执行结果逐字如下：

```
zpaq/7.15@ohpcd/stable (test package): RUN: "/data/service/hnp/bin/bash" ".../test_package/test.sh" ".../p/bin/zpaq"
[PASS] T1 no-arg invocation prints the zpaq v7.15 banner and usage
[PASS] T2 add+extract round trip is byte-identical for both payload members
[PASS] T3 second add() created a second journal version (2 versions)
[PASS] T4 -until 1 restores the v1 revision byte-exactly
[PASS] T5 listing accounts for cross-version fragment dedup
[PASS] T5b second add() re-added only the changed member
[PASS] T6 missing archive is diagnosed and reported as rc=2
RESULT: 7/7 checks passed
```

| # | 断言 | 覆盖的真实行为 |
|---|------|----------------|
| T1 | 无参数调用打印 `zpaq v7.15 journaling archiver` 横幅与用法 | 二进制可执行 + 版本串正确 |
| T2 | `add` → `extract -to` → `cmp`：2.2 MB 二进制成员 + 文本成员字节级一致 | 上游 `make check` 同口径往返，附带多成员 |
| T3 | 第二次 `add` 后 `zpaq l` 报 `2 versions` | 日志式归档：改动的成员存为新版本而非新文件 |
| T4 | `x ... -until 1 -to v1copy.txt` 与 v1 内容字节级一致 | 历史版本回滚 |
| T5 | 列表含 `after dedupe` 记账 | 片段级去重路径真实执行 |
| T5b | 第二次 `add` 报 `1 +added, 0 -removed.` | 增量归档只新增改动成员 |
| T6 | 归档不存在时输出 `no-such-archive.zpaq: No such file or directory` **且退出码非 0** | 错误路径有可诊断输出（输出目录已预建，排除输出路径干扰） |

**7/7 通过。** 断言口径说明（逐条实测，非推断）：

| 调用 | 退出码 | 输出 |
|------|--------|------|
| 无参数 / 未知选项（含 `--version`） | 1 | 横幅 + 用法 |
| `x <不存在的归档>` | **2** | `<archive>: No such file or directory`（stderr）+ `zpaq error: …` |
| `add <归档> <不存在的输入路径>` | **0** | 只有诊断，**不返回非 0** |
| 成功的 add / extract / list | 0 | —— |

即「错误命令一律返回 0」不成立：**既不能只断言退出码，也不能完全不看退出码**。
正向用例断言产物字节（`cmp`），错误用例（T6）同时断言诊断文本与退出码；
脚本以 `set -euo pipefail` 开头，并对每处 zpaq 调用显式捕获返回值
（`rc=0; cmd || rc=$?`），避免 `set -e` 在「期望失败」的调用上提前中断脚本。
解释器由 `test_package/conanfile.py` 解析：`$CONFIG_SHELL` → 固定候选清单
`os.path.exists()` 探测 → 都取不到即 `ConanException`（**不用** `shutil.which("bash")`，
它会误取调用方运行时自带的 bash，conan 起的 shell 执行它报 `Permission denied`，exit 126）。

---

## 4. L2 冒烟门禁的本包特例（如实记录）

`conan-verify` / CI 的 L2 冒烟检查执行 `bin/<tool> --version`（失败再试 `--help`）并要求退出码 0。
**zpaq 7.15 没有 `--version` 选项**：任何未识别参数都会打印横幅 + 用法并以退出码 1 结束，
`--help` 同理。因此本包**不能**用 `--version` 证明可用性：

```
$ ./zpaq --version ; echo "exit=$?"
zpaq v7.15 journaling archiver, compiled Sep 25 2026
Unknown option ignored: --version
Usage: zpaq command archive[.zpaq] files... -options...
exit=1
```

本包的处理方式：

- 不给上游打补丁去伪造 `--version`（那会改变上游 CLI 语义，且与本次适配目的无关）；
- 可用性由 `test_package` 的真实归档往返 / 版本回滚 / 去重记账断言证明（§3）；
- CI 侧 L2 是 `[warn] ... (non-blocking)`，不阻塞流水线；
- 本地 `conan-verify` 本轮 G4 报 `⚠️ 无法找到程序包 ID`（application 包无 `lib/`），
  L2/L4/L5 随之报 `⏭️ 跳过（无 cache 路径）` —— **跳过不等于通过**，本包按
  「PASS 与 SKIP 并存时以 SKIP 为准」的口径记为未执行，并由
  `reports/conan-verify-supplement.md` 人工补测覆盖。

---

## 5. 产物属性

```
$ file bin/zpaq
ELF 64-bit LSB shared object, ARM aarch64, dynamic (/lib/ld-musl-aarch64.so.1)

$ llvm-readelf -dW bin/zpaq | grep -E "NEEDED|FLAGS|RPATH|RUNPATH"
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]
  0x000000000000001e (FLAGS)   BIND_NOW
  0x000000006ffffffb (FLAGS_1) NOW PIE
```

- 单一 `DT_NEEDED = libc.so`：libc++ 由 `-static-libstdc++` 静态烘焙，
  不会在设备上触发 `Error loading shared library libc++_shared.so`。
- `package_type = application`，包内制品为 `bin/zpaq` + `licenses/COPYING`
  （Unlicense；`libzpaq.cpp` 内嵌 divsufsort 片段为 MIT）；
  `bindirs=["bin"]`，`includedirs` / `libdirs` 为空，无系统同名库冲突。
- 完整的 ELF 安全属性判据（PIE / 栈不可执行 / RELRO / BIND_NOW / 依赖）
  见 `reports/conan-verify-supplement.md` §L4。

---

## 6. 结论

| 维度 | 结果 |
|------|------|
| 上游测试 | 1/1 通过（`make check`，仅收尾 `rm` 受沙箱影响 127） |
| 本地构建（conan create） | 通过 |
| conan-verify 门禁 | G0-G3 通过；G4/L2/L4/L5 工具未执行（SKIPPED）→ 人工补测通过 |
| test_package 消费者断言 | 7/7 通过 |
| 补丁 | 无（源码零修改） |
| 依赖 | 零外部依赖 |
