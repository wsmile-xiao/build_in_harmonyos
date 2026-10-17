# cfm 0.6.6 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-20
- 编译器: /data/service/hnp/bin/clang (aarch64-unknown-linux-ohos, clang 15.0.4)
- 状态: built

## 编译步骤

1. 官方源码：https://github.com/sophec/cfm/archive/refs/tags/v0.6.6.tar.gz
   SHA-256: 7977431d8074d3a2f0dad4e431e558201073631fa5f0e7d92b37b100feae6ed3
2. `make -j1`（Makefile 自动从 config.def.h 生成 config.h）
3. 产物：cfm（ELF, aarch64, musl dynamic）
4. pty 驱动运行验证：TUI 渲染转义序列正常，`q` 退出码 0
5. 非 TTY 运行（stdin 关闭）快速退出 0，可用作冒烟

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 失败：`install: No such file or directory` | HarmonyOS 环境无 GNU install 命令（知识 E108/E182） | 配方 package() 用 conan copy() 直接拷贝 cfm 与 cfm.1，不依赖 make install |

## 源码修改

无补丁（原始官方源码直接构建）。

## 依赖版本

无运行时/构建依赖（纯 libc/POSIX + termios）。

## 验证结果

- conan create（ohos-aarch64 profile）通过
- 消费者用例：pty 驱动 `cfm <dir>` → TUI 渲染（\x1b[ 转义序列）+ `q` 退出码 0
- C 消费者：fork+execvp(cfm, <mkdtemp 临时目录>) 关闭 stdin → 干净退出 0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 型配方（application），package() 拷贝 bin/man |
| conandata.yml | 官方 GitHub archive URL + SHA-256 |
| test_package/ | 消费者测试（pty TUI 渲染 + C fork/exec 冒烟） |
| commands.json | R38 CLI 工具声明（软件级） |

## 注意事项

- cfm 无 `--version/--help` 参数（argc==1 视为目录）；L2 冒烟对 `--version` 返回非 0，
  属上游行为，不做补丁（TUI 工具以 pty 渲染作为冒烟证据）。
- 上游无任何测试（tarball 全文件枚举确认无 tests/、无 check 目标）。
---

**编译结束**: 2026-09-20 21:43
**最终状态**: built
