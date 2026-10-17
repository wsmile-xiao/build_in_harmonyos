# memchan 2.3 HarmonyOS PC 适配笔记

## 编译环境

- 目标平台：HarmonyOS PC（OHOS 6.0，AArch64）
- 编译器：Clang 15
- 构建系统：Autotools/TEA
- Conan 依赖：`tcl/8.6.16`
- 状态：全部构建与测试通过

## 编译与打包

配方从 SourceForge 官方发布包构建，使用 Conan 提供的 Tcl 配置执行
`configure --with-tcl=<tcl-package>/lib tcl_cv_sys_version=Linux-6.6`，随后只构建
`binaries libraries`，避免文档生成器成为运行库构建的额外依赖。打包阶段执行
`install-binaries install-libraries`，安装共享库、stub 库、头文件和 `pkgIndex.tcl`。

## 适配修改

| 补丁 | 问题 | 解决方案 |
|---|---|---|
| `0001-configure.patch` | 旧版 `config.status` 以 `umask 077` 创建临时目录，在 HMDFS 上可能不可执行 | 使用 `umask 022`，保持临时目录可访问 |
| `0002-isaac-rand.h.patch` | 1990 年代风格的空参数声明在现代 C 模式下被解释为无参数函数 | 增加严格原型，并显式保留带种子的 ISAAC 初始化 |
| `0003-isaac-randport.c.patch` | K&R 函数定义不兼容当前编译器的严格 C 语义 | 改为 ANSI C 函数定义 |

## 测试结果

- 上游 legacy 套件：38/38 通过。
- 上游 TEA black-box 套件：15/15 通过。
- 上游合计：53/53 通过，失败 0，跳过 0。
- 消费者测试：7/7 通过，覆盖 `package require`、memchan、fifo、null、zero、random。
- HarmonyOS 特有测试：延迟非阻塞 channel 的 `fileevent` 事件循环路径通过。
- 总计：60/60 通过，测试数量不低于上游实测数量。

## 交付物

包内提供 `lib/Memchan2.3/libMemchan2.3.so`、`libMemchan2.3stub.a`、
`pkgIndex.tcl` 和公开头文件，可由 Tcl 的 `package require Memchan 2.3` 直接加载。

**编译结束**: 2026-09-27
