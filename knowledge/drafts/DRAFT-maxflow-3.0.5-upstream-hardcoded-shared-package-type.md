# DRAFT-maxflow-3.0.5-upstream-hardcoded-shared-package-type — 上游硬编码 SHARED
# 时 E283 的 declare-shared-contract 不适用，应改 package_type="shared-library"

> Contributor: codex | Status: Draft | Updated: 2026-09-27
> Source event: maxflow 3.0.5 HarmonyOS PC 适配，真机 shadow CI r1
> （archives/m/maxflow/3.0.5）

## 错误特征

```text
ERROR: maxflow/3.0.5: Package type is 'library', but no 'shared' option declared
L1_RESULT=fail: conan create failed
```

conan create 在 Computing dependency graph 阶段即失败，配方根本没进 build()。

## 与 E283 的关系（查重边界）

E283（declare-shared-contract）与本条目**错误签名完全相同**，但推荐方案只覆盖
"构建系统可尊重选项"的场景：声明 `options={"shared":[True,False]}` 并把选项传递
给构建系统。当上游 CMake/Mmake **硬编码** `ADD_LIBRARY(xxx SHARED ...)`（无
BUILD_SHARED_LIBS 选项、无任何开关）时，该方案不可用：

- 照抄 E283 声明 shared 选项 = **假契约**：选项翻转改变 package_id 却不改变
  产物（static=True 时拿到的仍是 .so），消费者被误导；
- 为尊重选项去 patch 上游构建系统 = 改动面大、偏离上游，且 static 产物可能与
  上游显式实例化模板的链接模型不兼容。

## 解法（硬编码 SHARED 子型）

```python
package_type = "shared-library"   # 仓库惯例，161 个配方同款
# 不声明 shared 选项；附注释说明上游硬编码 SHARED、非 R26 系统同名库
```

- `shared-library` 类型不需要 shared 选项，Conan 依赖图校验直接通过；
- 消费者侧 cpp_info.libs=["xxx"] 不变，CMakeDeps/传递性消费正常；
- R26（系统同名库禁动态）不受影响——仅当库名与 /lib、/lib64 系统库撞名时才
  必须静态，此时应 patch 上游改静态而不是用本条方案。

## 验证证据

- maxflow 3.0.5 真机 shadow CI r1 失败 → r2 改 shared-library 后该错误消失
  （r2 起依赖图计算通过，进入 source()/build()）。
- 仓库惯例核查：`grep -rl 'package_type = "shared-library"' archives/ | wc -l`
  = 161（如 archives/a/abiword-plugin-clarisworks/3.0.8，同为无 shared 选项
  的纯 shared-library 声明）。

## 查重（B1 证据摘要）

- 检索词：`no 'shared' option` / `shared-library` / `package_type`
  （knowledge/ 全目录）。
- E283：同签名不同修复路径（见上）；E277 仅在错误特征里顺带引用该签名；
- DRAFT-libharu-2.3.0-missing-dt-soname、E330、E331：shared 库的 soname/软链
  主题，与 package_type 契约无关。
- 新增价值：为 E283 补上"上游硬编码 SHARED"这一常见子型的正确解法，防止贡献
  者按 E283 声明假选项。
