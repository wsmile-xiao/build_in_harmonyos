# playumidi 0.8.3 适配笔记

## 编译环境
- 构建系统: **makefile（BSD make 原件 → GNU make 适配）**
- 编译日期: 2026-10-01
- 编译器: clang 15.0.4（target `aarch64-unknown-linux-ohos`）
- 平台: OpenHarmony PC (aarch64, musl)
- 状态: built

## 源码与上游核验

### 上游身份
- 上游工程：**OSDN 项目 playumidi**（作者 Koine Yuusuke / koinec），
  `https://osdn.net/projects/playumidi/`
- 版本 0.8.3（`src/playumidi.h`: `"Version 0.8.3 (2020/08/23)"`）
- 打包参照：FreeBSD ports `audio/playumidi`（PORTVERSION=0.8.3, PORTREVISION=1）

### 源码获取（R39 说明）
实测证据（`logs/source_probe.log`）：

```
$ curl -sS https://ja.osdn.net/projects/playumidi/                 -> rc=6  Could not resolve host
$ curl -sS https://osdn.net/projects/playumidi/                    -> rc=6  Could not resolve host
$ curl -sS https://distcache.FreeBSD.org/ports-distfiles/...tar.gz -> rc=28 Connection timed out (Fastly 段不可达)
$ curl -sSLk https://distcache.us-east.FreeBSD.org/ports-distfiles/playumidi-0.8.3.tar.gz
  -> 200, size=22160   （区域站点 TLS 证书为 *.freebsd.org 通配、不覆盖二级子域，需放宽校验）
$ sha256sum playumidi-0.8.3.tar.gz
  518e6cefc77d057ab7a802041c4d250a208f93d1bd054fed42a76d6a387dfb1e   <= 与 FreeBSD ports distinfo 完全一致
  SIZE(22160) 亦一致
```

结论：OSDN 已停止服务，源码实体取自 **FreeBSD 官方 distcache**（FreeBSD Project
基础设施，缓存的就是上游原始 tarball）。sha256 与权威打包元数据逐字节一致，
可确认是上游原件、非二次打包。

### 上游测试入口核验（**上游无自动化测试**）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 测试目录 | `tar tzvf playumidi-0.8.3.tar.gz` | 无 `tests/`、无 `test/`（仅 src/ man/ 与文档） |
| test target | `grep -nE "^(test\|check\|regress):" Makefile src/Makefile` | 无匹配（仅 `all/install/deinstall/clean`） |
| 测试样例 | tar 清单 | 无任何 `.mid` 样例文件 |

因此上游**不存在自动化测试框架**。但上游代码内建了真实的自校验通道：
`-DWITH_DEBUG` 会同时启用 `-DWITH_VERIFY`，编译进 `src/verify_event.c`，在
`read_smf.c:750` 调用 `Veryfy_Event()` 逐事件比对“解析出的事件流”与“源文件原始字节”
（DeltaTime / 3Byte / 2Byte / SysEx(F0) / SysEx(F7) / Meta 六类），失败即返回非 0。

## 编译步骤

```bash
# 1) 解包（init-build 完成）源码位于 $BUILD_SRC_DIR
# 2) 应用补丁（3 个，见下）
# 3) 构建
make CC=clang -j1
#    -> src/*.o + src/playumidi -> 顶层 ./playumidi + ./playumidi.1.gz
# 4) 安装到 staging
make install DESTDIR=$TEST_PREFIX prefix=/usr/local
```

## 遇到的问题与解决方案（按真实发生顺序）

| # | 首个错误（原始输出） | 根因 | 修复 |
|---|---|---|---|
| 1 | `Makefile:40: *** missing separator.  Stop.`（exit=2） | 上游 Makefile 是 **BSD make** 语法（`.ifdef`/`.else`/`.endif`），OHOS 只有 GNU make 4.4.1，GNU make 把 `.ifdef` 当普通文本行 | `patches/0001,0002`：改写为 `ifdef/else/endif` |
| 2 | 递归子 make 打印 `Usage: make [options] ...`，`make: *** [Makefile:72: playumidi] Error 2` | 上游用 BSD make 的变量定义选项 `-DWITH_DEBUG`/`-DWITH_ICONV`，GNU make 中 `-D` 是未定义选项 | `patches/0001`：`BUILD_FLAGS += WITH_DEBUG=1 WITH_VERIFY=1`（命令行变量传递） |
| 3 | `src/midi_device.c:64: error: no member named 'd_namlen' in 'struct dirent'` | `d_namlen` 为 BSD/FreeBSD 专有 dirent 成员，musl 未提供 | `patches/0003`：`i_len == (int)strlen( p_dent->d_name )`（语义等价，**未使用平台宏**） |
| 4 | `make: install: No such file or directory`（exit=2，`Error 127`） | OHOS 无 `install(1)` 可执行文件 | `patches/0001`：install 目标改为 `mkdir -p` + `cp -f` + `chmod` |

## 源码修改（补丁，均为无条件可移植性改写，无平台宏）

| 补丁 | 内容 | 规模 |
|---|---|---|
| `0001-Makefile.patch` | BSD→GNU make 条件语法；新增 `prefix`/`DESTDIR`；install 用 mkdir+cp+chmod | +16/-11 |
| `0002-src-Makefile.patch` | BSD→GNU make 条件语法（WITH_VERIFY / WITH_ICONV / WITH_DEBUG） | +7/-7 |
| `0003-src-midi_device.c.patch` | `d_namlen` → `strlen(d_name)` | +1/-1 |

> R8 合规：三个补丁**均未引入 `__OHOS__` 等平台宏**，为通用可移植性改写。

