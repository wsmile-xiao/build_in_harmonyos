# clitest 0.5.0 适配笔记

## 编译环境
- 构建系统: custom（无构建系统：单文件 POSIX shell 脚本，直接安装）
- 编译日期: 2026-09-21
- 编译器: 不适用（零编译单元）；配方仍声明标准 settings 四项
- 状态: built

## 软件性质与选型核验

clitest 是一个「文档即测试」工具：读取文本/Markdown 文件，执行其中记录的命令并与
文件里写明的预期输出逐字节比对。上游交付物是**单个 POSIX shell 脚本 `clitest`**
（0.5.0 为 964 行）。

- 本仓库无 clitest 历史归档（`ls archives/c/clitest*` → 不存在），无历史结论可比对。
- 同形态先例：`archives/c/cronic/3`（纯 bash 脚本包）、`archives/l/lynis/3.1.7.1`
  （shell 工具 + shebang 适配 + commands.json）、`archives/p/powerlevel10k/1.20.0`。
  本包的配方形态、test_package 组织与 commands.json 均按此先例对齐。
- 依赖（W0）：`requires`/`tool_requires` 均为空，无需制品仓探测。运行期依赖
  `sh/sed/grep/diff/cat/mktemp/awk/tr` 属系统工具，不是 Conan 包；可选的
  `#=> --perl` 内联匹配才需要 `perl`。

### 顶层 Makefile 不是构建系统（选型关键）

上游根目录有 `Makefile`，但内容只是把 `shfmt`/`checkbashisms`/`shellcheck` 与多
shell 测试封装成 `docker run`：

```
docker_run = docker run --rm -t -v $$PWD:/mnt $(docker_image)
test_cmd   = ./clitest --first --progress none test.md
test: test-bash test-dash test-mksh test-sh test-zsh
```

没有 `all`/`install` 目标，没有编译单元。因此配方 `build_system: custom`，
`build()` 只应用补丁并做产物校验。

### lang-preflight 误判（已如实记录，见 SKILL_FEEDBACK）

```
$ OHPCD_LANG=bash python3 scripts/ohc-run.py lang-preflight clitest 0.5.0 --src <src>
  ❌ 语言不匹配: task=bash, detected=c → env_unsupported
     build_system: "make"
     manifest:     "顶层 Makefile（无更强 manifest）"
     source_stats: "无源文件可统计"
```

判定器「构建系统 > 源码统计」的优先级把这个仅用于 docker 封装的 `Makefile` 当成
C 项目证据，即便同一份证据里 `source_stats` 自承「无源文件可统计」也未降级。
实际源码构成：`.sh` 62 个 + 主脚本 1 个（`find . -type f | sed 's/.*\.//' | sort |
uniq -c`），C/C++ 源文件 0 个。工具自身默认口径（`OHPCD_LANG=cpp`）下 detected=c
属兼容族，返回 `语言匹配 … 继续适配主流程`。本包按仓库既有脚本类先例继续适配，
该误判已写入 SKILL_FEEDBACK「自动化补全」节。

## 编译步骤

无编译。等价的固化步骤即配方本身：

