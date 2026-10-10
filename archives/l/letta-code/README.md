# letta-code

`letta-code`（npm 包 `@letta-ai/letta-code`）是 Letta 生态的**有状态 AI 编码代理命令行工具**，
以 Node.js CLI 形态发布。上游使用 **bun** 将应用打包为**单文件 `letta.js`**，随 npm 发布物分发；
配方只做「校验 + 打包 + launcher」（外加构建期编译一个约 20 行的启动 trampoline），**不编译上游 JS**。

上游 [GitHub letta-ai/letta-code](https://github.com/letta-ai/letta-code)（Apache-2.0）。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | letta-code（`@letta-ai/letta-code`） |
| 版本 | 0.28.17 |
| 上游标签 / commit | `v0.28.17` / `c9a66725b0cdc8386d2496cb373f08ca642feda0` |
| 许可证 | Apache-2.0 |
| 发布物 | npm tarball `https://registry.npmjs.org/@letta-ai/letta-code/-/letta-code-0.28.17.tgz` |
| SHA256（主包） | `10deb90f108b766d20c0743878219a23a09e7bd409d1621e80df4c6e6088f0a3` |
| 形态 | npm 预构建 Node.js CLI（bun 打包单文件 `letta.js`） |
| 运行时要求 | Node.js `>= 22.19.0`（系统提供） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC（HongMeng Kernel 1.12.0） |
| 架构 | aarch64（OHOS armv8），musl libc |
| 运行时 | 系统 Node.js（hnp）`v24.13.0`（`/data/service/hnp/bin/node`） |
| 构建系统 | npm-prebuilt（不编译上游 JS；仅构建期编译启动 trampoline） |
| Conan profile | `ci/conan/profiles/ohos-aarch64` |

## 编译安装步骤

因为发布物已是最终产物，`conan create` **不编译上游 JS**，只下载校验、编译启动 trampoline、打包并生成 launcher：

```bash
# 1. 从制品仓/源码目录创建包（本机实跑命令）
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64

# 2. 配方内部执行序列（不编译 JS，但含真实冒烟）：
#    - 下载 npm tarball，校验 SHA256
#    - 下载 vendor ws 8.19.0，校验 SHA256，解入包内 node_modules/ws
#    - 用目标 clang 编译启动 trampoline bin/letta-exec（优先 -static）
#    - 打包 letta.js + node_modules 到 libexec/letta-code（排除一切构建缓存）
#    - 生成可重定位 launcher bin/letta：解析支持 -u 的 env → 真剥离 LD_LIBRARY_PATH
#      → 经 bin/letta-exec 重执行 → 正常 JIT 启动 node
#    - build() 构建期真实冒烟：按安装后布局 staged launcher+trampoline+letta.js+node_modules/ws，
#      在「继承污染环境（带 LD_LIBRARY_PATH）」下经额外 /bin/sh -c 层执行
#      <stage>/bin/letta --version / --help，断言 --version 精确等于 0.28.17 (Letta Code)、
#      --help 含 USAGE 与 headless（不使用 --jitless：yoga-layout 的 WASM 依赖 JIT）
```

安装后可直接运行：

```bash
letta --version     # 输出: 0.28.17 (Letta Code)
letta --help        # 自定义 USAGE/OPTIONS/SUBCOMMANDS 帮助
```

## 补丁说明

- **无源码补丁**：`letta.js` 是上游 bun 打包的**预构建单文件**，发布物即最终产物，配方不改任何上游源码
  （`patches_applied: []`，无 `patches/` 目录）。
- **ws vendoring（产物级依赖补齐，非源码补丁）**：`letta.js` 对 `ws` 使用**未打平的静态 bare import**，
  启动时必须可解析，故随包 vendor：
  - `ws` 8.19.0，`https://registry.npmjs.org/ws/-/ws-8.19.0.tgz`
  - SHA256 = `7fb02dae000a91ccd9d2ae51cda3672ab6c1685ecd26e07c668996ce52e25609`
  - 解入包内 `node_modules/ws`，使 bare import 命中。
  - `node-pty` / `sharp` 为**动态 require**，缺失时降级，**不 vendor**。
- **`bin/letta-exec` 启动 trampoline（产物级启动补齐）**：约 20 行 C，构建期由目标 `clang` 编译，运行期
  `unsetenv("LD_LIBRARY_PATH")` 后 `execvp` node。它是让 node 在本机可靠启动的那一次「重执行」，
  同时兜底真剥离 `LD_LIBRARY_PATH`（详见下方「运行时关键约束」）。

## 测试结果

| 测试项 | 范围 | 结果 |
|--------|------|------|
| tarball SHA256（主包） | 官方 npm tarball | ✅ pass |
| vendor ws SHA256 | ws 8.19.0 | ✅ pass |
| 真机离线 CLI 冒烟（`--version` / `--help`） | OHOS aarch64，node v24.13.0 | ✅ pass（经 trampoline，正常 JIT） |
| `build()` 构建期冒烟（**跑真 launcher**：staged launcher+trampoline+letta.js+ws；继承污染 `LD_LIBRARY_PATH`、多一层 `/bin/sh -c`、正常 JIT） | 本机 `conan create`，OHOS aarch64，node v24.13.0 | ✅ pass（`--version` = `0.28.17 (Letta Code)`；`--help` 含 `USAGE`/`headless`） |
| `conan inspect .` | 本机 | ✅ pass |
| `conan create`（source / trampoline / build 冒烟 / package / test_package，`test.sh` **53 条断言** = 1 版本横幅 + 3 帮助段头 + 21 条 USAGE 命令行 + 27 条 SUBCOMMANDS 条目 + 1 断言数自检） | 本机，OHOS aarch64 | ✅ pass，退出码 0：`letta-code 0.28.17 consumer checks: PASS (assertions=53)` |
| CLI 接口面覆盖（交付包 `--help` 的**全部**可验证条目，按 `USAGE` / `SUBCOMMANDS` 区块逐条对真实输出校验） | 本机，OHOS aarch64，node v24.13.0 | ✅ pass：48/48 条目（21 USAGE + 27 SUBCOMMANDS），非抽样 |
| test_package 断言口径（2026-09-27 rule4 复核修订） | 本机 | ✅ 11 → 53：初版只覆盖 6 个命令被判「少报」，现按完整接口面全查（详见 notes.md） |
| 反向验证：临时把 launcher 改回旧 `unset` 版 / 仅 `env -u` 无 trampoline 版 | 本机 `conan create` | ✅ 均如预期在 `build()` 冒烟阶段失败（Exit 133 / Signal 5）——证明新冒烟能拦住回归 |
| `conan-verify` / Shadow CI | 本机 | ⏳ TODO-VERIFY（尚未执行） |
| 上游 `bun test`（553 个测试文件 = 541 `.ts` + 12 `.tsx`；白名单 24 目录 433 + `src/channels` 82 + 根级 31；`src/integration-tests` 8 个被 API 门控排除） | 上游源码 tag `v0.28.17` | ❌ 本机不可运行（已实测定论）：设备 `execve` 对**非本会话产出**的二进制一律 `EACCES(13)`，含官方 musl 变体 `@oven/bun-linux-aarch64-musl@1.4.2`；**并非**「bun 是 glibc 链接 / 缺 glibc loader」（该旧结论已实测推翻）。`cases_run = 0`，不虚报通过率（R51 三步法与对照矩阵见 notes.md） |

> 运行时关键约束：
> 1. **必须保持 JIT**（`yoga-layout` 依赖 WASM，`--jitless` 下 WASM 不可用）；
> 2. launcher 的 `unset LD_LIBRARY_PATH` 在 `/system/bin/sh` 下**并未真剥离**（置空同样致命），
>    必须用 `env -u` 真剥离；且**仅剥离还不够**——node 直连系统 shell 时 V8 的 CodeRange 预留会失败
>    （`Check failed: 12 == (*__errno_location())`，Signal 5），因此还要经 `bin/letta-exec` trampoline 重执行。

## 参考资料

- 上游仓库与发布：<https://github.com/letta-ai/letta-code>
- 适配笔记：`archives/l/letta-code/0.28.17/notes.md`
- 源码校验与补丁声明：`archives/l/letta-code/0.28.17/conandata.yml`（与 manifest.yaml 双处声明）
- 配方与测试：`archives/l/letta-code/0.28.17/conanfile.py`、`archives/l/letta-code/0.28.17/test_package/`
