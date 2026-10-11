# DRAFT 知识条目（md 成对版）— Conan 2 conandata.yml 结构双坑：sources 按包名嵌套 vs patches 必须平铺

> Status: DRAFT | 来源: tetraproc/0.9.2 真机 shadow CI 2026-10-04（r2 第 4、5 轮）

## 使用说明

给所有使用 `conandata.yml` 管理 source/patch 的配方的**结构约定**。两处结构选错，
`conan export` / `source()` / `apply_conandata_patches()` **静默变空或直接抛错**，
且失败点远离真实原因（一个炸在 source() 的 TypeError，一个炸在几十行之后的
编译命令里），排查成本高。本条给出正确写法 + 两条失败指纹。

## 适用范围

- Conan 2.x（2.0–2.29 实测），所有 `archives/*/*/*/conandata.yml`。
- 单包配方、多 source 配方均适用。

## 输入 / 输出

- 输入：conandata.yml 的 sources/patches 结构、conanfile.py 的
  `source()` / `export_sources()` / `build()` 写法。
- 输出：可被 Conan 2 正确消费的结构；两条“补丁没生效”的快速判定指纹。

## 坑 1：sources 按包名嵌套时，`get(**self.conan_data["sources"])` 直接 TypeError

conandata.yml 里 sources 写成（很多模板/工具按包名嵌套生成）：

```yaml
sources:
  tetraproc:
    url: "https://.../tetraproc-0.9.2.tar.bz2"
    sha256: "9116..."
```

配方若写 `get(self, **self.conan_data["sources"], strip_root=True)`，
运行期报：

```text
TypeError: get() got an unexpected keyword argument 'tetraproc'
```

修复二选一：按名索引 `get(self, **self.conan_data["sources"]["tetraproc"],
strip_root=True)`；或把 sources 写成平铺单 dict（无包名层）。

## 坑 2：patches 嵌套在包名下 → export/apply 静默为空（最阴）

```yaml
patches:            # ❌ Conan 2 不认这层
  tetraproc:
    - patch_file: "patches/0001-....patch"
```

`export_conandata_patches()` / `apply_conandata_patches()` 读的是
`conan_data["patches"]` **平铺列表**。嵌套写法不报错、不告警：
`conan export` 日志里"Exporting conandata.yml"一切正常，只是
**补丁从未进入配方**，build 时跑的是未打补丁的上游 Makefile/源码。

失败指纹（不用读 conan 源码即可判定）：

```text
# export 阶段（健康样例应能看到补丁文件被复制）:
tetraproc/0.9.2: exports: File 'conandata.yml' found. Exporting it...
# 只有 .yml/.py 被复制、没有 patches/*.patch → 补丁没进配方

# build 阶段: 明明写了补丁的修改却没生效
# 本例: 去掉 -march=native 的补丁没生效，编译命令里仍出现 -march=native
clang++ -O2 -Wall -ffast-math -march=native -MMD -MP ...
```

正确写法：

```yaml
patches:
  - patch_file: "patches/0001-....patch"
    patch_description: "..."
```

## 示例（本次实证）

- 错误结构 + 两条指纹的完整日志见 notes.md"r2 迭代 4/5"。
- 修复后 conandata.yml：sources 保留包名嵌套 + source() 按名索引；
  patches 平铺 → export 复制 1 个 .patch，build 命令行中 -march=native 消失。

## 查重边界

全库检索 conandata：E241（数据包模式）、E248/E254/E255（下载/镜像）均不涉及
conandata 的**结构**约定；无既有条目覆盖这两个失效模式。
