# DRAFT-driver-hardcoded-tmp-on-harmonyos — 驱动硬编码 `/tmp` 导致「除 `-E` 外编译全失败」

> 配对的 kv：`knowledge/drafts/DRAFT-driver-hardcoded-tmp-on-harmonyos.kv`
> 来源：pcc（Portable C Compiler）1.2.0-devel-20220331 适配，PR !14348
> 分类：platform / tmpdir

## 错误特征

```
error: /tmp/ctm.XXXXXX: Read-only file system
```

## 根因分析

pcc 驱动 `cc/cc/cc.c` 的 `gettmp()` 把临时文件模板**硬编码**为 `/tmp/ctm.XXXXXX`。
鸿蒙的 `/tmp` 是 **erofs 只读挂载**，于是：

- `-E`（仅预处理，不落中间文件）→ 能过；
- `-S` / `-c` / `-o` 等**每一次真正编译** → 创建中间文件时失败。

## 关键线索：上游自己已有正确约定

`cc/driver/driver.c`（上游**未启用**的那份）里就是：

```c
template = getenv("TMPDIR");
```

因此修法不是「新造机制」，而是**把在用的驱动对齐到上游既有约定** ——
这能显著降低评审对「自造机制」的质疑。

## 推荐方案

**方法**: `honour-tmpdir-with-fallback`

让 `gettmp()` 优先读 `$TMPDIR`，取不到再回退 `/tmp`（补丁 0002）：

```c
char *
gettmp(void)
{
	const char *dir = getenv("TMPDIR");
	char *sfn;
	int fd = -1;

	if (dir == NULL || *dir == '\0')
		dir = "/tmp";
	sfn = xmalloc(strlen(dir) + sizeof("/ctm.XXXXXX"));
	snprintf(sfn, strlen(dir) + sizeof("/ctm.XXXXXX"), "%s/ctm.XXXXXX", dir);
	...
}
```

实测（补丁后，`TMPDIR` 指向可写目录）：

```sh
pcc -S -o out.s in.c     # rc=0，产出 992 字节汇编
```

## 陷阱

**配方侧注入 `TMPDIR` 对硬编码 `/tmp` 的驱动是空操作。**

| 驱动形态 | 配方侧注入 `TMPDIR` | 结论 |
|---|---|---|
| `getenv("TMPDIR")` | 有效 | 无需打补丁 |
| 硬编码 `/tmp/...XXXXXX` | **无效** | **必须打补丁** |

## 与现有知识库的关系

本条是 **E002**（`set-env-var`：把 `TMPDIR` 指到可写目录）在**驱动硬编码场景**下的具体化：
E002 是通用手段；本条界定其**适用边界**（对硬编码 `/tmp` 的驱动无效），
并给出「引用上游自身未启用代码的既有约定」这一论证套路。两者互补，故各立一条。
