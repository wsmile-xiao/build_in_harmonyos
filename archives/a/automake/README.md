# GNU Automake

GNU Automake 自动生成符合 GNU 标准的 Makefile.in 文件。

## 特殊说明

automake 是**纯 Perl 项目**，构建存在鸡生蛋问题：
- automake 的 `make` 需要 `bin/automake` 脚本，但该脚本依赖 `Config.pm`
- `Config.pm` 由 configure 生成，但 make 规则会尝试用尚未构建好的 automake 重新生成 Makefile.in

解决方案：使用 `gen-all.pl` 手动执行 @VAR@ 替换，绕过标准 make 流程。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.16.5](./1.16.5/) | published | 2026-04-09 |
| [1.17](./1.17/) | built | 2026-04-25 |
| [1.18](./1.18/) | published | 2026-07-30 |
| [1.19](./1.19/) | built | 2026-09-26 |
