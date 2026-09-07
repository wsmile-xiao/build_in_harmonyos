# libiconv 1.17.1 适配修复记录

## 修复目标

本版本修复已发布 `libiconv/1.17` 制品的消费者兼容性问题。旧制品中的 `libtool` 元数据文件包含构建机绝对路径及 `libdir='//lib'`，会被 Autotools 消费者读取，导致 iconv 能力检测和运行时链接失败。该问题已在 GnuPG 2.4.9 适配中复现，并影响 GMime 的 EUC-KR→UTF-8 与 UTF-8→ISO-2022-JP 场景。

## 修复内容

- 版本号从 `1.17` 递增为 `1.17.1`，源码仍使用官方 GNU libiconv 1.17 发布包。
- 保留原有 4 个 HarmonyOS Autotools 兼容补丁；移除会降低临时文件安全权限的 `umask 022` 补丁，保持上游 `umask 077`。
- Conan `package()` 安装完成后删除 `lib/*.la`，不向消费者暴露不可移植的 libtool 元数据。
- 保留 `libiconv.a`、`libcharset.a`、头文件和 `iconv` 工具。
- 消费者测试覆盖 UTF-8→ASCII、EUC-KR→UTF-8、UTF-8→ISO-2022-JP。

## 测试要求

- 上游完整测试：在配置成功后执行 `make -j1 check`，不得只执行单个 `tests/check-*` 脚本。
- 消费者回归：执行 `test_package`，确认上述 3 个 API 转换场景全部通过。
- 上游完整测试：`make -j1 check` 在 Conan 构建目录 `build-release/` 通过，递归执行上游 `check`（包含 `tests/`），展开 201 个测试命令，结果 201/201。证据见 `reports/test-report.md`，对应 Conan recipe `8545618022496ff2c0d87bbd8ac61f86`。
- 消费者回归：Conan `test_package` 通过，3/3（UTF-8→ASCII、EUC-KR→UTF-8、UTF-8→ISO-2022-JP）。对应包 ID `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`，package revision `fcd1c297e8323d8ba957441b00499c71`。
- 包内容检查：最终包不包含任何 `*.la` 文件。
---

**编译结束**: 2026-09-05 15:01
**最终状态**: built
