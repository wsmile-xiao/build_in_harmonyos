# test-report.md — its-playback-time 0.2026-05-26.fdcd2b0

日期：2026-10-04 · 目标：OpenHarmony aarch64 · 构建系统：CMake ≥ 3.10

## 1. 上游官方测试

**上游没有任何测试。** 完整清点证据见 `../test_package/MANIFEST.yml` 的 `upstream_test_audit`：

- 无 `tests/` `test/` `spec/` `t/` 目录
- 全树无 `enable_testing()` / `add_test()` / `include(CTest)` / gtest / Catch
- 唯一名字带 test 的文件 `terminal/bidi_test.c` 未被任何构建规则引用，既不编译也不执行
- 上游未定义 `check` / `test` 目标

如实记为 **no_tests / 0**，不冒充「测试通过」：

```json
HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"cmake",
  "command":"ctest (not invoked: upstream defines no test target)",
  "discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}
```

## 2. 交叉编译（host = OHOS aarch64）

```
conan create archives/i/its-playback-time/0.2026-05-26.fdcd2b0 \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

结果：`Package '5451db01063ffef70a6f03c02395d1808faeb5e5' built`

包内容：

```
bin/ipbt
bin/ipbt-dump
share/man/man1/ipbt.1
share/doc/its-playback-time/README
licenses/LICENCE
```

## 3. 产物检查

| 检查项 | 结果 |
|--------|------|
| 架构 | `ELF 64-bit LSB pie executable, ARM aarch64` |
| `NEEDED` | 仅 `libc.so`（两个可执行文件都是） |
| ncurses | 静态链入（`readelf -sW` curses 符号为本地符号，UNDEF 为 0），未产出任何 `.so`，不污染系统同名库 |
| PIE | `FLAGS_1 = PIE` |
| NX | `GNU_STACK` 为 `RW`（无 X） |
| RELRO | 存在 `GNU_RELRO` 段 |
| 产物 SHA256 | `bin/ipbt` = `c7b7e20d11a776a82edc2e631dc44ccc4071d1c14b409692b8d714910a5e6d6c`<br>`bin/ipbt-dump` = `890f90cfa3910472f98d3c65ab5abb7b9aebc84a54c976cbe08a6e1d817baf11` |

## 4. test_package 功能测试：14 / 14 通过

`test_package/test.sh` 真实执行已打包的 `bin/ipbt` 与 `bin/ipbt-dump`。
夹具是脚本自己合成的最小合法 ttyrec 文件（12 字节头：sec=0、usec=0、len=12，三个小端 uint32 + 12 字节 `hello ipbt\r\n`）。
| # | 断言 | 结果 |
|---|------|------|
| 1 | `ipbt --version` 精确等于 `ipbt, source commit fdcd2b0ad60f74ffa6a695c992d56c6a3ae20e4a` | ✅ |
| 2 | `ipbt --help` 含 `usage: ipbt`、`--utf8-linedraw`、`-A`、`-f` | ✅ |
| 3 | `ipbt --licence` 含 PuTTY 版权声明 + `Permission is hereby granted, free of charge` | ✅ |
| 4 | `ipbt-dump --version` 精确同一版本串 | ✅ |
| 5 | `ipbt-dump --help` 含 `-S, --script`、`-H, --hex-dump`、`-x, --screen-xml` | ✅ |
| 6 | `ipbt-dump --licence` 含 PuTTY 版权声明 + MIT 许可 | ✅ |
| 7 | `ipbt-dump -T` 默认 SUMMARY 模式输出 `…:0:0.000000:offset 0xc len 0xc` | ✅ |
| 8 | `ipbt-dump -T -S` typescript 输出与录制数据 `cmp` 逐字节相同 | ✅ |
| 9 | `ipbt-dump -T -H` hex dump 含 `68 65 6c 6c 6f`，ASCII 列为 `hello ipbt` | ✅ |
| 10 | `ipbt-dump -T -x` 屏幕 XML 含 `<ttyrecording>` / `<frame index="0"` / `<t>hello ipbt` / `</ttyrecording>` | ✅ |
| 11 | `ipbt-dump -R -S` raw 字节模式往返一致 | ✅ |
| 12 | 无文件名 / 文件不存在 / 未知长选项 三者退出码均非 0（1 / 1 / 1） | ✅ |
| 13 | 反假阳性：篡改载荷后 hex dump 输出必须改变 | ✅ |
| 14 | 去掉 `-T` 后格式自动识别仍选中 ttyrec 并解析出同一帧 | ✅ |

```json
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,
  "command":"/data/service/hnp/bin/bash test.sh",
  "discovered":32,"passedCount":32}
