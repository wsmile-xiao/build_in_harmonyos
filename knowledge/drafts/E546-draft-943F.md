# E546 — Conan 仓库内 `test_package` 以自身为 `build_folder`：测试产物会混入归档并被提交

## 错误特征

`git status` / PR diff 中出现测试运行时产物：

```
archives/r/r-base/4.5.1/test_package/moved-r-base/...        （被测包完整副本，实测 87 MB / 2025 文件）
archives/r/r-base/4.5.1/test_package/conanbuild.sh
archives/r/r-base/4.5.1/test_package/conanrun.sh
archives/r/r-base/4.5.1/test_package/deactivate_conanbuild.sh
archives/r/r-base/4.5.1/test_package/deactivate_conanrun.sh
```

或 `du -sh archives/.../test_package` 出现与包本体同量级（数十 MB 以上）的体积，而 `test_package/` 本应只有几个源文件。

## 触发条件

- 构建系统: conan v2 recipe；`test_package/` 位于**仓库内**（`archives/.../<ver>/test_package`）
- 阶段: testing → 入库（`git add`）
- 测试脚本中包含"把被测包复制/移动到临时目录做重定位校验"的步骤（`cp -a` / `mv` / `conan cache path` + 复制）

## 根因分析

当 `conan create <path>` 的配方是"仓库内配方 + 同级 `test_package/`"时，Conan 会把**`test_package/` 目录自身**当作该测试包的 `build_folder`，而不是在一个临时目录里展开：

- 测试脚本里 `cp -a "$pkg_folder" moved-<pkg>` 的结果直接落在**源码树**中；
- Conan 生成的 `conanbuild.sh` / `conanrun.sh` / `deactivate_*.sh` 同样落在该目录；
- 结果是"构建产物"与"源码"混在一起：一次成功的本地验证就会污染工作区，作者若在 `git add archives/ ...` 时未察觉，产物会被提交；
- 危害不止体积：残留状态会**改变后续运行的前置条件**（下一次跑测试时 `moved-<pkg>` 已存在、磁盘占用异常、`git status` 噪声掩盖真实改动），使 CI 结果不可复现。

真实案例：`r-base/4.5.1` 归档 87 MB，其中几乎全部是 `test_package/moved-r-base/`（2025 个文件）；`4.5.1.1` 修复后归档 **462 KB**。

## 解决方案

### 推荐方案

在 `test_package/conanfile.py` 的 `test()` 中**无条件**清理测试产物（`try/finally`，成功/失败/异常都清理），保证 `test_package/` 始终是纯输入：

```python
def test(self):
    moved = os.path.join(self.build_folder, "moved-r-base")
    command = [...]
    try:
        self.run(command, env=None)
    finally:
        # Conan 对仓库内 test_package 以该目录自身作为 build_folder，
        # 被测包副本会落在源码树内，必须在测试结束时清理。
        shutil.rmtree(moved, ignore_errors=True)
```

配套约定：

1. Conan 生成的 activate 脚本交由**仓库根 `.gitignore`** 兜底（如 `**/test_package/conanbuild*.sh`），避免每个包自带 `.gitignore`；
2. 归档入库前用 `du -sh <ver>/test_package` 自检：体积应与"几个脚本 + 清单"同量级；
3. 提交前 `git status --porcelain` 必须只剩**有意修改**的文件。

### 禁止做法

- ❌ `git add -f` 把 `moved-<pkg>/` 一起提交（体积与可复现性问题都被固化）；
- ❌ 只在"成功路径"清理（断言失败/异常退出时产物仍留在源码树，恰好是最需要排查的场景）；
- ❌ 依赖手工 `rm -rf`：本地验证跑第二遍时必然忘记。

## 验证

```bash
# 1) 归档体积自检（应为 KB 量级，而非数十 MB）
du -sh <pkg>/<ver>/test_package

# 2) 运行两次完整测试后检查残留
conan create <pkg>/<ver> -pr:h=<profile> -pr:b=<profile> --build=missing
conan create <pkg>/<ver> -pr:h=<profile> -pr:b=<profile> --build=missing
git status --porcelain <pkg>/<ver>     # 期望：只列出有意修改的文件，无 moved-*/conanbuild*.sh
```

## 关联条目

- 相关: E545（test_package 硬编码宿主绝对路径导致 CI 中止 —— 同属"test_package 自身缺陷阻断发布"，一个来自环境假设、一个来自产物未清理）
