# E429 — make 命令行 CFLAGS 覆盖 Makefile 的 += 追加导致 -DVERSION 丢失

## 错误特征
```
error: use of undeclared identifier 'VERSION'
（或链接期）undefined reference to `VERSION'
```
Makefile 中明明有 `CFLAGS += -DVERSION=\"$(VERSION)\"`，但编译命令行中看不到 `-DVERSION`。

## 触发条件
- 构建系统: raw Makefile（非 autotools/cmake）
- 阶段: make/compilation
- 配方在 `build()` 中以 `self.run(f'make CFLAGS="..."')` 方式传入 CFLAGS

## 根因分析
GNU make 中**命令行变量优先级最高**：`make CFLAGS="-O2"` 传入后，Makefile 内的
`CFLAGS += -DVERSION=...` 追加不再生效——实际生效的只有命令行传入的值，
Makefile 默认的 `-DVERSION/-Wall` 等关键宏和参数全部丢失。

## 解决方案

### 推荐方案
raw Makefile 项目的 Conan 配方**只注入工具变量（CC/CXX），不传 CFLAGS/CXXFLAGS**，
让 Makefile 保留自己的默认 CFLAGS 与 `+=` 追加：

```python
self.run(f'make -j1 CC="{cc}"')
```

### 禁止做法
- ❌ `make CFLAGS="-O2 ..."` —— 覆盖 Makefile 的追加，丢失 -DVERSION/-Wall 等
- ❌ 用本地缓存或 `--build=missing` 绕过依赖验证（违反 R36）

## 实例
sluice/0.03.01（OHOS aarch64, Conan 2.29）：修复前 `use of undeclared identifier 'VERSION'`，
修复后 conan-verify 8 门禁全 PASS（来源：sluice-0.03.01，2026-09-21）
