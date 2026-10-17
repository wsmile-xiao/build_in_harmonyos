# spell 1.1 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，1996 年代脚本）
- 编译日期: 2026-09-13
- 编译器: clang（OHOS aarch64 交叉工具链）
- 状态: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` 风险（jwhois/marst 同批实测命中） | 老年版 config.guess/config.sub 在 OHOS 上无法猜测且不认识新 triplet | generate() 在 `os == "OHOS"` 时追加 `--build=aarch64-unknown-linux-gnu`（adms 配方先例） |
| 2 | `config.status` 阶段 conf* 临时文件 Permission denied 风险（E011，实测 configure 含 2 处 `umask 077`） | HMDFS UID 映射使 umask 077 临时文件不可读写 | 按 E011 受控方案在 build() 内替换为 022（gsl/2.8 同款实现） |
| 3 | VPATH 构建下 `fatal error: 'config.h' file not found`（实测命中） | 1996 年 Makefile 以 `-I$(srcdir)` 解析 config.h，而 VPATH 布局中 config.h 生成在 build 目录，源码目录里没有 | 改为**树内构建**：configure/make/install 直接在源码目录执行（conanbuild env），`--prefix` 指向包目录，安装直达包文件夹 |

## 上游测试清点（R51 第一步）

- Makefile.in 的 `check:` 目标为**空**；tarball 无 tests/ 目录、无任何测试框架
- **上游静态测试数 N_static = 0**（如实申报）

## 消费者测试（test_package，N_consumer = 1）

`test.sh` 对 spell 二进制做 3 项行为断言（全部离线确定性）：

1. `spell --version` 输出含 `GNU Spell 1.1`，退出码 0
2. `spell --help` 输出含 `Usage:`，退出码 0
3. 无效选项 `-Z` 走 getopt 错误路径，`exit(EXIT_FAILURE)` 非零退出

注：spell 运行时引擎是外部 ispell/aspell（OHOS 无此引擎），故拼写检查主功能不在离线断言范围；消费者测试覆盖参数处理与错误路径的真实行为。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | tarball 静态清点（check 目标为空） |
| 构建系统注册 N_registered | 0 | 空 check 目标 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（3 断言） | test_package/test.sh |

## 源码修改

无补丁（patches: {}）。

## 依赖版本

无编译期依赖（仅 libc）。运行时引擎 ispell/aspell 为可选外部程序，OHOS 不提供。

## 路径 B 判断

- 本包构建期问题均为仓库已知模式（--build triplet、E011 umask），无新错误签名、无新跨仓库知识。
- 结论：**纯路径 A，不申报路径 B**。

## 验证结果

- conan-verify（2026-09-13 11:37，rc=0）：G0/G1/G2（conan create 干净构建）/G3/G4/L2/L4/L5 全部通过
- 消费者测试 test_package/test.sh 真机执行输出（见 reports/conan-create.log）：`--version`/`--help`/无效选项三断言全过 → `ALL CONSUMER TESTS PASSED`

### 对话 #1（2026-09-13，GLM-19）

状态: built

- W0/W0b：预检通过（零编译期依赖）；上游无历史归档与历史 notes
- 语言预检：c，autotools，通过
- 配方：conan-init 模板首稿 + 三项适配（--build triplet；E011 umask 022；树内构建）
- conan-verify：rc=0（G0-G4/L2/L4/L5 全过），消费者测试 3/3 断言 PASS
- configure 参数与耗时：`--build=aarch64-unknown-linux-gnu --prefix=<包目录>`，make -j1 数分钟
- 编译结果：bin/spell 正常产出
---

**编译结束**: 2026-09-13 12:07
**最终状态**: built
