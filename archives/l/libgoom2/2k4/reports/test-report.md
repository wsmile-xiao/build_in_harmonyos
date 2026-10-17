# libgoom2 2k4 测试报告

> **项目**: libgoom2（上游 goom2k4）
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（OHOS SDK native clang 15，Target aarch64-unknown-linux-ohos）
> **测试类型**: test_package 消费者测试（上游无官方测试套件）

---

## 一、测试摘要

| 指标 | 数值 | 说明 |
|:----:|:----:|:------:|
| 上游自动化测试入口 | 0 | 上游无任何自动化测试（清点证据见下） |
| test_package 消费者测试 | 1 | PASS（12 项断言） |

**消费者测试通过率**: 1/1（100%）

**上游测试通过率**: 0/0（不适用——上游 0 个可运行测试入口）

---

## 二、上游测试清点证据（R51 三步法）

1. **清点**：原始包 sha256 `d993c904c05faba87fd7f159291fa1cb7aadcff2edd28454d8e967880a8a0c85`；
   对整棵树执行 `grep -rn "TESTS\|check_PROGRAMS" --include="Makefile.am" --include="configure.in" .`
   零命中；`test/` 目录只有 17 行的手工演示程序 `testapp.c`，且没有 `Makefile.am`
   （不属于任何构建目标、也没有 TESTS 注册）；`tools/`（gfont.c、minicompress.c）是
   构建期代码生成器。→ 自动化测试入口 0 个。
2. **运行**：`make -j1 check` 在根、src、xmms-goom、sdl-goom 四个目录全部输出
   `Nothing to be done for 'check'`（automake 结构性空跑），原始输出见 W3 日志
   `reports/w3-local-ci.log`。
3. **申报**：上游通过率 0/0（不适用），消费者测试照常计入「鸿蒙特有测试」行。

## 三、test_package 消费者测试（鸿蒙特有）

| # | 断言内容 | 结果 |
|---|----------|------|
| 1 | `goom_init(320, 240)` 返回可用实例（非 NULL） | ✅ PASS |
| 2 | 请求分辨率生效（`screen.width==320 && screen.height==240`） | ✅ PASS |
| 3 | `screen.size` 与 width*height 一致 | ✅ PASS |
| 4 | 至少注册了一个可视化效果（`nbVisuals >= 1`） | ✅ PASS |
| 5 | 64 帧合成音频全部返回帧缓冲（64/64） | ✅ PASS |
| 6 | 首个采样帧已绘制（FNV-1a 哈希非 0） | ✅ PASS |
| 7 | 帧缓冲随帧变化（采样哈希 ≥2 种，动画真实运行） | ✅ PASS |
| 8 | 声音分析消费了音频数据（`sound.volume ∈ (0,1]`） | ✅ PASS |
| 9 | `goom_set_resolution(640, 480)` 生效 | ✅ PASS |
| 10 | 分辨率变更后继续渲染（16/16 帧） | ✅ PASS |
| 11 | 640x480 帧与 320x240 帧哈希不同 | ✅ PASS |
| 12 | `goom_close` 正常返回（无崩溃） | ✅ PASS |

执行日志（W3 conan create，见 `reports/w3-local-ci.log`）：

```
libgoom2/2k4 (test package): RUN: clang -std=c11 -I<package>/include test_libgoom2_consumer.c -L<package>/lib -lgoom2 -o ...
libgoom2/2k4 (test package): RUN: .../test_libgoom2_consumer
ok: goom_init(320, 240) returns a plugin instance
...
checks=12 failures=0
```

## 四、构建产物（G4）

| 产物 | 说明 |
|------|------|
| `lib/libgoom2.so.0.0.0` | 共享库，SONAME `libgoom2.so.0`，NEEDED 仅 `libc.so` |
| `lib/libgoom2.so.0` / `lib/libgoom2.so` | libtool 符号链接 |
| `include/goom/*.h` | 12 个公共头文件 |
| `lib/pkgconfig/libgoom2.pc` | pkg-config 描述文件 |

`.la` 文件已由配方在 `package()` 中移除（避免把构建期绝对路径带进包）。

## 五、L2/L4/L5 门禁的口径说明

| 门禁 | 本轮读数 | 说明 |
|------|----------|------|
| W3 本地 CI 的 L2 | `skip: no executables` | 该检查面向包内 CLI 产物（`bin/` 下可执行文件）做 smoke test；本包是纯库（`bin/` 0 个文件），按既有口径跳过，非失败 |
| conan-verify 的 L2 | `PASS`（0 个二进制文件通过 smoke test） | 该检查在配方验证阶段执行，纯库包无二进制可探针，同样按包形态给出通过读数 |
| L4（静态安全扫描） | CI `pass: patches clean`；conan-verify `无可扫描的 ELF 文件` | 补丁无危险函数调用；包内无 `bin/` ELF，产物 .so 的安全属性由 G4/L5 与 `llvm-readelf` 抽查承担 |
| L5（产物基线） | `PASS`（首次运行，基线已保存，17 个文件） | 基线 JSON 见 `reports/baseline.json` |

库的「真实运行」证据由 test_package 消费者测试承担（W3 日志 L1 段实跑 12 项断言，
`Launching test_package` 与运行输出均在 `reports/w3-local-ci.log` 内）。
