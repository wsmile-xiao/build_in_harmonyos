# DRAFT-bison-ohos-datadir-m4sugar — bison/3.8.2 在 OHOS 上找不到 m4sugar.m4

> **Contributor**: codex | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: blocking (3) | **Category**: ohos / bison / tool_requires / packaging
> **Audience**: 所有在 OHOS 上用 `tool_requires("bison/3.8.2")` 生成 parser 的 Conan 配方

## 触发（trigger）

- 上游 tag 归档不含 Bison 生成物（`parser.cpp`/`parser.hpp`），配方 `build()` 内直接调用 bison 生成。
- bison 报错：`bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory`。

## 机制（root cause）

- bison/3.8.2 的 OHOS HNP 包编译时 `datadir` 被配成绝对 `/share`，运行时按 `${pkgdatadir}/m4sugar/m4sugar.m4` 定位自身 m4 宏 → 得到根目录下不存在的 `/share/bison/m4sugar/m4sugar.m4`。
- 实际宏文件在 bison 包内 `<pkg>/share/bison/m4sugar/m4sugar.m4`（`find "$CONAN_HOME/p" -name m4sugar.m4` 可定位）。
- 只要带 `-D`/`%define` 参数的 `.y` 文件都会触发 m4 处理，因此必然命中。

## 修复（rec）

```python
# build() 内、调用 bison 前
bison_pkg = self.dependencies.build["bison"].package_folder
bison_datadir = os.path.join(bison_pkg, "share", "bison")
self.run(f'BISON_PKGDATADIR="{bison_datadir}" bison {flags} -d -o src/asm/parser.cpp src/asm/parser.y')
```

修复后 bison 正确生成 `parser.cpp` + `parser.hpp` + `stack.hh`（rgbds 1.0.1 真机 shadow CI 实测 exit 0）。

## 注意

- 不要误判为「缺 m4 工具」—— bison 自带 m4sugar.m4，只是 datadir 指错位置；重装 bison 无效。
- 生成输出目标必须在可写目录（build 目录），不要落到 `/tmp`（OHOS `/tmp` 只读，见 E002）。

## 查重（dedup）

- `grep -rl "m4sugar\|BISON_PKGDATADIR\|bison.*datadir" knowledge/` → **0 命中**。
- 相近条目：E109（fortran/gfortran 缺失，无关）、DRAFT-ohos-missing-awk-variant-supply（awk 变体 bison 生成物，触发库不同，无 datadir 修复）。

## Source

- Package: `archives/r/rgbds/1.0.1`（conanfile.py build()，bison 生成 parser 阶段）
- 真机验证：rgbds/1.0.1 shadow CI，job `rgbds-1.0.1-shadow-20260920-144737`，L0/L1/L4/L5 pass
