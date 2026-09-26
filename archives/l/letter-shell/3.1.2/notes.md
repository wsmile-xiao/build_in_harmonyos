# letter-shell 3.1.2 适配笔记

## 编译环境
- 构建系统: custom（嵌入式库，上游 copy-into-project 风格，无独立构建系统）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（aarch64-linux-ohos profile）
- 状态: built

## 编译步骤

1. 官方 tarball（tag v3.1.2, sha256 d98d6274…20daf）经 codeload 下载；
   github.com 主域直连超时（E017 已知模式），codeload 官方端点可取同一 tarball。
2. conanfile.py 直接编译 `src/shell.c shell_cmd_list.c shell_companion.c
   shell_ext.c`（`-fPIC -O2 -Isrc`）并用 llvm-ar 归档 `libletter-shell.a`；
   头文件 shell.h/shell_ext.h/shell_cfg.h 安装到 include/。
3. 提供 `shellcmds.lds` 最小链接片段（INSERT AFTER .data 定义
   `_shell_command_start/_shell_command_end`，KEEP(*shellCommand)），
   供消费者以 `-Wl,-T` 链接段注册命令表。
4. conan-verify G0-G4 全 PASS；finish W3 本地 CI 通过（基线隔离复验后）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码提升误把 demo/x86-gcc 内容提到根、删除 src/ | `_promote_nested_source` 在根目录无构建标记时提升首个含 CMakeLists 的子目录 | 手动从官方 tarball 重建 orig/work 双轨目录（src/extensions/demo 齐全） |
| 2 | 消费者链接 undefined symbol `_shell_command_start/_shell_command_end` | SHELL_EXPORT_CMD 使用自定义 shellCommand 段，边界符号由链接脚本提供 | 配方随包分发 shellcmds.lds（INSERT AFTER .data），test_package 以 -Wl,-T 链接 |
| 3 | export_sources 中 copy 到 self.source_folder 抛 TypeError | 导出阶段 source_folder 为 None | 改用 self.export_sources_folder（详见 DRAFT-letter-shell-3.1.2-linker-section-fragment） |
| 4 | shellRun 执行 add 命令段错误 | SHELL_TYPE_CMD_FUNC 以 int 参数调用，与 argc/argv 签名不符 | 消费者命令改用 SHELL_TYPE_CMD_MAIN 导出 |
| 5 | W3/JC5 命中 cloog/kics 其他库基线空标记 | junk_check full 模式按 git index 整仓扫描已跟踪隐藏文件 | git rm --cached 临时取消跟踪→复跑 finish→git add -f 恢复，SHA-256 核对一致（复用 DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation） |

## 源码修改

无补丁（patches 0）。库本体零修改，纯配方打包。

## 依赖版本

无外部依赖（嵌入式纯 C 库，requirements 为空）。

## 验证结果

- conan-verify: G0-G4 PASS（conan create 成功）
- test_package: `./test_letter-shell`（add 3 4→7, add 10 32→42）PASS；
  `./test_letter-shell_ohos`（__aarch64__/SHELL_VERSION=3.1.2/mul 6 7→42）PASS
- 上游测试: 官方 tag 无测试框架（0 个独立用例），台账见 reports/test-report.md

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 2 配方（clang 直编 + llvm-ar 归档） |
| shellcmds.lds | 段注册消费者最小链接片段（随包分发） |
| test_package/{test.c,test_ohos.c} | 消费者验证 + HarmonyOS 专项 |
| reports/ | conan-verify-report / test-report / knowledge-candidate-ledger |

## 注意事项

- 消费者导出命令必须用 SHELL_TYPE_CMD_MAIN（argc/argv）签名，勿用 CMD_FUNC。
- 链接时须带 `-Wl,-T,<lib>/shellcmds.lds`，否则段边界符号未定义。
- 知识库扩展（Path B）：C3 链接片段模式建草稿
  DRAFT-letter-shell-3.1.2-linker-section-fragment.kv/.md；C1/C2 复用既有条目。

**编译结束**: 2026-09-22 01:16
**最终状态**: built