# libdvbv5 1.32.0 上游测试处理报告

日期：2026-09-22
设备：OHOS aarch64 worker（本机）
源码：v4l-utils-1.32.0.tar.xz（sha256 6828828a17775526eb93fb258a9294d1d1073d633c344dd71ecd4e7a1ffb7dfc）

## 一、上游测试入口核验（R51 第一步：清点）

libdvbv5 是 v4l-utils 源码树中的 `lib/libdvbv5` 子库，随 v4l-utils 整体发布。

清点命令与原始输出：

```
$ cd v4l-utils-1.32.0.work
$ grep -rn "^\s*test(" --include="meson.build" . | wc -l
0
$ grep -rn "^\s*test(" --include="meson.build" .
(无输出)
```

配置并构建后，Meson 侧的权威判定：

```
$ meson test -C build --list
No tests defined.
```

**结论：上游没有为 libdvbv5（乃至本构建范围内的任何目标）注册自动化测试。
Meson `test()` 注册数 = 0。**

## 二、真实测试入口（存在但不是自动化测试）

全树检索 `*test*` 共 58 个文件，逐项归属如下：

| 资产 | 位置 | 是否覆盖 libdvbv5 | 可否在 worker 执行 |
|---|---|---|---|
| `dvb-format-convert.c` | `utils/dvb/` | **是**（唯一不依赖硬件的 libdvbv5 消费者） | 否——依赖 `argp`，OHOS/musl 无 argp |
| `dvb-fe-tool.c` / `dvbv5-scan.c` / `dvbv5-zap.c` | `utils/dvb/` | 是 | 否——需真实 DVB 前端 `/dev/dvb/adapterN/frontend0` |
| `utils/edid-decode/test/*.test`（24 个） | `utils/edid-decode/` | 否（属 edid-decode 工具） | 本包不构建该工具 |
| `utils/v4l2-compliance/*` | `utils/` | 否 | 需 `/dev/video*`、`/dev/media*`、内核模块 |
| `utils/cec-compliance/*` | `utils/` | 否 | 需 CEC 设备与 root |
| `contrib/test/*`（`executable()` 声明 11 个） | `contrib/` | 否（V4L2 设备测试） | 需视频设备 |

`meson test --list` 为空的直接原因：上游把 `contrib/test/meson.build` 里的
11 个可执行文件用 `executable()` 声明（无条件 8 个：`ioctl-test`、
`sliced-vbi-test`、`sliced-vbi-detect`、`v4l2grab`、`driver-test`、
`mc-nextgen-test`、`stress-buffer`、`capture-example`；条件 3 个：
`pixfmt-test`（`dep_x11`）、`v4l2gl`（`dep_gl` + `dep_glu` + `dep_x11`）、
`sdlcam`（`dep_jpeg` + `dep_sdl` + `dep_sdl_image`）），但**没有任何 `test()` 注册**，
所以它们永远不会被 `meson test` 驱动。

此外 `contrib/test` 还受两重条件约束：顶层 `meson.build` 的
`if get_option('v4l-utils')` 才 `subdir('contrib')`，而 `v4l-utils` 是
`type : 'boolean'` 且未声明 `value`（Meson boolean 默认 `false`）；
`contrib/meson.build` 内又要求 `host_machine.system() == 'linux'`。
本配方显式设 `-Dv4l-utils=false` 且 host 为 `harmonyos`，因此这些可执行文件
在本次构建中**根本不会被构建**。

## 三、实际执行情况

### 3.1 已执行的等价测试路径

`dvb-format-convert` 的 `convert_file()` 只调用两个 libdvbv5 公共 API：

```c
dvb_file = dvb_read_file_format(args->input_file, args->delsys, ...);
ret = dvb_write_file_format(args->output_file, dvb_file, ...);
```

该代码路径已在本机通过 `test_package/test_libdvbv5.c` 的
`test_channel_roundtrip` **实际执行并断言**（同一对 API、同样的
channel → DVBv5 格式转换）。

执行记录：

```
命令:  ./test_libdvbv5
日志:  /storage/Users/currentUser/tmp/dvbtest-run/logs/roundtrip.log
退出码: 0
输出:
  parsed_entries=3
  write_ok
  roundtrip_ok
```

输入 fixture（legacy channel 格式，3 条 DVB-T 频道）：

```
T 578000000 8MHz 2/3 1/2 QAM64 8k 1/8 NONE
T 666000000 8MHz 3/4 2/3 QAM64 8k 1/4 NONE
T 754000000 7MHz 1/2 NONE QPSK  2k 1/32 NONE
```

输出（DVBv5 原生格式，节选，值均正确解码）：

```
[CHANNEL]
	DELIVERY_SYSTEM = DVBT
	FREQUENCY = 578000000
	BANDWIDTH_HZ = 8000000
	CODE_RATE_HP = 2/3
	MODULATION = QAM/64
	TRANSMISSION_MODE = 8K
	GUARD_INTERVAL = 1/8
	HIERARCHY = NONE
```

### 3.2 统计口径

| 项目 | 数值 |
|---|---|
| 上游注册的自动化用例总数 | **0** |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |
| 用例名称 | 无（`meson test --list` → `No tests defined.`） |
| 日志路径 | `reports/upstream-test.log`（清点证据） |

`test_package` 的 19 项断言属于消费者测试（L1），**不计入**上游用例统计，
仅用于证明产物可被消费者正确使用。

## 四、不可执行项与具体技术原因

| 测试入口 | 不可执行的具体技术原因 |
|---|---|
| `dvb-format-convert` | 源文件 `#include <argp.h>` 并调用 `argp_parse`/`argp_help`/`argp_state_help`。OHOS sysroot **无 `argp.h`、无 `libargp`、libc 无 `argp_parse` 符号**（实测 `clang t.c -largp` → `ld.lld: error: unable to find library -largp`）。补齐需要自研完整 argp 兼容层，已超出库适配范围。 |
| `dvb-fe-tool` | 需 `/dev/dvb/adapterN/frontend0` 真实前端设备 |
| `dvbv5-scan` / `dvbv5-zap` | 需 DVB 前端 + 解复用设备，且需实际调谐信号 |
| `v4l2-compliance` | 需 `/dev/video*`、`/dev/media*` 与 root 级内核模块控制 |
| `test-media` | 需 `modprobe`、`udevadm`、可写 `/dev/kmsg`，worker 均缺失 |
| `edid-decode` 语料 | 属 `edid-decode` 工具，本包不构建该工具，与 libdvbv5 无关联 |

## 五、结论

- 上游为 libdvbv5 **没有自动化测试**，清点证据为
  `meson test --list` → `No tests defined.` 与全树 `test(` 注册数 = 0。
- 唯一覆盖 libdvbv5 的非设备测试入口是 `dvb-format-convert`，其 libdvbv5
  代码路径已用等价消费者测试实际执行并全部通过（3/3 频道往返）。
- 其余入口均绑定 V4L2/DVB 硬件或内核模块，本 worker 不具备条件，已逐项
  给出具体技术原因。
- 本次适配另新增 1 项**鸿蒙特有测试**（`test_ohos_packaging`），见
  `notes.md` 与 `test_package/MANIFEST.yml`。
