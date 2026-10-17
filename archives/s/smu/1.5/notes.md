# smu 1.5 适配记录

日期：2026-09-23。任务 10744，任务分支 `feat/smu-1.5`。
状态：H1 HarmonyOS/aarch64 原生构建两次通过，32 项功能测试两次全通过；
Conan 2.29.1 使用 `ohos-aarch64` 单文件 profile 创建包并实际执行包内测试，
32/32 通过。第四轮隔离框架 G2 又从源码构建并完成包内 32/32，但
G4 未找到已生成的包 ID 仍标 PASS，L2/L4/L5 因无缓存路径跳过仍标 PASS。
完整 `conan-verify` 门禁未通过审计；`finish`、官方 CI、上传及 PR 尚未完成。

## 源码与依赖

- 官方源码：https://github.com/Gottox/smu/archive/refs/tags/v1.5.tar.gz
- SHA256：`f3bb18f958962679a7fb48d7f8dcab8b59154d66f23c9aba02e78103106093a4`
- 来源归档共 8 个文件：`LICENSE`、`Makefile`、`config.mk`、`documentation`、`smu.1`、`smu.c`、`smu.h`、`testdoc`。
- C 标准库依赖，无额外第三方库、无 Conan requirements/tool_requires。
- 上游 MIT 许可证随包复制到 `licenses/`。

## 适配方式

不修改 smu C 源码。使用原 Makefile，命令行传入 CC/CFLAGS/LDFLAGS/INCS/LIBS，覆盖 config.mk 的 `/usr/include`、`/usr/lib`、`-O0`、`-Werror`。Conan AutotoolsToolchain 提供 profile 与 build_type 标志；补充 VERSION、PIE/RELRO、串行 make；OHOS 使用 CONFIG_SHELL 或平台 bash 默认路径。包中保留 smu 可执行文件、版本替换后的 man 页与许可证。

该变化是构建配方适配，不是通用创新，也未证明存在鸿蒙特有源码缺陷。

## 上游测试清点

`Makefile` 目标为 all/options/smu/clean/dist/install/uninstall，另有 `.c.o` 编译规则；没有 test/check 目标、测试目录、自动测试注册或预期输出。`testdoc` 是示例/测试输入，不能把它计作已通过的自动测试套件；`documentation` 记录受支持的简化 Markdown 语义与已知限制。没有删除、修改或跳过已注册的上游自动测试。

补充消费者测试 `test_package/functional.py`：32 项、每项分别核对 stdout、stderr 和退出码条件，共 96 项比较。覆盖标题、强调、段落、链接、图片、列表、代码、引用、HTML 严格转义、UTF-8、文件/stdin、空输入、多缓冲区输入和错误路径。固定预期由上游文档和源码核对，不从待测二进制自动生成。

上游 `-v`、`-h`/非法参数通过 eprint() 退出失败，版本信息写 stderr；测试保留此行为。Windows 主机检查仅在 Windows 上归一化 CRLF，OHOS 按原始字节比较。

## 验证层级

- Windows 源码行为检查：MinGW GCC 8.1.0 编译原版源码，32/32 通过。仅为宿主预检。
- 测试有效性：将独立测试构建中的 VERSION 宏改为 1.4，版本用例失败、测试程序返回 1，证明版本断言能检出错误。
- 配方预检：在工作区隔离的标准 Conan 2.29.1 上 inspect 和 generate 成功；
  此阶段只检查 API，不充当目标平台构建证据。
- H1 原生构建：两次独立运行，构建退出码 0；原生 `smu` 的 AArch64 ELF、
  SHA-256 和 32 项逐字节功能结果已从原始运行目录核验。
- H1 Conan 配方：2026-09-23 在正常 HiShell 使用与提交
  `b74b737720429399df35f5302cd5edde2d9ce312` 匹配的配方 ZIP 及单文件
  `ohos-aarch64` profile。`conan create` 日志记录源码编译、打包并运行
  `test_package`；32 通过、0 失败。实际配置为 OHOS 6.0/armv8/Clang 15，
  源码和配方输入哈希已核对。原始日志、逐项汇总与审计报告保存在
  本次工作区的 `work/smu/evidence/`，提交时按上游要求提供可复核证据。
