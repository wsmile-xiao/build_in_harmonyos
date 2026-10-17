# OHOS libc 不声明也不导出 reallocarray()：用溢出检查的本地实现替代

> Draft: `DRAFT-XFSPROGS-720-OHOS-LIBC-MISSING-REALLOCARRAY`
> Stem: `xfsprogs-7.2.0-ohos-libc-missing-reallocarray` — 与同名 `.kv` 配套
> 实例来源: xfsprogs 7.2.0 适配（补丁 `0009-mkfs-proto.c.patch`）
> 关联知识: E386/E490（同为 OHOS 构建环境/工具链差异大类）

## 基本信息

- **ID**: DRAFT-XFSPROGS-720-OHOS-LIBC-MISSING-REALLOCARRAY
- **严重度**: 2
- **类别**: libc, musl, ohos, portability, compat
- **触发工具**: clang|gcc|make|conan
- **阶段**: compilation（失败可延续到 linking）

## 使用说明（这份知识怎么用）

- **适用**：源码里出现 `reallocarray(` 调用，且目标是 OHOS/musl（含 OHOS SDK 自带 sysroot）。
- **不适用**：宿主机 glibc 构建（照常链接 libc 版本）；或目标 libc 已实现该符号（先用下面探针确认）。
- **判定顺序**：先跑声明探针 → 再跑符号探针 → 两者都缺才落到"本地实现"方案。

## 输入输出定义（替代实现）

- **输入**：`ptr`（可空旧块）、`nmemb` × `size`（乘法可能溢出）。
- **输出**：
  - 成功：返回新块指针（可 `free`，内容语义同 `realloc`）；
  - 乘法溢出：置 `errno = ENOMEM`，返回 `NULL`，原块不动；
  - 内存不足等：沿用 `realloc` 语义（返回 NULL、原块不动）。
- **语义对照**：与 glibc `reallocarray(3)` 一致；与 `realloc(ptr, nmemb*size)` 的差别仅在**溢出检查**。

## 错误特征（逐字实测）

```
mkfs/proto.c:1396:36: warning: call to undeclared function 'reallocarray';
                       ISO C99 and later do not support implicit function declarations
mkfs/proto.c:1396:20: error: incompatible integer to pointer conversion initializing
                       'struct hardlink *' with an expression of type 'int'
```

探针实测（OHOS clang 15.0.4）：

```
# 声明探针（含 _GNU_SOURCE）
$ clang -c r.c -o /dev/null
error: use of undeclared identifier 'reallocarray'

# 符号探针（手动 extern 后链接）
$ clang r2.c -o r2
ld.lld: error: undefined symbol: reallocarray
>>> referenced by r2.c
```

即：**头里没有、库里也没有**——不是"只缺声明"。

## 根因

`reallocarray()` 属 glibc/BSD 扩展（POSIX.1-2024 才收录）。OHOS 的 libc 副本两缺：

1. `<stdlib.h>` 不声明（`_GNU_SOURCE` 无效）；
2. libc 不导出符号（链接期 undefined symbol）。

上游在 C99+ 下调用未声明函数时：clang 报错，或按隐式声明把返回值当 `int` 用，
触发 `incompatible integer to pointer conversion`；补声明后又死在链接期。

## 影响范围

- 任何调用 `reallocarray()` 的项目在 OHOS/musl 上构建时；
- 同类"glibc 有、OHOS 可能无"的扩展函数可复用同一处置流程
  （`explicit_bzero`、`strchrnul`、旧 musl 的 `memfd_create` 等）——
  先用探针确认是"缺声明"还是"缺符号"，再决定本地实现或替代调用；
- 反面做法（须避免）：
  - 只补 `extern` 声明 → 链接期 undefined symbol；
  - `-Dreallocarray=realloc` → 丢溢出检查（安全语义变化）；
  - 空壳 stub → 违反 R8（禁止无实质逻辑）。

## 推荐方案

**方法**: `provide-overflow-checked-reallocarray-shim-at-source-level`

1. 全仓清点调用点：`grep -rn "reallocarray" --include=*.c --include=*.cpp --include=*.h .`
2. 在调用点所在模块（或项目级 compat 头）加入等价实现：

```c
static void *
xfs_reallocarray(void *ptr, size_t nmemb, size_t size)
{
	size_t bytes;

	if (__builtin_mul_overflow(nmemb, size, &bytes)) {
		errno = ENOMEM;
		return NULL;
	}
	return realloc(ptr, bytes);
}
```

3. 原地替换调用（`reallocarray(` → `xfs_reallocarray(`），保持错误处理路径不变
   （xfsprogs 的调用点原本就对 NULL 走 `fail(...)`）。
4. 命名带项目前缀，避免与未来 libc 声明冲突；若放公共 compat 头，注释写明出处。

## 验证命令

```bash
# 声明探针（期望报 undeclared identifier）
printf '#define _GNU_SOURCE\n#include <stdlib.h>\nvoid *(*p)(void*,size_t,size_t)=reallocarray;\n' > r.c
clang -c r.c -o /dev/null

# 符号探针（期望 undefined symbol: reallocarray）
printf '#include <stdlib.h>\nextern void *reallocarray(void*,size_t,size_t);\nint main(){void*p=reallocarray(0,1,1);free(p);return 0;}\n' > r2.c
clang r2.c -o r2

# 替代实现落地后：目标文件应正常编译、链接、运行（xfsprogs 侧: make 全通过 + tools -V rc=0）
```

## 取证记录

- 包: xfsprogs 7.2.0（`archives/x/xfsprogs/7.2.0`，补丁 `0009-mkfs-proto.c.patch`）
- 报错原文: `reports/conan-create.log`（patch 后首次构建段）
- 修复后: `make` RC=0；W3 `.ci-result.json` exit_code=0（integrity b68060e8…）
