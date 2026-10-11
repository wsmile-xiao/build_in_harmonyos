# mgetty 1.2.1 适配笔记

## 结论

适配成功：本地 `conan create`（profile `ohos-aarch64`）构建 + 上游测试 + test_package 全绿
（上游 20 项用例/断言通过；消费者 25 + 鸿蒙 16 = 41 条断言通过）。

## 版本映射与源码身份

- 产品版本 `1.2.1` = 上游 mgetty+sendfax 1.2.1（Gert Doering）。
- 官方发布点 `http://mgetty.greenie.net/source/1.2/mgetty-1.2.1.tar.gz`
  SHA256 `c8a72f5ca4142e30627ad16725c40692fb09e6284514392b95ac02062cac9a89`
  （与官方 `ftp://mgetty.greenie.net/pub/mgetty/source/1.2/` 同一份原件，
  两路实测同哈希；站点无 https，443 实测拒连，故取官方 HTTP——R39 官方源）。

## 依赖闭包

- **无第三方依赖**（只用 libc / POSIX）。这不代表无需适配：见下「关键坑」。
- 运行期可选：`perl`（faxrunqd 前端是 `#!/usr/bin/perl -w` 脚本）、`awk`/`sed`（G3 测试脚本用）。
  打包产物本身不依赖 conan 依赖包。

## 上游测试（R51 三步法：清点 → 实跑 → 如实回填）

- **入口**：`make test`（顶层 Makefile）→ 依次进入 `g3/` 与 `t/` 执行其 `test` 目标。
- **清点**：g3/ 图像工具套件 15 项字节级断言（`cmp`/`test` 调用，含 -a/-R/-p 各档位
  47/54/42/52/102/1002/47 与 -L/-w 5 项行数/宽度）；t/ 共 5 个用例
  （`t_config`、`t_ring` 两个 C 程序 + `t_echo`、`t_trap`、`t_g3file` 三个 shell 脚本；
  另编译 `t_g3f_c` 作为 t_g3file 的辅助程序）。
- **实跑**（build() 内执行，非本环境跳过）：

  ```console
  mgetty/1.2.1: R51/build: make -j20 test CC="/data/service/hnp/bin/clang" CFLAGS="-fPIC -O2 -O3 -DPTR_IS_LONG" LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" LIBS=
  ...
  testing g3cat -a / -R / -p <padding>...
  testing g3cat -L <length> / -w <width>....
  all G3 program tests passed!
  ...
  run t/t_config...
  run t/t_ring...
  run t/t_echo...
  run t/t_trap...
  run t/t_g3file...
  OK
  ```

- **结果**：上游用例 **20/20 通过**（失败 0、跳过 0）。
  日志：`~/tmp/mgetty-work/conan-create.log`（本地）；CI 为 `conan create` 输出。

## 构建方案

