# QDirStat 2.0 目标验证

| 项目 | 结果 | 依据 |
| --- | --- | --- |
| 源码与依赖 | PASS | 官方 tag 2.0 SHA-256 `a0b2ba91caf68ec4ee7705d5063bc542ac8aea4d421451103245c69d272bf19f`；四项依赖在 ohpcd 已发布。 |
| `conan create` | PASS | q3 真机 RC 0；日志 SHA-256 `34c17c43fb5d36c7e7d0ec560ea9372f290ec4131fd47d396d138b5ab4e58705`。 |
| 上游自动测试 | 无入口（N=0） | `test/` 仅有数据包及 `create-files`；`qdirstat.pro`、`src/src.pro` 无 test target，不伪造通过率。 |
| 安装包消费者 | 1/1 PASS | `QT_QPA_PLATFORM=offscreen` 下启动已打包签名的 GUI 程序，核对 `--help` 用法和退出码。 |
| 事务完整性 | PASS | q3 单次 launch、独立传输回读、release/postrelease、冻结 validator PASS。 |
| 比赛 PR CI | 待验证 | 本地真机 PASS 不等于比赛 worker PASS。 |

q1、q2 是独立失败事务：前者在 `Translator.cpp` 因 `dgettext` 未声明停止；后者在最终链接因 Qt5Compat 错误绝对路径停止。两轮均按各自终态释放，未把不同 run 的结果拼接为 PASS。
