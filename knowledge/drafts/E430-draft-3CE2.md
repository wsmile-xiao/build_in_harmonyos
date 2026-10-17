# E430 — 本仓 OHOS 适配版 conan 的 self.run(env=) 语义是环境文件名而非环境变量表

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
env argument to ConanFile.run() should be a list
```

实际遇到的报错：

```text
env=dict -> AssertionError: env argument to ConanFile.run() should be a list
```

## 触发条件

- 分类：`conan-api`
- 阶段：`configuration`
- 工具：`conan`
- 适用范围：在本仓 OHOS 适配版 conan 2.29.1 上，配方试图用 self.run(env=...) 传自定义环境变量的场景

## 根因分析

该 conan 的 ConanFile.run(env=...) 形参语义是“环境文件名字符串列表”（默认 conanbuild/conanrun），不是 Conan 2 官方文档中的环境变量表。传 dict 触发 assert 报 should be a list；传 [(k, v)] 则在解析成路径时报 expected str/bytes/os.PathLike, not tuple。

## 解决方案

### 推荐方案

不要用 self.run(env=) 传自定义环境变量；改用 GnuToolchain(self).extra_env.define(K, V) + tc.generate()。

**方案说明**：自定义环境变量走 toolchain 的 extra_env，而不是 self.run 的 env 形参。

```bash
tc = GnuToolchain(self)
tc.extra_env.define("BRANCH", "master")
tc.generate()
self.run('make release CC="<cc>" -j1', cwd=self.source_folder)
```

### 禁止做法

- ❌ 不要传 env=dict 或 env=[(k, v)]——前者触发 assert，后者触发 PathLike 类型错误。
  - 原因：该形参被实现为环境文件名列表，不接受变量表。
  - 后果：conan create 抛 ConanException，配方无法构建。

### 回退方案

若既不能用 extra_env 又必须传变量，可在 build() 里先生成 conanbuild 扩展 env 文件，或直接改用 Python 写出构建期元文件。

## 验证

```bash
conan create 通过且生成的 conangnutoolchain.sh 含目标 export；由 rtl-wmbus/1.1.0 实测。
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 完整踩坑记录：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 7 节
