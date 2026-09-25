# clitest

clitest 是一个 Unix 命令行测试器（单文件 POSIX shell 脚本）。它读取一个纯文本或
Markdown 文件，把文件里记录在提示符之后的每一条命令真实执行一遍，再把实际输出与
文件中写明的预期输出逐字节比对。这让「文档即测试」成为可能：README 里的示例、
教程里的命令行片段，都可以直接当作回归测试跑。

- 上游：https://github.com/aureliojargas/clitest （tag `0.5.0`）
- 许可证：MIT

## 交付内容

- `bin/clitest`：上游单文件脚本，应用了 1 个鸿蒙适配补丁（见下）。
- `share/doc/clitest/README.md`、`share/doc/clitest/CHANGELOG.md`：上游文档。
- `licenses/LICENSE.txt`：上游 MIT 许可证正文。

上游没有编译单元，也没有 `configure`/`CMakeLists.txt`；仓库根的 `Makefile` 只是把
`shfmt`/`shellcheck`/多 shell 测试封装成 `docker run`，供维护者本地使用，不是构建
系统。因此本包没有编译步骤。

## 使用

```sh
# 把 README 里的命令示例当测试跑
clitest README.md

# 纯文本测试文件
clitest tests.txt

# Markdown 中以 tab 缩进的代码块
clitest --prefix tab doc.md
```

测试文件的写法（`$ ` 之后是命令，紧随其后的是预期输出）：

```
$ echo ok
ok
$ printf '1\n2\n3\n'            #=> --lines 3
$ sh -c 'exit 3'                #=> --exit 3
```

全部通过时退出码为 0，有用例失败时退出码非 0 并打印 diff。

## 运行时依赖

`sh`、`sed`、`grep`、`diff`、`cat`、`mktemp`、`awk`、`tr` —— 都是操作系统自带工具，
不是 Conan 包，因此配方没有 `requires`/`tool_requires`。可选的 `#=> --perl` 内联
匹配方式需要 `perl`，其余匹配方式（`--text`/`--lines`/`--exit`/`--egrep`/`--file`/
`--eval`）不需要。

## HarmonyOS 适配

单个补丁 `patches/0001-clitest.patch`，两处改动，都是运行期可验证的实际问题：

1. **shebang → `/system/bin/sh`**（知识条目 E165）。鸿蒙没有传统的 `/bin` 目录，
   `sh` 位于 `/system/bin/sh`。不改则安装后的 `clitest` 无法直接执行，而软件级
   `commands.json` 声明的正是直接执行 `bin/clitest`。
2. **临时目录默认值**（知识条目 E002）。上游把基路径硬编码成 `${TMPDIR:-/tmp}`，
   而鸿蒙的 `/tmp` 只读：`$TMPDIR` 未设置时 clitest 会以
   `cannot create temporary dir` 直接失败，工具完全不可用。补丁只改**默认值**
   （`/tmp` 可写则仍用 `/tmp`，否则回退 `$HOME`）；**显式设置的 `$TMPDIR` 仍原样
   尊重**，上游「无效 `TMPDIR` 必须大声失败」的语义及其测试用例保持不变。

补丁价值有对照实验佐证（只读 `/tmp` + 未设 `$TMPDIR`）：未打补丁的脚本报
`cannot create temporary dir` 退出，打补丁后同场景下测试正常通过。

其他平台约束：

- 纯脚本包，`package_id` 删除 `arch`/`compiler`/`build_type`，保留 `os`（产物带鸿蒙
  专用 shebang）。
- HMDFS 上 `chmod` 常被忽略、执行位不可靠：配方尽力 `chmod 0755`，但 test_package
  一律通过显式解释器（`sh <pkg>/bin/clitest`）调用，不依赖执行位。

## 测试

| 来源 | 用例数 | 结果 |
|------|--------|------|
| 上游 `test.md`（自举测试） | 286 | 286/286 通过（bash / dash / zsh / busybox sh / shebang 直执行，补丁前后一致） |
| `test_package/test_clitest.sh` | 12 断言 | 12/12 通过 |
| `test_package/test_clitest_ohos.sh` | 9 断言 | 8 通过 + 1 SKIP（只读 `/tmp` 前提在适配机上不成立，CI 设备上会实跑） |

完整清点证据、实跑记录与对照实验详见版本目录的 `notes.md`。

## 版本

| 版本 | 制品引用 | 上游版本 | 状态 |
|------|----------|----------|------|
| 0.5.0 | `clitest/0.5.0` | 0.5.0 | built |

## 参考资料

- 源码与文档：https://github.com/aureliojargas/clitest
- 作者主页：http://aurelio.net
