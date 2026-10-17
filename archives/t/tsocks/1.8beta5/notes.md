# tsocks 1.8beta5 适配笔记（HarmonyOS PC）

- 适配路径：路径 A（上游 configure 直编 + 三个可移植性处置，无知识库扩展新机制）
- 使用知识库：config.guess/config.sub 短路放行族（OHOS autotools 先例）；musl 头文件族（sys/poll.h → poll.h）
- 知识库扩展：B判定=none（终），理由见登记表——所有症状均有既有条目覆盖，无新机制签名
- 关联 Issue：-（无新增机制）

## 上游与取源

- 官方上游：http://tsocks.sf.net（sourceforge 项目 tsocks，1.8 beta 5，2002）
- 源码包 sha256：849d7ef5af80d03e76cc05ed9fb8fa2bcc2b724b51ebfd1b6be11c7863f5b347
- 实测 Debian +ds1 orig 与官方 sourceforge 件逐字节相同（同一哈希），配方取官方 URL
- 语言 C（6 个 .c），构建 configure（2002 年 autoconf 2.13 生成）+ Makefile（无 VPATH、无 libtool）

## 症状 / 根因 / 处置

| # | 症状 | 根因 | 处置 |
|---|------|------|------|
| 1 | configure 报 unable to guess system type | 2001 年 config.guess 不识 aarch64-ohos；uname -s=HarmonyOS 至今最新上游 config.guess（2026-05）也不识别 | 不换脚本，configure 显式 --host=aarch64-linux-ohos（config.sub 已识别该三元组），config.guess 不再被调用 |
| 2 | configure: error: sys/poll.h not found | glibc 习语 sys/poll.h；musl/OHOS 只有 poll.h | 补丁 0001/0002：configure 与 configure.in 的探测与引用改 poll.h（不重生成 configure，避免 2.72 改坏 2.13 脚本） |
| 3 | 老自动 configure 报 no acceptable cc | autoconf 2.13 只探测 gcc/cc，不认 clang | 配方显式 CC/CXX=clang 注入（profile compiler_executables 回退 clang） |
| 4 | conan strip_root 失效，源码落在 tsocks-1.8/ 子目录 | tarball 条目带 ./ 前缀（./tsocks-1.8/...），conan 判不出单一根目录 | source() 内归一化：子目录内容上提一层 |
| 5 | make install 把库装到 /lib（Read-only file system） | 老 configure 对 --libdir 的默认值硬编码 /lib | configure 显式传 --libdir/--bindir/--includedir |

## 失败方案（走过的弯路，勿重复）

- VPATH 构建（driver 默认）：Makefile.in 无 srcdir/VPATH 变量，No rule to make target tsocks.o ⇒ 必须 in-tree。
- AutotoolsToolchain+Autotools 类：make 的工作目录与 configure 产物目录错位（HMDFS 负缓存叠加 getcwd 假错误）⇒ 改 valkey 式 self.run 直跑（cwd=source_folder, env=conanbuild）。
- conandata 补丁未配 patch_strip 时，本仓 conan 的 patch_ng 不自动剥 a/ 前缀（报 source/target file does not exist）⇒ 单文件补丁 + 根相对裸路径（strip=0 命中）。

## 适用边界

- 本体是 LD_PRELOAD 垫片库：G2 消费者测试以 dlopen+dlsym(connect) 证明 .so 在真机可加载、ABI 可解析（2/2 过）；完整 SOCKS 拦截链路依赖 /etc/tsocks.conf 与真实代理，不在包级测试面内。
- saveme 工具以 -static 链接，随包发布但不在消费者测试面。

## 测试账本（五维口径）

- N_static：0（上游无成体系测试入口；实测 configure/make 无 test 目标，tests/ 目录不存在）
- N_registered：0
- N_executed：0（无上游可执行测试）
- N_consumer：2（test_package/test.c：dlopen libtsocks.so + dlsym connect，日志原句 tsocks consumer test passed: 2 assertions）
- 通过率：消费者 2/2；上游 N/A（分母为 0，不虚报）

## 验证结果

- conan-verify：G0/G1/G2/G3 PASS，L2/L4/L5 见 reports/conan-verify-report.md（✅ 配方验证通过，可标 published）
- 编译环境：A 机（HarmonyOS PC aarch64），CONAN_HOME ~/tmp/ch/home-tsocks，profile ci/conan/profiles/ohos-aarch64
---

**编译结束**: 2026-09-26 03:24
**最终状态**: built
