# E429 — conan 2.29 不可见传递依赖 package_folder=None 致配方遍历 TypeError

## 错误特征
```
TypeError: expected str, bytes or os.PathLike object, not NoneType
```
conan create 的 build() 阶段抛出，堆栈指向配方内 `os.path.join(<dep>.package_folder, ...)`。

## 触发条件
- 构建系统: conan 配方（任意构建系统）
- 阶段: build() 遍历 `self.dependencies.values()` 取依赖路径（PKG_CONFIG_PATH/SHIM 生成等）

## 根因分析
ohpcd 社区适配 conan 2.29 对消费者不可见的传递依赖（Traits headers=False/libs=False，如 bzip2/xz/openssl——上游仅声明了依赖关系但未实际消费其头/库）不为其解包，`Dep.package_folder=None`。且 `self.dependencies.values()` 遍历的是**全部传递依赖**（非仅直接 requires），`os.path.join(None, ...)` 即 TypeError。

## 解决方案

### 推荐方案
配方遍历依赖取路径处一律先判空：`pf = d.package_folder; if not pf: continue`。只取特定依赖用 `self.dependencies[name]`（直接依赖均有 folder）。
实证（mpd 0.24.12，2026-09-27）：16 个直接依赖全有 folder；bzip2/xz/openssl 三个传递依赖 None。

### 禁止做法
- ❌ 无守卫直接 `os.path.join(d.package_folder, ...)`——任何含"不可见传递依赖"的图必炸

## 验证
```bash
python3 - <<'EOF'
# conan create 日志无 TypeError 即通过；或本地 conan graph info 核对：
# 直接依赖 package_folder 均非空，不可见传递依赖为 None（预期行为）
EOF
```

## 关联条目
- 相关: E430（同为 mpd 0.24.12 适配期发现）
