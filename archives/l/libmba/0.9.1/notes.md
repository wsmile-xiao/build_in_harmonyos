# libmba 0.9.1 适配笔记

## 编译环境
- 构建系统: makefile（无 configure，纯 Makefile + mktool 驱动）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（ohos-aarch64 profile，aarch64-linux-ohos）
- 状态: built

## 编译步骤

1. `init-build libmba 0.9.1 --url=https://www.ioplex.com/~miallen/libmba/dl/libmba-0.9.1.tar.gz`
   - 官方正式发布包（2005-04-29 发布 0.9.1），SHA-256 已核验
2. 探索性原生编译（gcc→clang PATH shim，因 mktool 硬编码 gcc）
3. `conan-init` → 生成配方 → 修改 conanfile.py
4. `conan-verify libmba 0.9.1` → G1-G5 全部 PASS
5. `finish libmba 0.9.1 built` → W3 本地 CI 模拟通过，submit 就绪

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 900:TcharAll SIGABRT | `tmpfile()` 在 /tmp 只读平台返回 NULL，fputtc 崩溃 | 改用 `mkstemp($TMPDIR)`（补丁 0006） |
| 2 | 上游测试 5200/5300/5500/5700/5900 系列失败 | src/svsem.c / tcase 硬编码 `/tmp` 路径，E002 只读 | `/tmp` → `$TMPDIR`（回退 /tmp）补丁 0002-0005；svsem_t.name 扩容 17→256（补丁 0001） |
| 3 | 上游测试 5200/5500/5700/5900 仍崩溃（Signal 31 SIGSYS） | OHOS 平台 seccomp 拦截 SysV 信号量系统调用（semget），E051 未实现 syscall 类平台限制 | 非源码缺陷；如实记录，4 个套件标记平台阻塞 |
| 4 | conan create 失败 `tools.build:compiler_executables:c` 不识别 | conf 键语法错误 | 按本仓惯例改 `tools.build:compiler_executables` dict 取值 |
| 5 | conan create 失败 `env argument ... should be a list` | Conan 2 run() env 参数不接收 dict | 改用 `conan.tools.env.Environment` + `cwd=source_folder` |
| 6 | W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | util-linux-login 历史 PR 合入 main 的未登记隐藏文件（无关历史基线） | JUNK_PR_DIFF 隔离复验（仅本库受控文件），记录审计后恢复，无 worktree 残留 |

## 源码修改

补丁由 finish refresh-patch --auto 生成（6 个）：

- `0001-src-mba-svsem.h.patch`：svsem_t/_svs_data.name 17→256（容纳 TMPDIR 路径）
- `0002-src-svsem.c.patch`：svsem 临时文件路径 → `$TMPDIR`（E002）
- `0003-tcase-common.c.patch`：open_mmap `/tmp/` → `$TMPDIR`
- `0004-tcase-tests-OpenCre.c.patch`：`/tmp/file.%d` → `$TMPDIR`
- `0005-tcase-tests-SvsemCounter.c.patch`：`/tmp/...shm/.sem` → `$TMPDIR`，补 `#include <limits.h>`
- `0006-tcase-tests-TcharAll.c.patch`：`tmpfile()` → `mkstemp($TMPDIR)` + `remove()`

## 依赖版本

无第三方依赖（requirements() 为空，自包含 C 库）。

## 上游测试申报表（R51）

- 上游测试清点：tcase/ 目录 `make` 生成 tmba 驱动，25 个测试套件（含 27 个运行编号）
- 实测结果：**23/27 通过**（linkedlist/hashmap/csv/cfg/pool/varray/stack/path/suba/text/diff/bitset/msgno/eval/hexdump/daemon/time 等全部功能套件）
- 平台阻塞（4 个）：SvsemCounter(5200)、SharedAdts(5500)、SvcondProdCons(5700)、OpenCre(5900)
  - 具体技术原因：均依赖 SysV 信号量（semget/semop），OHOS 平台 seccomp 直接 SIGSYS 终止（E051 未实现 syscall 类），非本库源码缺陷
- 上游测试适配：4 个 /tmp 硬编码路径类套件因 E002 只读平台无法运行，已按平台惯例改为 `$TMPDIR` 后 3 个转为通过；剩余 4 个纯 SysV 信号量套件平台无法运行

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify libmba 0.9.1   # G1-G5 PASS, exit 0
python3 scripts/ohc-run.py finish libmba 0.9.1 built   # W3 通过, exit 0, submit 就绪
# test_package：linkedlist/varray/csv 真实 API 消费者测试 13 断言全过
```

## 交付物

库类型（libmba 静态库 + 可选动态），无 commands.json（R38 仅命令行工具需要）。

## 注意事项

- svsem(3m)/svcond(3m) 模块在 OHOS 平台因 SysV IPC 被 seccomp 拦截而无法运行，属 E051 类平台限制；库本身编译、链接、安装正常，其余全部模块可用
- mktool 驱动硬编码 `gcc`，配方中已用 build-local PATH shim 解决（R33）