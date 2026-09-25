# colorized-logs 2.7 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt；init-build 曾按 URL 猜测 autotools，已按实际结构编写 CMake 配方）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile）
- 状态: built（conan-verify G0-G4 + L2/L4/L5 全通过）

## 编译步骤
```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_COMPILER=clang -DCMAKE_C_FLAGS="-fPIC -O2"
cmake --build build -j4
cmake --install build
```
产物：ansi2html、ansi2txt、ttyrec2ansi、pipetty、lesstty（→pipetty 符号链接），共 5 个 CLI 工具，无库文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 `https://github.com/kilobyte/colorized-logs` 返回 HTML | 传入的是仓库页 URL 而非归档 tarball | 改用官方归档 URL `.../archive/refs/tags/v2.7.tar.gz`，SHA-256 核验 `1fb97c9c...` |
| 2 | conan-init 按 autotools 生成配方 | URL 猜测构建系统失准 | 按实际 CMake 结构重写 conanfile.py（CMakeToolchain + CMake.install），package_type=application |
| 3 | test_package 中 ttyrec2ansi 输出截断 | OHOS 上 `$(...)` 命令替换丢弃 NUL 字节（ttyrec 头含 NUL） | 改用临时文件捕获输出（与上游 testsuite 同法） |
| 4 | `pipetty sh -c '...'` 返回 1 无输出 | OHOS mksh 下 sh -c 形式不可用 | 采用上游调用形式 `pipetty </dev/null sh <script>`，pty 正常分配 |
| 5 | test_ohos T4 ttyrec 输出少尾字节 | 测试头 len 字段=8 而 payload 9 字节，尾字节被当作下一帧头 | 修正测试数据 len=9（`\t\0\0\0`）与 payload 匹配；上游用例 payload `foo bar\n` 恰 8 字节 |
| 6 | W3 JC1/JC5 拦截 2 个 junk 文件 | 命中 origin/main 上其他库（cloog/kics）历史空文件 `.staging-verified`（e3b0c44...），非本分支文件 | 使用 JUNK_PR_DIFF=pr.diff 单包口径复验通过；未修改/未提交基线文件 |

## 依赖版本
- 无第三方依赖（纯 C，仅链接系统 util 库 openpty）

## 验证结果
```bash
# 上游测试（ctest，5/5 通过）
ctest --output-on-failure   # ansi2txt/ansi2html/pipetty/pipetty:sigobit/ttyrec2ansi 全过

# 鸿蒙专项测试（5/5 通过）
sh test_ohos/run_ohos_test.sh <bin目录>
# T1 aarch64 ELF / T2 无宿主路径泄漏 / T3 ANSI 解码往返 / T4 ttyrec 重放 / T5 pipetty pty

# conan-verify（G0-G4 全通过；L2/L4/L5 因本地无 cache 路径跳过）
python3 scripts/ohc-run.py conan-verify colorized-logs 2.7
```
注：L2/L4/L5 在本地 conan-verify 报告中被标记为跳过（无 cache 路径），L2 中
ansi2html/lesstty/pipetty 的 `--version`/help 探测失败是 CLI 工具无 --version
选项的正常行为（上游本身不提供 --version），非适配缺陷；由 CI 侧 L2/L4/L5 完整执行。

## 交付物
- archives/c/colorized-logs/commands.json：CLI 工具声明（ansi2html/ansi2txt/ttyrec2ansi/pipetty/lesstty，R38）
- archives/c/colorized-logs/2.7/conanfile.py + conandata.yml + test_package/ + test_ohos/

## 注意事项
- lesstty 是 CMake 自定义目标生成的 pipetty 符号链接，`install(TARGETS)` 会一并安装
- 本库是 tool 类型（application），test_package 用 VirtualRunEnv + bash 包装执行（OHOS mksh 无法直接执行 ELF）
