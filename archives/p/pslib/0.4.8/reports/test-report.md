# pslib 0.4.8 — HarmonyOS PC 验证报告

- 日期：2026-09-26
- 环境：HarmonyOS aarch64 / OHOS 6.0、Clang 15、Conan 2.29.1
- 当前验证输入：`pslib-w3-20260926T082400Z`，候选 SHA-256 `4a5a2970bcc3ece067e07b41f26dd7a3c6fa4c41518b9ddb52d0c672255b3304`
- 当前原始日志 SHA-256：`6e0fb01f926e98bf9315f5a274effbec244824ab68d5f8bb1ab6b05737494161`

## 结论

针对 CI #61625 的 `config.status: subs1.awk: Permission denied` 调整配方后，当前目标机 `conan create` 返回 0，安装包消费者 1/1 PASS，W3 冻结验证器返回 `W3_PASS`，12/12 阶段回执完整，任务进程已退出并释放。CI 对此新提交尚待重跑，不预称 CI 已修复。`configure` 确认 PNG 和 JPEG 支持均启用。上游发行包没有注册测试用例，故上游通过率是 0/0（不适用），不是伪造的 100%；但完整执行了上游 `make check -j1`，退出码为 0，包含 `po` 的 catalog 检查。

| 项目 | 数量/结果 | 依据 |
|---|---:|---|
| 上游注册测试 | 0/0（不适用） | `upstream-test-inventory.txt`；`make check -j1` 日志 |
| 安装后消费者 | 1/1 PASS | `test_package/test.c` 生成并检验一页内存 PostScript 文档 |
| 构建/打包 | PASS | Conan package `0735cfed086ab2582fd5fb1a97464975bdcccd70` 创建成功 |
| 图片格式探测 | PNG=yes、JPEG=yes | `configure` 检测行与 `config.h` 严格校验 |

## 失败到恢复

早期四次独立尝试依次发现：缺 intltool、缺 gettext、缺 XML::Parser、预编译 XML::Parser XS 与设备 Perl ABI 不兼容。初版目标机 W3 `pslib-w3-20260926T024600Z` 已 PASS，但平台 CI #61625 在 HMDFS 上创建 `config.status` 临时目录后读取 `subs1.awk` 被拒绝。前一版仅将 `mktemp -d` 的 umask 放宽到 022；`mktemp -d` 仍固定创建 0700 目录，故 CI 继续失败。当前候选在预生成 `configure` 中用带 PID/随机后缀的原子 `mkdir`，创建时使用 `umask 007` 使目录组可访问，不依赖事后无效的 chmod。此模式复用现有 E129/E6340 的 HMDFS 创建时权限知识。新 W3 是独立事务，没有拼接此前通过记录。配方仍保留真实 intltool/gettext 工具，以当前设备 Perl 的构建目录包装器处理过时 shebang，并仅在关闭 NLS 时跳过不需要的 XML 模块检查。该新增知识边界见 `knowledge/drafts/E6402-draft-8B7F.md`。

## 限制

- GIF/TIFF 可选支持未启用，消费者未覆盖这些格式。
- 上游没有自动注册测试；本报告不声称全 API 覆盖。平台 AI Review 曾对旧 HEAD 给出“未发现问题”；当前修复后的 CI/Review 仍须重新回读，不借用旧结果。
- 目标机上游源码存在原有 Clang 告警，本次构建未将它们当作测试通过的替代证据。

## 当前难度重判

依据当前配方、上游测试清单、CI #61625 错误和本次 W3 日志（SHA-256 如上）：`HD1_PRIVATE_OS_INTERFACES=false`，只使用公开 C/Autotools 接口；`HD2_PRIVATE_TOOLCHAIN=false`，使用已发布的 Clang、Perl、intltool/gettext；`HD3_COMPLEX_ARCHITECTURE=false`，无多进程或私有系统组件；`HD4_LARGE_DEPENDENCY_TEST_COST=false`，上游注册测试为 0，两个链接依赖及两个构建工具均已发布。CI 的 HMDFS 权限问题有 E129/E6340 的相关先例，当前候选仍待 CI 实测，不单独申报高难条件。因此路径仍为 A+B，标题保留 `【知识库扩展】`；本次新增知识仍是 NLS/Perl XS ABI 的可复用边界。
