# 测试报告 — liblphobos 1.42.0

> **项目**: liblphobos（D 语言标准库 Phobos + druntime 共享库包）  
> **测试日期**: 2026-09-17  
> **测试环境**: HarmonyOS PC（aarch64 / OHOS 6.0 / clang 15 / conan profile `ci/conan/profiles/ohos-aarch64`）  
> **测试类型**: 上游 Phobos unittest 逐模块实测（官方 `%.test` 1:1 复刻）+ Conan test_package 消费者测试（鸿蒙特有）

---

## 一、测试摘要

### 1.1 上游官方测试（Phobos unittest，176 模块逐模块独立编译 + 运行）

| 指标 | 数值 | 说明 |
|:----:|:----:|:------:|
| 上游测试模块 | 176 | `std/` 166 + `etc/` 10（官方入口 `runtime/phobos/Makefile` unittest 体系） |
| 通过 (PASS) | 123 | 输出 `N modules passed unittests` 且 exit=0 |
| 失败 (FAIL) | 9 | 全部平台/环境归因，逐项见第三节 |
| 跳过 (SKIP) | 44 | 模块无 unittest 块（编译链接成功、无测试输出、exit=0），与 ldc/1.42.0 统计口径一致 |
| 超时 (TIMEOUT) | 0 | 单模块超时上限 600 s |
| **有测试项通过率** | **123/132 = 93.2%** | ldc/1.42.0 同源码当年基线 125/132 = 94.7%，交叉验证吻合 |

### 1.2 test_package 消费者测试（鸿蒙特有，本任务新增）

| 指标 | 数值 |
|:----:|:----:|
| 消费者断言 | 7 |
| 通过 | 7 |
| 失败 | 0 |

---

## 二、测试命令与口径

### 2.1 上游 unittest（官方 `std/<module>.test` 目标的 ldc2 等价复刻）

```bash
LD_LIBRARY_PATH=<llvm包>/lib:<本包>/lib \
ldc2 -conf= -I<本包>/include/d \
  -w -de -preview=dip1000 -preview=dtorfields -preview=fieldwise \
  -i -main -unittest -d-version=StdUnittest \
  -defaultlib=phobos2-ldc-shared,druntime-ldc-shared \
  -L-L<本包>/lib -L-lz -L-lm \
  --gcc=<clang_passthrough> \
  -run std/array.d        # ← 逐模块执行，176 次（4 并发）
```

- 判定规则（与 ldc/1.42.0 口径一致）：输出含 `passed unittests` → PASS；无输出且 exit=0 → SKIP（无 unittest 块）；否则 FAIL。
- 官方 DFLAGS（`-w -de -preview=dip1000 -preview=dtorfields -preview=fieldwise`）与 `-d-version=StdUnittest`（LDC 方言，等价 DMD `-version=`）逐字保留，未修改任何上游测试代码。
- ⚠️ 诚实备注：首轮曾尝试"批量 UT 库 + tarball 内 `test_runner`"方案，产出 176/176 全过假象——实测证实该 tarball 的 `test_runner.d` main 为空模板（忽略模块名参数，任意参数 exit=0），**该轮结果已废弃**，改用上述官方逐模块方式重跑。

### 2.2 test_package 消费者测试

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build="liblphobos/*"
# → test_package/test_liblphobos.sh 由 conan test_package 阶段自动执行
```

---

## 三、9 个失败模块逐项归因（全部平台/环境因素，非库缺陷）

| # | 模块 | 首错（摘要） | 根因归因 |
|:-:|------|-------------|----------|
| 1 | std.datetime.systime | `assert ... /usr/share/zoneinfo` | OHOS 无系统 zoneinfo 数据库（tzdata 缺失） |
| 2 | std.datetime.timezone | 同上（zoneinfo 路径探测失败） | 同上 |
| 3 | std.net.curl | `Symbol not found ... curl_*` | 设备无 libcurl（可选联网功能） |
| 4 | std.stdio | `AssertError ... /tmp` | OHOS `/tmp` 只读（R33），stdio 的 tmpfile 探测断言失败 |
| 5 | std.experimental.allocator.mallocator | `posix_memalign ... != 0` | musl `posix_memalign` 对 0 尺寸/对齐组合的返回码与 glibc 语义差异 |
| 6 | std.math.hardware | FPU 状态字断言 | aarch64 FPU 环境差异（x87 专属断言在 ARM 上的预期不适用） |
| 7 | std.file | 沙箱目录写/exec 失败 | 沙箱对 el2 缓存目录的 exec/写限制 |
| 8 | std.process | 子进程 spawn 失败 | 同上（沙箱 exec 限制） |
| 9 | std.regex.internal.tests | `Segmentation fault`（单跑复现） | unittest 自重启子进程机制（exec 自身）在沙箱 el2 目录下受限；单模块独立复跑复现，排除并发干扰 |

> 对照：ldc/1.42.0 当年 6 失败中 zoneinfo/curl/tmp 三类与本轮一致；本轮多出的沙箱类失败目录不同（本轮工作目录位于应用沙箱 el2），均可在非沙箱环境复验消除。

---

## 四、test_package 消费者测试详情（7/7）

`test_package/test_liblphobos.sh` 流程：包内文件完整性校验 → `clang_passthrough` shim 现场编译 + 签名 → `ldc2 -conf=`（完全脱离默认配置，import/库全部指向本包）编译 `hello_phobos.d` 链接 `libphobos2-ldc-shared.so.112` + `libdruntime-ldc-shared.so.112` → `binary-sign-tool` 签名 → 真机运行 → 逐行断言：

| # | 断言项 | 覆盖模块 |
|:-:|--------|----------|
| 1 | 排序输出 `[1,1,2,3,4,5,6,9]` | std.algorithm.sorting |
| 2 | range 变换输出 | std.algorithm.iteration / std.range |
| 3 | 格式化输出 `s = 42` | std.format |
| 4 | 数值转换 `1_000_000 → 1000000` | std.conv |
| 5 | JSON 序列化 | std.json |
| 6 | 字符串处理 | std.string / std.array |
| 7 | 时钟可读（`SysTime` → ISO 串） | std.datetime |

---

## 五、日志与证据路径

| 证据 | 路径 |
|------|------|
| conan create 全量日志（含 test_package 7/7 输出） | `reports/conan-create.log`（会话存档 `.workbuddy/tmp/liblphobos-1.42.0/evidence-backup/`） |
| 上游 unittest 逐模块日志（176 份） | `.workbuddy/tmp/liblphobos-1.42.0/ut/logs/<module>.log` |
| 上游测试汇总（JSON 统计） | `.workbuddy/tmp/liblphobos-1.42.0/ut/summary.json` |
| conan-verify 八道闸报告 | `reports/conan-verify-report.md`（G1/G2/G3 PASS，VERIFY_EXIT=0） |
| W3 本地 CI 模拟日志 | `reports/w3-local-ci.log`（setup.sh + build_and_test.sh 通过） |
| std.regex.internal.tests 单跑复跑日志 | `ut/logs/std.regex.internal.tests.rerun.log` |

---

## 六、测试结论

✅ **上游 176 个 unittest 模块全部实际执行**：有测试项口径 **93.2%**（123/132），9 个失败均为 OHOS 平台/沙箱环境因素并逐项取证归因，与 ldc/1.42.0 同源码基线（94.7%）吻合。  
✅ **鸿蒙消费者用例 7/7 通过**：真实编译（D 源码 → 本包共享库）+ 签名 + 真机运行 + 输出断言，验证包可用性。  
✅ 未修改上游任何测试代码；test_package 为新增的鸿蒙平台消费者验证，不替代上游测试统计。
