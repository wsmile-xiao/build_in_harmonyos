# 草稿知识条目 E627 — autotools 库在 Conan 下选 static/shared 前必须实测的两件事

- 软件：libgig 4.5.2（C++ / autotools + libtool；1 个库 + 14 个 CLI 工具）
- 平台：HarmonyOS PC aarch64（clang 15.0.4，libc++，`aarch64-linux-ohos`）
- 状态：UNMATCHED（待人工/AI 复核后提升为 E 条目）
- 关联：E503（CLI 缺 GNU 长选项 → L2 smoke 失败）、E007（config.guess/toolchain）、E011（configure umask）

---

## 1. 一句话结论

autotools + libtool 的包在 Conan 下**不能凭直觉选 static/shared**：

| 选择 | 得到的面 | 实测症状 |
|---|---|---|
| `--enable-shared` | libtool 按安装期前缀写 **绝对 RUNPATH** | `RUNPATH=//lib/libgig`（不存在路径）→ 裸环境 `Error loading shared library libgig.so.13` |
| `--enable-static --disable-shared` | 工具自包含（无 DT_NEEDED/RUNPATH） | 但**静态链接激活上游潜伏的静态初始化顺序缺陷** → 测试在 `main()` 之前 SIGSEGV |

两条路都必须**先实测**再定案，且实测必须在**裸环境**（清掉 `LD_LIBRARY_PATH`）下做。

## 2. 证据一：libtool 的绝对 RUNPATH（shared 变体）

```
$ ./configure --prefix=/ --host=aarch64-linux-ohos --build=aarch64-linux-ohos \
      --enable-shared --disable-static && make -j2 && make install DESTDIR=$PWD/stage
$ llvm-readelf -d stage/bin/gigdump | grep RUNPATH
 0x000000000000001d (RUNPATH)  Library runpath: [//lib/libgig]     # 14/14 个工具全同
$ (cd stage/bin && env -u LD_LIBRARY_PATH ./gigdump -v)
Error loading shared library libgig.so.13: (needed by ./gigdump)   # rc≠0
```

根因：上游 `src/Makefile.am` 用 `pkglib_LTLIBRARIES = libgig.la libakai.la`
（`pkglibdir = $(libdir)/$(PACKAGE)`），`--prefix=/` 下拼出 `//lib/libgig`。
libtool 把它作为安装期 rpath 写进 14 个工具。

**同一份日志里 `make check` 4 套上游测试全绿**（90/104/84/128）——
测试链接的是 `.libs/` 里的 `.so`（构建树内），没有暴露安装后的 RUNPATH。

与 libfstfar 的 W4 P1（`RUNPATH=//lib`，`farinfo --help` rc=127）是**同一族缺陷的第二个独立实例**。

## 3. 证据二：静态链接激活静态初始化顺序缺陷（static 变体）

```
$ ./configure ... --enable-static --disable-shared && make -j2 && make check
...
********** RUNNING SERIALIZATION TESTS **********
./serializationtests
make[2]: *** [Makefile:669: check] Segmentation fault (core dumped)
```

- `helpertests` OK(90) / `rifftests` OK(84) / `gigtests` OK(128) 全过，**只有 `serializationtests` 崩**。
- rc=139，且**输出 0 字节**（连 `main()` 第一行 `printf("\n")` 都没有）⇒ 崩在 `main()` 之前。
- 用 gdb 不可行（`ptrace: Permission denied`），改用「在 main 第一行加 `write(2,"START",5)`」证明：

```
$ ./serdbg2 ; echo rc=$?
rc=139            # START 未打印 ⇒ 崩在 main 之前（动态初始化阶段）
```

- 定位到 `SerializationTests.cpp` 的**全局对象**：
  ```cpp
  static Serialization::DataType::NativeDataTypeRegistry<PolyB> _registerPolyB;
  static Serialization::DataType::NativeDataTypeRegistry<PolyC> _registerPolyC;
  static Serialization::DataType::NativeDataTypeRegistry<VirtPolyB> _registerVirtPolyB;
  ```
  其构造器调用 `DataType::registerNativeDataType<T>()`，而该函数访问库内的
  **`static std::map<String,NativeType> DataType::m_nativeTypes`**（定义在 `Serialization.cpp`）。
  静态链接时链接顺序是「消费者对象 → 静态库成员」，消费者的全局构造器先跑，
  访问到的 map 还是零初始化内存 → 解引用空指针 → SIGSEGV。

