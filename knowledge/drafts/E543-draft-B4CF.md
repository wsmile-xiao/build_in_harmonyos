# E543 — 无 VPATH 支持的老 Makefile.in 在 Conan 默认 out-of-source 构建下找不到源文件

> 触发实例: compface 1.5.2 适配（任务 #6567，PR #9043，OHOS aarch64 / Conan 2.29.1 / clang 15），2026-09-09。

## 错误特征

conan create 在 build() 阶段（configure 已成功、make 启动后）报：

```text
compface/1.5.2: RUN: make -j1
make: *** No rule to make target 'cmain.c', needed by 'cmain.o'.  Stop.
```

特征：报错目标是**源码树里确实存在的 .c 文件**，且该 Makefile 规则形如 `cmain.o: cmain.c`（无任何目录前缀）。

## 触发条件

- 构建系统: autotools（2005 年代及更早的 Makefile.in，规则不带 `$(srcdir)` 前缀，无 VPATH 支持）
- 阶段: make（configure 正常通过，编译刚开始）
- 布局: Conan 2 默认 `basic_layout`（out-of-source，构建目录 `build-release/` 与源码目录分离）

## 根因分析

Conan 2 的 `basic_layout` 让 configure 在独立的 build 目录运行，生成的 Makefile 工作目录是构建目录。老 Makefile.in 的对象文件规则写作 `cmain.o: cmain.c`——make 会在**构建目录**里找 `cmain.c`，而源文件在**源码目录**，于是报 "No rule to make target"。现代 automake 生成的规则带 `$(srcdir)/` 前缀与 VPATH 支持，不受影响（这是本条与 E519 install-data-am 找不到文件、E434 copystamp 同文件错误的区别：错误发生在编译规则层而非安装/拷贝层）。

## 解决方案

### 推荐方案
conanfile 的 `layout()` 改为源码目录就地构建（in-source），与老构建系统的工作方式一致：

```python
def layout(self):
    self.folders.source = "."
    self.folders.build = "."
```

compface 1.5.2 实测：改后 `conan create` 一次通过（含上游功能验证与 test_package）。

### 禁止做法
- ❌ 用 sed 给老 Makefile.in 逐规则补 `$(srcdir)/` 前缀或 VPATH 支持——规则多时极易遗漏，且属源码补丁，改动面与风险远超收益。
- ❌ 在 build() 里手工把源码文件拷进构建目录——文件清单会随上游版本漂移。

## 验证

```bash
# 诊断：确认 Makefile.in 无 VPATH 支持
grep -c 'srcdir' Makefile.in        # 为 0（或仅出现在注释）即中招
# 修复后：conan create 全流程通过
conan create . -pr:h=<profile> --build=missing
```

## 关联条目
- 相似: E519（out-of-source 下 install-data-am 找不到源文件——同一根因域，但错误在安装阶段）
- 相似: E434（copystamp 同文件错误——in-tree 与 srcdir 语义，方向相反）
- 相关: E386（HMDFS 上 configure 子 shell 的 getcwd 失败，同样影响老式 autotools 在 conan 下的构建）
