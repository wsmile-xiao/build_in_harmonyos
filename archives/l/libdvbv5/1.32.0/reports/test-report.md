# libdvbv5 1.32.0 测试报告

日期：2026-09-22
平台：OHOS aarch64 (HarmonyOS PC)
参考：`libdvbv5/1.32.0@ohpcd/stable`
Profile：`ci/conan/profiles/ohos-aarch64`

## 1. 上游测试（R51 三步法）

### 1.1 清点（第一步）

```
$ cd v4l-utils-1.32.0.work
$ grep -rn "^\s*test(" --include="meson.build" . | wc -l
0
$ meson test -C build --list
No tests defined.
```

上游为 libdvbv5 **未注册任何自动化测试**。

### 1.2 运行（第二步）

唯一不依赖 DVB 硬件的 libdvbv5 消费者是 `utils/dvb/dvb-format-convert`
（调用 `dvb_read_file_format` / `dvb_write_file_format`）。它依赖 `argp`，
而 OHOS sysroot 无 `argp.h`、无 `libargp`、libc 无 `argp_parse` 符号，
因此无法原样构建。

其 libdvbv5 代码路径已用等价消费者程序实际执行：

```
命令:   ./test_libdvbv5（test_package fixture）
日志:   reports/upstream-roundtrip.log
退出码: 0
输出:
  parsed_entries=3
  write_ok
  roundtrip_ok
```

输入 3 条 DVB-T 频道（legacy channel 格式），输出 DVBv5 原生格式，
FREQUENCY / BANDWIDTH_HZ / CODE_RATE_HP / MODULATION /
TRANSMISSION_MODE / GUARD_INTERVAL 全部正确解码。

### 1.3 用例统计（第三步，如实回填）

| 项目 | 数量 |
|---|---|
| 上游注册的自动化用例总数 | **0** |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |
| 用例名称 | 无（`No tests defined.`） |
| 日志路径 | `reports/upstream-test.log` |

> 无上游用例可统计；`test_package` 的 19 项断言属消费者测试（L1），
> 不计入上游用例统计。

完整清点证据与逐项不可执行的技术原因见 `reports/upstream-tests.md`。

## 2. test_package 消费者测试（L1）

```
命令:   conan create archives/l/libdvbv5/1.32.0 \
          -pr:h=ci/conan/profiles/ohos-aarch64 \
          -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
退出码: 0
结果:   checks=19 failures=0 / RESULT: PASSED
```

| # | 断言 | 结果 |
|---|---|---|
| 1 | `dvb_read_file_format()` 读取缺失文件返回 NULL | PASS |
| 2 | fixture 文件可写 | PASS |
| 3 | `dvb_read_file_format()` 解析 legacy channel 格式 | PASS |
| 4 | 解析出 3 条频道 | PASS |
| 5 | 首条频道 FREQUENCY 解码为 578000000 | PASS |
| 6 | 首条频道 DELIVERY_SYSTEM 为 SYS_DVBT | PASS |
| 7 | 首条频道 BANDWIDTH_HZ 解码为 8000000 | PASS |
| 8 | 首条频道 CODE_RATE_HP 已解码 | PASS |
| 9 | `dvb_write_file_format()` 写出 DVBv5 原生格式 | PASS |
| 10 | 回读写出的 DVBv5 原生格式 | PASS |
| 11 | 往返后条目数仍为 3 | PASS |
| 12 | 往返后 FREQUENCY 保持 578000000 | PASS |
| 13 | 非法输入 fixture 可写 | PASS |
| 14 | 非法 channel 数据被拒绝 | PASS |
| 15 | `dvb_parse_delsys("DVBT")` == SYS_DVBT | PASS |
| 16 | `dvb_parse_format("CHANNEL")` == FILE_CHANNEL | PASS |
| 17 | `dvb_parse_format("DVBV5")` == FILE_DVBV5 | PASS |
| 18 | **鸿蒙特有**：消费者二进制在 OHOS 上加载并运行打包产物 | PASS |
| 19 | SYS_DVBT ABI 常量为非零 | PASS |

**合计：19/19 通过。**

## 3. 鸿蒙特有测试

`test_package/test_libdvbv5.c` 中的 `test_ohos_packaging`（上表 #18）：
在 OHOS 上构建并运行链接打包库的消费者二进制。该断言只能在前述条件下成立：

1. `package()` 已用 `binary-sign-tool -selfSign 1` 对 ELF 签名
   （否则加载器报 `Error loading shared library libdvbv5.so.0`）；
2. `package()` 已生成 `libdvbv5.so` / `libdvbv5.so.0` 别名，使加载器
   能按 SONAME 解析。

上游没有任何测试覆盖打包产物契约。

## 4. 产物核验

```
lib/libdvbv5.so.0.0.0   ELF64 AArch64, SONAME libdvbv5.so.0
                        NEEDED: libudev.so.1, libc.so
lib/libdvbv5.so.0       -> libdvbv5.so.0.0.0
lib/libdvbv5.so         -> libdvbv5.so.0
lib/pkgconfig/libdvbv5.pc
include/libdvbv5/*.h    47 个头文件
licenses/COPYING, COPYING.libdvbv5
share/locale/*/LC_MESSAGES/{libdvbv5,v4l-utils}.mo   9 个（5 个语言目录）
```

`package()` 中的 `_prune_non_libdvbv5()` 按 `libv4l` 前缀裁剪，
实测已剔除全部 libv4l 库与头文件：

- 库：`libv4l1.so*` / `libv4l2.so*` / `libv4lconvert.so*` / `libv4l2rds.so*` 及其
  `libv4l/` 插件目录 —— 已剔除（产物中零残留）
- `.pc`：`libv4l1.pc` / `libv4l2.pc` / `libv4lconvert.pc` / `libv4l2rds.pc` —— 已剔除，
  仅保留 `libdvbv5.pc`
- 头文件：`libv4l*.h` / `libv4l-plugin.h` / `libv4l1-videodev.h` 等 —— 已剔除，
  仅保留 `include/libdvbv5/`
- **仍保留**：`share/locale/*/LC_MESSAGES/v4l-utils.mo`（5 个语言目录各 1 个）。
  这是 v4l-utils 的 gettext 翻译目录，名称不以 `libv4l` 开头，故未被前缀规则覆盖。
  它不影响链接或头文件契约，属已知的微小残留。

## 5. 汇总

| 层次 | 结果 |
|---|---|
| 上游测试 | 0 用例（上游未注册） |
| L1 test_package | 19/19 PASSED |
| G0-G4 门禁 | 全 PASS |
| L0 | pass（all checks passed） |
| L1 | pass（test_package executed） |
| L2 | skip（无 bin/ 目录，纯库包） |
| L4 | pass（patches clean） |
| L5 | pass（lib/ has content） |
| W3 本地 CI | pass，pass rate 100% (1/1) |

## 6. 未覆盖范围

libdvbv5 的运行时 DVB 行为（前端调谐、解复用、服务扫描）需真实
`/dev/dvb/adapter*/frontend*` 设备与信号；本 worker 不具备条件，故不在
本次测试范围内。R40 对上述运行时路径的适配完整性仍需在合适硬件上人工确认。
