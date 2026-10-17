# mkcue 1.0 — 上游样例（README 用法）实际执行报告

- 日期：2026-09-29
- 被测二进制：`<package_folder>/bin/mkcue`（OHOS aarch64 ELF，由 `conan create` 产出；
  包路径 `/storage/Users/currentUser/.conan2/p/b/mkcuefb2e8738d17cc/p/bin/mkcue`）
- 执行方式：**在本机（HarmonyOS / aarch64）原生运行**打包后的二进制
- 原始日志：`archives/m/mkcue/1.0/test_package/build-release/mkcue-cases.log`
  （`conan create` 的 test_package 阶段产出；同内容另存 `.task-logs/11-test-package-local.log`）

上游没有测试套件，唯一可执行的上游"样例"来自 `README:7-10` 的用法说明：

```
Usage is quite simple.  By default, list all tracks from /dev/cdrom in
the cue sheet.  An optional device argument overrides /dev/cdrom.  The
-t track-count option only lists up to track-count tracks in the cue
sheet, which is handy for CDs with data tracks you want to ignore.
```

## 用例统计（上游样例）

| 指标 | 值 |
|------|-----|
| 用例总数 | **6** |
| 通过 | **6** |
| 失败 | **0** |
| 跳过 | **0** |
| 不可测（需真实光驱的 happy path） | 1（如实记录，不计入通过） |

## 逐项用例

| # | 用例名称 | 命令 | 期望 | 实测输出 | 退出码 | 结果 |
|---|----------|------|------|----------|--------|------|
| 1 | `upstream-default-device-open-error` | `mkcue` | 默认设备 `/dev/cdrom` 打不开 | `Cannot open '/dev/cdrom'` | 2 | PASS |
| 2 | `upstream-explicit-device-open-error` | `mkcue /nonexistent-device` | 显式设备参数生效 | `Cannot open '/nonexistent-device'` | 2 | PASS |
| 3 | `upstream-trackcount-zero-rejected` | `mkcue -t 0` | `-t` 下界校验（<1） | `invalid track-count 0` | 2 | PASS |
| 4 | `upstream-trackcount-over-99-rejected` | `mkcue -t 100` | `-t` 上界校验（>99） | `invalid track-count 100` | 2 | PASS |
| 5 | `upstream-trackcount-one-accepted` | `mkcue -t 1 /nonexistent-device` | `-t 1` 合法（不报 invalid），设备仍打不开 | `Cannot open '/nonexistent-device'`（**无** `invalid track-count`） | 2 | PASS |
| 6 | `upstream-unknown-option-usage` | `mkcue -x` | 未知选项打印用法行 | `mkcue [-t track-count] [device]` | 2 | PASS |

## 不可测项（如实记录，未伪装为通过）

| 项 | 原因 |
|----|------|
| TOC 读取 happy path（列出真实音轨并输出 TRACK/INDEX 行） | 需要真实 CD 设备与 `CDROMREADTOCHDR` / `CDROMMULTISESSION` / `CDROMREADTOCENTRY` ioctl；本机与 CI 均无光驱。已确认这些 ioctl 的编译依赖（`<linux/cdrom.h>`）在 OHOS sysroot 中存在且编译通过，但运行时行为无法在无硬件环境验证。 |

## 原始日志摘录

```
$ mkcue
Cannot open '/dev/cdrom'
exit=2

$ mkcue /nonexistent-device
Cannot open '/nonexistent-device'
exit=2

$ mkcue -t 0
invalid track-count 0
exit=2

$ mkcue -t 100
invalid track-count 100
exit=2

$ mkcue -t 1 /nonexistent-device
Cannot open '/nonexistent-device'
exit=2

$ mkcue -x
mkcue: unrecognized option: x
mkcue [-t track-count] [device]
exit=2
```
