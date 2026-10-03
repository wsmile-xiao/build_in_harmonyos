# sexpect 2.4.0 适配笔记

## 状态

- 平台任务: #10515「sexpect 2.4.0」；分支: `feat/sexpect-2.4.0`；适配路径: 路径 A + B（知识库扩展）
- 当前状态: `conan-verify` G0–G4/L2/L4/L5 全 PASS（干净 `conan create` 内上游 CTest 25/25、
  消费者测试 10/10）；W3 本地 CI 与 W4 审计进行中

## 编译环境

- 构建系统: CMake（`cmake_minimum_required(VERSION 3.17)`；`project(sexpect C)`）
- 编译日期: 2026-09-26
- 编译器: OHOS SDK clang 15.0.4（`$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang`）
- 目标: aarch64-linux-ohos（设备本机编译），Conan profile `ohos-aarch64` / 验证用 `ohos-aarch64-device`
- 依赖: 无（纯 C + POSIX；`build.dependencies: []`）

## W0 依赖检查

- `conanfile.py` 无 requires；构建与测试仅需 C 编译器、CMake 与 bash。
- 设备实测（2026-09-26）：
  - `conan download sexpect/2.4.0 -r=ohpcd --only-recipe` → `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`（制品仓无此包）
  - `conan list "sexpect/*" -r=ohpcd` → `Found 0 pkg/version recipes matching sexpect/* in ohpcd`（确认未发布，可正常适配）
- bash 可用性: `/storage/Users/currentUser/.harmonybrew/bin/bash`（GNU bash 5.3.9，上游测试脚本全部 `#!/bin/bash`）

## 源码与构建分析

- 官方源码: <https://codeload.github.com/clarkwang/sexpect/tar.gz/refs/tags/v2.4.0>
  （GitHub 官方 tar 入口，即 `github.com/clarkwang/sexpect/archive/refs/tags/v2.4.0.tar.gz`
  的官方 302 目标；两者字节一致，jattach 2.2 先例、仓库内多个既有配方同源）
- SHA256: `8f7a989ecf67f4ff6eb167d29a8e2e54db85143ebf3e8f904ea16ee5576a4b0d`（设备重下核对一致）
- 许可证: GPL-3.0；语言: C（`project(sexpect C)`，`-std` 未指定，clang 默认 gnu17）
- 架构: client/server —— `spawn` 起 server（守护进程，持 pty master，在 sockfile 上 `bind` 路径 socket），
  `send/expect/interact/wait/get/close/kill/set` 为短命 client，经 AF_UNIX 流套接字通信
- PTY 实现: `pty.c` 用 `posix_openpt/grantpt/unlockpt/ptsname` + `setsid` + `open(slave)` +
  `TIOCSCTTY`/`TIOCSWINSZ`；`server.c` 对 ptm 做 `select`/非阻塞读，处理 pts 关闭后的 `EIO`
- 上游测试: `tests/` 共 32 个文件；`tests/CMakeLists.txt` 通过 `add_test()` 注册 26 个 bash 用例
  + `glob2re` 直跑 1 个 = 27 个 CTest 条目；其中 `spawn-nowait`、`still-open-after-exit` 由
  `if (CMAKE_SYSTEM MATCHES "Linux.*")` 守卫（OHOS 上不注册；上游设计，非本次裁剪）

## 关键问题与修复（真实报错）

### 1) 基线全灭：`bind: Operation not permitted`（22/25 失败）

- 未打补丁、设备原样运行（`.work` 手动 CMake 构建后 `ctest -j1`）：
  ```
  [ERROR] bind: Operation not permitted (1)
  !! ASSERT: sexpect sp -t 10 -ttl 20 bash --norc
  ...
  12% tests passed, 22 tests failed out of 25
  ```
  仅 `glob2re`、`version` 通过（不依赖 sockfile），`interact-re-helper` 无 tty 按上游设计空跑通过。
- 根因: HarmonyOS 对普通用户态进程拒绝创建 AF_UNIX **路径名** socket。设备探针（python，覆盖所有可写位置）：
  ```
  BIND FAIL  $HOME/.../tmp/sexpect-probe.sock       -> [Errno 1] Operation not permitted     (HMDFS)
  BIND FAIL  $HOME/sexpect-probe.sock               -> [Errno 1] Operation not permitted     (HMDFS)
  BIND FAIL  /tmp/sexpect-probe.sock                -> [Errno 30] Read-only file system
  BIND FAIL  /dev/shm/sexpect-probe.sock            -> [Errno 13] Permission denied
  BIND FAIL  /data/local/tmp/sexpect-probe.sock     -> [Errno 13] Permission denied
  ABSTRACT BIND OK / ABSTRACT CONNECT OK / ABSTRACT DATA: b'ping'
  ```
  即 E024/E461 族平台限制：只余**抽象命名空间**可用。
