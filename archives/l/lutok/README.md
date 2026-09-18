# lutok

Lightweight C++ API for Lua — a RAII C++ wrapper over the Lua C API
(base building block of the FreeBSD/ATF test stack).

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/jmmv/lutok |
| 版本 | 0.6.2 |
| 许可证 | BSD-3-Clause |
| 构建系统 | GNU Autotools（官方 release 附件自带 configure） |
| 依赖 | lua/5.4.8；测试依赖 atf/0.23（test_requires） |
| 状态 | built |

## 适配要点

- config.guess 不识别 HarmonyOS：显式 `--build/--host=aarch64-unknown-linux-gnu`；
- Lua 经 pkg-config 探测（`lua-5.4` 优先，PkgConfigDeps 生成）；
- 上游测试 `--enable-atf` 开启，kyua 不可用时以 ATF `-l` + 逐用例接口全量执行
  （6 个 atf-c++ 程序 97 用例 + examples_test 4 用例，全部通过）；
- atf/0.23 的 `.pc`/`.la`/编译期 shell 路径不可迁移：配方自写 `.pc`、
  以 `.a` 拷贝目录绕开坏 `.la`、运行 examples_test 前修正 ATF 环境变量；
- lua 制品缺 `lua.hpp`：配方生成标准包装头并随包安装（消费者可直接包含
  `<lutok/c_gate.hpp>`）；
- HMDFS `mktemp -d` 不可写：mkdir 版 shim 前置 PATH。

详见 [0.6.2/notes.md](0.6.2/notes.md) 与 [0.6.2/reports/](0.6.2/reports/)。
