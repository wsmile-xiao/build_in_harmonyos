# shml 1.1.0 适配笔记

## 编译环境
- 构建系统: custom（纯 Bash 脚本库，无编译；供 `source` 加载，非独立命令行工具）
- 编译日期: 2026-09-29
- 编译器: 库本体无编译；test_package 用 profile 的 OHOS clang 静态编译消费者
- 状态: built

## 编译步骤

1. `init-build shml 1.1.0`：官方源 `https://github.com/odb/shml/archive/refs/tags/1.1.0.tar.gz`，sha256 `0f0634fe…8f4f`（github.com 与 codeload 两个入口一致）。
2. 语言判定（未运行会写终态的 `lang-preflight`）：只读调用 `detect_language()` 得 `nodejs`（`package.json` 含 bin/scripts，`.sh` 不计入主体，统计为“无源文件可统计”）。实际为 33 个 `.sh`（库脚本、测试、示例及文档代码样例）、无任何 `.js/.ts/.py/.c/.cpp/.h` 源文件的纯 Bash 库；按任务要求 shell 库直接适配，不能为迁就检测器伪报语言，也不写 `env_unsupported` 终态。
3. 手工功能验证：`bash -c 'source ./shml.sh; fgcolor red OHOS'` 输出 `ESC[31mOHOSESC[39m`。
4. 配方：`source()` 取上游源码与 shunt v0.3.1；`build()` 用显式 bash 运行上游测试；`package()` 只装 `share/shml/shml.sh` 与 `licenses/LICENSE`；`package_id` 清空（同一脚本适用所有 os/arch）；`package_info` 导出 `SHML_SCRIPT` 运行期变量。
5. `conan-verify shml 1.1.0`：G0–G4 全部 PASS（含 `conan create` 与 test_package）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-init` 骨架不可用 | 因顶层 Makefile 被识别为 autotools：模板含 `cpp_info.libs=["shml"]`、扁平 `sources:`、`{BUILD_SYSTEM}` 占位符 | 手写无编译配方：`resdirs=["share"]`、版本键 `sources`、manifest 占位符补实 |
| 2 | 语言预检把 Bash 库判为 nodejs | `package.json` 仅为 npm 分发元数据；`.sh` 属辅助脚本不进统计 | 只读探针留证并在本文件记录；不运行会落终态的 `lang-preflight` |
| 3 | 上游 `make test` 运行时 `curl … \| bash` 下载 shunt（`latest` 浮动引用、无校验和） | 测试框架是运行时下载物；CI L0o 禁止配方内 curl 下载 | conandata.yml 固定官方 tag 归档 `odb/shunt v0.3.1` + sha256；其 `shunt.sh` 与 master 字节一致（sha256 `b166a8e4…f90e`） |
| 4 | shunt 遇到含 “-h” 的绝对路径只打印 usage 并以 0 退出 | `grep "\-h"` 扫描包含全部测试路径的 argv | 只传相对路径，并断言汇总行 `Total == 172`，防止静默跳过 |
| 5 | G1 报缺 `export_sources()` 与补丁应用调用 | 门禁对这两个标准调用做字面检查 | 保留 `export_conandata_patches` / `apply_conandata_patches`（无补丁时为空操作） |
| 6 | conan-verify 通过，finish 的 W3 却在 test_package 的 `test()` 失败 | 我用 `tested_reference_str.split("@")` 取版本；W3/CI 不带 user/channel，引用为 `shml/1.1.0#<revision>%<timestamp>` | 改用 `str(self.dependencies[self.tested_reference_str].ref.version)`，并在日志打印引用（知识草稿 E6441） |
| 7 | W3 脚本把 `conandata.yml` 改成带 `gh-proxy.com` 的 URL 列表且未真正还原 | `build_and_test.sh` 先追加镜像回退、之后才备份，“还原”写回的是已改写版本 | 每次 finish 后 `git checkout -- conandata.yml` 还原提交版本，提交前确认 conandata 只含官方 `github.com` URL |

## 源码修改

无。0 个补丁，上游源码与测试文件保持原样。

## 依赖版本

