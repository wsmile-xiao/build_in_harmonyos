# smem 1.5 适配笔记

## 编译环境

- 构建系统：无（1.5 tag 不带 Makefile/CMake/configure，`smemcap.c` 由配方直接编译）
- 编译日期：2026-10-03
- 编译器：OHOS clang 15（`/opt/lpk-fixed/clang` → `clang-15 --target=aarch64-linux-ohos`；CI 上是 `/data/service/hnp/bin/clang`）
- Profile：`ohos-aarch64-wsl`（os=OHOS / arch=armv8 / clang 15 / libc++ / Release），本地为 x86_64 runner
- 依赖：无（0 requires，0 tool_requires）
- 状态：built（`conan create` + 本地同源门禁全绿，产物待 CI release 上传）

## 源码

- 上游：<https://www.selenic.com/smem/>（Matt Mackall 的 Mercurial 仓库，项目官网）
- 钉住 changeset `98273ce331bb`：这是被打上 **1.5** 标签的 changeset（`.hgtags` 里最后一条是 1.4 = `e143c8fdb6f5`，该 changeset 在其后补上 1.5 标签）
- sha256 `161131c686a6d9962a0e96912526dd46308e022d62e3f8acaed5a56fda8e08ce`
- 交叉验证：OpenEmbedded `meta-oe/recipes-support/smem/smem_1.5.bb` 用同一个 changeset 与同一个 sha256；Debian 1.5-1 / Gentoo `dev-util/smem-1.5` / nixpkgs 均取 1.5
- 交付内容（未裁剪）：`smem`（733 行 Python 3 报告前端）+ `smemcap.c`（114 行 C 采集助手）+ `smem.8` 手册 + `COPYING`（GPL-2）

## 编译步骤

```python
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = compilers.get("c")          # R33：不读裸 ${CC}
self.run(f"{cc} -O2 smemcap.c -o smemcap", cwd=self.source_folder)
```

`smem` 是纯脚本，不编译，按原样装进 `bin/`（补丁 0001 改 shebang）。`package()` 用 `os.chmod` 把
`bin/smem`、`bin/smemcap` 恢复成 0755 —— Conan 的 `copy()` 不接受 `chmod=` 参数（2.29.1），
且复制时会归一化模式。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `smem -S <tar>` 在 python3 下必崩：`File "smem", line 193, in memory / m = f.match(l) / TypeError: cannot use a string pattern on a bytes-like object` | 上游 1.5 的 Python 3 移植只做了一半：`tardata._read()/_readlines()` 直接返回 `tarfile` 的 `bytes`，而消费方全按 `str` 写。python3.10 实测三个受害点，**一个抛栈、两个静默**：① `memory()`(smem:193) 抛 `TypeError: cannot use a string pattern on a bytes-like object`（唯一会冒泡的，路径 `showtable → totalmem → memory()`）；② `pidmaps()`(smem:147) 的 `'-' in f[0]` 抛 `TypeError: a bytes-like object is required, not 'str'`，被 `processtotals()` 的裸 `except:` 吞掉 → 进程表整表为空；③ `pidcmd()`(smem:50) 的 `bytes.replace('\0',' ')` 抛同一 TypeError，被同函数裸 `except:` 吞掉 → 进程名/命令行退化成 `'?'`。另注 `f[-1] == 'kB'` 对 `bytes` 恒 False，故 PSS/RSS 列本就永远填不上 | 补丁 0001 在 `tardata` 的 I/O 边界集中解码（新增 `_decode()`，`_readlines()` 改为从 `_read()` 派生），一处修好三个调用点。实测：同一份合成归档，pristine rc=1（`smem:193` TypeError），打补丁后 rc=0 并正确输出 `1000 18 / 1001 8` |
| 2 | `smem --bar=pss` 在 python3 下 `NameError: name 'xrange' is not defined` | `showbar()` 用了 python2 的 `xrange()` | 补丁 0001 改 `range()`（`--pie/--bar` 需要 matplotlib，本身是可选功能） |
| 3 | shebang 是 `#!/usr/bin/env python` | 1.5 只支持 python3（Debian 1.5-1 "Switch to python3"、Gentoo、OE 均如此），但 shebang 未同步；多数发行版的 `python` 是 python2，部分系统根本没有 | 补丁 0001 改 `python3` |
| 4 | `conan create` 报 `TypeError: copy() got an unexpected keyword argument 'chmod'` | 本仓 OHOS 适配版 conan 2.29.1 的 `tools.files.copy()` 没有 `chmod` 形参 | 改为 `copy()` 后显式 `os.chmod(..., 0o755)`（只对两个可执行文件，man/许可证保持 0644） |
| 5 | `TypeError: conan.tools.files.files.get() got multiple values for keyword argument 'strip_root'` | `conandata.yml` 里写了 `strip_root: true`，配方又传了 `strip_root=True` | 从 conandata.yml 移除该键，只保留配方里的 `strip_root=True` |
| 6 | 测试里自制的"smemcap 同款归档"被 `tarfile` 判 `invalid header` | 两个字节级 bug：① 校验和误写成 `sum % 4096`（smemcap 是 `sprintf("%06o", sum)`，不取模）；② **Python `bytearray` 切片赋值长度不足会整体左移**——`hdr[124:136] = 11 字节` 把 12 字节字段压成 11 字节，其后所有字段（含 156 处的 typeflag）整体前移 1 位 | ① 去掉取模；② 所有字段写入统一走 `put(offset, width, value)`，内部 `ljust(width)[:width]` 补齐；并加 `assert len(header) == 512` 自检 |
| 7 | 期望 `smem -u` 输出用户名（`tester`/`root`），实测是数字 uid | **smemcap 只写数字 uid/gid，从不写 tar 头的 uname/gname（265/297 偏移恒为 0）**；`tardata.piduser()` 只在 `t.uname` 非空时填 `_ucache`，所以 `--source` 路径永远回落成 `str(uid)`。直读 `/proc` 时才会走 `pwd.getpwuid()` 出用户名 | 实采一份真 smemcap 归档确认 `uname=''` 后，把期望改成数字 uid，并在注释与 MANIFEST 里写明这条上游行为差异 |
| 8 | `-c` 列解析按空格切分导致列错位 | smem 每列定宽，`command`（`/usr/bin/thing --serve`）、`map`、`area`（`kernel dynamic memory`）本身含空格 | 测试改为"从行尾取固定个数的数值列 + 行首按 key 索引"，含空格的字段另用两列窄表单独校验 |