```bash
# 取源码（构建机 github.com 不可达，改用 GitHub 官方 tarball 端点 codeload）
curl -sSL -o clitest-0.5.0.tar.gz \
  https://codeload.github.com/aureliojargas/clitest/tar.gz/refs/tags/0.5.0
sha256sum clitest-0.5.0.tar.gz
# 4005de0bc27e4676e418ab1e1e64861272aa74af1212c73a1173760fc449b049

# conan 侧：source() → get(strip_root) ；build() → apply_conandata_patches + 校验
#           package() → copy clitest 到 bin/，LICENSE.txt 到 licenses/，文档到 share/doc
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后 `clitest` 在鸿蒙上无法直接执行 | 鸿蒙无传统 `/bin` 目录，`sh` 在 `/system/bin/sh`（知识条目 E165）；上游 shebang 为 `#!/bin/sh` | 补丁改写 shebang 为 `#!/system/bin/sh`；`build()` 中断言 shebang 生效，补丁没打上即 `ConanException` |
| 2 | `$TMPDIR` 未设置时 clitest 在鸿蒙上完全不可用 | 上游把临时目录基路径硬编码为 `${TMPDIR:-/tmp}`，而鸿蒙 `/tmp` 只读（知识条目 E002），`mktemp -d`/`mkdir` 均失败 → `cannot create temporary dir` 退出 | 补丁只改**默认值**：`/tmp` 可写则仍用 `/tmp`，否则回退 `$HOME`。显式设置的 `$TMPDIR` 不受影响 |
| 3 | 第一版临时目录补丁打挂了 1 个上游用例 | 初版把「显式 `$TMPDIR` 无效」也一并回退，改掉了上游语义；上游 test.md 第 52 行专门断言 `TMPDIR=/notfound` 必须报错 | 收窄补丁范围到「仅 `$TMPDIR` 未设置时的默认值」，上游用例恢复通过（286/286） |
| 4 | 上游测试在改 shebang 后大面积失败（262/286） | `test.md` 的用例以 `./clitest` 形式调用，依赖 shebang；适配机无 `/system/bin/sh` | 适配机建立 `/system/bin/sh -> /bin/dash` 映射（构建机准备，不入配方）后复跑，286/286 恢复。CI 设备本身就有 `/system/bin/sh` |
| 5 | `github.com` 在构建机上连接超时 | 网络环境限制（`curl` 30s timeout，`http=000`） | 改用 GitHub 官方 tarball 端点 `codeload.github.com`（与 `/archive/refs/tags/` 同一字节流），仓库先例：`archives/w/wiggle/1.3`、`archives/w/wireguard-tools/1.0.20250521` |
| 6 | `conan-init` 生成 autotools + C 模板（`test.c`/`CMakeLists.txt`） | 同问题 1 的误判链：顶层 Makefile 被当作 autotools 证据 | 按 `cronic/3` 先例改写为脚本包配方，删除 C 模板文件 |
| 7 | PR #11869 CI 构建 #56023（鸿蒙真机）：test_package 通用脚本 5 过 7 败，报 `can't create temporary file /tmp/sh*.tmp: Read-only file system`，随后 clitest 报 `no test found in input file` | **测试脚本自身的问题，与 clitest 及补丁无关**：鸿蒙 `/system/bin/sh` 为每个 here-document 在只读 `/tmp` 建临时文件，失败后不中止脚本，`cat > f <<'EOF'` 把 fixture 静默写成空文件。worker 自带可写 `TMPDIR`、脚本也 export 了可写 `TMPDIR`，均无效。佐证：同一次运行中唯一用 `printf` 写 fixture 的 `--prefix tab` 用例通过 | 两个测试脚本的 fixture 全部改用 `printf` 生成并校验非空；`TMPDIR` 仅在缺失/不可写时才兜底覆盖。本地「只读 `/tmp` + zsh/bash 驱动」同构场景先复现出与 CI 逐条一致的 5 过 7 败，修复后 12/12、9/9。沉淀为知识草稿 E547-draft-3028 |

## 源码修改

`patches/0001-clitest.patch`（由 `refresh-patch --auto` 生成，+16/-3，单文件两处）：

1. `clitest:1` — `#!/bin/sh` → `#!/system/bin/sh`
2. `clitest:582` — `tt_make_temp_dir()` 的基路径选择：

```sh
    if test -n "${TMPDIR:-}"; then
        tt_temp_base="$TMPDIR"
    elif test -d /tmp && test -w /tmp; then
        tt_temp_base='/tmp'
    else
        tt_temp_base="${HOME:-.}"
    fi
```

并把随后的 `mktemp -d`/手工 `mkdir` 两处从 `${TMPDIR:-/tmp}` 改为 `$tt_temp_base`；
新增全局变量 `tt_temp_base=` 声明（与上游 `tt_` 前缀风格一致）。

补丁中**没有任何平台宏**（shell 脚本无 `__OHOS__` 概念），shebang 是静态路径改写，
临时目录改动是运行期可写性探测，在任何 POSIX 系统上语义一致（`/tmp` 可写时行为与
上游完全相同）。

## 依赖版本

无 Conan 依赖。适配机验证用到的解释器：bash 5.2、dash 0.5.12、zsh 5.9、
busybox 1.37 sh。

## 验证结果

### 1. 上游测试清点（R51 第一步）

```bash
$ wc -l test.md            # 上游自举测试文档
2420 test.md
$ ls test | wc -l          # fixture / 辅助脚本
65
$ grep -n 'test_cmd\|^test:' Makefile
test_cmd = ./clitest --first --progress none test.md
test: test-bash test-dash test-mksh test-sh test-zsh
```

无 ctest/pytest 注册，无编译型测试。上游 `.github/workflows/check.yml` 跑同一矩阵。

### 2. 上游测试实跑（R51 第二步）N=286

