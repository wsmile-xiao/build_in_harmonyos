# tradcpp 0.5.3 — HarmonyOS PC (aarch64) 适配笔记

- 上游：tradcpp — a traditional (K&R-style) C preprocessor，David A. Holland
- 项目页：https://www.NetBSD.org/~dholland/tradcpp/
- 下载站：https://cdn.NetBSD.org/pub/NetBSD/misc/dholland/tradcpp-0.5.3.tar.gz
  （项目页指向的 ftp.NetBSD.org 同一目录；38683 字节）
- 版本：0.5.3（`version.h`: `VERSION_STRING "0.5.3"`，`VERSION_LONG "NetBSD tradcpp 0.5.3"`）
- 许可证：BSD-2-Clause
- 构建系统：**NetBSD makefile**（见 §2）
- 依赖：**无**
- 包形态：`bin/tradcpp` + `share/man/man1/tradcpp.1`（应用包 → 软件级 commands.json，R38）
- 状态：**READY_FOR_HARMONY**（WSL 侧准备完成，真机 conan create 未执行）

## 1. 工具定位（为什么值得适配）

tradcpp 实现的是 **Reiser 传统预处理算法**，而不是 ISO 算法。区别不是
"旧一点"，而是**语义不同**：

```
$ printf '#define STR(x) #x\nSTR(hello)\n' | cpp        # ISO: 字符串化
"hello"

$ printf '#define STR(x) #x\nSTR(hello)\n' | tradcpp    # 传统: 原样透传
#hello
```

现代 cpp 不再支持传统语义，而 NetBSD 构建系统仍需它来处理老式 K&R C。
这是"适配一个、解锁一串老代码预处理"的工具。

## 2. 构建系统：上游 Makefile 是 NetBSD 专用（核心适配点）

上游 `Makefile` 全文只有 9 行，末尾是：

```make
.include <bsd.prog.mk>
```

这是 NetBSD make（bmake）的语法，**GNU make 完全无法解析**（直接语法错误，
不是警告）。仓库 worker 上是 GNU make。

### 解法：新增 `GNUmakefile`，不动上游 `Makefile`

GNU make 的文件查找顺序是 `GNUmakefile` → `makefile` → `Makefile`。因此补丁
只是**新增**一个 `GNUmakefile`，两个文件并存：

- worker（GNU make）自动选中 `GNUmakefile`；
- NetBSD 用户仍用原 `Makefile`，上游零改动。

`GNUmakefile` 里的 `SRCS` 与上游 `Makefile` 的 `SRCS` 逐项一致（9 个 .c）：

```
main.c files.c directive.c eval.c macro.c output.c place.c array.c utils.c
```

编译器与标志全部取自 Conan toolchain 环境（`$(CC)` / `$(CPPFLAGS)` /
`$(CFLAGS)` / `$(LDFLAGS)`），不写死 `cc`（R33）。

> 补丁写法：新增文件必须用 `diff -u /dev/null b/GNUmakefile` 的 `/dev/null`
> 约定。用 `diff -N` 会得到 `--- a/GNUmakefile` 头，`patch -p1` 会停下来问
> `File to patch:`，在非交互构建里就是失败。

## 3. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_case_total` | **40** | `tests/Makefile` 里 `TESTS=` 显式枚举 `t01 … t40`，是**可靠的 runner 枚举**，不是 UNKNOWN |
| `upstream_test_files` | **80** | 40 个 `tNN.c`（输入）+ 40 个 `tNN.good`（期望输出）；另有 `tests/subdir/test.h`、`tests/Makefile` |
| `upstream_test_targets` | **1** | `tests/Makefile`: `all: run-tests .WAIT show-diffs`；40 个 `$(T).diff` 是其内部依赖，不是独立测试程序 |

### 复现 harness 的两个必须细节

上游 `tests/Makefile` 的每个用例：

```make
$(T).run: $(TRADCPP) $(T).c
	$(TRADCPP) $(T).c > $(T).run 2>&1 || echo FAILED >> $(T).run
$(T).diff: $(T).run $(T).good $(TRADCPP)
	-diff -u $(T).good $(T).run > $(T).diff
```

1. **cwd 必须是 `tests/`**：t17.c 与 t38.c 使用 `#include "subdir/test.h"` 这样的
   相对路径。
2. **必须传裸文件名 `tNN.c`**：t38 断言 `__FILE__`，其 `.good` 里记录的是
   `"t38.c"`；若传绝对路径或从父目录运行，输出会变成 `"../tests/t38.c"`，
   diff 立刻失败（已实测复现）。

