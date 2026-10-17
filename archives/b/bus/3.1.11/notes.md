# bus 3.1.11 适配笔记

## 编译环境
- 构建系统: makefile（纯 POSIX Makefile + config.mk，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-linux-ohos, musl)
- 状态: built

## 编译步骤

```bash
# 探索编译（原始 Makefile，直接 make）
cd <src>
make CC=clang CFLAGS="-Wall -Wextra -pedantic -O2 -fPIC -D_DEFAULT_SOURCE -D_BSD_SOURCE -D_XOPEN_SOURCE=700 -D_GNU_SOURCE" LDFLAGS="-lrt"
# 产物: bus(CLI) + libbus.a + libbus.so (soname libbus.so.3)

# Conan 配方验证（干净构建，G2 通过）
python3 scripts/ohc-run.py conan-verify bus 3.1.11
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连 GitHub 下载超时 | 本机直连 github.com 被限 | 经 codeload/ghfast 镜像预下载官方 tag tarball 到 TMPDIR/builds 缓存，init-build 复用并核验 SHA-256 |
| 2 | conan-init 生成 autotools 配方 | init-build 对 URL 误判构建系统 | 重写 conanfile.py 为纯 Makefile 构建（config.mk 内 CC=c99 需命令行覆盖为 conf 的 clang） |
| 3 | conan create 报 `win_bash` 参数错误 | Conan 2.29 的 run() 不接受 win_bash | 移除 win_bash 参数 |
| 4 | test_package 运行 test_bus 报 127 | conanrun 环境（VirtualRunEnv）未注入 libdirs/PATH，动态库找不到 | test() 显式设置 `LD_LIBRARY_PATH=<dep.libdirs>` + 绝对路径调用 |
| 5 | bus 全 API 运行时 SIGSYS(Signal 31) | OHOS 沙箱 seccomp 拦截 System V IPC（semget/shmget） | 取证+处理：SIGSYS 可捕获（TRAP）；test_ohos 如实报告 PLATFORM_LIMITATION；POSIX sem_open 不受阻。恢复条件：非沙箱/启用 SysV IPC 环境 |
| 6 | 示例运行时 `/tmp` 只读 | 平台 TMPDIR 限制 | 改用 $TMPDIR（/storage/Users/currentUser/tmp）下专用目录 |
| 7 | finish G0 clean-verify exit 127 | manifest 误标 autotools，clean-verify 跑不存在的 ./configure | manifest build_system 改 makefile |
| 8 | conan-verify 镜像注入残留 .ghfast-bak/.orig | E017 预防逻辑备份 | 提交前删除残留（JC1 拦截） |
| 9 | gen_summary 'str' object has no attribute 'append' | 框架 SUMMARY 生成工具 bug（非本包） | 不修框架；非阻塞（INDEX/知识完整性均通过） |

## 源码修改

无源码补丁（上游源码零改动，纯配方层适配）。

## 依赖版本

- 无外部 conan 依赖（依赖仅 libc/librt/musl 运行库）

## 验证结果

```bash
# conan-verify 8 门禁全过（G0-G4 + L2/L4/L5）
VERDICT: PASS
# 消费者用例（test_package/test.c）
PASS: bus_open(nonexistent) -> -1 errno=ENOENT
# 鸿蒙专项（test_package/test_ohos.c）
BUS_MEMORY_SIZE=2048; PASS bus_open; PLATFORM_LIMITATION(SysV IPC SIGSYS) 如实报告
# CLI 冒烟
bus (无参) -> exit 2（文档规定 command not recognised）
# 上游示例 23/23 编译通过；运行均被 SysV IPC SIGSYS 平台阻塞（详见 test-report.md 台账）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 配方（库 + CLI 混合包） |
| conandata.yml | 官方 tag 源 + SHA-256 |
| commands.json | CLI 声明（软件级，R38/L0k） |
| test_package/ | 消费者用例 + 鸿蒙专项测试 + L1 冒烟 |
| reports/test-report.md | 双口径台账 + 平台阻塞取证 |
| reports/ohos-test-evidence.log | 测试运行证据（sha256: 9fd0b0d0...） |

## 注意事项

- bus 核心依赖 System V IPC：库可编译、可链接、可加载；但应用运行时若在 OHOS
  AppSpawn 沙箱内会被 seccomp SIGSYS 拦截，业务集成需在启用 SysV IPC 的上下文运行。
- 上游 Makefile VERSION=3.1.7（未随 tag 更新），以 tag 3.1.11 为准，不影响构建。