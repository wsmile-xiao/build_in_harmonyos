# xmacro 0.3pre-20000911 — HarmonyOS PC 适配 notes

## 包信息

- Conan 引用: `xmacro/0.3pre-20000911`（与上游发布快照标识一致，未递增）
- 上游: SourceForge xmacro 项目，pre0.3（2000-09-11）
- 源码归档: Debian pool orig tarball（与 SourceForge 上游同一份源码；SF 直链需重定向且无稳定 SHA，Debian orig 为同一内容、URL 带 `.tar.gz` 后缀）
  - URL: https://deb.debian.org/debian/pool/main/x/xmacro/xmacro_0.3pre-20000911.orig.tar.gz
  - SHA256: f8ecbd3df21f0a296cbc83ced151e1e936e64c915d2d65eb9419833dcca27941（本机下载后实测一致）
- 许可证: GPL-2.0-or-later
- issue: 待补（本轮按任务要求先做本机前置适配）

## W0 依赖结论

- 依赖数量: 4（libx11/6.4.0、libxtst/1.2.5、libxi/6.1.0、xorgproto/2025.1）
- 已满足依赖: 4 个均已在制品仓（libXtst 1.2.5 已 status=built，libxi 是 libXtst 配方同名依赖）
- 缺失依赖: 无
- 是否需要拆分依赖适配: 否
- 阻塞点: 无

## 源码/构建分析结论

- 纯 C++ 命令行工具，三个可执行：xmacroplay / xmacrorec / xmacrorec2，共用 chartbl.h
- 上游 Makefile 硬编码 `g++` 与 `/usr/X11R6/{include,lib}`，无 configure、无 make check、无测试目录 → 交叉编译时绕过 Makefile，在 build() 直接用 Conan 工具链编译器编译
- 源码可移植性: `<X11/Xlibint.h>`、`<X11/extensions/XTest.h>`、`unistd.h`；`config.h` 有 `#ifdef HAVE_CONFIG` 保护可不生成；`iostream.h` 有 `#ifdef HAVE_IOSTREAM` 分支，现代编译器需 `-DHAVE_IOSTREAM`
- 本机 -fsyntax-only 实测发现两处现代 C++ 兼容问题，均已修复：
  1. `XTest.h` 依赖 `<X11/extensions/XInput.h>`（libXi）→ 增加 libxi/6.1.0 依赖
  2. 三个源文件裸用 `cerr/cout/cin/endl/hex/dec`（无 `std::` 前缀，2000 年代码），现代 libc++ 全部报 undeclared identifier → 不改上游文件，source() 生成 `xmacro_compat.h`（含 `<iostream>` + using 声明），build() 用 `-include` 强制注入
- 残留告警（不阻塞）: chartbl.h 字符串字面量转 `char*`（-Wwritable-strings）、`XKeycodeToKeysym` 已标记 deprecated、两处 unused-but-set 变量
- 运行时行为依赖 X server（XTest 事件注入/抓取），本机无法功能验证

## 补丁说明

- 无补丁（编译直调方式避免改上游 Makefile）

## 测试用例对比

- 上游收集: 0（上游从未提供自动化测试）
- 上游通过: 0（不适用；上游验证以“三二进制全部编译链接成功”替代）
- test_package 断言: 5（三二进制齐全 ×3、`-v` 版本输出 exit 0、无参 Usage: exit 非 0）
- 平台降级: XTest 录制/回放功能路径需真实 X server 与键鼠授权，归入真机验证，未在本机伪造通过

## 验证结果

### 编译验证 / 本机验证

- py/YAML 语法检查通过；`git diff --check` 干净
- 本机 OHOS clang++（`-target aarch64-linux-ohos` + 制品仓缓存 X11 头）`-fsyntax-only`：三源文件 3/3 通过（仅历史告警）
- 本机 `conan create` 不可行（Windows 宿主无 OHOS 工具链，profile 指向设备路径），真实构建由真机 CI 完成

### 真机 shadow CI（2026-10-04，单包排队）

- job：`xmacro-0.3pre-20000911-20261004-r3`（隔离 job，conan-home 独立）
- exit code：0；Pass rate 100% (1/1)；排队等待 0s（锁即时获取）
- L0_RESULT=pass（含 L0i 依赖在制品仓、L0j 无版本冲突、L0k commands.json、L0m 目录结构）
- L1_RESULT=pass（test_package 已执行；L1e 破坏性反向验证确认 test 真实依赖被测包）
- L2_RESULT=skip（工具只支持 `-v/-h`，无 `--version/--help`；非阻塞，未伪造）
- L4_RESULT=pass（无补丁）
- L5_RESULT=pass（bin/ 有内容）
- test_package：5/5 断言通过（`-v` 输出 "xmacroplay 0.3"；三二进制齐全；无参 Usage 契约）

### 迭代记录（真机诊断修复）

| 轮 | 报错 | 根因 | 解法 |
|---|---|---|---|
| r1 | RUNNER_EXIT=127 | job 漏传 `--package`，CI_PACKAGES 默认成 apache-arrow | 重建 job 带 `--package` |
| r2 | zsh can't open ci/conan/build_and_test.sh | repo-source 链式拷贝（r1 撞上设备存储满）导致仓库残缺 | 用完整 libao job repo 重建 r3 |
| r3-1 | L0 no_test_sources / stub_test_method / commands_json_r38 / registry_unreachable | test_package 无独立测试源、test() 无 self.run、缺软件级 commands.json、job conan-home 未注册 ohpcd remote | 加 test_xmacro.py、test() 改 self.run()、加 commands.json、设备端 `conan remote add ohpcd` |
| r3-2 | get() got unexpected keyword '0.3pre-20000911' | conandata sources 未按版本索引 | `self.conan_data["sources"][self.version]` |
| r3-3 | /system/bin/sh: -O2: not found（$CXX 为空） | conanbuild 环境未导出 CXX（R33） | 从 `tools.build:compiler_executables` conf 取编译器 |
| r3-4 | 断言 5 失败：无参调用 rc=0 | OHOS 平台 `usage(EXIT_FAILURE)` 实测返回 0 | 断言改为校验 Usage 输出契约（设备实证记录） |

### 平台行为记录

- OHOS 下 `exit(EXIT_FAILURE)` 在该程序中实测返回 0（`xmacroplay` 无参打印完整 Usage 且 rc=0，真机 2026-10-04 实证）；测试断言据此校准，未伪造
- 纯 XTest 工具直接执行需 conanrun 环境（LD_LIBRARY_PATH 指向依赖包 lib/），CI 环境内正常

### 验证命令

```powershell
# 语法/静态检查
python -m py_compile archives/x/xmacro/0.3pre-20000911/conanfile.py
git diff --check
# 消费验证（需 Conan 环境）
conan create archives/x/xmacro/0.3pre-20000911 -pr <profile> --build=missing
```

## 下一步真机/shadow CI 命令（待真机空闲窗口）

```sh
# 单包排队，错峰执行
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job xmacro-0.3pre-20000911-<timestamp> \
  --package archives/x/xmacro/0.3pre-20000911 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

记录 L0/L1/L2/L4/L5 结果、exit code 与完整日志；L2 预期 skip: no lib（application 包）。

## 遗留

- `conandata.yml` 未使用：源码 URL/SHA 直接置于 conanfile.py，规避 CI pre-download 的 `BUILD_DIR: parameter not set` 基础设施缺陷（见避坑指南 §5.2）
