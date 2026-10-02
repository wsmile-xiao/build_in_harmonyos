# DRAFT: BSD make $(.TARGET) 语法的手写 Makefile 在 GNU make/Conan 下的两类规则失效与等价改写

- **草稿 ID**: E639（E639-draft-9C4A）
- **来源库**: udfclient 0.8.21（UDFtoolkit；OHOS PC aarch64，clang 15.0.4 / OHOS SDK 26.0.0.18，Conan 2.29.1）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **源 PR**: #13235（路径 A+B）

## 现象（真机实测）

上游 `Makefile.in` 面向 BSD make（Arch makedep 与 Debian 打包均按 bmake；本 PR 实测读取了 Debian
`debian/rules` 的 `--buildsystem=bmake`），链接规则使用 BSD make 专有自动变量 `$(.TARGET)`：

```
$ grep -n '(\$\.TARGET)' Makefile.in
83:$(SCSI_APPS): $(.TARGET).o libuscsi.a
86:$(APPS): $(.TARGET).o libuscsi.a libudf.a
```

GNU make 下该变量展开为空，规则退化到内建 `.o` 规则：

```
$ make -j1
.../clang      -o .o
clang-15: error: no input files
make: *** [<builtin>: .o] Error 1
```

把规则改为 GNU make 可用的写法后，Conan 的 out-of-source 构建（独立 build folder + 绝对 srcdir）
还会暴露第二类失败——源树定位：

```
make: *** No rule to make target 'udfdump.o', needed by 'udfdump'.  Stop.
```

（证据：`archives/u/udfclient/0.8.21/reports/conan-create.log`；复现记录 `udfclient-target-repro.txt`）

## 根因

1. **规则语义层**：`$(.TARGET)` 是 BSD make 自动变量；GNU make 无定义 → 展开为空 → 规则失效；
2. **源树定位层**：手写 Makefile 只在编译选项里带 `-I$(srcdir)`，没有 `VPATH`。Conan/`Autotools`
   在独立 build folder 中调用 `$(source_folder)/configure`，Makefile 生成于 build folder，
   GNU make 在 build folder 找不到 `.c` 源文件。
   两层失败互相独立：只修 `.TARGET` 仍会踩 VPATH，只加 VPATH 也进不到正常规则。

## 处理方式（udfclient 0.8.21，PR #13235）

补丁 `patches/0001-Makefile.in.patch`（要点）：

```diff
-srcdir=		@srcdir@
+srcdir=		@srcdir@
+VPATH=		@srcdir@
...
-$(SCSI_APPS): $(.TARGET).o libuscsi.a
-	$(LD) -o $(.TARGET) $(LDFLAGS) $(.TARGET).o libuscsi.a $(POSTOBJ)
+$(SCSI_APPS): %: %.o libuscsi.a
+	$(LD) -o $@ $(LDFLAGS) $@.o libuscsi.a $(POSTOBJ)
-$(APPS): $(.TARGET).o libuscsi.a libudf.a
-	$(LD) -o $(.TARGET) $(LDFLAGS) $(.TARGET).o libudf.a libuscsi.a $(POSTOBJ)
+$(APPS): %: %.o libuscsi.a libudf.a
+	$(LD) -o $@ $(LDFLAGS) $@.o libudf.a libuscsi.a $(POSTOBJ)
```

配合 `make -j1`（E074）后：conan-verify G0-G4、本地 CI（L0/L1/L1e/L5）、test_package 13 断言全部通过。

## 适用范围与边界

- **适用**：任何 `Makefile.in` 出现 `$(.TARGET)`（或发行版标识 bmake）的手写 Makefile 项目；
  GNU make 是仓库 Conan/CI 的默认 make。
- **边界（查重）**：E074 是 make 并发/fifo 层；E110/E114 是 configure/config.status 临时目录层；
  E007/E205 是 config.guess/config.sub 三元组层；本条目是**规则语义 + 源树定位**层，互不替代。
- **备选方案**：`tool_requires("bmake/20200710")` 直接使用 bmake（制品仓已有）。注意其 `sys.mk` 位于
  `<pkg>/share/mk`，需 `bmake -r`/`-m` 指定（见 DRAFT-9200-lddtree-shell-tool-portability）；
  相比改写会增加 CI 对非默认 make 的依赖，故本 PR 选择等价改写。

## 验证

```bash
# A. 规则语义失败（原始 Makefile.in + GNU make）
make -j1
# → clang -o .o / clang-15: error: no input files / [<builtin>: .o] Error 1
# B. 源树定位失败（静态规则但无 VPATH，Conan out-of-source）
conan create archives/u/udfclient/0.8.21 ...
# → No rule to make target 'udfdump.o'
# C. 修复后
python3 scripts/ohc-run.py conan-verify udfclient 0.8.21 --profile ohos-aarch64-device
# → G0-G4 PASS；test_package 13/13
```

## 关联

- 相似条目: E074（make 并发/环境）；DRAFT-9200-lddtree-shell-tool-portability（bmake 使用侧）
- 依据: PR #13235 `patches/0001-Makefile.in.patch`、`reports/w3-local-ci.log`
