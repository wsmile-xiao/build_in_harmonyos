# micron 1.4 适配笔记

## 编译环境
- 构建系统: autotools（GNU 项目，自带 configure，捆绑 gnulib 与 libopts）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. init-build 从官方 URL 下载 tarball（sha256=036e662f…73cda4）。
2. 手动探索构建暴露核心阻塞：链接期 `undefined symbol: pthread_cancel`
   （ld.lld，引用自 micrond.c 的 default_stop_thread 与 runner.c 的 outfile_release）。
3. 实施协作式关闭移植（5 个补丁，见下），手动构建通过：`make -j1` 全树成功
   （src/micrond、src/crontab、tests/micronh 全部产出）。
4. `make check`：14 项全部执行 → 2 通过 / 12 跳过 / 0 失败。
5. conan-init 骨架 + 手写配方（units/2.22、bc/1.07.1 范式，application 类型）。

## 核心适配：pthread_cancel → 协作式关闭（知识库 E085）

**问题**：OHOS 的 musl libc 不实现 POSIX 线程取消 API（pthread_cancel /
pthread_testcancel / pthread_setcancelstate / pthread_setcanceltype，E085）。
micron 用「pthread_cancel + pthread_join」停止 6 个线程，故链接失败。

**为何不能用 stub 兜底**：E085 的 fallback（空实现满足链接）对 micron 是有害的——
`default_stop_thread()` 的语义是 `pthread_cancel(tid); pthread_join(tid);`，
cancel 变空操作后 join 会**永久阻塞**，守护进程一收到关闭信号即死锁；输出线程
的 cancel 同理。这类「cancel 语义承载线程生命周期正确性」的场景必须做真实移植。

**移植方案**（5 个补丁，全部为可移植性改动）：

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | src/micrond.h | 声明共享停止标志 `cron_shutdown` 与唤醒函数 `cron_threads_wakeup()` |
| 0002 | src/micrond.c | `default_stop_thread` 改为：置标志 → `cron_threads_wakeup()` + `cron_main_wakeup()` → `pthread_join`；调度线程主循环每轮检查标志后自愿退出 |
| 0003 | src/runner.c | 新增 `cron_threads_wakeup()`（广播 runner/proctab/cronjob_output 三个条件变量）；runner 与 cleaner 循环检查标志并自愿退出（cleanup 处理器改为正常退出时也执行，`pthread_cleanup_pop(0)`→`(1)`）；输出线程改用独立标志 `cronjob_output_stop` + 1s 定时等待（规避 outfile_mutex 与 cronjob_output_mutex 的锁序风险）；fork 失败路径不再 cancel 短命输入线程（该线程写完有界输入后自然结束） |
| 0004 | src/watcher.c | inotify 监视线程 `poll(-1)` → `poll(1000)` + 每轮检查标志，保证 1 秒内响应关闭 |
| 0005 | tests/micronh.c | 测试辅助程序同款处理：syslog 读取线程改停止标志 + `SO_RCVTIMEO` 1s |

补丁由真实 `diff -u`（a/ b/ 前缀）生成，并逐个在纯净源码树上用 `patch -p1` 应用、
与移植后的工作树逐文件 `cmp` 校验一致（`ohc-run.py refresh-patch --auto` 对该两
个大文件 dry-run 失败，故改手工生成同格式补丁并做应用性自测）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接失败：`undefined symbol: pthread_cancel` | OHOS musl 不提供线程取消 API（E085）；micron 用 cancel+join 停止线程，stub 会导致 join 死锁 | 协作式关闭移植（5 个补丁，见上） |
| 2 | conan create 中 configure 报 `working directory cannot be determined` | 设备 `/data/service/hnp/bin/bash` 的 getcwd 已损坏，而 conan profile 的 buildenv 把 `SHELL`/`CONFIG_SHELL` 指向它，autoconf 经 `$CONFIG_SHELL` 重 exec 后必挂 | 配方以 `env -u CONFIG_SHELL SHELL=/bin/sh` 前缀调用 configure/make/install |
| 3 | `make` 进 doc/ 时 makeinfo 缺失（Error 127） | micron 的 `all` 目标会重新生成 info/man 页 | build() 中先刷新 tarball 自带 doc 产物（.info/.1/.5/.8）的 mtime 使其原样使用（不碰 Makefile.am/in 以免触发 automake） |
| 4 | configure 阶段 `umask 077` mktemp 探针 | HMDFS 权限组合使 config.status 临时目录不可写（E011 同源） | 配方 build() 中 replace_in_file 放宽为 umask 002 |
| 5 | config.sub 不识别 linux-ohos triplet | 2024 年代 config.sub 无 ohos 支持 | `--build`/`--host` 均传 aarch64-unknown-linux-gnu |

