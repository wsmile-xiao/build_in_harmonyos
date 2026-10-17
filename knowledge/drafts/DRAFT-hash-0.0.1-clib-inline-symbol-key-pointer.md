# DRAFT-hash-0.0.1-clib-inline-symbol-key-pointer

> 草稿：clib 风格单文件 C 库（上游 Makefile 仅 test/clean 目标、无库构建/安装
> 规则）在 OHOS 上的配方直接编译模式，以及 C99 `inline` 定义函数的外部 T
> 符号实证与 khash 键指针存储语义。触发自 hash 0.0.1 适配（2026-09-18）。

## 问题描述

clibs 生态（github.com/clibs/*）与 khash 系 C 库常以单文件 + 极简 Makefile
发布，Makefile 仅有 `test`/`clean` 目标（如 clibs/hash 0.0.1 的
`Makefile` 只有 `test: hash.c` 一条构建规则），**没有库构建（.a/.so）与
install 目标**。直接套用 autotools/cmake 流程不可行；且 hash.c 用 C99
`inline void hash_set(...)` 定义公开 API，库化后符号是否对外可见、消费方
能否链接需实测验证，不能凭"自测可跑"推断。

典型错误签名（error_signature，与 .kv 配对字段一致）：
- `FAIL: size after insert = 40339, expected 100000` —— 复用栈缓冲键导致
  khash 全部键别名同一地址、`hash_size` 失真（本条实测首错）；
- `make: *** No rule to make target` / `make: *** No targets specified and
  no makefile found` —— 上游 Makefile 仅 test 目标、无库构建/install 规则；
- `undefined reference to 'hash_set'` / `undefined symbol: hash_set` ——
  C99 inline 定义未外化为 T 符号时消费方链接失败（需 llvm-nm 实测确认）。

此外，OHOS 专项压力测试暴露第二个真实陷阱：clibs/hash 的
`KHASH_MAP_INIT_STR` 存储的是**键指针**而非键拷贝，复用栈缓冲区做键会使
表中全部键别名同一地址，10 万次插入后 `hash_size` 仅 40339（本应 100000）。

## 根因

1. clib 生态包不提供库构建目标：配方必须自行合成
   `clang -std=c99 -fPIC -O2 -c hash.c` + `ar rcs libhash.a` + 打包头文件。
2. C99 语义下，头文件内普通原型声明 + 源文件 `inline` 定义 → 经 `-std=c99`
   编译为**外部定义**（T 符号），消费方可正常链接；但必须实测确认
   （`llvm-nm hash.o` 见 `hash_set/hash_get/hash_has/hash_del` 全部 T）。
3. khash（Attractive Chaos）的 str 键哈希表按 `(const char*)` 指针 + strcmp
   判等，**表内保存键指针本体**；键生命周期须由调用方维持，复用临时缓冲即
   造成别名去重、size 失真。

## 修复（验证通过）

A. 配方直编三要素（clib 无库目标包）：

```python
def build(self):
    compiler_exe = self.conf.get("tools.build:compiler_executables") or {}
    cc = compiler_exe.get("c", "clang")
    ar = compiler_exe.get("ar", "ar")
    src = self.source_folder
    self.run(f"{cc} -std=c99 -fPIC -O2 -c hash.c -o hash.o", cwd=src)
    self.run(f"{ar} rcs libhash.a hash.o", cwd=src)

def package(self):
    copy(self, "hash.h", src=src, dst=<include>/)
    copy(self, "khash.h", src=src, dst=<include>/)
    copy(self, "libhash.a", src=src, dst=<lib>/)
```

B. 消费方/测试键必须用稳定内存（strdup），结束前 free；绝不复用栈缓冲。

## 验证证据（hash 0.0.1 实测）

- `llvm-nm hash.o`：`hash_del/hash_get/hash_has/hash_set` 均为 `T` 符号
  （编译 `clang -std=c99 -fPIC -O2`），静态链接无缺符号。
- conan create test_package：`test_hash_consumer: OK (public API exercised)`
  —— 真实消费者链接 libhash.a + 公开头文件编译运行成功。
- OHOS 专项测试（ohos_test.c，10 万键）：
  - 修复前（栈缓冲键）：`FAIL: size after insert = 40339, expected 100000`
  - 修复后（strdup 键）：`hash_ohos_test: OK (100000 entries, 100000 iterated,
    del/clear/lifecycle passed)`，exit=0。
- 上游自测 9/9（`make test` exit=0）。

## 适用边界

- 适用：clibs/khash 系**无库构建目标**的单文件 C 库（Makefile 仅 test 类
  目标）；C99 `inline` + 头文件原型模式的单源库；以稳定指针为键的哈希库
  消费方/测试编写。
- 反例/不适用：普通 raw-makefile（有 all/install 目标，含 configure 产物）
  走 E392 raw-makefile-conan-recipe-pattern；头文件声明 `static inline`
  的库无外部符号问题；键已由库内部 strdup 拷贝的哈希实现不涉及键生命周期。

## 关系

- similar_to: E392（raw-makefile-conan-recipe-pattern，部分重叠）；
  DRAFT-lbfgs-1.10-single-source-direct-compile-triage
- caused_by: clib 生态发布形态（无 dist 构建目标）
- prerequisite_of: 消费者用例编写规范（键内存语义）

## 验证命令

```
llvm-nm <build>/hash.o | grep ' T hash_'
conan create archives/h/hash/0.0.1 --build=missing   # test_package 两用例全过
```