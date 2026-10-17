# fcgi2 2.4.2 适配笔记

## 编译环境
- 构建系统: autotools（GitHub archive 无 configure，需 autoreconf 自举；cliquer 同款）
- 编译日期: 2026-09-14
- 编译器: clang（OHOS aarch64 交叉工具链）
- 状态: built

## 语言预检说明（重要）

lang-preflight 曾误判 detected=perl：根因是 `perl/Makefile.PL`（辅助绑定目录）被
manifest 扫描按文件名命中（检测器 manifest 扫描未限定根目录，违反 SKILL §4.6 边界
「辅助脚本不算主体」与 §4.7「manifest 与统计矛盾→mixed」）。实际语言分布
c:12 / h:7 / cpp:2，perl 仅 2 个辅助脚本、java 6 个绑定文件均不参与构建。
本包主体为 C/C++（构建产物 libfcgi/libfcgi++/cgi-fcgi），按 SKILL 文档边界继续适配，
证据留档于此。已向用户汇报检测器 bug。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 无 configure | autoreconf 产物不进版本库 | tool_requires automake/1.18 + libtool/2.5.4（CI 缺自举工具），autotools.autoreconf() 自举（cliquer 同款） |
| 2 | cannot guess build type 风险 | 2007 年代 config.guess/sub | os==OHOS 时追加 `--build=aarch64-unknown-linux-gnu`（jwhois 先例） |
| 3 | E011 umask 077 风险 | 自举生成的 configure 含 umask 077，HMDFS 上临时文件不可写 | autoreconf 之后替换 022（顺序不能反，cliquer 注释明确） |

## 上游测试清点（R51 第一步）

- tarball 无 tests/ harness；Makefile.am 无 TESTS/check_PROGRAMS；examples/ 为独立示例程序；perl/ 为辅助绑定
- **上游静态测试数 N_static = 0**（如实申报）

## 消费者测试（test_package，N_consumer = 1）

`test.sh`：以使用者身份用 clang 编译 FastCGI 消费程序（FCGI_Accept 循环）链接安装后的
libfcgi，并以 CGI 回退模式运行（无 web server 派生时 libfcgi 服务单个 CGI 请求），
断言输出含 `fcgi-ok` 且退出码 0。编译输出进临时目录。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | tarball 清点 |
| 构建系统注册 N_registered | 0 | 无 check 目标 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（链接+运行断言） | test_package/test.sh |

## 源码修改

无补丁（patches: {}）。

## 依赖版本

无外部依赖（libfcgi 仅 libc；libfcgi++ 需 libstdc++）。

## 路径 B 判断

- 自举/umask/triplet 均为仓库已知模式；无新错误签名。
- 结论：**纯路径 A，不申报路径 B**。

## 验证结果

（待 conan-verify / W3 运行后回填）
---

**编译结束**: 2026-09-14 03:26
**最终状态**: built
