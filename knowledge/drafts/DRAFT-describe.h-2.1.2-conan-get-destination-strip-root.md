# DRAFT — Conan get(destination=...) 不剥离归档根目录：多源码配方 source() 下载到子目录的正确写法

> **Contributor**: pc5-2 | **Status**: DRAFT | **Updated**: 2026-09-19
> **Severity**: medium | **Category**: conan / packaging / source / multi-source
> **Source**: describe.h 2.1.2 R01 conan-verify G2 首次失败 + 修复复验（真实日志）
> **Audience**: 在 source() 中下载多个官方依赖包并解压到子目录（deps 补拉 / vendored 依赖）的 Conan 配方

## 问题签名

```text
conan create ... --build=missing
ERROR: <pkg>/<ver>: Error in source() method
fatal error: 'xxx/xxx.h' file not found        # 编译阶段依赖头缺失
# 或
NotADirectoryError / 文件层级错误              # 解压路径与预期不符
```

配方写法的典型错误：
```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)          # 主源码 OK
    for dep_dir, info in self.conan_data["deps"].items():
        get(self, url=info["url"], sha256=info["sha256"],
            destination=os.path.join(self.source_folder, "deps", dep_dir))  # ❌ 根目录未剥离
```
解压结果：`deps/<dep>/<repo>-<ver>/xxx.h`（多了一层 `<repo>-<ver>` 目录），
而 Makefile/头文件 include 期望 `deps/<dep>/xxx.h` → 头文件找不到。

## 根因

Conan `tools.files.get()` 的 `destination` 参数**只指定解压目标目录**，与 `strip_root`
是两条独立路径：`destination` 生效时归档根目录**不会被剥离**（解压时保留 `<repo>-<ver>/`
这一层）。调用方期望 dest 下直接是 strip 后的文件，需要用 `get(..., strip_root=True)`
解到 source 根（此时 strip_root 生效），再 `copy()` 到目标子目录。

## 方案（配方侧修复，可跨库复用）

```python
from conan.tools.files import get, copy

def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)
    # 依赖 tarball 解到 source 根（strip_root 生效），再 copy 进 deps/<dep>/
    for dep_dir, info in self.conan_data.get("deps", {}).items():
        get(self, url=info["url"], sha256=info["sha256"], strip_root=True)
    dep_files = {
        "assertion-macros": ["assertion-macros.h"],
        "console-colors": ["console-colors.h", "console-colors.c"],
    }
    for dep_dir, files in dep_files.items():
        for f in files:
            copy(self, f, self.source_folder,
                 os.path.join(self.source_folder, "deps", dep_dir))
```

## 验证

describe.h 2.1.2：修复后 conan-verify G2 PASS；conan create + test_package 执行 PASS；
W3 build_and_test.sh PASS（Pass rate 100%）。修复前 G2 FAIL（头文件找不到）。

## 适用边界 / 反例

- 适用：source() 中下载多个官方依赖包到子目录（deps 补拉、vendored 依赖、多源码包）。
- 反例：单源码包且不需要子目录解压的配方不受影响；`destination` 用于**整体替换解压位置**
  且不关心层级时（如 E250 Go SDK 下载）仍可用 destination + strip_root=False。

## 查重（四范围）

- 正式 E483（URL 无扩展名 BadZipFile）：显式 filename 解决编码器推断，不覆盖 destination 语义。
- 正式 E392（raw makefile 三陷阱：显式 filename / compiler_executables dict / make cwd）：不覆盖。
- 正式 E466（sdist strip-components 提升）：init_build 目录提升问题，不覆盖 destination。
- 正式 E378（source probe 隔离副本）：conan source 探测污染，不覆盖。
- 图谱/drafts：无 destination+strip_root 交互命中 → **UNMATCHED**，新建草稿。
