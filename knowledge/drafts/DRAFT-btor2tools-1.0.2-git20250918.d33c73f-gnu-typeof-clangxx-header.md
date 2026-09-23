# DRAFT — GNU typeof 宏被 C++ 编译单元引入导致 clang++ undeclared identifier

- **草稿 ID**: DRAFT-btor2tools-1.0.2-git20250918.d33c73f-gnu-typeof-clangxx-header
- **触发事件**: btor2tools 1.0.2-git20250918.d33c73f HarmonyOS PC 适配（archives/b/btor2tools/1.0.2-git20250918.d33c73f）
- **Gate**: conan-verify G2（btorsim*.cpp 编译阶段）

## 问题

上游 C 头文件 `src/util/btor2mem.h` 用 GNU 扩展写内存分配宏：

```c
#define BTOR2_NEWN(ptr, nelems) \
  ((ptr) = (typeof(ptr)) btorsim_malloc ((nelems) * sizeof *(ptr)))
```

C 模式下 clang/gcc 均接受 `typeof`。但该头被 C++ 编译单元（`btorsim*.cpp`）经
`util/btor2stack.h` → `btor2mem.h` 间接引入时，clang++ 不识别 GNU `typeof`（提示
`did you mean 'typeid'?`），报 `use of undeclared identifier 'typeof'`，编译直接失败。

## 根因

- `typeof` 是 GNU C 扩展，clang++/严格模式 C++ 下未定义
- 头文件是 C 库的公共内存宏，被 C++ 翻译单元间接包含（非本库有意为之）
- g++ 兼容 GNU 扩展可能放行，clang++ 严格拒绝 → 跨编译器行为不一致，CI（clang）必挂

## 方案

把宏定义中的 `typeof(expr)` 全部改写为 `__typeof__(expr)`：

```c
#define BTOR2_NEWN(ptr, nelems) \
  ((ptr) = (__typeof__(ptr)) btorsim_malloc ((nelems) * sizeof *(ptr)))
```

`__typeof__` 是 GCC/Clang 双兼容的关键字拼写，C 与 C++ 编译单元均可用，零语义变化。
用 `refresh-patch --auto` 落成 `patches/*.patch` 并在 `conandata.yml` patches 列表登记。

## 验证

- 修复后 `make` 全量编译通过（btorsim/catbtor/btorsplit + libbtor2parser）
- `conan-verify` G2 全绿（干净源码 + test_package）
- 上游回归 `test/runtests.sh` 67/67 通过

## 适用边界

- 头文件含 GNU `typeof`（或 `__auto_type` 等 GCC 扩展）宏的 C 库
- 该头被 C++ 翻译单元间接包含（parser/工具库的公共 util 头常见）
- clang/clang++ 工具链（OHOS 默认），g++ 场景可能未暴露

## 反例与限制

- **禁止**把 .cpp 编译单元改成 C 编译、加 `-fpermissive` 掩盖、删掉使用宏的 C++ 文件
- `__typeof__` 在 C23 已是标准关键字，向后兼容性良好；老编译器（C89/C99）也支持作为扩展
- 若宏在头文件中定义且该头被大量 C++ 引用，替换范围就是宏定义处，改动面小

## 查重差异

- E530 涉及 `__typeof__` 强类型活重定位但主题是 X11 无 X server 消费者测试（ABI 校验），
  与本条目的"typeof 在 C++ TU 未声明"错误签名、根因、方案均不同
- E500（MAX_INPUT undeclared）是 musl libc 宏缺失，同属"undeclared identifier"家族但
  根因（缺宏定义 vs GNU 扩展不被 C++ 识别）不同
- 知识库无既有条目覆盖"GNU typeof 宏被 C++ 包含"这一可移植性模式 → 新增草稿

## 字段一致性

- `.kv` 与 `.md` 同 stem，`doc_file` 指向配对 md，id/error_signature/root_cause/rec_approach 均已填写。
