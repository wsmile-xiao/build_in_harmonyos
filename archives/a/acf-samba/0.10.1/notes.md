# acf-samba 0.10.1 适配笔记

## 编译环境
- 构建系统: makefile (单一递归 Makefile, 纯 Lua 无 C 编译)
- 编译日期: 2026-08-09
- 编译器: clang/clang++ (未使用, 纯 Lua 模块)
- 状态: built

## 编译步骤

acf-samba 是 Alpine Configuration Framework 的 Samba 模块。
纯 Lua 实现, 无 C 源码, 无 configure 脚本。

1. `make -C <src> -j1 all` — Makefile 的 `all:` 目标为空操作, 仅验证 Makefile 语法
2. `make -C <src> install DESTDIR=<pkg> -j1` — 复制 samba-controller.lua, samba-model.lua,
   samba.menu, samba.roles + 2 个 HTML 视图模板 (.lsp) 到 `<pkg>/usr/share/acf/app/samba/`

config.mk 定义 `prefix=/usr`, `appdir=${datadir}/acf/app` (即 `usr/share/acf/app`).

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitLab 418 拦截 Conan 下载器 | gitlab.alpinelinux.org 对 urllib 反爬虫 | conandata.yml 添加 file:// 本地 fallback URL |
| 2 | init-build dual-track 失败 | HMDFS 拒绝硬链接 + 符号链接解引用失败 | 手动 `cp -a` 创建 work 目录, 绕过 Python shutil 限制 |

## 源码修改

无补丁。acf-samba 的 Makefile 仅用 `cp -a` 复制文件, 不依赖 coreutils `install`
(与 acf-core 的 bin/Makefile 补丁场景不同).

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| acf-core | 0.24.1 | 运行时框架依赖 (mvc.lua dispatch), 已通过 PR #4363 发布到 ohpcd |
| lua | 5.4.8 | Lua 运行时 (通过 acf-core 传递) |

## 验证结果

```
conan create archives/a/acf-samba/0.10.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
→ test_package: PASS=5 FAIL=0
  ✅ file exists: samba-controller.lua
  ✅ file exists: samba-model.lua
  ✅ file exists: samba.menu
  ✅ file exists: samba.roles
  ✅ controller has expected content

conan-verify: G0-G4 + L2/L4/L5 all PASS
W3 本地 CI 模拟: setup.sh ✅ + build_and_test.sh ✅
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (make all + make install) |
| conandata.yml | 源码 URL + sha256 + 本地 fallback |
| test_package/test_acf_samba.sh | L1 功能测试 (4 文件检查 + 内容完整性) |
| reports/test-report.md | 测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |

## 注意事项

- acf-samba 是纯 Lua 模块, 无二进制产物, 无 commands.json (R38 不适用)
- 上游无测试套件 (aports `options="!check" # no test suite`), test_package 采用自建功能测试
- 2 个符号链接 (samba-expert-html.lsp, samba-status-html.lsp) 指向 acf-lib 共享模板, 属上游预期行为
- acf-core 0.24.1 已发布到 ohpcd, 消费者用 `--build=missing` 可自动解析

---

**编译结束**: 2026-08-09 09:20
**最终状态**: built
