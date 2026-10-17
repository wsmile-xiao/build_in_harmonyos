# DRAFT-yosys-0.66 — release tarball 的子模块为空：外部工具接线

## 使用说明

GitHub 的 `refs/tags/<v>.tar.gz`（以及 codeload 归档）**不包含 git 子模块内容**。
如果项目用子模块承载①构建期头文件/源码，或②运行期外部工具二进制，适配时会分别遇到：

1. 构建期缺头文件 → 从对应 conan 包把文件**物化**到树内路径（构建期动作，不改上游源码）
2. 运行期缺二进制 → 声明为 **host requirement**（不是 tool_requires），用项目的『外部工具』开关指向它，
   并在 `package_info()` 用 `runenv_info` 导出环境变量

先核实归档与 release 资产（**不要只看 releases/download 的 404，要用 API 看 assets 数**）：

```bash
tar -tzf v0.66.tar.gz | grep -c '^yosys-0.66/abc/.'  # 0 -> 无文件（只有目录项 yosys-0.66/abc/）
curl -s https://api.github.com/repos/YosysHQ/yosys/releases/tags/v0.66 | grep -c '"name": "yosys-src.tar.gz"'  # 1 -> 有资产（该资产内联 abc/ 2316 文件与 libs/cxxopts）
```

## 适用范围

- 构建系统：任意（本条以自带 Makefile 为例），关键是源码/构建脚本按树内路径引用子模块
- 阶段：compilation（缺头文件）或 runtime（缺外部二进制）
- 适配源码来自 tag/codeload 归档而非 `git clone --recursive`
- 不适用：归档确实内联了子模块内容；或上游 release 附带独立资产

## 输入输出定义

- 输入：conan 包 `cxxopts`（头文件）、`abc`（外部二进制）；项目开关 `ABCEXTERNAL`、`DISABLE_SPAWN`
- 输出：树内 `libs/cxxopts/include/*.hpp`；`make` 时的 `ABCEXTERNAL=<abs>/bin/abc`；
  产物运行环境里的 `ABC=<消费者自己的 abc 路径>`

## 示例

```
$ make ENABLE_ABC=1 DISABLE_SPAWN=0
make: *** [Makefile:856: check-git-abc] Error 1
  ... is not configured as a git repository, and 'abc' folder is missing.
  If you already have ABC, set 'ABCEXTERNAL' make variable to point to ABC executable.

# 加 ABCEXTERNAL 后：
$ make ENABLE_ABC=1 ABCEXTERNAL=/home/.../abc/p/bin/abc DISABLE_SPAWN=0
... built bin/yosys (aarch64)                          # RC=0

# 运行期（ABC 环境变量优先于编译进去的路径）：
$ ABC=/consumer/abc/p/bin/abc yosys -p 'read_verilog t.v; synth; stat'
Time spent: 49% 1x abc (0 sec)                          # RC=0
```

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation` | 都涉及子模块/外部依赖的替代 | 那条针对 Catch2 单头文件测试依赖；本条同时覆盖**运行期外部工具**（host requirement + runenv 导出），并给出『不固化构建机路径』的接线 |
| `cvs-fast-export-1.59-generated-parser-sources-vs-regen-rules` | 都关于上游归档内容不完整 | 那条是生成产物与生成源并存导致的时间戳再生成；本条是子模块目录为空 |

## 验证证据

```
$ tar -tzf v0.66.tar.gz | grep -c '^yosys-0.66/abc/'   # 1（只有目录项）
$ tar -tzf v0.66.tar.gz | grep -c '^yosys-0.66/abc/.'  # 0（0 个文件）
$ ls /home/qianxia/.conan2/p/yosys.../s/abc/ | wc -l
0

$ conan create archives/y/yosys/0.66 -pr:h=... -pr:b=... --build=missing
yosys/0.66: Package 'c42828e97568cfa87dd952edd6ec0ca8338078f6' created    # EXIT=0

# test_package 真实执行（含 abc 综合）
PASS: yosys -V reports the 0.66 version banner
PASS: synthesized test.v (read_verilog + synth + stat)   # RC=0
```

- 退出码：0
- 日志绝对路径：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/033-local-create.log`
- 上游任务：PR #11115