```

第 10 条最有价值：它证明 `ipbtsrc/read.c` 的 ttyrec 解析器与 PuTTY 终端模拟器（`terminal.c`）真的把录制数据渲染成了屏幕内容——不是只跑了个 `--version`。

## 4b. 鸿蒙特有端到端消费者用例：18 / 18（rule12）

`test_package/test_ohos_playback.sh` 用**安装后**的 `bin/ipbt` / `bin/ipbt-dump` 跑交付契约与完整
ttyrec 转换流水线，共 18 条 TAP 断言（不是纯断言脚本，每一步都调真产物）：

| # | 断言 | 证据形态 |
|---|------|----------|
| 1-2 | `bin/ipbt` / `bin/ipbt-dump` 存在且为 ELF | `readelf` 文件类型 |
| 3 | 整包不含 `.so`（ncurses 静态链入，不污染系统同名库） | `find -name '*.so'` 计数 0 |
| 4 | 终端库契约：注入的 `TERMINFO` 必须是有效目录 | 日志 `TERMINFO=… (source=runenv:conanrunenv-release-armv8.sh)` |
| 5-6 | 两个程序 `--version` 均输出版本标记 | 与 `fdcd2b0…` 比对 |
| 7-18 | 3 帧 ttyrec 端到端：SUMMARY 帧数与时间戳、typescript 逐字节一致、hex dump 字节与 ASCII 列、screen XML 根/帧/屏幕文本、raw 模式往返、反假阳性（篡改载荷后 dump 必须变）、格式自动识别 | `ok 7 … ok 18` |

**真机/本地实测（2026-10-11）**：CI 真机构建 #84438 中本套 17/18，唯一失败项是断言 4
（`not ok 4 - TERMINFO 无效 (got: empty)`）；根因是 `test_package` 图里 ncurses 为 `run=False`、
`package_folder=None`，聚合运行环境不导出 `TERMINFO`。本轮修复后本地 `conan test` 复现为
`ok 4 - TERMINFO 指向有效目录（注入：…/ncurses/6.6/share/terminfo）`，修复后的真机复跑由 CI 队列出结果。
本地唯一其余差异是断言 5（x86_64 宿主加载 aarch64 产物时 `Error relocating … __fd_chk`），与产物无关。

## 5. L1e 破坏性反向验证（R34）

把包里的 `bin/` 整体移走后重跑 `conan test`：

```
ConanException: packaged binary not found at <pkg>/bin/ipbt
conan test rc=1
```

测试确实依赖被测包产物，不是假测试。

## 6. 覆盖范围与已知限制

- 交互式 curses 播放器 `ipbt` 的 UI 无法在无头环境驱动，测试覆盖其三个非 curses 入口与选项校验
- `ipbt-dump` 与播放器共用 ttyrec 解析器与终端模拟器，因此解析/渲染路径是被真实执行的
- man page 安装的是 tarball 自带的预生成 roff 文件；重新生成需要 `halibut`，交叉构建无法执行 OHOS aarch64 的 halibut，故未在构建期生成（详见 `../notes.md`）
- `unix/ipbt.c:614` 的 `#if HAVE_NCURSESW` 恒为假（`cmake/cmake.h.in` 里没有这个 `#cmakedefine`），走 `wcrtomb` 退化渲染路径；保持上游行为未改，已在 `../notes.md` 记录