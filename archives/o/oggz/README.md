# oggz

oggz（liboggz 1.1.3）是在 libogg 之上提供 Ogg 流解析/生成/操作的高层 C 库，
并附带 oggz 命令行工具集（oggz-dump/info/merge/rip/chop/sort/validate/codecs/
comment/known-codecs/scan 及 oggz-diff 脚本）。

- 上游: https://www.xiph.org/oggz/
- 依赖: libogg/1.3.6.1（系统同名库, 强制静态, R26）
- 平台: OpenHarmony PC (aarch64-linux-ohos), musl, clang 15
- 构建: autotools (conan 配方)
- 版本状态: 1.1.3 = built（conan-verify G1-G4/L2/L4/L5 通过）

版本索引见 manifest.yaml；命令行工具声明见 commands.json（R38）。
