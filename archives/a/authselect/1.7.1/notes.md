# authselect 1.7.1 — OHOS aarch64 适配笔记

## 上游信息

- 项目：authselect/authselect
- 版本：1.7.1（2026-01-20 发布）
- 仓库：https://github.com/authselect/authselect
- 构建系统：Autotools（configure.ac + Makefile.am）
- 许可证：GPL-3.0-or-later
- 语言：C (85%)

## 依赖

| 依赖 | 类型 | 适配状态 |
|------|------|----------|
| popt 1.16 | 构建/运行时 | archives/p/popt — partial |
| libselinux 3.10 | 构建/运行时 | ohpcd remote 已发布 |
| libcmocka 2.0.2 | 测试（构建时） | archives/c/cmocka — built |
| gettext 0.22.5.1 | 国际化（构建时） | archives/g/gettext — 已存在 |

## 上游测试

- 3 个 cmocka 单元测试：`test_util_string_array`、`test_util_evaluator`、`test_util_template`
- 3 个 pytest 系统测试：`test_cli.py`、`test_local.py`、`test_sssd.py`
- 入口命令：`make check`（单元测试）/ `pytest`（系统测试）

## 已知适配要点

1. libselinux 3.10 是唯一需要新建配方的强制依赖，其余三个已有配方。
2. Autotools 需要 `autoreconf -i` 生成 configure 脚本（上游未预生成）。
3. 需 OHOS config.guess/config.sub 替换（标准 E007 portability 补丁）。
4. upstream 测试中的系统测试需要 SSSD/PAM 环境，OHOS 上需排查兼容性。
5. CLI 工具，R38 需要 `commands.json`。
---

**编译结束**: 2026-08-26 10:19
**最终状态**: published
