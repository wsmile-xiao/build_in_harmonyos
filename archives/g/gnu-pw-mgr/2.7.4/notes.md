# gnu-pw-mgr 2.7.4 适配笔记

## 编译环境
- 构建系统: autotools（GNU 项目，自带 configure，捆绑 gnulib 与 libopts）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. init-build 从官方 URL 下载 tarball（sha256=0d33591d…2dc028a）。
2. 手动探索构建（Mode B Step 2）迭代定位三个头文件/环境问题后
   `CC=clang ac_cv_header_sys_time_h=yes ./configure … --disable-nls` →
   `make -j1` → `make check`（日志 ~/tmp/uc2/gnu-pw-mgr-2.7.4/manual-build.log）。
3. conan-init 骨架 + 手写配方（units/2.22、bc/1.07.1 范式，application 类型）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 中 configure 报 `working directory cannot be determined`（伴随大量 `shell-init/job-working-directory: getcwd` 错误） | 设备上 `/data/service/hnp/bin/bash` 的 getcwd 已损坏（HMDFS 构建目录下必失败），而 OHOS conan profile 的 buildenv 把 `SHELL`/`CONFIG_SHELL` 都指向它；autoconf 会经 `$CONFIG_SHELL` 重 exec 自身，于是 configure 必挂（与内存/负载无关） | 配方 build()/package() 以 `env -u CONFIG_SHELL SHELL=/bin/sh` 前缀调用 configure/make/install（保留完整 conan 工具链环境，仅换 shell） |
| 2 | lib/ (gnulib) 编译失败：`redefinition of 'timeval'`（sys/time.h vs musl bits/alltypes.h） | gnulib 判定平台 sys/time.h 不可用而启用替换头，与 OHOS musl 全类型头冲突 | configure 传缓存变量 `ac_cv_header_sys_time_h=yes`，跳过替换头 |
| 3 | libopts 编译失败：gettext.h 隐式声明（int→指针转换错误） | OHOS 无 libintl/gettext 运行时，clang15 将隐式声明视为错误 | configure 传 `--disable-nls`，gettext.h 走纯宏回退 |
| 4 | config.sub 不识别 linux-ohos triplet | 2021 年代 config.sub 无 ohos 支持 | `--build`/`--host` 均传 aarch64-unknown-linux-gnu（先例范式） |
| 5 | make install 进 doc/ 时 makeinfo 缺失（Error 127） | 安装期会重新生成 info 页，设备无 texinfo | package() 中把 tarball 自带 doc 产物（.info/.8/.5 等）mtime 刷新为最新，使 `make install` 原样拷贝（不动 Makefile.am/in，避免触发 automake） |
| 6 | configure 阶段 `umask 077` mktemp 探针（3 处） | HMDFS 权限组合使 config.status 临时目录不可写（E011 同源） | 配方 build() 中 replace_in_file 放宽为 umask 002 |

## 上游测试失败根因分析（R51 证据链）

- base.test：脚本向 `/dev/tty` 写入测试标识 → OHOS SSH 会话无控制终端
  （`can't create /dev/tty: No such device or address`）——环境限制。
- dom.test：基线文件 dom.base 由测试内 `/usr/bin/printf '%-10.10lu'`（busybox
  语义，空格填充）生成，而被测程序输出经 musl libc printf（POSIX 精度语义，
  零填充 "0000020709"）→ `cmp` 在 char 14 失配。两侧工具格式语义不一致，
  属测试基线生成工具的平台差异；程序本体执行链路（配置解析、域存储、
  输出）均正常运行（dom.res 除填充宽度外内容正确）。

## 上游测试四维账本

- 上游静态声明总数：**2**（tests/base.test、tests/dom.test）
- 实际执行：2
- 通过/失败/跳过：0 通过 / 2 失败 / 0 跳过（两项失败均为上述环境限制，
  有完整 test-suite.log 证据）
- 新增消费者测试：1 个程序（test_package/test.sh，2 处断言：
  sort-pw-cfg --version 冒烟 + 配置校验路径"缺 id 标签必须拒绝"）

## 运行时已知限制

- gnu-pw-mgr 主程序启动即调用 getpwuid(getuid()) 查询用户信息；OHOS 的
  HMDFS uid（如 20020084）不在 /etc/passwd 数据库中，导致任意参数
  （含 --version/--help）均以 "no password entry for uid" fatal 退出。
  这是上游设计（用户上下文先于参数处理初始化）与 OHOS 多用户环境的
  结构性差异，消费者测试因此以同包的 sort-pw-cfg 工具为行为断言载体。

## 验证结果

```bash
$ make check        # base.test FAIL(/dev/tty) + dom.test FAIL(printf 语义)
$ ./src/gnu-pw-mgr --version
gnu-pw-mgr fatal error: no password entry for uid 20020084
$ ./src/sort-pw-cfg --version
sort-pw-cfg 2.7.4
```

## 对话 #

- 2026-09-14 夜跑窗口（GLM-24）：首版适配、构建与提审（PR #10005）。
- 2026-09-15 晚（GLM-26 接手收尾）：补回被本地副本覆盖抹掉的 finish 收尾块，
  使 submit 的 `progress_closed` 自检恢复通过；配方与产物未改动。
---

**编译结束**: 2026-09-15 21:13
**最终状态**: built