```bash
# 原始源码
$ bash ./clitest --progress none test.md        → OK: 286 of 286 tests passed
$ dash ./clitest --progress none test.md        → OK: 286 of 286 tests passed

# 打补丁后（/system/bin/sh -> /bin/dash 为构建机准备）
$ bash ./clitest --progress none test.md        → OK: 286 of 286 tests passed
$ dash ./clitest --progress none test.md        → OK: 286 of 286 tests passed
$ zsh ./clitest --progress none test.md         → OK: 286 of 286 tests passed
$ busybox sh ./clitest --progress none test.md  → OK: 286 of 286 tests passed
$ ./clitest --progress none test.md             → OK: 286 of 286 tests passed
```

未复现的上游矩阵行：`mksh`、`ksh`（适配机未安装，`command -v` 为空）。

### 3. 补丁价值对照实验（只读 `/tmp` + 未设 `$TMPDIR`）

```bash
$ unshare -rm sh -c 'mount -t tmpfs -o ro,size=1m tmpfs /tmp; \
    cd <orig> && unset TMPDIR; HOME=/root dash ./clitest test/ok-1.sh'
mkdir: cannot create directory '/tmp/clitest.0.97017.2257289': Read-only file system
clitest: Error: cannot create temporary dir: /tmp/clitest.0.97017.2257289   ← 未打补丁：失败

$ unshare -rm sh -c 'mount -t tmpfs -o ro,size=1m tmpfs /tmp; \
    cd <work> && unset TMPDIR; HOME=/root ./clitest test/ok-1.sh'
#1      echo ok
OK: 1 of 1 test passed                                                      ← 打补丁后：通过
```

上游语义未被破坏：

```bash
$ TMPDIR=/notfound ./clitest test/ok-1.sh
clitest: Error: cannot create temporary dir: /notfound/clitest.0.128877.2257205
```

### 4. test_package（补全用例，适配机实跑）

```
generic:   12 passed, 0 failed
harmonyos:  8 passed, 0 failed, 1 skipped
```

CI 构建 #56023 暴露的 here-doc 问题修复后（问题表第 7 行），追加在「只读 `/tmp`」命名空间内
复验（`unshare -rm` + 只读 tmpfs 挂载 `/tmp`，与真机 `/tmp` 只读同构）：

```
zsh 驱动 + 未设 TMPDIR           : generic 12 passed / harmonyos 9 passed, 0 skipped
bash 驱动 + TMPDIR=/nonexistent  : generic 12 passed / harmonyos 9 passed, 0 skipped
dash / busybox sh（常规环境）     : generic 12 passed / harmonyos 8 passed, 1 skipped
```

只读 `/tmp` 场景下，原先 SKIP 的「`$TMPDIR` 未设置时回退 `$HOME`」断言前提成立，转为实跑通过。

唯一 SKIP 为「只读 `/tmp` 回退」——适配机 `/tmp` 可写，前提不成立，脚本打印 SKIP
而非当作通过；CI 运行在鸿蒙设备上，该前提成立，届时会实跑。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/clitest` | 上游单文件脚本 + 1 个适配补丁（shebang / 临时目录默认值） |
| `share/doc/clitest/README.md` | 上游使用文档 |
| `share/doc/clitest/CHANGELOG.md` | 上游变更日志 |
| `licenses/LICENSE.txt` | 上游 MIT 许可证 |

## 注意事项

- **执行位不可依赖**：HMDFS 上 `chmod` 常被忽略。配方尽力 `chmod 0755`，但
  test_package 一律以 `sh <pkg>/bin/clitest` 显式解释执行；调用方遇到执行位问题时
  同样可以这么做。
- **`package_id` 保留 `os`**：产物含鸿蒙专用 shebang，不是平台无关脚本，因此只删
  `arch`/`compiler`/`build_type`（与 `archives/l/lynis/3.1.7.1` 同口径）。
- **上游测试不在 `build()` 内运行**：`test.md` 的用例通过 shebang 调用 `./clitest`，
  在非鸿蒙构建机上会测到「构建机有没有 `/system/bin/sh`」而不是 clitest 本身；且其
  中若干用例依赖 `perl` 与 GNU diff 行为，鸿蒙 toybox 不提供。上游套件已在适配阶段
  完整实跑（上方第 2 节），平台相关行为由 test_package 在 CI 设备上复验。
- **可选功能的运行期依赖**：`#=> --perl` 内联匹配需要 `perl`，鸿蒙上没有时该匹配方式
  不可用，其余匹配方式（`--text`/`--lines`/`--exit`/`--egrep`/`--file`/`--eval`）不受影响。
---

**编译结束**: 2026-09-21 12:01
**最终状态**: built