- 隔离框架验证：H1 在新检出中使用固定提交及全新 `CONAN_HOME`，
  G2 从源码生成包并运行 32/32 测试。G4 因包 ID 定位失败仍显示 PASS，
  L2/L4/L5 实际跳过却标 PASS，框架命令退出 0 不代表完整门禁通过。
  本轮原始目录 85/85 项 SHA-256 已核对，独立审计位于项目工作区
  `work/smu/evidence/h1-framework-gates-fourth-audit.md`。同轮包缓存 JSON、
  ELF 和功能结果的只读取证请求已冻结，结果待 H1 回收。
- `finish`、官方 CI、上传及 PR：未完成，不能用单文件配方或 G2 成功
  代替后续门禁。

框架参考提交：`b724a3b395df573e21a85cd0a0114bc2acebdea6`。
现有验证器 G2 依赖 `/bin/sh`（H1 晚间探针确认其可执行），G4 对
Conan 包定位与 JSON 解析已经在第四轮造成 G4/L2/L4/L5 假通过。
另经静态核对，完整 W3/远端 CI 的 L2 对 `--version` 和 `--help` 非零
只记 `failed (non-blocking)` 警告，不因该项退出。smu 1.5 的版本与帮助
选项分别是 `-v`/`-h`；本地同源构建成品对两个双横线参数均返回 1 并输出 usage；
正式结论仍以真实 W3/远端 CI 原始日志为准。不为迎合烟测修改 smu
上游行为；不手写 `.ci-result.json` 或
`.audit-result.json`。随后 H1 对 Conan 包内成品运行的 `sha256sum`
和 `readelf` 输出已回传：哈希与 `test_package` 汇总一致，显示
ELF64 AArch64 PIE、GNU_RELRO、不可执行栈、NOW 和 `libc.so` 动态依赖。
成品二进制本体未回传，不能称在 Windows 已独立解析该成品。

2026-09-24 正式 `finish` 首轮在 H1 使用 UID 私有目录的全新 Conan 缓存，
G2 再次从源码建包、包内测试 32/32；`conan-verify` 的 G4 仍未找到包 ID，
L2/L4/L5 仍跳过，不能据总体 PASS 标签验收。W3 `setup.sh` 退出 0，
但 `build_and_test.sh` 的整仓 JC 回退扫描因 cloog/kics 三个上游基线已
跟踪的状态文件而退出 1；L0 失败，L1/L2/L4/L5 均未执行，未产生真实
`.ci-result.json`。原始 236/236 哈希审计见本项目
`work/smu/evidence/h1-006-finish-w3-audit.md`。后续只在冻结完整、真实的
候选 PR diff 后，使用框架内置的 `JUNK_PR_DIFF` 模式复验整个 W3；不删除
全库基线文件，也不把该次 W3 失败改写为通过。

2026-09-24 后续 H1 复验：完整 15 文件 smu 候选 diff 的官方 JC 以
`prdiff` 模式通过。第七轮因外部提前终止而无 W3 终态；第八轮在新隔离
检出和私有 Conan 缓存中自然完成，`finish` 内 G2 与 W3 都从源码建包、
运行包内 32/32。W3 的 setup、G0/G0e、L0/L1/L4/L5、KC/JC 及 L1e
破坏性负测通过；L2 对上游没有的 `--version`/`--help` 记非阻塞 skip。
`.ci-result.json` 与 W3 日志完整性哈希匹配，证明本地 W3 通过。
完整 `finish` 随后仍因仓库知识图谱字段/遗漏与 submit 就绪预检未满足
而退出 1；生成 SUMMARY.md 也有框架解析警告。当前 `conan-verify` 的
G4“找不到程序包 ID”和 L2/L4/L5“无 cache 路径”仍是假 PASS，不据此
宣称全部门禁通过；官方 CI、上传和 PR 尚未执行。本项目工作区保留第八轮
原始 256/256 文件及哈希清单供复核。

## 最终状态

本地 W3 与 32 项包内功能测试通过，状态为 built；官方 CI、PR 及赛事验收待进行。公开 reports 中个人 home 前缀统一替换为 `<USER_HOME>`，原始证据私下保留，测试结果未改动。