- 修复（补丁 0001–0003，无平台宏的可移植回退）:
  - `common.c` 新增 `sock_abstract_addr()`：按 sockfile 路径做 FNV-1a 64 哈希，
    生成 `@sexpect-<16hex>` 抽象名（server/client 同源推导，路径长度无关）；
  - `sock_connect()`：先试路径 socket，失败再试抽象名；
  - 新增 `sock_bind()`：路径 `bind()` 仅在 `EPERM/EACCES/EROFS` 时回退抽象命名空间
    （其余 errno 照旧 `fatal_sys`）；`server.c` 改用之，抽象模式跳过 `realpath()`
    （无文件可 canonicalize）。
- 修复后（同一设备、同一源码树）: **25/25 全部通过**（见 `reports/test-report.md`）。

### 2) 只读 `/tmp`：`send-null`、`send-128k` 的临时文件

- 上游 `tests/send-null.sh`、`tests/send-128k.sh` 硬编码 `/tmp/...`；设备 `touch /tmp/x` →
  `Read-only file system`（E002 家族）。修复（补丁 0005/0006）:
  `/tmp/...` → `${TMPDIR:-/tmp}/...`；配方 `build()` 内把 `TMPDIR` 指向构建目录下的可写 `tmp/`。

### 3) `chdir-after-logfile`：`ls -l /` 被沙箱拒绝导致 wait 非零

- 修复后复测该用例失败，原始输出：
  ```
  # sexpect sp -t 10 -logf chdir-after-logfile.vJv0TT.log -ttl 30 ls -l /
  # sexpect ex -eof
  ls: /: Permission denied
  # sexpect w
  !! ASSERT: sexpect w
  ```
- 根因: 该测试用 `ls -l /` 产生日志输出，而 OHOS 沙箱拒绝列 `/`（EACCES），`ls` 非零退出；
  `sexpect wait` 的退出码 = 子进程退出码，断言因此失败——**被测行为（logfile 相对路径在
  chdir 前打开）本身正确**，是测试夹具依赖了平台能力。
- 修复（补丁 0004）: 子命令改为 `ls -l $tmpfile`（列刚创建的日志文件，同 cwd），
  断言逻辑不变；若真的回归到 chdir-then-open，日志会落到 `/` 而打不开，该用例仍会失败。

### 4) 编译告警：`call to undeclared function 'umask'`

- 把 `umask(0077)` 移入 `common.c` 后触发 `-Wimplicit-function-declaration`；补 `#include <sys/stat.h>`
  （补丁 0001），复测构建日志零告警。

### 5) `conan-verify` G2：E017 预防注入的加速镜像不可达

- 现象: `conan-verify` 的 G2 会把 conandata.yml 中 `https://github.com` 前缀**临时**改写为
  `https://ghfast.top/https://github.com/...`（E017 预防，G2 结束自动恢复）；本构建网络访问该镜像
  连接超时（`ConnectTimeoutError ... ghfast.top`），而 GitHub 直连正常（0.7s 下载完成，sha256 一致）。
- 处理: `conandata.yml` 源码 URL 采用 GitHub **官方 tar 入口** `https://codeload.github.com/...`
  （`github.com/.../archive/...` 的官方 302 目标，字节一致；jattach 2.2 先例）。E017 的字符串替换
  只命中 `https://github.com` 前缀，官方域不受影响。
- 二次报错与修法: codeload URL 末段是 tag 名 `v2.4.0`（无扩展名），Conan `get()` 推导文件名为
  `v2.4.0` 并按 zip 解码 → `BadZipFile: File is not a zip file`。在 `sources` 中显式声明
  `filename: "sexpect-2.4.0.tar.gz"` 后按 tar.gz 解压（abbtr 1.0.4 / accel-config 4.1.9 同款先例），
  下载与 sha256 校验通过。

### 6) `cmake.test()` 无法转发 ctest 参数

- 现象: `cmake.test(cli_args=["--output-on-failure", "--parallel", "1"])` 实际执行
  `cmake --build <dir> --target test --output-on-failure --parallel 1`，CMake 报
  `Unknown argument --output-on-failure`（该参数只属于 ctest，不属于 `cmake --build`）。
- 修法: 显式 `self.run("ctest --output-on-failure --parallel 1", cwd=self.build_folder)`
  （plfit 0.9.6 同款处理），保留与 `cmake.test()` 等价的构建目录与 conanbuild 环境。

## 上游测试清点（R51 申报表）

| 检查项 | 命令/依据 | 结果 |
|---|---|---|
| tests/ 文件数 | tarball 解压树 `find tests -type f` | 32（含 `CMakeLists.txt`、`common.sh`） |
| CTest 注册数 | `tests/CMakeLists.txt` 的 `add_test` | 27（26 bash + 1 直跑 glob2re） |
| Linux 守卫用例 | `grep -n 'CMAKE_SYSTEM' tests/CMakeLists.txt` | 2 个（`spawn-nowait`、`still-open-after-exit`） |
| OHOS 运行数 | 设备 `ctest -N` | 25 |
| 实测运行 | 设备 `ctest --output-on-failure -j1` | **25/25 PASS**（详见 `reports/test-report.md`） |

