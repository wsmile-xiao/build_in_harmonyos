# OHOS 下 autotools 库两项无补丁构建适配：--build triplet + CPPFLAGS 注入

> 草稿（DRAFT）。与同目录 `libgetline-1.0-ohos-autotools-configure-args.kv` 成对。

## 问题

libgetline 1.0（autotools/libtool C 库）在鸿蒙 PC（OHOS, ohos-aarch64）上 conan 构建两次首错：

1. `./configure` → `configure: error: cannot guess build type; you must specify one`
2. 修好 1 后 `make` → `src/libgetline.c:14:10: fatal error: 'libgetlineP.h' file not found`

## 根因

1. 上游自带的 `config.guess`/`config.sub`（2018-02-24）不认识 HarmonyOS：
   `uname -s = "HarmonyOS"`、`uname -r = "HongMeng Kernel 1.12.0"`，无法猜测构建类型；
   直接 `./configure`（不带三元组）必然失败。`config.sub` 也不接受 `*-linux-ohos`。
2. conan 2 的 `basic_layout` 把构建目录放在 `b/<pkg>/build-release/`，源码在父目录，
   automake 的默认 `DEFAULT_INCLUDES` 只含 `-I. -I$(top_builddir)`，**不含
   `$(top_srcdir)/include`**。`src/libgetline.c` 用引号包含 `"libgetlineP.h"`（位于
   `include/`），在 out-of-tree (VPATH) 布局下找不到（in-tree 手动编译因为
   `-I./include` 恰好在构建根目录而"侥幸"通过，掩盖了问题）。

## 方案（conanfile.py，无源码补丁）

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    if str(self.settings.os) == "OHOS":
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")  # ①
    tc.generate()

def build(self):
    apply_conandata_patches(self)
    env = Environment()
    env.append("CPPFLAGS", f"-I{os.path.join(self.source_folder, 'include')}", separator=" ")  # ②
    with env.vars(self).apply():
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
```

要点：
- ① `config.sub` 接受 `aarch64-unknown-linux-gnu`（实测归一化为该三元组），跳过猜型。
- ② 把 `CPPFLAGS=-I<source>/include` 经 **Environment** 注入 configure 环境，
  configure 将其写入 Makefile 的 `@CPPFLAGS@`，automake 编译规则引用 `$(CPPFLAGS)`。
  ⚠️ 不要用 `configure_args.append("CPPFLAGS=...")`——VAR=value 形式在该工具链
  AutotoolsToolchain 中可能被吞掉，Environment 注入最稳。

## 验证

- 探索编译与 conan create（ohos-aarch64, clang 15）均通过：configure/make/make check/
  make install 全绿；
- test_package 双用例（消费者 + 鸿蒙专项）全部通过；
- conan-verify G1-G4 PASS。

## 适用边界

- 适用于所有自带老版 config.guess/config.sub 的 autotools 库在 OHOS 上构建；
- `--build=aarch64-unknown-linux-gnu` 无需任何源码补丁（a52dec/abiword-plugin-* 已实证）；
- CPPFLAGS 注入适用于所有 conan 2 out-of-tree 布局下 src/ 引 include/ 头文件的
  autotools 库。

## 查重差异

- 与 E007/E072/E160/E279（config.guess/config.sub 无法识别 OHOS，方法=改脚本补丁）
  触发重叠：`trigger_overlap` —— 同一问题域，但本条目是**无源码补丁的参数注入法**
  （--build triplet），`solution_overlap` 中的新增差异成立；
- CPPFLAGS 注入为知识图谱**未命中**的新模式（`boundary_novelty`：conan 2 out-of-tree
  布局上下文）；
- 上游 lsize/realloc 内存缺陷另见
  `libgetline-1.0-upstream-uninitialized-lsize-exponential-realloc.*` 草稿。
