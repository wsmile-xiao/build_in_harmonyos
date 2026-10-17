# DRAFT-build-dir-path-with-space-make-target-split — 含空格构建路径导致 make 拆词

## 可复现症状与稳定错误签名

```
Makefile:96: warning: overriding recipe for target '/storage/Users/.../build_in_harmonyos-main'
Makefile:95: warning: ignoring old recipe for target '/storage/Users/.../build_in_harmonyos-main'
make[43]: /bin/sh: Resource temporarily unavailable
make[44]: *** [Makefile:79: /storage/.../build_in_harmonyos-main] Error 127
```
签名正则：`overriding recipe for target .*build_in_harmonyos` 或
`Resource temporarily unavailable` 出现在 make 递归日志中。

> ⚠️ 坑点：报错文本里**完全不会提到"空格"**，反而像是某个 target 定义冲突或
> 资源不足，极易被误判为"库本身/依赖有问题"。

## 根因与最小复现

- autotools 生成的 `Makefile` 中 `abs_builddir` 是**未加引号**的绝对路径：
  ```make
  abs_builddir = /storage/.../build_in_harmonyos-main 小号专用工作室/.tmp/inn-2.7.4
  LIBINN       = $(abs_builddir)/lib/libinn.a
  $(LIBINN):   ; (cd ../lib ; $(MAKE))
  ```
- make 的目标/依赖列表按空白分词。路径里的空格把 `$(abs_builddir)` 切成两段，
  前半段被当成**伪目标**，于是 make 去"构建" `/storage/.../build_in_harmonyos-main`，
  并在重复定义时打印 `overriding recipe for target ...`。
- 递归子 make 随之爆炸，进程/资源耗尽 → `Resource temporarily unavailable`，
  最终 `Error 127` / `Error 2`。

最小确认：
```bash
pwd | grep -q ' ' && echo 'BUILD PATH CONTAINS SPACE'
make -n 2>&1 | grep -c 'overriding recipe for target'   # >0 即命中
```

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 在含空格目录内直接 `configure && make` | 失败（本条）；日志数万行、反复"构建"父目录 |
| 调低并发 `make -j2` | 仍失败 —— 只是把资源耗尽推迟，分词问题未解 |
| 迁到无空格路径 `~/builds/inn-2.7.4.work` | **通过，采用**（`make -j2` exit 0，0 error，275 个 .o） |

## 最终方案、输入输出与真实验证

- **方案**：构建目录必须不含空格。本仓库 `init-build` 的默认落点是
  `~/builds/<name>-<ver>.work`，天然满足；手工构建时同样应迁到此类路径。
- **验证**：inn2/2.7.4 迁至 `~/builds/inn-2.7.4.work` 后
  `configure` exit 0、`make -j2` exit 0、产物为真 aarch64 ELF
  （`innd/.libs/innd` 4.5 MB 等）；而同一源码在含空格目录下必失败。

## 注意事项

1. **不要把这类报错当成库本身的问题去改依赖或源码**——方向错会白费大量时间
   （本例曾把父目录当 target 反复构建，产生数万行日志）。
2. 本条的适用面是**通用 make 语义**，与具体三方库无关；凡是构建路径含空格
   （例如桌面上的中文命名工作目录）都可能命中。
3. 相关但不同：`E392` 是 make/no-makefile（构建目录选择错误，报
   `No targets specified and no makefile found`）；本条是路径**分词**，
   两者都会表现为"make 报错但根因在构建目录布局"，排查时可一并对照。