`patches/` 无 `__OHOS__` 等平台宏；配方也未注入任何平台宏（补丁 0001 是纯 Python 3 语义修正，所有平台通用）。

## 源码修改

| 补丁 | 文件 | 修改 |
|---|---|---|
| 0001 | `smem` | shebang `python`→`python3`；`tardata` 新增 `_decode()`，`_read()`/`_readlines()` 解码为 str；`showbar()` 的 `xrange`→`range` |

## 上游测试清点（R51）

- 1.5 tag 共 6 个文件（`tar tvjf` 实测）：`.hg_archival.txt`、`.hgtags`、`COPYING`、`smem`、`smem.8`、`smemcap.c`，**无 `test/` 或 `tests/` 目录**
- 无 Makefile（也就没有 `make check`）；无 CMake / automake / pytest 配置，ctest/TESTS 注册数均为 0
- 结论：**上游无自动化测试，N = 0、N缺 = 0**；功能覆盖全部由 `test_package/` 补齐

## 验证结果

### 1. `conan create`（W3，x86_64 runner，profile `ohos-aarch64-wsl`）

```
smem/1.5: Package '6b129b068851896169fae42d399fa922d239ce8a' built
smem/1.5: package(): Packaged 3 files: COPYING, smem, smemcap
smem/1.5: package(): Packaged 1 '.8' file: smem.8
smem/1.5 (test package): Running test()
...
104 checks passed, 0 failed
ALL SMEM CONSUMER TESTS PASSED
```

`test_package` 断言数：**110**（104 条恒执行 + 6 条只在 AArch64 构建机上执行的实机采集校验）。

### 2. 断言分组（`test_package/test_smem.py`）