配方的 `conanfile.py::_run_upstream_tests()` 逐条复现上述命令（含
`|| echo FAILED`），再用 Python 做逐字节比较（等价于上游的 `diff`），
**失败即构建失败**——不做"测试红了还出包"的处理。

## 4. WSL 侧已完成的可验证证据（无 Harmony PC）

### 4.1 补丁 apply
```
$ patch -p1 --batch -i patches/0001-add-GNUmakefile.patch
patching file GNUmakefile          # 无 fuzz、无交互
```

### 4.2 打补丁后在 GNU make 下构建
```
$ make -s CC=gcc CFLAGS="-O2 -std=gnu17"
$ ls -l tradcpp
  81648  tradcpp
```
（上游 `Makefile` 仍在原地未被修改。）

### 4.3 上游全部 40 个用例在本机实跑
```
$ cd tests && for i in $(seq -w 1 40); do ./tradcpp t$i.c > t$i.run 2>&1; diff -q t$i.good t$i.run; done
PASS=40  FAIL=0
```

### 4.4 平台无关性核查（决定 aarch64 上是否也会 40/40）
```
$ grep -l "__linux__\|__aarch64__\|__x86_64__\|__unix__\|__NetBSD__\|__ELF__\|__LP64__\|__TRADCPP__" tests/*.c tests/*.good
（无输出）
```
40 条用例都不依赖平台相关预定义宏；`config.h` 对未知平台回落 `__unix__`。
因此 x86_64 Linux 与 aarch64 OHOS 的输出应当一致。

### 4.5 test_package 语义实测（决定断言值）
```
$ printf '#define concat(a, b) a/**/b\n#define STR(x) #x\nconcat(abc,def)\nSTR(hello)\n#ifdef GREETING\nGREETING\n#endif\n' > input.c
$ ./tradcpp -DGREETING=bonjour input.c output.txt
$ cat -A output.txt
abcdef$
#hello$
bonjour$
```
`#hello` 这一行是传统预处理语义的直接证据（ISO cpp 会输出 `"hello"`）。

## 5. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：确认 GNU make 选中 `GNUmakefile`
   且上游 `Makefile` 不被读到
2. `build()` 内 40 条上游用例的真机通过数（预期 40/40；若因平台差异有失败，
   失败用例名会被写进 ConanException 消息）
3. test_package 的 CLI 语义断言（`#hello` 而非 `"hello"`）
4. 软件级 commands.json 是否被 CI L0k 接受

## 6. 补充：WSL 侧完整 `conan create` 实测（本机原生 Linux profile）

在独立 `CONAN_HOME` 上真跑完整 `conan create`，暴露出两个纯静态检查
抓不到的问题，均已修复：

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | `make` 报 `No targets specified and no makefile found` | `Autotools.make()` 在 **build 目录**执行，而 GNUmakefile 在源码目录 | 改为 `self.run("make -j1", cwd=self.source_folder)`；toolchain 生成的 CC/CFLAGS/CPPFLAGS/LDFLAGS 对 `self.run` 同样生效（探针实测确认） |
| 2 | `bool.h:36:13: error: 'bool' cannot be defined via 'typedef'` | `bool.h` 写的是传统写法 `typedef int bool;`。**C23 把 bool 变成关键字**，该 typedef 从 `-std=c23` 起是硬错误。Conan 默认不传 `-std`，GCC 15 默认 gnu23 → 直接编不过。（本地手工验证时我显式传了 `-std=gnu17`，所以没暴露——这正是"必须真跑 conan create"的理由） | GNUmakefile 增加 `CSTD ?= -std=gnu17` 并接进编译规则；clang 15（OHOS worker）默认就是 gnu17，固定只是防新编译器默认上浮 |

最终本机 `conan create` 结果：

```
tradcpp/0.5.3: RUN: make -j1
tradcpp/0.5.3: tradcpp upstream tests: 40/40 passed      ← build() 内真实执行
tradcpp/0.5.3: Package created
test package: RUN: tradcpp -DGREETING=bonjour input.c output.txt
→ 无异常，test_package 通过
```

> 注：`tradcpp` 是 `application` 类型，其 bin/ 会被 Conan 注入构建环境，
> 所以 test() 里可以直接用裸命令名 `tradcpp`（与 triangle 那种库包不同）。
