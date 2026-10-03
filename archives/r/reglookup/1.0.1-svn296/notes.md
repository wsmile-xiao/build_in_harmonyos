# reglookup 1.0.1-svn296 适配笔记

- 构建环境：HarmonyOS PC aarch64，clang 15，Conan 2；2026-10-01。
- 源码：Debian 上游归档 `reglookup_1.0.1+svn296.orig.tar.xz`，SHA-256 `0deff234d6a4e3b13be410fb532df012ba4921e89676f627c177d035b1b88893`。
- 依赖：talloc/2.4.4。上游 `SConstruct` 默认搜 `/usr/local/include`、`/usr/include`、`/usr/lib`；配方从 Conan 依赖读取绝对路径。
- 目标机无 SCons，制品仓无 SCons 配方；按 `SConstruct` 明示的 `regfi.c`、`winsec.c`、`range_list.c`、`lru_cache.c`、`void_stack.c` 构建 `libregfi`，再分别编译 `reglookup.c` 和 `reglookup-recover.c`。`common.c` 由两者的 `#include` 引入，不重复编译。
- 上游源码内 `REGFI_VERSION` 实际为 `1.0.1.283`；任务版本 `1.0.1-svn296` 是归档标签。二者不应混写。
- 不构建 DocBook 手册与 Python 绑定；核心 C 库及两条 CLI 均构建并打包。共享库 SONAME 别名实体化，ELF 目标机签名。
- 上游无自动测试目标、无示例 hive，记为 `0/0`。消费者测试在目标机调用安装后的 `range_list` 公开 API，8 个断言通过；真实 hive 解析仍需样本做端到端验证。
- 首次冻结输入真机事务 `reglookup-w3-20260930T161921Z` 为 `W3_PASS`。配方许可证和测试元数据修正后，最终文件重新冻结为 `reglookup-w3-20260930T173100Z`，12/12 收据 `W3_PASS`；最终日志 SHA-256 `0cc993be2da4481a54804ce261e3087dab39e856ed2300802038aabd31f5d673`。
