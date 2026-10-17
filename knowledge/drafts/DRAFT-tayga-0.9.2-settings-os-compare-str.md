# DRAFT — settings.os == "OHOS" 在原版 conan 下抛 Invalid setting；用 str() 比较

> Status: **Draft**（待审核 promote）｜ severity: `2` | category: `conan|recipe|portability` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-tayga-0.9.2-settings-os-compare-str.kv`

## 错误签名

```text
ERROR: ... Error in build() method, line NN
	if self.settings.os == "OHOS":
	ConanException: Invalid setting 'OHOS' is not a valid 'settings.os' value.
Possible values are ['Windows', ..., 'Linux', ...]
```

## 根因

Conan 的 settings 对象重载了 `__eq__`：**右值会被当作 setting 值做枚举合法性校验**。真机 CI 的 conan 定制过 settings.yml（含 `OHOS`），所以 kelbt 式的直接 `==` 写法能跑；但本机 Docker/WSL 用 pip 装的原版 conan，其 settings.yml 没有 `OHOS` 枚举——**比较动作本身**就抛异常，即使该分支在 Linux profile 下本不该命中。结果：配方在任何非 OHOS 环境都无法构建，本机回归会误报"配方损坏"。

## 推荐方案

```python
# ❌ 只能在真机定制 conan 下跑
if self.settings.os == "OHOS":
# ✅ 双环境通用：先转 str 再比较，不触发枚举校验
if str(self.settings.os) == "OHOS":
```

`str(settings.os)` 输出就是枚举值名，语义完全等价。本机（Linux → False 跳过 OHOS 分支）与真机（OHOS → True）都能构建——这是"一份配方、双环境可验证"的最低成本写法。对 `settings.compiler` 等其他定制枚举同理。

## 验证

```bash
grep -n 'settings.os ==' conanfile.py   # 右值是定制枚举即中招
# 修复后本机 conan create . --build=missing 不再报 Invalid setting
```

## 来源

tayga/0.9.2 适配（2026-10-01）：build() 里加 OHOS 分支（TMPDIR 重定向）后，本机 Docker 回归报 Invalid setting，栈指向比较行本身；改 `str()` 后本机与真机 CI 均绿。

---
*本文由 `knowledge/drafts/DRAFT-tayga-0.9.2-settings-os-compare-str.kv` 字段衍生（补齐 kv→md 配套）。*
