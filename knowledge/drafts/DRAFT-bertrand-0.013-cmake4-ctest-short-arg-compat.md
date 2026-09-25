# DRAFT: 上游 shunit2/CTest 脚本用旧短参 `ctest -N -o`，CMake 4.x 移除 -o → PATH 前置兼容包装剥离 -o 后整脚本实跑（零源码修改）

> 来源: bertrand 0.013 R02 返工（shunit2 14 项整脚本实跑恢复）
> 状态: 草稿 (draft) — 与 DRAFT-bertrand-0.013-cmake4-ctest-short-arg-compat.kv 配对
> 关联: archives/b/bertrand/0.013/reports/knowledge-candidate-ledger.md (C5/C6)

## 问题

bertrand 上游 `test/installation-tests.sh` 的 4 个 shunit2 函数
（testDisablingOfBertrandBuildingTests / testGlobalDisablingOfTests /
testAllTestsEnabled / testUsageAsSubdirectory）执行：

```bash
NUMBER_OF_TESTS=$(ctest -N -o | grep -E '^Total Tests: [0-9]+')
```

执行端 CMake 4.1.2 报：

```
CMake Error: Unknown argument: -o
CMake Error: Run 'ctest --help' for all supported options.
```

`-o`（旧 CTest 输出短参）在 CMake 4.x 已被移除（列表计数由 `-N` 承担，输出由
`--output-on-failure` 等长参表达），断言因此拿不到 `Total Tests: N` 计数，
整脚本失败（R02 首跑 8 函数 16 项断言失败均源于此 + cpack/conan 项）。

## 根因

上游测试脚本对 CTest CLI 版本的隐性依赖：按旧版编写 `ctest -N -o`，CMake 4.x
收紧 CLI 后失效。非库源码缺陷。

## 方案（path-compat-wrapper-strip-obsolete-flag）

在运行测试的 PATH 前置层放置 ctest 兼容包装，仅剥离已移除的 `-o` 短参，
其余参数（含 `-N`）原样转发真实 ctest；断言文本与执行语义不变。

```sh
mkdir -p compat-bin && cat > compat-bin/ctest <<'EOF'
#!/bin/sh
# CMake 4.x removed ctest -o; strip it (upstream scripts use `ctest -N -o`)
args=""
for a in "$@"; do
  [ "$a" = "-o" ] && continue
  args="$args \"$a\""
done
eval exec /data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest $args
EOF
chmod +x compat-bin/ctest
PATH="$(pwd)/compat-bin:$PATH" bash test/installation-tests.sh
```

结果：4 个受影响函数全部通过（`Total Tests: 0` / 非 0 断言原样执行，
r02-installation-script2.log）。同轮 test-program-termination.sh 7/7 通过。

## 附带恢复（同轮，入适用边界说明）

- **shunit2 宿主供给（C6）**：设备无 shunit2（PATH/usr/share/pip/registry/包
  管理均缺）；raw.githubusercontent.com 不可达，但 github codeload 与
  gitcode 镜像可达 → 从官方 codeload tarball（v2.1.8，52458B）取单文件脚本
  安装 usr/local/bin，`. shunit2` 冒烟通过后两个套件整脚本实跑。
- **CPack 生成器**：CPack 默认 NSIS 生成器缺 makensis → 环境以
  `set(CPACK_GENERATOR "STGZ")` 恢复（工作源码副本，非 PR 内容），
  cpack 安装脚本断言原样执行。

## 验证

- ctest 包装独立冒烟：`compat-bin/ctest -N -o` 输出 `Total Tests: 0`（exit 0）
- installation-tests.sh：8 函数中 7 个整脚本实跑通过（含 4 个 ctest -N -o 项）；
  testConanInstallation 因上游 Conan 1.x 专属 CLI/配方被 Conan 2.29.1 拒绝，
  属真实工具链硬阻塞，单独记录证据与恢复条件，未伪报
- 台账: reports/upstream-test-ledger.md（31/32 实跑，17/17 可执行集合）

## 适用边界 / 反例

- 适用：上游脚本 `ctest -N -o`（或其它 CTest 旧短参）且执行端 CMake ≥4.0；
  -N 列表计数场景剥离 -o 不改变语义。shunit2 缺失且官方/镜像可达时可单文件供给。
- 反例：若脚本依赖 `-o` 的实际输出行为（非仅计数），需映射为
  `--output-on-failure` 等价长参并核对断言；CMake <4.0 环境无需包装。
- 同类 CMake 4.x CLI 收紧（configure 阶段）见 E103/E187（cmake_minimum_required
  移除）；Conan CMake.test cli_args 路由见 E301——触发不同，方案不同。

## 查重差异

- E103/E187：cmake_minimum_required VERSION<3.5 在 CMake 4.x 移除（configure
  阶段、改 CMakeLists 版本号）；本候选为 ctest 短参移除（testing 阶段、
  运行层兼容包装，零源码修改）。
- E301：Conan 2 CMake.test() cli_args 路由到 cmake --build 而非 ctest；
  本候选不涉及 Conan 生成器路由。

## 关系

similar_to: E103, E187, E301