# kamailio-xml 6.0.6 适配笔记

## 任务对应关系

积分赛任务 `kamailio-xml` 对应 kamailio 6.0.6 源码树内的 **xmlops** 模块
（XML operations，基于 libxml2 的 XML 伪变量 `$xml` 支持，含 XPath 求值）。
源码树无名为 `xml` 的模块；`presence_xml`/`xmlrpc` 是另外的独立模块（对应其他任务）。

## 编译环境

- 构建系统: kamailio 经典 Makefile（src/Makefile + Makefile.defs），非 CMake 主导
- 依赖: libxml2/2.15.3.1（conan 制品仓已发布，W0 通过）
- 配方骨架: 复用 archives/k/kamailio-tls/6.0.6 同族先例（PLATFORM_DEFS 宏集一致）

## 构建要点

1. `make cfg include_modules=xmlops` + `make modules modules=modules/xmlops`
2. `PKGCFGTOOL=`（make 命令行变量）钉死模块 Makefile 的 LOCALBASE 回退分支，
   防构建机 xml2-config/pkg-config 劫持探测（与 kamailio-tls 的 SSL_BUILDER= 同思路）
3. `LOCALBASE=<conan libxml2 包目录>` + CPATH/LIBRARY_PATH 注入依赖路径（R33）
4. extra_defs 平台宏集照抄 kamailio-tls（OS=harmonyos 不在 Makefile.defs 平台分支内）

## 上游测试清点（R51 三步法）

1. **清点**：源码包顶层无 `test/` 目录；`src/modules/xmlops/` 仅源码+doc，无测试源文件，
   无 add_test/enable_testing；`src/Makefile` 无 check 目标。上游可运行测试数 = 0。
2. **运行**：无可运行环境（上游无测试）。
3. **回填**：适配后补全 1 个消费者用例（test_package/check_xmlops.py，7 项实质检查：
   ELF 架构 / libxml2 API 符号链入证据 / module_exports 模块契约 / 许可证 /
   动态段 RPATH-RUNPATH / NEEDED libxml2）。

## 遇到的问题与解决

- 初版 check 脚本按 tls 先例查 `mod_register` 失败：xmlops 实际导出的模块契约符号是
  `module_exports`（kamailio 模块入口结构）。tls 能命中 mod_register 是其符号表中
  恰含该字符串。已改为查 `module_exports`。
- 初版宿主路径泄漏检查扫原始字节，误报 debug 信息中的 conan 缓存源路径。
  按 tls 先例口径改为查动态段 RPATH/RUNPATH（真正影响目标机加载的泄漏）。

## 状态

- conan create: 通过（test_package 7/7 PASS）
- 状态: built（待 CI upload 后 published）
---

**编译结束**: 2026-09-28 22:28
**最终状态**: built
