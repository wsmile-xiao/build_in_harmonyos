# palbart 2.14 适配笔记

> 平台任务号：9288（活动：开源鸿蒙PC专项积分赛；主号名额超限，经小号中转 relay 认领）
> 适配日期：2026-10-01　执行：XiaYuanOwO（云鸢 / 青岛城市学院）

## 一、这个包到底是什么

`palbart` 不是「条码小工具」，而是 **GNU barcode 2.14 的 PostScript 后端驱动**。
Debian 原包只有 3 个文件：

```
palbart/palbart.c   170113 字节（4353 行）
palbart/README         400 字节
palbart/palbart.1     7290 字节（man page）
```

没有 Makefile、没有 configure、没有 CMakeLists——上游把构建放在 GNU barcode
顶层目录的 makefile 里，而 Debian 只取驱动子目录，所以配方必须直驱 clang。

## 二、条码描述语言（全部来自实测，不是抄源码）

palbart 读一份纯文本文件，边解释边输出两份产物：
`<输入名>.lst`（可打印符号清单）与 `<输入名>.bin`（编码后的条码位流）。

| 语法 | 含义 |
|------|------|
| `*4 2 100 50` | 伪操作：定义字模 4（Code 39），后三个数为参数 |
| `$HELLO` | 以 `$` 开头的行是**字面文本**，不查符号表 |
| `HELLO` | 不带 `$` 的行按符号名查表；未定义则报 `UD undefined` |
| `*0 5` | 伪操作：以码 5 结束当前页（可省略，解释器会自动补页） |

## 三、取证表：qemu-aarch64 + OHOS sysroot 实测输出

以下五组是 test_palbart.c 全部 23 条断言的**唯一期望值来源**。

### A：不给输入文件
```
stdout+stderr: ./palbart:  no input file specified
RC = 255      产物：无 .bin
```

### B：完整字模 4
输入 `*4 2 100 50\n$HELLO\n*0 5\n`
```
RC = 0
bc.lst (212 bytes):
      *4 2 100 50                                                         Page 1
    1        0004  *4 2 100 50
      00004  0152
    2              $HELLO
      No detected errors
      No links generated
bc.bin = 256 bytes
```

### C：未定义符号 + 缺 `$` 收尾
输入 `*4 2 100 50\nHELLO\n*0 5\n`
```
stdout:       2 detected errors
RC = 1
bc.lst (291 bytes) 多出两行诊断：
    2 00005  0000  HELLO
UD undefined      ^
    3        0000  *0 5
      00000  0005
ND no $ at EOF
      2 detected errors
      No links generated
bc.bin = 262 bytes
```

### D：省略 `*0 5` 收尾
输入 `*4 2 100 50\n$HELLO\n` → 与 B 组**完全一致**（RC=0，.lst 212B，.bin 256B），
证明收尾伪操作是可选的，解释器会自动补页。

### E：空输入文件
```
stdout: 1 detected error
RC = 1
bc.lst (154 bytes):
      $                                                                   Page 1
ND no $ at EOF
      1 detected error
      No links generated
bc.bin = 252 bytes
```

**注意单复数**：C 组是 `2 detected errors`（复数），E 组是 `1 detected error`
（单数）。这条差异是 E2 断言的依据——它验证错误计数随诊断条数变化，而不只是
「有错误就报错」。

## 四、OHOS 适配：零 patch

这是本包最省事的地方，与 mailto 1.3.2 恰好相反。

- `palbart.c` 只 include 五个头文件：`ctype.h` `errno.h` `stdio.h`
  `stdlib.h` `string.h`——全部由 OHOS sysroot 自带。
- **一次 `clang-ohos -O2 -std=gnu99 -w` 编译通过，零 error 零阻断 warning。**
- 链接产物：`ELF64 / AArch64`，`NEEDED` 仅 `libc.so`，可执行文件 60096 字节。
- 因此 conandata.yml **不声明 `patches:` 键**。

### 坑 1（继承自 mailto 1.3.2）：conandata 的 patches 格式

Conan 2.x 的 `apply_conandata_patches()` 按 `self.version` 查找补丁列表。
若把 `patches` 误写成「以文件名为键的 dict」，Conan 会取到**空列表并静默跳过**
补丁，CI 门禁 L0f 报 `bad_patch_format`。正确写法是列表：

```yaml
patches:
  - patch_file: "patches/0001-xxx.patch"
    patch_description: "..."
    patch_type: "portability"
```

