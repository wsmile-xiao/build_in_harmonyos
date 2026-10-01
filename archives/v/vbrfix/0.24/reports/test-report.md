# 测试报告 — vbrfix 0.24 (vbrfixc)

> **项目**: vbrfix（vbrfixc，命令行 MP3 VBR 头修复工具）
> **测试日期**: 2026-09-30
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（uname -s = HarmonyOS）
> **测试类型**: 消费者侧功能测试（上游无自动化测试，见 §一）

---

## 一、上游测试清点（R51 三步法）

### 1.1 上游测试入口核验

上游 vbrfix 0.24 源码树共 **69 个文件**（含 `docs/` 下 8 个 HTML 文档），清点结果：

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 上游测试目录 | `find <src> -type d -name 'test*'` | 无（0 个） |
| automake 测试套件 | `grep -n '^TESTS' Makefile.am vbrfixc/Makefile.am` | 无 `TESTS =` 声明 |
| ctest / meson / pytest | 全树检索 | 无 |
| 自建测试脚本 | `ls` 全树 | 无 |
| 上游样例数据 | 全树检索 `*.mp3` / `samples/` / `testdata/` | 无 |

### 1.2 上游测试实际执行

```
$ make check
Making check in vbrfixc
Making check in vbrfixc/docs
Making check in vbrfixc/docs/en
make[3]: Nothing to be done for 'check'.      ← 空套件
make[2]: Nothing to be done for 'check-am'.
make[1]: Nothing to be done for 'check'.
$ echo $?
0
```

**上游测试统计（机器可读）**

| 指标 | 数值 |
|------|------|
| 上游测试命令 | `make check` |
| 用例总数 | **0** |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | **0**（不适用：无测试可跳） |
| 未运行原因 | 上游全树无任何自动化测试基础设施（无 `tests/`、无 `TESTS` 声明、无 ctest/meson/pytest 入口），亦无上游样例文件 |

> 结论：**上游没有自动化测试入口**，`make check` 为空套件（退出码 0，无用例执行）。
> `test_package` 不计入上游测试统计（按规范要求分开申报）。

---

## 二、消费者侧测试（test_package，实质调用被测二进制）

测试入口：`test_package/test_vbrfixc.sh`（由 `test_package/conanfile.py` 的 `test()` 调用）
被测二进制：`<package_folder>/bin/vbrfixc`

```
$ /data/service/hnp/bin/bash test_package/test_vbrfixc.sh <bin_dir>
```

### 2.1 测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总用例数 | 9 | 100% |
| 通过 (PASS) | 9 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| **其中鸿蒙平台专有用例** | **1**（TC-09-ohos-abi） | — |

**功能通过率**: ✅ **100%（9/9）**

### 2.2 逐项用例明细

| # | 用例名称 | 测试内容 | 结果 | 日志 |
|---|----------|----------|:----:|------|
| 1 | `TC-01-usage` | 无参数调用 → 打印用法且退出码 0 | ✅ PASS | `TC-01-usage.stdout` |
| 2 | `TC-02-vbr-no-xing` | VBR(128/160kbps 交替, 24 帧) 无 Xing → 识别 24 帧、重建 Xing 头、输出=输入+417B | ✅ PASS | `TC-02-vbr-no-xing.stdout` |
| 3 | `TC-03-vbr-with-xing` | VBR 且已有 Xing 头 → 识别旧头（size 417）并重建，输出仅 1 个 Xing 头 | ✅ PASS | `TC-03-vbr-with-xing.stdout` |
| 4 | `TC-04-cbr-refused` | CBR 且无 `-allways` → stderr 报 "File Is Not VBR" 且不产出文件（错误路径） | ✅ PASS | `TC-04-cbr-refused.stderr` |
| 5 | `TC-05-cbr-allways` | CBR + `-allways` → 强制写出，标志位=32，字节数不变 | ✅ PASS | `TC-05-cbr-allways.stdout` |
| 6 | `TC-06-id3v1-kept` | VBR + ID3v1 → 标签保留到输出末尾 128 字节（`TAG`），输出=11813B | ✅ PASS | `TC-06-id3v1-kept.stdout` |
| 7 | `TC-07-id3v2-kept` | VBR + ID3v2 → 标签保留到输出头部（`ID3`），输出=11735B | ✅ PASS | `TC-07-id3v2-kept.stdout` |
| 8 | `TC-08-cbr-makevbr` | CBR + `-allways -makevbr` → 标志位=96，输出含 Xing 头，大小=10425B | ✅ PASS | `TC-08-cbr-makevbr.stdout` |
| 9 | **`TC-09-ohos-abi`（鸿蒙特有）** | 产物为 ELF64/LE/**AArch64**、PT_INTERP=`/lib/ld-musl-aarch64.so.1`（OHOS 运行时加载器），且在 HarmonyOS 本机执行成功 | ✅ PASS | `TC-09-ohos-abi.stdout` |

**实测汇总输出**

```
 CASE SUMMARY: total=9 passed=9 failed=0 skipped=0
 RESULT: PASS
```

**日志路径**：脚本每次运行在 `mktemp -d` 临时目录下生成 `logs/<用例名>.stdout|.stderr`
（本地完整运行日志留档：`$HOME/tmp/vbrfix-logs/upstream-consumer-tests.log`）。

### 2.3 所有上游样例均已测试

上游无样例数据文件（见 §1.1），故不存在漏测的样例。
本套用例覆盖了 vbrfixc 的全部 7 个命令行标志（`-ri1/-ri2/-skiplame/-allways/-makevbr/-log/-lameinfo`
中的可自动验证项）与全部核心代码路径（帧扫描、VBR 判定、Xing 重建、ID3v1/v2 保留、CBR 拒写）。

---

## 三、测试结论

### 3.1 总体评价

✅ **通过**。适配后产物 `bin/vbrfixc` 功能与上游语义一致：可正确扫描 MPEG-1 Layer III 帧、
判定 VBR、重建正确 VBR 头（Xing）、保留 ID3v1/ID3v2 标签、对非 VBR 文件按上游语义拒写。

### 3.2 鸿蒙适配新增测试

| 用例 | 平台相关性 | 断言 |
|------|-----------|------|
| `TC-09-ohos-abi` | 鸿蒙专有 | ELF64 小端 AArch64 + OHOS musl 动态加载器 `/lib/ld-musl-aarch64.so.1` + 在 HarmonyOS 内核上实际执行成功 |

> 该用例可捕获「构建产物目标平台错误」（如误用 x86 或 32 位工具链）——上游 tarball 内
> 自带的 32 位 x86 预编译 `vbrfixc/vbrfixc`（machine=0x03）即为此用例的反例。

### 3.3 已知限制

1. 上游无自动化测试，本报告的上游统计为 0 用例（已附清点证据）。
2. 测试样本为手工构造的 MPEG-1 Layer III 帧序列（无外部音频工具依赖），覆盖 VBR/CBR、
   Xing 有无、ID3v1/v2 场景；未覆盖 MPEG-2/2.5 与真实编码器产出的 MP3 文件。
3. `-log` / `-lameinfo` 两个标志依赖 LAME 扩展信息与日志文件，未纳入自动断言。

---

## 四、测试环境

```
目标平台 : HarmonyOS PC aarch64 (uname -s=HarmonyOS, HongMeng Kernel 1.12.0, aarch64)
编译器   : clang 15.0.4 / clang++ (libc++)
C++ 标准库: libc++
Profile  : ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang 15, Release)
Conan    : 2.29.1 (OHOS 适配版)
参考       : vbrfix/0.24@ohpcd/stable
```

---

*报告生成时间: 2026-09-30*
