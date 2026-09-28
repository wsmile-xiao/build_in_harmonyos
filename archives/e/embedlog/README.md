# embedlog

embedlog — Simple and fast C logging library (log4j-like).

- 上游：https://github.com/mlyszczek/embedlog
- 版本：0.7.2（HarmonyOS PC aarch64 适配）
- 构建系统：autotools（tarball 无预生成 configure，build() 内 autoreconf -fi 引导）
- 制品：静态库 libembedlog.a（R26 系统同名库静态策略），公开头文件 include/embedlog.h
- 适配笔记：见 0.7.2/notes.md；测试台账：见 0.7.2/reports/test-report.md
- 覆盖版本：0.7.2