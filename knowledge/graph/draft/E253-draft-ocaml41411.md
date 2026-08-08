# E253 — OCaml 4.14.1.1 在 HarmonyOS PC 上的编译/测试适配

## 错误特征

OCaml 4.14.1.1 工具链迁移到 HarmonyOS PC (aarch64) 时，在 configure、构建、上游 testsuite 三个阶段遇到以下典型失败：

- `config.guess` 无法识别 OHOS，主机三元组判定为 `unknown-unknown-linux-gnu`
- configure 生成的 `config.status` 使用 `mktemp -d` → `Permission denied`（OHOS `/tmp` 为 erofs 只读文件系统）
- 字节码版 `ocamltest` / `ocamldebug` 被 hmmac 拦截（`Operation not permitted`）
- `ocamldebug` 默认 UNIX socket `bind` 被 hmmac 拒绝
- `Unix.create_process` 调用 `fork+exec` 被 OHOS 安全策略禁止（`EPERM`）
- `posix_spawn` 相对路径（`./xxx`）解析失败（`ENOENT`）

## 触发条件

- 构建系统: configure + make（`configure --no-create → config.status → make world.opt`）
- 阶段: configuration / building / testing / runtime
- 典型库: OCaml 全系列（39 个 bin），及下游 dune、zarith 等

## 根因分析

OHOS PC 与标准 Linux 在 4 个层面存在差异：

1. **平台识别**：`config.guess` 未内置 OHOS 分支，configure 无法正确判定 host 三元组。
2. **临时目录**：`config.status` 的 `mktemp -d` 在 OHOS `/tmp`（erofs 只读）上失败。
3. **hmmac 安全策略**：字节码可执行文件、UNIX socket bind、`fork+exec` 子进程创建均被拦截——这是 OHOS 系统级安全机制，非编译缺陷。
4. **动态链接器**：符号解析行为与 glibc 不同（如 `camlPlugin: symbol not found`）。

## 解决方案

### 推荐方案（6 点 OHOS 适配）

1. **config.guess OHOS 识别**：patch 0001 为 `config.guess` 增加 OHOS aarch64 识别分支。
2. **configure tmpdir 修复**：patch 0002 将 `config.status` 中 `mktemp -d` 替换为 `rm -rf && mkdir -p`，`TMPDIR` 指向可写目录（如 `/storage/Users/currentUser`）。
3. **编译链**：`LN` 用 `cp` 替代、`CC` 注入 `/data/service/hnp/bin/clang`、`--prefix` 用 `shlex.quote` 引用。
4. **testsuite 迁移**：入口为 `make all`（无 `make check`）；先构建 `ocamltest.opt`（原生版，字节码版被 hmmac 拦截）；ocamldebug 通信改用 TCP socket（`ocamltest/ocaml_actions.ml` 的 debug action 传 `-s 127.0.0.1:PORT`），且**不得**在 debugger 自身环境设置 `CAML_DEBUG_SOCKET`（否则 debugger 尝试连接自身触发 SIGABRT/Signal 6）；随机端口需基于时间种子初始化避免 `Address in use`。
5. **create_process EPERM**：修改 `otherlibs/unix/spawn.c`，用 `posix_spawn`/`posix_spawnp` 替代 `fork+exec`；含 `/` 的相对路径先 `realpath` 转绝对路径，裸命令名（如 `cp`）保留走 PATH 查找。
6. **flambda 跳过**：当前构建 `FLAMBDA=false`，13 个 flambda 用例跳过并如实声明豁免（强制 `ocamltest_config.ml` 的 `flambda=true` 会因编译器实际不支持导致大量用例回归至 81%，不可用）。

### 验证

- `conan create` RC=0，test_package 冒烟通过（3 个工具版本断言）
- 上游 testsuite 真机实测 **2951/3144（93.9%）** 通过
- 剩余失败为平台硬限制（hmmac 拦截字节码可执行文件、UNIX socket bind、子进程创建、动态链接器符号解析差异），已在 MANIFEST.yml `fail_analysis` 逐类归因并按 TEST_QUALITY_SPEC 3.3 声明豁免

### 禁止做法

- 禁止虚报通过率为 100% 或"上游无测试"（E011 规则，通过率必须如实填报 2951/3144）
- 禁止强制 `ocamltest` 报告 `flambda=true` 作为修复手段（实测导致大量用例回归）

## 相关原则

R33（编译器从 conan conf 读）、R37（制品仓版本冲突递增后缀）、R38（工具类包需 commands.json）、R39（conandata 只留官方 URL，镜像由 CI 注入）、W2/R21（PR 原子性，ci/ 框架改动不混入配方 PR）

## 参考

- PR: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/3767
- 库: ocaml 4.14.1.1
