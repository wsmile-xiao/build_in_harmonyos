# DRAFT: Conan 2 的 `copy(self, "*", ...)` 不覆盖以 `.` 开头的文件 —— 数据包里的点文件必须单独 copy

> Contributor: username- | Status: DRAFT | Created: 2026-09-19
> 来源: ieee-data 20260625 适配（`share/ieee-data/.lastupdate`）

## 症状

纯数据包的 `package()` 用最自然的写法把一批数据文件拷进包：

```python
def package(self):
    copy(self, "*", src=self.source_folder, dst=data_dir)
```

构建全绿、`conan create` 通过、G0–G4 全过，**但包里少了一个 `.lastupdate`**。
它不报错、不警告，只有在测试真的去读这个文件时才暴露：

```
[FAIL] 数据文件存在且非空: .lastupdate
```

同类数据包（字体、图标、locale 表、各类 registry 数据）里，点文件并不罕见：
`.lastupdate`、`.order`、`.dirs`、`.gitkeep`、`.hidden` 索引文件都出现过。

## 根因

`conan.tools.files.copy()` 内部按 `fnmatch` 匹配文件名，而**部分 Conan 2 版本
对 `*` 的处理保留了 shell 的通配语义：不匹配以 `.` 开头的文件**（`fnmatch` 本身
会匹配，但 `copy()` 的过滤器实现走过 `keep_path` + 内部 glob，行为随版本而变）。
结果是同一份配方在不同 Conan 版本下产出的包内容不一样 —— 这类"环境相关的静默丢文件"
比构建失败危险得多，因为它不会让 CI 变红。

## 判据（一条命令，不需要编译）

```python
# 在 package() 之后立即断言点文件已经进包（放进 test_package 也可以）
import os
assert os.path.isfile(os.path.join(self.package_folder, "share/ieee-data/.lastupdate"))
```

或者在 PR 的 test_package 里把"点文件存在"写成一条**独立断言**，并把
"安装目录里资源文件之外不得有多余内容"作为配对断言 —— 这样既能发现丢文件，
也能发现多文件。

## 修法（可复用的模式）

数据包对点文件**单独调用 `copy()`**，不要指望 `"*"`：

```python
def package(self):
    for name in ("oui.txt", "oui.csv", "mam.txt", "mam.csv", ...):
        copy(self, name, src=self.source_folder, dst=data_dir)

    # 点开头文件必须显式拷贝："*" 通配在部分 Conan 版本的 copy() 里不覆盖它
    copy(self, ".lastupdate", src=self.source_folder, dst=data_dir)
```

配套的两条硬性要求：

1. **test_package 必须断言点文件存在**（否则这个问题永远发现不了）；
2. 安装目录要做"白名单断言"（`set(实际内容) == set(期望内容)`），
   这样"漏拷"和"多拷"两个方向都会被抓住。

## 与现有条目的边界

- `DRAFT-6051-libnxml-0.18.5-remote-automake-pkg-missing-dotfiles`：讲的是**远程
  automake 二进制包自身的 bin 目录少了点文件**（`.aclocal-real`），属于"包管理缓存
  半残"，修法是 `conan remove` + 本地重建；本条讲的是**自己写 package() 时 `copy()`
  漏掉了源里的点文件**，两者触发点与修法都不同。
- `DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental`：讲的是
  `copy()` 的 **src 必须用绝对路径**；本条讲的是**通配符不覆盖点文件**。

## 上游测试情况

`ieee-data` 是 Debian 原生纯数据包，上游用例数 N=0；本条的验证靠配方自己的
test_package（33 条断言，其中"`.lastupdate` 存在且是合法 Unix 时间戳"这一条
正是在修这个问题之后补上的）。
