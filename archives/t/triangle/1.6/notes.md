# triangle 1.6 — HarmonyOS PC (aarch64) 适配笔记

- 上游：Triangle — A Two-Dimensional Quality Mesh Generator and Delaunay
  Triangulator，Jonathan Richard Shewchuk
- 官方页面：https://www.cs.cmu.edu/~quake/triangle.html
- 分发：页面唯一下载链接指向 https://www.netlib.org/voronoi/triangle.zip
  （`.zip`，扁平结构：README / triangle.c / triangle.h / tricall.c /
  showme.c / makefile / A.poly）
- 版本：1.6（README 首行 + `triangle -h` 输出的 "Version 1.6"）
- 许可证：**非商业**。上游原文：可自由再分发（保留版权声明、不得收费），
  私人/研究/院校使用免费，但 *"Distribution of this code as part of a
  commercial system is permissible ONLY BY DIRECT ARRANGEMENT WITH THE
  AUTHOR."* → conandata 只引用官方 URL，仓库不分发源码本体；许可证情况
  在此如实记录，供评审判断。
- 构建系统：上游手写 `makefile`（无 configure / 无 CMake / 无 autotools）
- 依赖：**无**
- 包形态：
  - `bin/triangle`（CLI，R38 → 软件级 commands.json）
  - `lib/libtriangle.a` + `include/triangle.h`（可嵌入 API）
- 状态：**READY_FOR_HARMONY** —— WSL 侧已跑通完整 `conan create`（见 §6），
  HarmonyOS 真机 conan create 尚未执行

## 1. 上游调查要点

分发 zip 只有 7 个文件，全部读过：

| 文件 | 用途 |
|---|---|
| `triangle.c` | 650 KB 单文件；不带宏 → CLI 主程序；带 `-DTRILIBRARY` → 可嵌入对象 |
| `triangle.h` | 嵌入 API：`struct triangulateio` + `triangulate()` / `trifree()` |
| `tricall.c` | 上游示例（README: "Sample program that calls Triangle"），**不是测试** |
| `showme.c` | X11 图形查看器，**不构建**（OHOS 无 X11） |
| `makefile` | 目标：`all` / `trilibrary` / `triangle` / `tricall` / `triangle.o` / `showme` / `distclean` |
| `A.poly` | 唯一随包样例输入（29 顶点 / 29 段 / 1 洞） |
| `README` | 说明 + 许可证 |

## 2. 平台适配点（1 个补丁，4 处改动，均无平台宏空壳）

补丁只动 `makefile`，**不改 triangle.c**：

### 2.1 `-DLINUX` 必须去掉（关键）
`-DLINUX` 在 triangle.c 里只做一件事：

```c
#ifdef LINUX
#include <fpu_control.h>          /* triangle.c:352 */
#endif
...
#ifdef LINUX
  cword = 4722;
  _FPU_SETCW(cword);              /* triangle.c:4902-4905 */
#endif
```

`<fpu_control.h>` 与 `_FPU_SETCW()` 是 glibc/x86 专有，OHOS（musl + aarch64）
上不存在 → 保留 `-DLINUX` 会直接编译失败。

去掉是**正确**而非绕过：这段代码的作用是压低 x87 的精度控制字以避免
80-bit 扩展精度干扰精确谓词。aarch64 用原生 IEEE 754 double，不存在 x87
扩展精度问题，本来就不需要这段。

### 2.2 去掉 X11 开关
`-I/usr/X11R6/include -L/usr/X11R6/lib` 只服务于 showme（X11）。本配方不
构建 showme。

### 2.3 让 Conan toolchain 提供编译标志（R33）
```diff
-CC = cc
+CC ?= cc
...
-CSWITCHES = -O -DLINUX -I/usr/X11R6/include -L/usr/X11R6/lib
+CSTD = -std=gnu17
+CSWITCHES = $(CPPFLAGS) $(CFLAGS) $(CSTD)
```

### 2.4 `-std=gnu17`（C23 兼容性）
triangle.c 是 1990 年代 K&R C，**124 个函数使用 old-style 定义**（无原型参数
表）。C23 删除了该语法。实测：

```
gcc 15.2.0（默认 -std=gnu23）：
  ./triangle.c:11190:15: error: too many arguments to function 'readline'; expected 0, have 3
  （同样的错误在 findfield 等处共数十条）

同一份源码：
  -std=gnu89 / gnu99 / gnu11 / gnu17  → 全部编译通过
  -std=gnu23                          → 失败
```

OHOS worker 的 clang 15 默认就是 gnu17，本来能过；固定 `-std=gnu17` 是防止
将来编译器默认上浮（GCC 15 已经是 gnu23），属于防御性但必要的声明。

## 3. WSL 侧已完成的可验证证据（无 Harmony PC）

### 3.1 补丁 apply
```
$ patch -p1 --dry-run -i patches/0001-makefile-ohos.patch
patching file makefile          # 无 fuzz、无 offset
```

### 3.2 打补丁后在本机（x86_64 gcc 15，默认 gnu23）完整构建
```
$ make triangle trilibrary CC=gcc CFLAGS="-O2"
$ ls -l triangle triangle.o
  227016  triangle
  187584  triangle.o
```
> 在本机默认就是 gnu23 的环境下能编过，正说明 `-std=gnu17` 的固定生效了。

