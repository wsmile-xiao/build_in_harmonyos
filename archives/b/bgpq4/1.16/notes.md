# bgpq4 1.16 适配笔记

## 上游信息

- 上游仓库：https://github.com/bgp/bgpq4
- 版本：1.16
- 源码包：https://github.com/bgp/bgpq4/archive/refs/tags/1.16.tar.gz
- SHA256：c228e44bb62141851e7213563b5800b9b7b56d183f71563d5f0fe1ecdf57709e
- 许可证：BSD-2-Clause（见 COPYRIGHT）

## 构建系统

上游项目使用 Autotools，但 1.16 的 GitHub tag archive 只有 `configure.ac`、`Makefile.am` 和 `bootstrap`，没有预生成的 `configure`。早期 PR 修复为随配方提交完整 Autotools/libtool 生成文件，以绕过 CI worker 缺少 `aclocal` 的问题，这导致 PR diff 异常膨胀。

当前配方改为直接编译上游 C 源码。`bgpq4` 的交付物是单个命令行程序和 man page，直接编译可以保留真实适配内容，同时删除 `configure`、`Makefile.in`、`ltmain.sh`、`m4/*.m4` 等生成文件。

## 测试

- 上游测试统计：上游拥有 44+ 个可识别检查点；1.16 tag archive 中 `tests/reference/` 有 44 个参考输出文件，由 `tests/generate_outputs.sh` 生成和比较，同时当前配方还验证 `bgpq4 -v` 版本路径。
- 未纳入 CI 的上游回归：参考输出回归依赖实时 IRR 数据、DNS 和外部网络，不适合作为比赛隔离 CI 的确定性门禁；后续可将 `generate_outputs.sh` 与 `tests/reference/` 的可离线部分拆成独立 Issue 深度移植。
- 构建阶段：当构建机可运行目标程序时执行 `bgpq4 -v`。
- `test_package`：执行打包后的 `bgpq4 -v` 并检查版本输出，同时执行离线 Junos prefix-list 输出格式检查，验证 `bgpq4 -J 192.0.2.0/24` 会生成包含 `prefix-list` 和目标前缀的输出。
- 当前包内测试通过率：4/4 个 smoke assertions 通过（版本关键字、版本号、prefix-list 关键字、目标前缀）。

## CI 修复记录

- 2026-07-16：早期 CI 在 `./bootstrap` 阶段失败，原因是 OHOS worker 缺少 `aclocal`。
- 2026-07-16：曾临时提交完整预生成 Autotools 文件让 CI 通过，但造成 PR 文件改动量异常。
- 2026-07-16：改为直接 C 编译，删除生成文件，避免对 CI Autotools 工具链的依赖。

## 已知限制

上游完整在线 IRR 查询依赖外部网络和实时数据，结果可能受网络环境影响；确定性验证使用 `bgpq4 -v`。