上游是**纯 Makefile 工程，没有 configure 脚本**（README.1st：复制 policy.h-dist →
policy.h，按需改 Makefile 的 CC/CCFLAGS/INSTALL/*DIR，再 `make` / `make test` / `make install`）。
配方据上游文档执行：

1. `shutil.copyfile(policy.h-dist → policy.h)`；
2. `make bin-all login.config mgetty.config sendfax.config`
   （`bin-all` 覆盖 mgetty/sendfax/newslock/sedscript + g3/tools/fax/callback 子目录；
   `all` 还会格式化 man 页，需要 nroff/groff，打包不需要；后 3 个配置文件由 `./sedscript`
   从 `*.cfg.in` 生成，属 `install.bin` 前置，tarball 里并不存在）；
3. `make test` 跑上游测试；
4. 打包 13 个可执行文件 + `etc/mgetty+sendfax/` 默认配置 + `lib/mgetty+sendfax/` 数据文件。

**R33（不裸用 shell 变量）**：CC/CFLAGS/LDFLAGS 由 `AutotoolsToolchain(self)` 的生成环境
取出（`tc.environment().vars(self)`），再以命令行变量形式传给 make
（GNU make：命令行变量优先于 Makefile 内的 `CFLAGS=-Wall -O2 -pipe` 等硬编码赋值）。

## 关键坑（OHOS/aarch64 移植）

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | `conf_mg.c: error: initializer element is not a compile-time constant`（`{ (p_int) "uucp", ... }`） | `config.h` 用 `PTR_IS_LONG` 决定 `p_int` 是 `long` 还是 `int`；LP64 下必须是 long，否则把指针常量塞进 int 不是常量表达式 | CFLAGS 追加 `-DPTR_IS_LONG`（上游自带开关，非改源码） |
| 2 | `ld.lld: undefined symbol: sys_nerr / sys_errlist` | `logfile.c` 直接 `extern` 引用这两个符号；musl 不提供（glibc 2.32+ 也已移除） | 补丁 `0001-logfile.c.patch`：删掉 extern，改用标准 `strerror(errnr)`（无平台宏） |
| 3 | 上游默认 `LIBS=-lutil` | Linux 专有库；OHOS/musl 无 libutil（openpty/logwtmp 在 libc 内） | `LIBS=` 置空 |
| 4 | `make all` 在 `doc/` 报 `nroff: not found`（Error 2 ignored） | 文档格式化需要 groff/nroff，非必需 | 构建目标用 `bin-all`（不含 doc-man-only） |
| 5 | 打包后 faxspool/faxrunq/faxq/faxrm/faxrunqd 不可执行 | 这些前端由 `./sedscript` 从 `*.in` **生成**（shell 重定向产物无 +x） | `package()` 内统一 `chmod 755`；HMDFS 会把权限归一为 770（E046），仍可执行 |
| 6 | `etc/…/login.config` 等 3 个配置缺失 | 它们由 `login.cfg.in`/`mgetty.cfg.in`/`sendfax.cfg.in` 经 sedscript 生成，不在 tarball 内 | 构建目标显式加入 `login.config mgetty.config sendfax.config` |
| 7 | `make: jobserver mkfifo ... Operation not permitted` | HMDFS 不允许 mkfifo（平台限制） | 无害，make 自动降级（仅告警） |

## test_package 设计

- **消费者测试** `test_mgetty.sh`（25 条）：13 个已安装可执行文件的存在性/可执行性；
  G3 工具的真实功能——pbm2g3 编码字节数 47、g3cat 文件/stdin 复制逐字节一致、
  `-a/-R/-p` 各档位 54/42/52/102/1002、`g3cat -p 100 -a | g3cat -` 47、
  g3cat 拼接与 `-h 10` 等价（与上游 g3/Makefile:test 同一契约）；sendfax/sff2g3 用法输出。
- **鸿蒙特有测试** `test_ohos.sh`（16 条，**本任务新增**）：8 个编译产物均为
  ELF64/AArch64（`llvm-readelf -h`）；5 个生成的前端脚本可执行且带合法 shebang；
  编译产物无 Linux 专有动态依赖（libutil/libpthread/librt）；g3cat 在 OHOS 上实际执行；
  G3 流水线设备端字节确定（1002 B）。

## 遗留风险

- **运行期工具链**：`faxrunqd` 是 `#!/usr/bin/perl -w` 脚本、G3 测试脚本用到 awk/sed，
  设备上需存在对应解释器（本包只打包上游二进制/脚本，不打包 perl/awk）。
- **编译期路径**：mgetty 用 Makefile 的 `prefix`（上游默认 `/usr/local`）把
  `CONFDIR/LIBDIR/FAX_SPOOL*` 编入二进制（policy.h 语义），Conan 包不重定位这些路径——
  与上游系统守护进程语义一致，消费方按系统路径部署或自行重设 `*DIR` 后重编。
- **setuid 辅助程序**：上游把 `faxq-helper` 装到 LIBDIR 并 `chmod 4711`（setuid）。
  本包不设 setuid（Conan 包内设 setuid 不安全），统一放 `bin/`。
- **真实设备语义未端到端覆盖**：mgetty 是拨入 getty（需真实串口/调制解调器），
  设备无 modem，故 test_package 不做拨号/传真收发；已覆盖的契约是插件/工具的可加载性、
  ELF/ABI、依赖解析与 G3 图像工具的功能与字节确定性。
- **语言预检（R47）误判**：`lang-preflight` 因源码树内 `voice/Perl/Makefile.PL`
  （随包的 Modem::Vgetty Perl 模块，辅助件）判 `mixed → env_unsupported`，
  而实际主体为 C（178 个 .c，占比 91%；顶层 Makefile 工程）。按规则
  「辅助脚本不算主体语言」应为 c（与任务语言 cpp 同族、兼容），此处为工具误判，
  已在 PR/反馈中说明。

## 验证命令

```bash
P=<repo>/ci/conan/profiles/ohos-aarch64
cd archives/m/mgetty/1.2.1
conan create . -pr:h=$P -pr:b=$P        # 构建 + 上游 make test + test_package（41/41 断言）
```
---

**编译结束**: 2026-10-10 13:47
**最终状态**: built