### 3.3 上游样例 CLI 冒烟（README 之外无测试，这是最接近的端到端验证）
```
$ ./triangle -pq A.poly
Statistics:
  Input vertices: 29 / Input segments: 29 / Input holes: 1
  Mesh vertices: 56 / Mesh triangles: 60 / Mesh edges: 116
  Mesh exterior boundary edges: 52
rc=0
产出：A.1.node  A.1.ele  A.1.poly
```

### 3.4 消费者 API 测试（test_package 的 C 程序）在本机实跑
```
$ gcc -std=gnu17 -I src -o test_triangle src/test_triangle.c libtriangle.a -lm
$ ./test_triangle
ok   unit square keeps its 4 input vertices
ok   unit square triangulates into exactly 2 triangles
ok   triangles are linear (3 corners)
ok   every triangle corner index is within the point list
ok   the two triangles together cover the unit square (area == 1)
ok   no vertex was added or removed
all triangle consumer checks passed      rc=0
```

### 3.5 CLI 冒烟（test() 里那条）在本机实跑
```
写 test_square.poly（4 顶点 4 段的 PSLG）
$ ./triangle -pzQ test_square.poly
rc=0
产出：test_square.1.node  test_square.1.ele  test_square.1.poly
```

## 4. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **0** | makefile 目标清单只有 `all` / `trilibrary` / `triangle` / `tricall` / `triangle.o` / `showme` / `distclean`，无 `check`/`test` |
| `upstream_test_files` | **0** | zip 内无测试源文件；`tricall.c` 是示例驱动，需人工输入 |
| `upstream_case_total` | **0** | 上游不提供用例。**是确认的 0，不是 UNKNOWN**——依据是 makefile 目标清单 + 7 文件清单，可逐条核对 |

因此本 PR **不申报上游测试通过率**。替代验证：
1. `build()` 内跑上游自带样例 `A.poly`（要求退出码 0 且产出 3 个文件）；
2. test_package 的 API 消费者测试（6 项断言）；
3. test_package 自建 PSLG 的 CLI 冒烟。

三者都如实标注为「我们补的验证」，不计入上游用例统计。

## 5. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：确认去掉 `-DLINUX` 后
   `<fpu_control.h>` 相关编译错误消失
2. `make trilibrary` → `ar rcs libtriangle.a triangle.o`（worker 上 `ar` /
   `llvm-ar` 哪个可用——配方已做双名回退）
3. `build()` 内 `./triangle -pq A.poly` 真机执行（**原生执行**，验证精确
   算术谓词在 aarch64 上行为正确）
4. test_package：CMakeDeps `find_package(triangle)` → `triangle::triangle`
   的 target 名与 `-lm` 传递是否正常
5. `triangle -pzQ test_square.poly` 在真机产出 3 个输出文件
6. 软件级 commands.json 是否被 CI L0k 接受

## 6. 补充：WSL 侧完整 `conan create` 实测（本机原生 Linux profile）

在独立 `CONAN_HOME`（不污染农场缓存）上真跑了一次完整 `conan create`，
暴露出三个只有在真实 conan 流程里才会出现的问题，均已修复：

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | `make` 报 `No targets specified and no makefile found` | `Autotools.make()` 把 make 跑在 **build 目录**（`basic_layout` 下 ≠ 源码目录），上游 makefile 在源码目录 | 改为 `self.run("make -j1 <target>", cwd=self.source_folder)`（仓库 lz4/ncompress 同款写法）；`AutotoolsToolchain` 生成的 CC/CFLAGS/CPPFLAGS/LDFLAGS 对 `self.run` 同样生效（已用探针配方实测确认） |
| 2 | `ERROR: Package type is 'library', but no 'shared' option declared` | Conan 2 要求 `library` 类型必须声明 `shared` 选项 | 改 `package_type = "static-library"`。Triangle 上游根本没有 shared 构建（无 libtool、无 -fPIC），声明一个做不到的 `shared` 选项是不诚实的；仓库内 `static-library` 有 139 处先例（含 farm main） |
| 3 | `test()` 里 `triangle -pzQ ...` 报 Error 127 | 生成的 `conanrun` 运行环境对**库包**不含 PATH（只有 `application` 类型的依赖才会把 bin/ 注入构建环境）。上游 lz4/cauchy 的 test_package 只跑自己编译的测试程序，所以没暴露这一点 | test_package 改为按**包内绝对路径**调用 CLI：`self.dependencies[ref].package_folder` + `cpp_info.bindirs[0]` |

最终本机 `conan create` 结果：

```
triangle/1.6: RUN: make -j1 triangle
triangle/1.6: RUN: make -j1 trilibrary
triangle/1.6: RUN: ar rcs ".../libtriangle.a" triangle.o
triangle/1.6: RUN: ./triangle -pq A.poly              # 上游样例冒烟
triangle/1.6: Package created
test package: RUN: ./test_triangle
ok × 6  (all triangle consumer checks passed)
test package: RUN: ".../p/bin/triangle" -pzQ test_square.poly
→ 无异常，test_package 通过
```

> 教训：`Autotools.make()` 的 cwd 语义与 `test()` 里 PATH 的可见性，
> 都属于"看起来能过、真跑才炸"的类别——纯静态检查（py_compile + 补丁
> dry-run）抓不到。凡是有条件，都应在 WSL 上真跑一次 `conan create`。
