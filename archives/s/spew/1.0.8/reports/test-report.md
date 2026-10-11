# spew 1.0.8 测试报告

## 测试清点

| 测试类型 | 上游用例数 | 适配后用例数 | 执行结果 |
|----------|-----------:|-------------:|----------|
| 单元测试 | 0 | 0 | 上游未提供 |
| 集成测试 | 0 | 0 | 上游未提供 |
| 其他上游测试 | 0 | 0 | `make -j1 check` 完整执行并通过（0/0） |
| 鸿蒙特有消费者测试 | 0 | 10 | 10/10 通过 |
| **合计** | **0** | **10** | **10/10 通过** |

## 上游测试完整性证据

官方 1.0.8 标签归档共 85 个文件，无 `tests/` 目录或名称包含 test 的源码。根 `Makefile.am` 仅声明 `SUBDIRS = src man etc`；`src/Makefile.am` 未声明 `TESTS`、`check_PROGRAMS` 或 `check_SCRIPTS`；`configure.ac` 未注册测试框架。因此上游静态测试清单为 0。配方仍执行完整的 `make -j1 check`，日志显示 `src`、`man`、`etc` 全部 check 目标成功，未跳过或删除测试。

## 新增测试

`test_package/test.sh` 包含 10 个独立断言，全部实际调用打包后的命令：

1. `spew` 可执行文件存在。
2. `gorge` 可执行文件存在。
3. `regorge` 可执行文件存在。
4. `spew --version` 返回 1.0.8。
5. `spew --help` 返回真实工具说明。
6. 在 OHOS 私有可写 `TMPDIR` 中写入 numbers 模式数据。
7. 写入文件大小严格为 4096 字节。
8. `gorge` 读取并校验 numbers 模式数据。
9. `gorge` 对被人为破坏的字节返回失败（反向完整性断言）。
10. `regorge` 完成 alt 模式写入、读取和完整性校验。

其中第 6-9 项构成鸿蒙特有测试：明确避开只读 `/tmp`，在平台私有可写目录完成真实 I/O、数据完整性闭环与损坏检测。

## 实测结果

- 构建：通过。
- 上游测试：0/0，通过率不适用（上游无测试，完整 `make check` 退出码 0）。
- 新增测试：10/10（100%）。
- 强制源码重建：`conan create --build='spew/*'` 通过；`reports/w3-local-ci.log` 记录真实重建全过程（`RUN: autoreconf --force --install -fi`、编译、`make -j1 check`、test_package 断言 `10 passed, 0 failed`）。
- W3 本地 CI：通过；CI 同样以 `--build='spew/*'` 强制重建目标包。
- 依赖发布核验：`conan download --only-recipe -r=ohpcd` 对 popt/1.16、ncurses/6.6、automake/1.18 均通过。
- 验证日志：`reports/w3-local-ci.log`（真实重建 + 断言全量输出）、`reports/conan-create.log`（配方导出与 test_package 断言输出）、`reports/conan-verify-report.md`。