## 依赖版本
- **强制第三方依赖：无**
- 可选：libiconv（`WITH_ICONV`，编码转换），上游默认关闭，且其 Makefile 将
  `-I/usr/local/include -L/usr/local/lib` 硬编码，本配方未启用，故不 require。
  （W0 已核验 `libiconv/1.17` 在 ohpcd 制品仓可消费：recipe rc=0、binary rc=0）
- 系统：libc(musl)、pthread（`-lpthread`，musl 下为 libc 内提供，实测可链接）

## 验证结果

### 上游测试入口实际执行（真实运行，非占位）

测试命令：`bash run_upstream_tests.sh`（脚本见证据目录）
日志目录：`playumidi-0.8.3-evidence/logs/upstream-*.log`

| 用例 | 名称 | 命令 | 结果 | 日志 |
|---|---|---|---|---|
| T1 | help/usage | `playumidi -h` | PASS (rc=0, 含 usage) | upstream-T1.log |
| T2 | no-arg usage | `playumidi` | PASS (rc=1, 含 usage) | upstream-T2.log |
| T3 | format0 解析+播放 | `playumidi -0 null t_format0.mid` | PASS (Title 读出) | upstream-T3.log |
| T4 | format1 多轨 | `playumidi -0 null t_format1.mid` | PASS (3 轨 Title) | upstream-T4.log |
| T5 | SysEx/Meta | `playumidi -0 null t_sysex.mid` | PASS (Text 事件读出) | upstream-T5.log |
| T6 | verbose | `playumidi -v -0 null t_format0.mid` | PASS (Format/Tempo/Rhythm) | upstream-T6.log |
| T7 | 文件不存在 | `playumidi -0 null does_not_exist.mid` | PASS (`Can't get MIDI filesize`) | upstream-T7.log |
| **HM1** | **鸿蒙特有：设备发现链被真实执行**（`opendir("/dev")`+`strlen(d_name)` 适配点） | `playumidi -0 null t_format0.mid`；断言 `Can't Open MidiDevice (Device=umidi15.0 Port=1)`——该串出现即证明设备发现遍历执行完毕 | PASS | upstream-HM1.log |
| **HM2** | **鸿蒙特有：无 /dev/umidi\* 设备处理** | `playumidi t_format0.mid`；断言 `Can't Open RawMidi Device` | PASS | upstream-HM2.log |
| T9 | 上游 verify 自校验（format0/1/sysex） | `playumidi(-DWITH_VERIFY) -r -0 null <mid>` | **3/3 PASS**（`Verify MidiEvent is Completed!!`） | upstream-T9-*.log |

**统计：用例总数 12，通过 12，失败 0，跳过 0**（release 9 + verify 3）。
样例文件由 `gen_midi.py` 按 SMF 规范生成（上游未提供样例）。

> T9 必须加 `-r`：默认行为会在首个 MIDI 事件前**自动追加 GM/XG/GS RESET**，
> 该合成事件不在源文件中，verify 会据实报 `Fail Verify MidiEvent -- SysEx(F0)`。

### 构建产物

```
$ file playumidi
playumidi: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -d playumidi | grep NEEDED
 (NEEDED)  Shared library: [libc.so]
```

### test_package
`conan create` 自动执行 `test_package/test.sh`（3 项断言：usage / OHOS 无设备行为 /
SMF 解析+播放），日志 `test-package.log`。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/playumidi` | 命令行可执行文件 |
| `share/man/man1/playumidi.1.gz` | 手册页 |
| `licenses/LICENSE` | 2-clause BSD |

## 注意事项

### CI 首次失败与修复（2026-10-01，PR !14131）

CI 构建 #66143 / #66146 两次均在 `checkout-pr` 步骤失败，真实日志：

```
error: missing binary patch data for 'archives/p/playumidi/0.8.3/test_package/t_min.mid'
error: binary patch does not apply to 'archives/p/playumidi/0.8.3/test_package/t_min.mid'
patch: Unknown option 'fuzz=3'      # OHOS toybox patch 不支持 --fuzz 回退
[ERROR] PR 14131 diff 无法应用——PR 与 main 分支存在冲突
```

**根因**：`test_package/t_min.mid` 是二进制文件，平台的 `pull/<N>.diff` 端点**不携带
二进制 patch 数据**，`git apply --3way` 与 `patch -p1` 回退均无法应用 → CI 在
`checkout-pr` 阶段即失败（尚**未**进入构建/AI 审核）。

**修复**：删除二进制 `t_min.mid`，改为在 `test_package/test.sh` 中以**文本转义序列内联生成**
（71 字节，format 0），输出到 `$TMPDIR/playumidi-test/`，仓库内不再保留任何二进制文件。
已验证内联生成结果与原文件 `cmp` 逐字节一致
（sha256 `291bd41602d708581ddbb3e1a784f648b342e31f8ed3931c640ee852be9e49b6`）。

> 经验（已沉淀至 `knowledge/drafts/E429/E430` 之外的一般性结论）：
> **PR 中不得包含二进制文件** —— 平台 diff 端点不支持二进制 patch，CI 会在 checkout 阶段失败。

- 本工具的设备控制层面向 **FreeBSD 专有 `/dev/umidi*.*`**；OHOS 无该设备节点，
  默认调用会以 `Can't Open RawMidi Device ... Exit.` 结束，这是**无设备时的预期行为**。
  平台无关部分（SMF 解析、事件生成、时序）已通过 T3–T9 实测。
- 设备发现路径 `MidiDevice_IsExistUMidiDevice()` 在 OHOS 上因 `/dev` 只读且无匹配
  节点而恒返回 0，但该函数已被 HM1 用例实际执行（`-0 null` 时端口 1..3 走搜索分支）。
---

**编译结束**: 2026-10-01 14:40
**最终状态**: built