## 源码修改清单（均由 `refresh-patch --auto` 生成）

| 补丁 | 文件 | 修改内容 |
|---|---|---|
| 0001-common.c.patch | `common.c` | 抽象命名空间回退（`sock_abstract_addr`/`sock_connect_one`，重写 `sock_connect`，新增 `sock_bind`）+ `#include <stddef.h>/<stdint.h>/<sys/stat.h>` |
| 0002-common.h.patch | `common.h` | 声明 `sock_bind()` |
| 0003-server.c.patch | `server.c` | 用 `sock_bind()` 绑定；抽象模式跳过 `realpath()`；删除不再使用的局部 `srv_addr` |
| 0004-tests-chdir-after-logfile.sh.patch | `tests/chdir-after-logfile.sh` | `ls -l /` → `ls -l $tmpfile`（断言逻辑不变） |
| 0005-tests-send-128k.sh.patch | `tests/send-128k.sh` | `/tmp/data` → `${TMPDIR:-/tmp}/data` |
| 0006-tests-send-null.sh.patch | `tests/send-null.sh` | `/tmp/file-with-nulls` → `${TMPDIR:-/tmp}/file-with-nulls` |

## 依赖版本

无（零第三方依赖）。

## 验证结果

### 设备手动基线（未打补丁，故障复现）

```bash
cmake -S sexpect-2.4.0.work -B build && cmake --build build -j4 && ctest -j1
# 12% tests passed, 22 tests failed out of 25（失败根因均为 bind: Operation not permitted）
```

### 打补丁后（上游 CTest 全量）

```bash
ctest --output-on-failure -j1
# 100% tests passed out of 25；Total Test time (real) = 129.39 sec
```

逐项结果：`glob2re`、`version`、`spawn-ttl`、`chkerr`、`cstring`、`chdir-after-exec`、
`chdir-after-logfile`、`cloexit`、`close`、`eof-before-exit`、`expbuf-overflow`、`expect_out`、
`expect-eof`、`expect-nocase`、`expect-pattern`、`get-expbuf`、`interact-re-helper`、`kill`、
`send-128k`、`send-null`、`spawn-nohup`、`spawn-nonblock`、`spawn-zombie-idle`、
`spawn-zombie-idle_02`、`still-data-after-exit` 全部 PASS。

### Conan 侧（`conan create` 干净构建，2026-09-26）

```bash
conan create archives/s/sexpect/2.4.0 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
    --build=missing --user=ohpcd --channel=stable
# 上游 CTest: 100% tests passed out of 25（Total Test time = 126.89 sec，rrev #f826ce580fc2…）
# test_package: assertions: 10 passed: 10 failed: 0 / ALL TESTS PASSED
# 产物: bin/sexpect, share/man/man1/sexpect.1, licenses/LICENSE
# conan-verify: G0-G4 + L2/L4/L5 全 PASS
```

逐项 25 条结果与完整日志见平台 CI 构建 #62096（https://ohpcd.atomgit.com/ci?id=62096）；
按仓库评审规则 19，原始 `*.log` 不随 PR 提交，关键汇总已引用在 `reports/test-report.md`。
`conan-verify`/finish 阶段为缓存命中（仅复跑 test_package 10/10）；`conan-verify` 判定为
G0–G4 与 L2/L4/L5 全 PASS。按仓库评审规则 19，原始过程文件（`*.log`、验证报告副本、
body 副本）不随 PR 提交。

## 交付物

- `test_package/`（消费者测试，10 条断言；真实执行打包后的 `bin/sexpect`）
- `patches/` 6 个补丁；`reports/test-report.md`；软件级 `README.md`/`commands.json`/`manifest.yaml`

## 注意事项

- `SEXPECT_SOCKFILE` 建议使用绝对路径：抽象回退名按传入路径字符串哈希，server/client 必须传入
  同一字符串（本仓库测试全部使用绝对路径）。
- 抽象命名空间 socket 随进程消失，无文件残留；`kill` 用例中「等待 sockfile 消失」的循环在
  OHOS 上等价于立即通过，但 `kill`/`wait` 的语义断言（退出码 143、EOF）仍全部生效。
- 共享设备运行上游测试会产生短暂的 sexpect 守护进程与 pty；测试全部自带 `-ttl`，结束即回收。

**编译结束**: 2026-09-26
**最终状态**: built（`conan-verify` G0–G4/L2/L4/L5 与 W3 本地 CI 全门禁 PASS；干净 `conan create` 内上游 CTest 25/25、消费者断言 10/10）
