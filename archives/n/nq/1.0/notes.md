# nq 1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游 v1.0 为纯 Makefile，无 configure）
- 编译日期: 2026-09-03
- 编译器: clang 15（/data/service/hnp/bin/clang，来自 conan profile tools.build:compiler_executables）
- 状态: built（conan-verify 全绿，CI release 合入 main 后 upload）

## 编译步骤
```bash
# 探索编译（模式 B）
cd $BUILD_SRC_DIR
make CC=clang              # 产出 nq nqtail（nqterm 为仓库自带 shell 脚本）
make check                 # prove -v ./tests → 36/36 通过
make install DESTDIR=$TEST_PREFIX   # 需 PATH 含 /bin（install(1) 所在）

# conan 配方验证
ohc-run.py conan-init nq 1.0
ohc-run.py conan-verify nq 1.0      # G1-G4 + L2/L4/L5 全 PASS
# 内部 conan create 真实执行：
#   build(): make CC=clang -j1 && make check（上游 36 条 TAP 全绿）
#   test_package: bash test_nq.sh → 1..6 全 ok（真实入队 job、等待、校验日志）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机 `make -j2` 报 `jobserver mkfifo: Operation not permitted` | HMDFS 文件系统限制（/tmp 下 fifo 受限） | make -j1（R9），日志仅告警不影响产物 |
| 2 | 上游 `make install` 报 `make: install: No such file or directory` | `install`(1) 只在 /bin（toybox），默认 PATH 不含 /bin | package() 改为 conan `copy()` 直接拷贝 bin/man 并 os.chmod 0755，不依赖 install(1)（CI 环境同样适用） |
| 3 | 探索时 nq/nqtail 链接到 musl loader | 本机 clang 默认 target 即 OHOS aarch64 musl | 与 CI 一致（同 /data/service/hnp/bin/clang），make check 在本机与 conan cache 内均真跑通过 |
| 4 | conan-init 自动模板按 autotools 生成 | init 探测将无 configure 的 Makefile 项目判为 autotools | 按 templates/conanfile-makefile.py.tmpl + abduco/0.6 先例整体改写为纯 make 配方；软件级/版本级 manifest build_system 改为 makefile |
| 5 | conan create: `conf 'tools.build:compiler_executables:c' does not exist` | OHOS 适配版 conan 2.29.1 不支持该子键点写法 | 改用 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 取 dict 后 `["c"]`（abduco 同款写法） |

## 源码修改

无平台宏、无补丁（R8：零 patch）。纯 POSIX C + flock(2)，无需任何修改即可在 OHOS aarch64 编译运行。

## 依赖版本

无（W0 依赖检查：requires 为空，纯 C 无第三方库）。

## 验证结果

```bash
# 上游测试（make check / prove -v ./tests）：36/36 PASS
All tests successful.
Files=1, Tests=36
# test_package 功能测试（bash test_nq.sh）：6/6 PASS
1..6
ok - enqueue a real job with nq
ok - wait for the job with nq -w
ok - job log contains command output
ok - job log records exited-with-status-0
ok - nqtail prints the completed job log
ok - nqterm wrapper is executable
# nq functional assertions: pass=6 fail=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/nq | 队列工具主程序（arm64 ELF） |
| bin/nqtail | 任务日志跟踪（arm64 ELF） |
| bin/nqterm | tmux/screen 包装脚本（shell） |
| share/man/man1/{nq,nqtail,nqterm}.1 | man 手册 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/n/nq/commands.json` 声明（R38）。
- L2 smoke 中 `nq --version` 会被 nq 当作后台 job 入队执行（nq 用法即 `nq CMD...`），进程立即返回 0，不阻塞 CI。
- test.dir/`,*` 任务日志会在运行目录残留由 make check 清理；test_package 自带清理。
---

**编译结束**: 2026-09-03 21:43
**最终状态**: built
