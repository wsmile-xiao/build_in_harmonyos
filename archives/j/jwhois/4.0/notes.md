# jwhois 4.0 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure，无需 autoreconf 自举）
- 编译日期: 2026-09-12
- 编译器: clang（OHOS aarch64 交叉工具链）
- 状态: built

## 编译步骤

1. `conan create`（AutotoolsToolchain 生成 OHOS aarch64 toolchain；configure 参数 `--disable-nls`）
2. 安装产物：`bin/jwhois`（单文件 CLI 工具），`etc/jwhois.conf`（example/ 随 install 安装）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NLS/gettext 风险 | configure.ac 用 `AM_GNU_GETTEXT([external])`；OHOS musl 无 libintl、CI 无 msgfmt | configure 传 `--disable-nls`，gettext 宏自动关闭 |
| 2 | `configure: error: cannot guess build type; you must specify one` | 2007 年版 config.guess 在 OHOS 上以 dummy 编译探测平台被 HMDFS 拒（`dummy.c: Permission denied`）；其 config.sub 也不认识 `aarch64-*`/`ohos` triplet（实测 `sh config.sub aarch64-unknown-linux-ohos` → Invalid configuration） | generate() 在 `os == "OHOS"` 时追加 `--build=aarch64-unknown-linux-gnu`（仓库 adms 配方同款先例），跳过平台猜测；不传 `--host`（老 config.sub 会直接拒绝 ohos triplet） |
| 3 | `config.status` 阶段 `./confXXXX/subs-1.sed: Permission denied` / `could not setup config files machinery`，Makefile 未生成 | 知识库 E011：HMDFS UID 映射导致 configure 内 `umask 077` 创建的临时文件（conf*/ 目录）对后续 sed/awk 不可读写 | 按知识库 E011 受控方案，在 build() 中对随包 configure 执行 `umask 077 → umask 022` 替换（gsl/2.8 配方同款实现），保留真实临时目录创建逻辑 |

## 上游测试清点（R51 第一步）

- Makefile.am 无 `TESTS`/`check_PROGRAMS`；tarball 无 `tests/`、`testsuite/` 目录；无 dejagnu 集成
- **上游静态测试数 N_static = 0**（如实申报，无 `make check` 可跑）

## 消费者测试（test_package，N_consumer = 1）

`test.sh` 对 jwhois 二进制做 4 项行为断言（全部离线确定性）：

1. `jwhois --version` 输出含 `jwhois version 4.0`，退出码 0
2. `jwhois --help` 输出含 `Usage: jwhois`，退出码 0
3. `-c /nonexistent/...` 缺失配置路径：打印 `Unable to open` 且退出码非 0（src/init.c `exit(1)`）
4. `-h 127.0.0.1 -p 1` 连接被拒路径：打印 `Unable to connect` 且退出码非 0（src/whois.c `exit(1)`）

（实际运行结果见验证结果节与 PR 正文；run 结果回填）

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | tarball 静态清点（Makefile.am/目录结构） |
| 构建系统注册 N_registered | 0 | 无 check 目标 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（4 断言） | test_package/test.sh |

## 源码修改（补丁）

| 补丁 | 原因 | 内容 |
|---|---|---|
| `patches/0001-src-Makefile-am-libgnu-builddir.patch` | VPATH（树外）构建时 gnulib 静态库生成于 build 目录，2007 年版 `src/Makefile.am` 硬编码 `$(top_srcdir)/gl/libgnu.a` 导致链接期 `No rule to make target` | `jwhois_LDADD` 改用 `$(top_builddir)/gl/libgnu.a` |
| `patches/0002-src-Makefile-in-libgnu-builddir.patch` | 同上，对随包发行的 `src/Makefile.in`（`jwhois_DEPENDENCIES` + `jwhois_LDADD` 两处；CI 无 autoreconf 不能重生成） | 同上两处替换 |

## 依赖版本

无外部依赖（gl/ 内嵌 gnulib 静态编入；仅链接 libc）。

## 路径 B 判断

- 症状/根因层面：本包未触发新的跨仓库知识（configure 自带、无 autoreconf、无系统同名库冲突、res_* 缺失本包不涉及）。
- `--disable-nls` 在 GNU 包中是已广泛使用的既有模式（仓库已有先例），非新增可复用知识。
- 结论：**纯路径 A，不申报路径 B**。查重依据：无新错误签名产生，无新 E 条目草稿生成。

### 对话 #1（2026-09-13，GLM-19）

状态: built

- W0/W0b：预检通过（零外部依赖）；上游无历史归档与历史 notes
- 语言预检：c，autotools，源文件占比 100%，通过
- 配方：conan-init 模板首稿 + 三轮修复（--build triplet 规避 config.guess；E011 umask 022；VPATH libgnu 补丁 ×2）
- conan-verify：rc=0（G0-G4/L2/L4/L5 全过），消费者测试 4/4 断言 PASS
- finish：W3 本地 CI 模拟通过；状态 built
- configure 参数与耗时：`--disable-nls --build=aarch64-unknown-linux-gnu`，单文件包 make -j1 数分钟内完成
- 编译结果：bin/jwhois 正常产出；遇到的问题见上方问题表

## 验证结果

- conan-verify（round3，2026-09-13 01:59，rc=0）：G0/G1/G2（conan create 干净构建）/G3/G4/L2/L4/L5 全部通过
- 消费者测试 test_package/test.sh 真机执行输出（见 reports/conan-create.log，4 项断言全过）：
  - `jwhois --version` → `jwhois version 4.0` 断言 OK
  - `jwhois --help` → `Usage: jwhois` 断言 OK
  - 缺失配置路径 → `Unable to open` + 退出码非 0 断言 OK
  - 127.0.0.1:1 连接被拒路径 → `Unable to connect` + 退出码非 0 断言 OK
  - `ALL CONSUMER TESTS PASSED`
- 编译告警仅 2 处 `-Wpointer-sign`（getsockopt 的 socklen_t，musl 与 glibc 类型差异）与 `timeout_init` 隐式声明（上游遗留），均不影响功能
