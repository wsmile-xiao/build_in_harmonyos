# agnostic-lizard

best-effort portable code walker for Common Lisp(`macroexpand-all` 及配套工具)。

- 平台任务:`agnostic-lizard/0~git20201010.1.fe3a737`(10 火种)
- 当前版本:`0~git20201010.1.fe3a737`(Debian 打包版 -2;conan/分支名中 `~`→`-`)
- 上游:https://gitlab.common-lisp.net/mraskin/agnostic-lizard
- Debian 源包:https://snapshot.debian.org/package/agnostic-lizard/0%7Egit20201010.1.fe3a737-2/
- 形态:**纯 Lisp 源码包**（27 个文本资产，生产包 noarch、无外部 ASDF 系统依赖）。
  不生成目标机器码不等于没有可执行语义；逐文件 SHA-256 只验证资产完整性，不能豁免功能回归。
  测试使用已发布的 OHOS ECL 24.5.10 和真实 ASDF，分别完整执行官方
  `examples.lisp` 与 `walking-examples.lisp` 两个核心回归入口，另有安装后消费者
  和独立 HMDFS 中文路径读写测试；本轮真机结果为 2/2、1/1、1/1 PASS。
  编译模式、其他 Lisp 实现、调试器和外部库互操作不在本轮已验证范围内。
- 消费:ASDF 实现(SBCL/CCL/CLISP 等)注册 `share/common-lisp/source/agnostic-lizard`
  后 `(asdf:load-system "agnostic-lizard")`;配方导出 `AGNOSTIC_LIZARD_SRC_DIR`
  与标准 `CL_SOURCE_REGISTRY`；测试通过 ASDF `load-source-op` 加载真实源码，
  不伪造 ASDF、不删减官方断言。
- 许可:GPL-3.0-or-later