### 最小复现（决定性判据，~10 行）

```cpp
// t4.cpp
#include <unistd.h>
#include "Serialization.h"
struct MyT { int x; void serialize(Serialization::Archive* a) { (void)a; } };
static Serialization::DataType::NativeDataTypeRegistry<MyT> _registerMyT;
int main() { write(2, "T4-OK\n", 6); return 0; }
```

```
$ clang++ $CXXFLAGS t4.cpp libgig.a -o t4    && ./t4   ; echo $?   # 139  ← 消费者对象在前
$ clang++ $CXXFLAGS -c Serialization.cpp -o ser.o
$ clang++ $CXXFLAGS ser.o t4.cpp libgig.a -o t4b && ./t4b; echo $?  # 0  ← 库对象在前即不崩
```

**同一个二进制内容、只改对象顺序，rc 从 139 变 0** ⇒ 确诊静态初始化顺序缺陷，
而不是别的崩溃（也解释了为什么 upstream 从未发现：shared 构建下 `.so` 的初始化先于可执行文件）。

## 4. 处置（本包采用）

1. **库与工具全部静态**（`--enable-static --disable-shared`）：从结构上消除 libtool 绝对 RUNPATH 这一面，
   14 个工具自包含（无 `DT_NEEDED`、无 `RUNPATH`），裸环境直接可跑。
2. **修上游缺陷**：把 `Serialization.h` 的
   `static std::map<String,NativeType> m_nativeTypes;` 改为函数内 static 访问器
   （首次使用即构造，与链接顺序无关），并删掉 `Serialization.cpp` 里的类外定义。
   修复后 4 套上游测试全绿。
3. 交付面实测：`bin/` 14 个工具 + `lib/libgig/{libgig.a,libakai.a}` + `include/libgig/*.h`
   + `lib/pkgconfig/{gig,akai}.pc`；`test_package` 额外做**裸环境** `--version`/`--help` smoke。

## 5. 复现命令（设备可直接执行，产物落 `~/tmp/libgig-4.5.2/`）

见 `.kv` 的 `rec_command`；关键三步：

```sh
TASK_DIR=$HOME/tmp/libgig-4.5.2
# ① shared：看 RUNPATH
for f in $TASK_DIR/shared/stage/bin/*; do llvm-readelf -d "$f" | grep RUNPATH; done
# ② static：真跑上游测试
HOME=$TASK_DIR/test-home make check
# ③ 最小复现：对象顺序
clang++ $CXXFLAGS t4.cpp libgig.a -o t4 ; ./t4 ; echo $?      # 139
clang++ $CXXFLAGS ser.o t4.cpp libgig.a -o t4b ; ./t4b ; echo $?  # 0
```

## 6. 边界与反面判据

- **禁止**用 `conanrun`（`self.run(..., env="conanrun")`）或手工 `LD_LIBRARY_PATH` 跑 smoke：
  它会掩盖错误的 RUNPATH，门禁全绿而交付物在裸环境不可用（本包 + libfstfar 两次独立实测）。
- `conan-verify` 的 L2 会把 `cache/lib` 注入 `LD_LIBRARY_PATH`；本包库在 `lib/libgig/`
  （`pkglibdir`），该注入**不覆盖** `lib/libgig`，此时 14 个工具会走「loader 缺库 → SKIP」分支，
  **SKIP 不代表产物可用** —— 必须人工裸跑补测。
- 若改回 shared 路线，rpath 修正**只看目标那一行的 LDFLAGS**（不要整文件守卫），
  并核对 `lib/libgig` 是否在 `$ORIGIN` 相对位置内。
- 静态链接下必须**真跑上游测试**：编译通过不等于测试通过（本包 `make` 全绿、`make check` 才崩）。