| 组 | 内容 | 断言数 |
|---|---|---|
| A 产物 / OHOS 目标 | 两程序存在 + 可执行位；`smem` shebang = `/usr/bin/env python3`；脚本可被 python3 `compile()`；man/许可证到位；`--help` rc=0 且列出上报选项；`smemcap` 是 ELF64、`e_machine=183`(EM_AARCH64)、`PT_INTERP` 为 AArch64 平台加载器 | 14 |
| B 合成采集归档上报 | 自制归档（与 smemcap 同字节布局）经独立 reader 校验 → 进程表 10 列 × 2 进程 / command 含空格 / `-t` 合计 / `-k` / `-p -R` / `-P` / `-s -r` / `-H` / `-m` 4 行 × 7 列 / `-M` / `-u` 2 行 × 5 列 / `-w` 5 行 × 3 列 / 三条错误路径 | 90 |
| C 实机采集（仅 AArch64 构建机） | `smemcap` 原生跑真实 `/proc` → 归档结构独立校验（成员数 / `meminfo` / 每 pid `smaps` / MemTotal 正则）→ `smem -S` 回读 | 6 |

### 3. 交付的 aarch64 产物本地实跑（qemu-aarch64，macutils 同款取证法）

交付件是动态链接 OHOS AArch64 ELF（PIE、`NEEDED libc.so`、`PT_INTERP` 为 AArch64 平台加载器），
x86_64 本机没有对应加载器，跑不起来。**本地实测到的 `PT_INTERP` 是 `/lib/ld-linux-aarch64.so.1`**
（本地 sysroot `/mnt/c/Users/13909/ohos-sysroot` 的命名）；CI worker 用 SDK 自带的
`/data/service/hnp/bin/clang` 与 OHOS sysroot，预期会给出 `/lib/ld-musl-aarch64.so.1`。
因此测试只断言"加载器路径里含 aarch64"而不写死具体文件名。
按既有先例做法：**用同一 OHOS clang 把同一份 `smemcap.c` 静态重链一份副本，在 qemu-aarch64 下实跑**
（静态副本 ≠ 交付产物，仅证明 C 侧逻辑与归档格式正确）：

```
$ /opt/lpk-fixed/clang -O2 -static smemcap.c -o smemcap_static
$ qemu-aarch64 ./smemcap_static > live.tar
exit=0   archive=4471296 bytes   members=262   smaps entries=65   MemTotal=32755400 kB
$ python3 <pkg>/bin/smem -S live.tar -c "pid pss"
  PID      PSS
15359       87
...
$ python3 <pkg>/bin/smem -S live.tar -w
Area                           Used      Cache   Noncache
firmware/hardware                 0          0          0
kernel image                      0          0          0
kernel dynamic memory      26219304   25086716    1132588
userspace memory         1353892     492380     861512
free memory               5182204    5182204          0
```

**说明**：qemu 跑的是同一 `smemcap.c` 的静态重链副本，**不等于交付的动态产物已实跑**；交付产物由
CI 的 AArch64 OHOS worker 在 `test_package` C 组里原生执行（`platform.machine()` 为 aarch64 时启用）。

### 4. 本地 CI 同源门禁（`ci/conan/build_and_test.sh`）

见交付摘要：G0 / L0 / KC / JC / L1（含 L1e 反向破坏）/ L2 / L4 / L5 全绿。

## 用例统计

| 类别 | 数量 |
|---|---|
| 上游测试 N / N缺 | 0 / 0（上游无测试） |
| test_package 用例 | 110（恒执行 104 + AArch64 实机 6） |
| 鸿蒙特有测试 | 3（ELF 目标断言 / python3 shebang+compile 断言 / AArch64 worker 原生实机采集回读） |

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/smem` | 报告前端（Python 3 脚本，GPL-2） |
| `bin/smemcap` | `/proc` 采集助手（C，AArch64 OHOS 动态链接） |
| `share/man/man8/smem.8` | 上游手册 |
| `licenses/COPYING` | 上游 GPL-2 全文 |
| `archives/s/smem/commands.json` | hicmd 命令行工具声明（R38） |

## 注意事项

- 上游 `/proc/<pid>/smaps` 若不可读（OHOS 内核未开 `CONFIG_PROC_PAGE_MONITOR` 或沙箱拒绝），
  `smemcap` 不会崩：`open()` 失败后 `fstat()` 失败、size 记 0，仍写出一个零长度归档条目，
  `smem` 侧 `pidmaps()` 得到空 maps 后该 pid 被跳过。因此实机上报行数取决于平台是否提供 smaps，
  测试对此**不做行数断言**，只断言归档结构与字段可解析。
- 同一上游版本若需再修适配问题，版本号走 `1.5.N`（R37，制品仓不支持同版本多 revision）。
- `--pie` / `--bar` 需要 matplotlib，属上游可选依赖，不在交付依赖内，也不在自动化用例内。