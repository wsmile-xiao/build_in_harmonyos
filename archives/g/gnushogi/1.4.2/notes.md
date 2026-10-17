# gnushogi 1.4.2 适配笔记

## 编译环境
- 构建系统: autotools（手写 Makefile，无 VPATH，不支持 out-of-source）
- 编译日期: 2026-09-15
- 编译器: clang 15（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: published
- 设备 worktree: ~/qzy/GLM-27-gnushogi-1.4.2（分支 feat/gnushogi-1.4.2）
- 平台任务号: 13463

## 编译步骤

配方 build() 实际执行（conan create 干净构建通过，W3）：

1. `apply_conandata_patches`：应用 E011 umask 补丁与 --version/--help 补丁
2. 源码拷入 build 目录（in-source 构建）
3. `./configure --prefix=/ --without-curses`（CONFIG_SHELL=/bin/sh，CFLAGS 含 -fcommon）
4. `make -C gnushogi -j1 gnushogi`（顶层 Makefile 的 all:/gnushogi 目标为空壳）
5. package(): 拷贝引擎二进制到 bin/ 并以 binary-sign-tool 自签（E077）

## 测试账本（四维，R51/§10.1）

| 维度 | 数值 | 说明 |
|---|---|---|
| 上游源码静态声明总数 N_static | **0** | 上游无自动化测试套件 |
| 构建系统注册/可执行目标数 | 0 | `grep -n 'check\|TESTS' Makefile.in` 无任何结果；gnushogi/Makefile 无 check 目标（手工核对） |
| 实际执行数 N_executed | 0 | 与静态一致（无套件可执行） |
| 新增消费者测试 N_consumer | 1 | test_package/consumer.c：运行引擎断言 --version rc=0 且含版本串；stdin 喂 quit 后输出 GNU Shogi 横幅且 rc=0（8 项断言） |

上游无自动化测试（N_static=0），按规则以真实行为断言的消费者测试补位。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: `can't create ./confXXX/subs1.awk: Permission denied` | E011：HMDFS 下 umask 077 临时目录不可写 | 补丁 configure：umask 077 → 022 |
| 2 | 链接期 `duplicate symbol DRAW`（globals.o/rawdsp.o） | clang 15 默认 -fno-common；2014 年代码大量暂定定义 | CFLAGS 追加 -fcommon |
| 3 | `configure: error: working directory cannot be determined` | E386：conan spawn 的 shell 继承 HMDFS 冷节点 cwd，首次 getcwd 必败；且 profile [buildenv] 将 CONFIG_SHELL/SHELL 强制为 hnp bash（source 顺序晚于工具链脚本），configure 以 bash 重执行后必死 | 每条构建命令先 `cd /` 恢复再进入工作目录；命令内 `export CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 覆盖回 ash |
| 4 | `checking for gcc/cc... no` | build() 曾 rmtree build_folder，把 conan generators（conanbuild.sh/CC 注入）一并删除 | 构建移入 build_folder/build 子目录，保留 generators |
| 5 | `make: Nothing to be done for 'gnushogi'` | 顶层 Makefile 的 gnushogi 目标为空壳（同 all:） | 使用 `make -C gnushogi gnushogi` |
| 6 | binary-sign-tool 加载 libc++.so 失败 | E540：conan 环境的 LD_LIBRARY_PATH 指向 SDK llvm/lib | 签名子进程剥离 LD_LIBRARY_PATH |
| 7 | 包内引擎 `can't execute: Permission denied`（消费者测试 rc=126） | E046：HMDFS 上 chmod 不生效，打包后 exec 位丢失 | test_package 将引擎拷到 /data/storage/el2/base（tmpfs）恢复 0755 后执行 |
| 8 | 无 curses 可链接 | 制品仓 ncurses 仅提供宽字符库（ncursesw/panelw/menuw/formw），上游探测 -lcurses/-ltermcap 无法命中；引擎文本 UI 不依赖 curses | `--without-curses`，无第三方依赖的完整功能构建 |

## 源码修改

见 patches/：
- 0001-configure.patch（E011，2 行）
- 0002-gnushogi-main.c.patch（GNU 标准 --version/--help，+22 行；上游 -v 以 exit(1) 结束，OHOS 打包 smoke 门禁要求 --version 以 0 退出；输出复用上游 case 'v' 与 usage 文案）

## 运行时数据文件说明

引擎以 `-DHASHFILE=<prefix>/lib/gnushogi/gnushogi.hsh` 编译（configure prefix 推导），该文件为运行时散置/开局库缓存，缺失时引擎自动以内置逻辑运行（已验证可正常启动、对局与退出）。开局书 gnushogi.bbk 需运行引擎编译生成（上游 make 目标），无法在交叉 CI 中复现，故不随包分发；如需开局库可在目标机用 `make gnushogi.bbk` 生成。
---

**编译结束**: 2026-09-15 02:15
**最终状态**: built
