# E429 — Conan 2.29 GnuToolchain has no .vars — use extra_env.define()

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
AttributeError: .GnuToolchain. object has no attribute .vars.
```

实际遇到的报错：

```text
tc.vars["BRANCH"]="master" -> AttributeError: 'GnuToolchain' object has no attribute 'vars'
```

## 触发条件

- 分类：`conan-api`
- 阶段：`configuration`
- 工具：`conan`
- 适用范围：配方内调用 GnuToolchain 并用旧写法 tc.vars[...] 注入环境变量的场景（本仓实测 conan 2.29.1 / OHOS 适配版）

## 根因分析

本仓 OHOS 适配版 conan 2.29.1 的 GnuToolchain 类不再提供 tc.vars 属性，自定义环境变量接口改为 tc.extra_env（Environment 对象）。访问 tc.vars 直接抛 AttributeError。

## 解决方案

### 推荐方案

把 tc.vars["K"]="V" 改为 tc.extra_env.define("K", "V")，随后 tc.generate()。

**方案说明**：用 tc.extra_env.define() 替代已移除的 tc.vars，变量写入 build scope 的 conanbuild env 文件。

```bash
from conan.tools.gnu import GnuToolchain
tc = GnuToolchain(self)
tc.extra_env.define("TAG", self.version)
tc.generate()
```

### 禁止做法

- ❌ 不要再用 tc.vars[...]——该属性在 2.29 已移除，会在 generate() 阶段直接抛 AttributeError。
  - 原因：tc.vars 是早期 Conan 2 API，2.29 已移除。
  - 后果：conan create 在 generate() 阶段失败，配方无法构建。

### 回退方案

若不想依赖 GnuToolchain，可在 build() 里先用 Python 写出构建期元文件（如 build/version.h），再调用构建命令。

## 验证

```bash
conan create 后检查生成的 conangnutoolchain.sh 含 export TAG=...；本条由 rtl-wmbus/1.1.0 实测，横幅正确输出 1.1.0。
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 完整踩坑记录：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 7 节
