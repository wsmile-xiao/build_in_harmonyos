# DRAFT — header-only 配方 package() 中 package_folder 为 str 时 `/` 拼接 TypeError

## 错误特征

`conan create`（或 `conan-verify` G2）在 package() 阶段报：

```
ERROR: qsort/0.1@ohpcd/stable: Error in package() method, line 41
    copy(self, "qsort.h", self.source_folder, self.package_folder / "include")
TypeError: unsupported operand type(s) for /: 'str' and 'str'
```

## 触发条件

- 构建系统: header-only / 无构建系统（单头文件 C/C++ 库），配方手工 `copy` 头文件到 include/
- 布局: `basic_layout`
- 环境: OHOS 适配版 Conan 2.29.1（`self.package_folder` 返回 `str`）
- 阶段: packaging（conan create 的 package()）

## 根因分析

`self.package_folder` 在该 Conan 版本与布局下返回 `str` 而非 `pathlib.Path`，`/` 运算符
对 str 不适用。conanfile 模板/既有配方中 `self.package_folder / "include"` 的写法依赖
`package_folder` 为 Path，并非在所有布局/环境下成立。header-only 库因为需要手工
`copy(..., include/)`，是最容易踩中该路径拼接错误的配方形态。

## 解决方案

### 推荐方案

conanfile.py 顶部 `import os`，package() 中统一使用：

```python
import os

def package(self):
    copy(self, "qsort.h", self.source_folder, os.path.join(self.package_folder, "include"))
```

`os.path.join` 对 str 与 Path 均兼容，消除类型依赖。

### 回退方案

显式 pathlib：

```python
from pathlib import Path
copy(self, "qsort.h", self.source_folder, str(Path(self.package_folder) / "include"))
```

### 禁止做法

- ❌ 用 `str.replace` / 字符串 `+` 拼接 package 路径（分隔符与类型兼容性双重风险）

## 验证

```bash
conan create archives/q/qsort/0.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 修改前: package() TypeError 中止
# 修改后: package 成功，test_package 1/1 Passed，conan-verify G2 PASS
```

qsort 0.1 实测：修改前 conan create 失败于 `package_folder / "include"` TypeError；
改用 `os.path.join` 后 conan create 全流程通过（exit 0，test 1/1 Passed）。

## 适用边界 / 反例

- 适用: basic_layout + header-library 手工 include 拷贝的配方
- 不适用（不触发）: 使用 CMake install/export 自动安装头文件的 INTERFACE 库配方
  （E321/E322 形态）、`package_folder` 为 Path 的环境
- 反例: 不应把 E257（build() 门禁 no-op）或 E415（conandata 镜像恢复）误记为同一条目

## 关联条目

- similar_to: E340（同为 package() 路径处理，但为 glob 定位产物）、E257（header-only 配方门禁）
- 原则: P016