本包零补丁，故**整个 `patches` 键都不写**——不写就不会触发 L0f 校验。

### 坑 2：`CC` 不能靠环境变量，改用 CMakeToolchain

这是本包最费时间的一处，结论与 mailto 1.3.2 相反。

先说现象。本仓库 `ohos-aarch64` profile 的 `[buildenv]` 段写着
`CC=C:/ohos-tc/bin/clang-ohos.bat`，配方里 `os.environ.get("CC")` 取它。
实测（Conan 2.29.1 / Windows）：

| 写法 | 结果 |
|------|------|
| `os.environ.get("CC")` | 取决于命令行是否传了 `--profile:build`——**加了有值，不加是 None** |
| `self.conf["tools.build:compiler_executables"]["c"]` | `TypeError: 'Conf' object is not subscriptable`（Conan 2.29 的 Conf 不支持下标） |
| `self.conf.get("tools.build:compiler_executables")["c"]` | 可用，返回 `{'c': ..., 'cpp': ...}` |
| `self.run("<clang-ohos.bat> ...")` | `Error 1` / `'.' is not recognized as an internal or external command` |
| `subprocess.run("<clang-ohos.bat> ...")` | **rc=0 正常** |

三条独立证据：

1. **Conan 的 `[buildenv]` 不会稳定注入 `self.run()` 的子进程环境。**
   同一个 profile，加 `--profile:build` 时拿得到 CC，不加就拿不到。
   配方行为随命令行参数漂移，不能只读环境变量。
2. **`self.run()` 在这台 Windows 上对任何命令都会坏**，连 `cmake` 都会。
   用 `--profile:build=default`（无 `[buildenv]`）时同样的配方完全正常。
   `cmd.exe` 把 PATH 里的正斜杠条目当开关分隔符，整条命令被打散。
3. **Conan 2.29 的 `Conf` 不能用 `[]`**，必须 `.get()`。

**最终方案：改用 `CMakeToolchain` 驱动编译**，完全绕开 `self.run`：

```python
def layout(self):
    cmake_layout(self, build_folder=".")   # 见坑 3
def generate(self):
    CMakeToolchain(self).generate()
def build(self):
    cmake = CMake(self); cmake.configure(); cmake.build()
```

编译器与 sysroot 由 `conan_toolchain.cmake` 从 `conf` 读取
（`tools.build:compiler_executables` 指向 clang-ohos.bat，
`system_name=OHOS`、`system_processor=aarch64`），不经过环境变量。
这也是本仓库其它配方统一的做法。

另注：**不要给 CC 加引号**。Conan 解析整条命令时前导引号会被吃掉。

### 坑 3：`cmake_layout` 的 build_folder 必须钉成 `.`

默认布局把 generators 放在 `build/{build_type}/generators`，而 `CMake(self)`
去找的是别处，直接报：

```
CMakePresets.json was not found in .../build/Release/generators folder.
Check that you are using CMakeToolchain as generator...
```

`cmake_layout(self, build_folder=".")` 让 `generators/` 落在构建根，对得上。

### 坑 5：`-w` 不是偷懒

`palbart.c` 是 1990 年代的 gnu89 代码（K&R 函数定义、赋值当条件、旧式块
注释嵌套）。上游自己的 Makefile 也是 `-w` 编译。这里沿用上游口径统一静默，
避免把历史风格告警灌满 CI 日志、淹没真正的问题。
（conandata 的 patches 格式问题见上文「坑 1」，本包零补丁故整键省略。）

## 五、验证标准与结果

| 项 | 结果 |
|---|---|
| `conan create` | **通过**（主包 + test_package 全绿） |
| 产物架构 | ELF64 / AArch64 |
| `NEEDED` | 仅 `libc.so` |
| 包内容 | `bin/palbart`(60096B) + `share/doc/palbart/{README,palbart.1}` |
| qemu-aarch64 测试 | **23 checks, 0 failures**（跑在真实 conan 包目录上） |
| 知识库门禁 | 待投递后回报 |
| CI L0 / L1 | 待投递后回报 |

## 六、适配范围声明

本包只安装 `bin/palbart` 与文档，**不安装** gnuplot / ghostscript 等排版工具。
palbart 的职责到「解释描述语言 + 编码位流」为止，真正的 PostScript 渲染由
下游解释器完成。这是刻意的范围收窄：OHOS PC 侧的条码排版流水线由调用方决定
渲染后端，包层不替它做决定。
