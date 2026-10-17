# E-DRAFT: 上游 gyp 生成器依赖 Python 2，OHOS 仅 Python 3 时按等价编译参数直接编译测试

- **触发实例**：pixelmatch-cpp 0.10.0 适配（2026-09-19，任务 pixelmatch-cpp-0.10.0-r01-pc4-1）
- **错误签名**：`env: exec python: No such file or directory` →
  `SyntaxError: Missing parentheses in call to 'print'`（deps/run_gyp / deps/gyp/pylib）
- **类别**：build-system / legacy-tooling
- **严重度**：2（构建生成阶段确定性失败，header-only 库可用等价编译绕过）

## 症状

```text
deps/run_gyp pixelmatch.gyp --depth=. -Goutput_dir=. --generator-output=./build -f make
env: exec python: No such file or directory        # shebang 找 python，环境仅 python3
make: *** [Makefile:6: build/Makefile] Error 127

# 补 python→python3 别名后：
File ".../deps/gyp/pylib/gyp/__init__.py", line 37
    print '%s:%s:%d:%s %s' % (mode.upper(), ...)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: Missing parentheses in call to 'print'  # 捆绑 gyp 是 Python 2 时代代码
```

## 根因

`deps/run_gyp` shebang 为 `#!/usr/bin/env python`，且捆绑 gyp 源码仍是 Python 2 语法。
gyp 只是**构建生成器**（Chromium 时代为 make/ninja 生成 build 文件），不是库本身。
对 header-only 库：gyp 生成的 build/Makefile 仅用于构建一个 test 可执行目标，无库产物
需要生成；该目标（test/test.cpp）的全部编译参数显式声明在 `pixelmatch.gyp` 的
`target_defaults.cflags_cc`（-std=c++11 -Wall -Wextra -Wshadow -fno-rtti -fexceptions）
中，可逐字等价复现。

## 修复方案（gyp-equivalent-compile-flags）

不移植/不修复 gyp（Python 2 语法面太广、修复收益低），按 pixelmatch.gyp 声明参数直接编译运行上游测试：

```bash
# cwd = 源码根目录（测试用相对路径读取 test/fixtures/*.rgba）
clang++ -std=c++11 -Wall -Wextra -Wshadow -fno-rtti -fexceptions -g -O0 \
        -I include test/test.cpp -o build_test
./build_test        # 4 个 diffTest 用例全部通过，exit 0
```

conan 配方按 header-library 交付头文件（package() 仅 copy include/mapbox/pixelmatch.hpp），
测试入口、cwd、退出码、日志记录进 notes.md 与 reports/test-report.md。

## 验证结果

- 上游测试 4/4 通过（1a/1b=143、2a/2b=12439、3a/3b=212、4a/4b=36089，含 diff 缓冲逐字节比对）
- 鸿蒙专项测试 4/4 通过（OHOS 工具链 /data/service/hnp/bin/clang++ 编译运行）
- conan-verify G0-G4/L2/L4/L5 全 PASS；finish W3 conan create exit_code=0
- test_package 消费者测试 1/1 Passed（真实调用 mapbox::pixelmatch()）

## 查重（七轴）

- exact_duplicate：否（知识图谱、正式条目、草稿、文档四范围检索 "gyp" 均无命中；
  E269 覆盖的是 Python 2 **测试 runner** 且解法为移植脚本，本例是 Python 2 **构建生成器**
  且解法为按等价参数直接编译，非同一场景）
- causal_duplicate：否（E269 根因=runner 脚本语法不可执行；本例根因=构建生成器不可用
  但编译参数可等价复现，绕过路径完全不同）
- trigger_overlap：与 E269（Python 2 print SyntaxError 签名）部分重叠——同为
  "Python 2 时代代码在 Python 3 环境抛 Missing parentheses"触发面，但触发主体不同
  （测试 runner vs 构建生成器）
- solution_overlap：与 E269 的 port-python-script 无重叠；与 E307/E321/E322
  （header-only 配方/直接编译）在"直接编译"动作上有部分重叠，但 E307 是 test_package
  用 profile 编译器直接编译，本例是绕过上游 gyp 生成器，场景不同
- combination_novelty：是（"gyp 生成器 Python 2 不可用 + header-only 库 + 按 gyp 声明
  cflags_cc 等价编译测试"三者组合在知识库无收录）
- boundary_novelty：是（适用边界=header-only/单测试目标可绕过生成器；不适用=依赖 gyp
  生成多目标/条件平台文件的大型项目）
- test_migration_novelty：否（上游测试形态未迁移，原样编译运行）

similar_to: [E269（Python 2 测试 runner）, E307（header-only 直接编译）, E321（header-only Conan 2 配方）]
caused_by: [] / conflicts_with: [] / prerequisite_of: []

## 复用要点

- 遇到 `env: exec python` 或 gyp `Missing parentheses` → 先判断是否 header-only/测试目标
  单一：是 → 读 gyp 的 cflags_cc 等价编译；否 → 才考虑 python2 别名或最小移植。
- 等价编译参数必须来自 pixelmatch.gyp 实际声明，不得自创参数；测试 cwd 保持源码根。
- 不得把该问题报为平台硬阻塞：编译参数明确可从 gyp 声明读取，属可修问题。

## 适用边界

- 适用：捆绑 gyp 且为 header-only 或单可执行测试目标的 C/C++ 项目（OHOS/CI 仅 Python 3）。
- 反例：依赖 gyp 生成多目标/平台条件产物的大型项目（如 Chromium 本体），必须解决
  Python 2 运行时或移植生成器。
