# DRAFT-kevlar-2.0.1-gcc-wrapper-for-makefile：raw Makefile 链接步骤硬编码 `gcc` 时，generate() 生成 gcc→clang wrapper 注入 PATH

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-21
> Source: kevlar 2.0.1 适配（本 PR）
> 对应：`knowledge/drafts/DRAFT-kevlar-2.0.1-gcc-wrapper-for-makefile.kv`

## 现象

`make all` 中 kevlar / rst2html 目标正常，唯独 `md2html` 目标失败：

```console
gcc ./recipes/md2html.o ... -lm -o ./bin/md2html
make: gcc: No such file or directory
make: *** [makefile:48: md2html] Error 127
```

构建环境只有 clang，没有 gcc。

## 根因

kevlar 是 raw makefile（无 configure/cmake/meson）工程，makefile 里大多数目标
通过 `$(CC)` 编译链接（`make CC=clang` 可覆盖），但 `md2html` 目标的链接命令
**硬编码了 `gcc`**：

```makefile
md2html: ./recipes/md2html.o ./src/kevlar_md_to_html.o ...
	gcc ./recipes/md2html.o ... -lm -o ./bin/md2html   # ← 硬编码 gcc
```

`make CC=clang` 不影响硬编码出现的 `gcc`，CI/本机无 gcc 时该目标必然失败。

## 方案

conanfile 的 `generate()` 在 **build_folder 私有 bin/ 目录**生成 `gcc`→clang
wrapper 脚本并 chmod +x；`build()` 执行 make 时把该目录前缀注入 PATH：

```python
def generate(self):
    # 编译器 id 从 Conan 工具链 conf 解析（R33：不依赖 shell 环境变量）
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = compilers.get("c") or shutil.which("clang") or "cc"
    wrap_dir = os.path.join(self.build_folder, "bin")
    os.makedirs(wrap_dir, exist_ok=True)
    wrapper = os.path.join(wrap_dir, "gcc")
    with open(wrapper, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nexec %s \"$@\"\n" % cc)
    os.chmod(wrapper, ...)
    self._cc = cc

def build(self):
    ...
    self.run("PATH=\"%s:$PATH\" make CC=%s CFLAGS='...' all" % (wrap_dir, self._cc),
             cwd=self.source_folder)
```

要点：编译器 id 从 Conan 工具链 conf（`tools.build:compiler_executables` 的 "c" 键）解析
（R33，不依赖 shell 未定义变量；仅 conf 为空时回退 which("clang")）；注入仅限
build_folder 私有 prefix（R49，不污染共享 /usr/local 或系统目录）；上游 makefile
零改动，保持干净。

已落地：`archives/k/kevlar/2.0.1/conanfile.py`（generate() + build()）。

## 验证

- 修复前：`make all` 在 md2html 链接步骤失败（gcc: No such file or directory）
- 修复后：三个 CLI（kevlar/rst2html/md2html）全部链接成功
- `conan-verify` G2 conan create 干净构建 PASS（G0-G4 + L2/L4/L5）

## 适用边界

- **适用**：raw makefile（非 autotools/cmake/meson）中个别目标硬编码了环境中
  不存在的编译器二进制（如 `gcc`），而 Conan 工具链提供等价编译器（clang）的配方
- **反例/边界**：autotools/cmake/meson 生成的 Makefile 不硬编码编译器（由
  toolchain 注入 CC），无需此方案；若 makefile 硬编码了上游专用工具（非编译器
  等价物），wrapper 不适用，应改 patch 上游或报依赖缺失
- **禁止**：把 wrapper 写入 /usr/local、/usr/bin 等共享路径（R49/PF6 拦截）；
  用 `os.access(X_OK)` 探测 work 目录（HMDFS 下恒 False）

## 查重差异（七轴）

| 轴 | 结论 |
|----|------|
| exact_duplicate | false |
| causal_duplicate | false（E392 是 get/compiler_executables/cwd 三陷阱） |
| trigger_overlap | true（同类 raw makefile 配方品类，E392） |
| solution_overlap | 无（E392 无 gcc wrapper 方案） |
| combination_novelty | true（generate wrapper + PATH 注入 + makefile 硬编码 gcc 新组合） |
| boundary_novelty | true（链接步骤硬编码编译器 = E392 未覆盖边界） |
| test_migration_novelty | true（conan-verify G2 复跑，可跨库迁移） |

关系：`similar_to E392`、`caused_by` makefile 硬编码编译器 + CI 无 gcc、`conflicts_with` 无。