## 上游测试四维账本

- 上游静态声明总数：**14**（tests/*.at 逐文件统计 AT_SETUP）
- 实际执行：14（autotest 套件全部执行）
- 通过 **2**：`cron expression parser`（tests/parsetest）、`next time calculation`
  （tests/timetest）——纯逻辑单元测试，在 OHOS 上真实通过
- 跳过 **12**：套件自身 `AT_SKIP_IF([test -z "$FAKELIB_PRELOAD"])` —— 这 12 项
  端到端场景（day/dom/dow/hr/mail/maxinst/min/outfile/vinput/syslog/vscope/linecont）
  需要 libfaketime / fakeroot 预载库并以 root 运行（tests/atlocal 中
  `FAKETIME_LIBDIR`/`FAKEROOT_LIBDIR` 均空、且 `id -u` 非 0），设备与 CI 环境
  均不具备 → 环境限制（R51 可接受原因：工具或依赖未安装且 CI 无法提供）
- 失败 **0**
- 新增消费者测试：1 个程序（test_package/test.sh，3 处断言：micrond -h 用法输出
  且退出 0、用法含 `-f` 选项、crontab 拒绝未知选项并返回非零）

## 运行时已知限制（环境限制，非配方问题）

micron 的两个二进制都在启动早期经 `getpwuid(getuid())` 解析使用者身份，而 OHOS
的 HMDFS uid（如 20020084）不在 `/etc/passwd` 数据库中：

- `crontab`（客户端）→ `crontab: who am I?` 后退出（crontab.c:163）
- `micrond`（守护进程）→ 在 crontab 扫描阶段段错误

**该段错误与本移植无关**（对照实验证据）：以**原始 upstream 逻辑 + `pthread_cancel`
空实现 stub** 另行构建的 micrond，在同一位置以完全相同的日志
（`rescanning crontabs` 之后）段错误——说明这是 micron 在「uid 不在 passwd 库」
环境下的既有行为，与协作式关闭移植无因果关系。容器/设备若提供 passwd 条目
（或由 root 运行，如上游测试预期），该路径即按上游设计继续执行。

## 验证结果

```bash
# 全树构建（设备原生，含测试框架程序）
$ make -j1
src/micrond / src/crontab / tests/micronh 均产出，MAKE=0

# 上游套件
$ make check
2 tests were successful. / 12 tests were skipped.
（14 项全部执行，0 失败）

# 补丁应用性自测
5 个补丁 patch -p1 应用到纯净源码树后，与移植工作树逐文件 cmp 一致
残余 pthread_cancel 引用：0
```

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/micrond | cron 守护进程（协作式关闭） |
| bin/crontab | crontab 客户端 |
| patches/0001-0005 | pthread_cancel → 协作式关闭移植补丁 |
| commands.json（软件级） | R38 可执行产物声明 |

## 注意事项

- micron 是应用（守护进程 + 客户端）：package_type=application、软件级 commands.json 必备。
- 补丁集中于线程停止语义；六个线程的停止路径分别为：标志检查（runner/cleaner/
  调度/inotify 监视）、独立标志 + 1s 定时等待（输出线程）、标志 + socket 接收超时
  （测试辅助的 syslog 线程）。
- 若后续 OHOS 环境补上 passwd/group 条目，建议复跑 `make check` 与 micrond 冒烟，
  以覆盖本次因环境受限未能执行的 12 项端到端场景。
---

**编译结束**: 2026-09-14 23:39
**最终状态**: built