- Conan 依赖：无（`requirements()` 为空）；运行期需要系统 Bash（脚本使用 `[[`、`local`、`{16..21}` 花括号展开）。
- 测试框架：odb/shunt v0.3.1（`conandata.yml` 固定，仅构建期使用，不进入包）。
- 构建机：GNU bash 5.2.15、qemu-aarch64 7.2.22、Conan 2.29.1；OHOS profile 编译器 `/data/service/hnp/bin/clang`。

## R51 上游测试清点

| 项 | 数量 | 说明 |
|----|------|------|
| `test/` 目录 | 1 | 仅含测试脚本，无 ctest/pytest 注册 |
| 测试文件 | 9 | `test/*_tests.sh` |
| `assert_equal` 调用点 | 142 | 静态计数（部分在循环内） |
| shunt 运行时断言（N） | 172 | shunt 汇总 `Total: 172` |
| Makefile `test` 目标 | 另含 2 条 source 冒烟 | `bash`/`zsh` `source ./shml.sh && color-bar`，无断言，仅退出码；不计入 N |

适配后 N′ = 172（`build()` 内运行，逐字使用上游 9 个文件），通过率 172/172。

## 验证结果

```bash
conan create（profile ohos-aarch64）:
  SHML UPSTREAM TEST PASS/FAIL: 172/172 (9 test files, rc=0)
  shml OHOS consumer PASS: 6 SGR codes, plain text "OHOS PC qemu B **** ✓"
finish W3（ci/conan/build_and_test.sh，无 user/channel 形态）: Pass rate 100% (1/1)；L1 pass（test_package executed）、L2 skip（无 bin/）、L4 pass、L5 warn（无 artifacts）；
  日志含 "tested reference: shml/1.1.0#<recipe-revision>%<timestamp> (version 1.1.0)"（revision 与时间戳每次不同） 与 "shml -v via SHML_SCRIPT: shml version 1.1.0"
staging: 包内 share/shml/shml.sh、licenses/LICENSE 与源码 sha256 一致；bash shml.sh -v → shml version 1.1.0
qemu-aarch64 直接运行 test_package 编出的 shml_consumer：输出 PASS 行，exit=0（静态 aarch64 ELF）
zsh 5.9 手动 source 冒烟 rc=0（本地，未入配方）
```

鸿蒙特有测试（rule12）：1 个完整消费者流程（`test_package/consumer.c` + `conanfile.py`）——conanfile 用 bash 加载**已打包**的 `shml.sh` 并调用 `fgcolor`/`bgcolor`/`attribute`/`hr`/`icon`，输出写入头文件，OHOS aarch64 静态 C 程序据此编译，在 qemu-aarch64（aarch64 主机则原生）中执行，按 ECMA-48 SGR 码与纯文本校验；`test()` 再经包的 runenv 执行 `bash "$SHML_SCRIPT" -v` 校验版本。执行方式：本地 `qemu-aarch64` 实跑，rc=0。

## 知识沉淀

- E6440（草稿）：上游 `make test` 运行时 `curl | bash` 拉浮动引用的测试框架 shunt；固定官方 tag + sha256 自包含；shunt 遇路径含 `-h` 静默打印 usage 并以 0 退出。
- E6441（草稿）：test_package 切分 `tested_reference_str` 取版本，W3/CI 形态带 `#revision%timestamp` 而失败。
- 查重：`draft-review` 两条均判 `create`（最高相似度 0.09 / 0.16）；`engine` 对 shunt 片段只命中泛化的 E185（HTTPS 证书）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| share/shml/shml.sh | 17037 B | 供 `source` 加载的库脚本（直接执行时支持 `-v` 与用法演示） |
| licenses/LICENSE | 1081 B | 上游 MIT 许可证 |

## 注意事项

- 本包是 Bash 库，不是独立命令：不设 `bin/`，不提供 `commands.json`（PF8 对纯库包要求无该文件）。使用方式：`source "$SHML_SCRIPT"`（由 `conanrun` 环境提供）。
- 未提交软件级 `README.md`/`manifest.yaml`：PF9 要求 `archives/` 变更全部落在 `包/版本` 目录，纯库包也无需 `commands.json`。
- `progress()` 需要 TTY，上游无用例，本次未覆盖。
- x86 runner 的局限见 test-report：上游用例由宿主 bash 执行，OHOS 原生 bash 需 CI 设备环境复跑。
---

**编译结束**: 2026-09-29 17:00
**最终状态**: built
