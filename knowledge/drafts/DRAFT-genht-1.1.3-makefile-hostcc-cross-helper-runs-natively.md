# 上游 Makefile `HOSTCC = $(CC)`：OHOS 交叉 ELF 可在 worker 直接执行，无需替换宿主工具

**条目**: `DRAFT-genht-1.1.3-makefile-hostcc-cross-helper-runs-natively`
**来源**: genht 1.1.3 适配（`src/Makefile` 的 `version.h` / `ver_edit`）
**状态**: DRAFT

## 现象

`src/Makefile`：

```make
HOSTCC = $(CC)

version.h: version.h.in ver_edit
	./ver_edit $(VER_MAJOR) $(VER_MINOR) $(VER_PATCH) < version.h.in > version.h

ver_edit: ver_edit.c
	$(HOSTCC) -o $@ $(CFLAGS) ver_edit.c
```

交叉编译时的直觉是「HOSTCC 必须用宿主编译器，否则 `./ver_edit` 跑不起来」，
于是会加补丁或绕开 version.h 生成。本机实测 `cc`/`c++` 也不存在。

## 结论（本环境实测）

- OHOS SDK clang 15 产出的 `aarch64-unknown-linux-ohos` ELF **可以在 worker 上直接执行**
  （test_package 的 `self.run(bin)` 走的就是这条路径）。
- 因此 `make CC=<ohos-clang> HOSTCC=<ohos-clang>` 即可：`ver_edit` 交叉编译后正常运行，
  生成正确的 `version.h`，**零补丁**。

## 更重要的推论

既然交叉 ELF 可执行，**上游自带的自测程序通常也能在 `build()` 里真跑**。
优先把上游回归测试集成进配方 `build()`（测试失败让 make 返回非 0 → 构建失败），
而不是在 PR 里声明「交叉编译无法执行」并填 `[0/N]`：

```python
self.run(f"make -C {src} -j1 test {vars}")   # diff 不一致 → 非 0 → conan create 失败
```

genht 实测：`make test` → `*** QC pass ***`，上游 1/1 通过。

## 边界

- 本机 **无宿主编译器**（`init-build` 报 `cc: 未找到`），真正需要宿主 cc 的项目
  不能照搬本条结论。
- 上游自测程序若链接了宿主机专属库（如宿主 ncurses/GL），仍需单独评估。
