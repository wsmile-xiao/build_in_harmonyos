# QDirStat 2.0 HarmonyOS PC 适配记录

- 官方源码 SHA-256：`a0b2ba91caf68ec4ee7705d5063bc542ac8aea4d421451103245c69d272bf19f`。依赖已发布的 `qtbase/6.11.1`、`qt5compat/6.11.1`、`zlib/1.3.2` 和 `gettext/0.22.5.1`。
- q1 的首个真实失败是 OHOS sysroot `libintl.h` 缺少 `dgettext` 声明；显式使用 gettext 包头文件和 `-lintl`，保留上游翻译功能。
- q2 源码编译完成后，qmake 生成了指向 `qtbase/lib/libQt6Core5Compat.so` 的错误绝对路径；实际库在独立 `qt5compat` 包。配方只在构建目录覆盖 Qt5Compat 的 qmake 模块描述，并在编译前核对 Makefile 链接路径，不改上游源码、Qt 包或 sysroot。
- 上游 `test/` 只有测试数据及文件生成器，顶层和 `src/` qmake 项目均没有自动化测试 target，故上游自动测试分母是 0，而不是声明 0/0 PASS。
- q3 真机冻结事务：`conan create` RC 0，安装后消费者离屏执行 `qdirstat --help` 为 1/1 PASS；release、postrelease、validator 均 PASS。原始日志 SHA-256：`34c17c43fb5d36c7e7d0ec560ea9372f290ec4131fd47d396d138b5ab4e58705`。
- 可复用知识聚焦分包 Qt 模块的 qmake 绝对库路径，见 `knowledge/drafts/E892-draft-QD1`；比赛 worker CI 与 AI Review 尚待 PR 创建后验证。
