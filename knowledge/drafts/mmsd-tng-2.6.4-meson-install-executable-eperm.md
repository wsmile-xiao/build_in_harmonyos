# meson install 落地的可执行文件在 OHOS 上被拒执行（EPERM）

> 草稿 ID：`mmsd-tng-2.6.4-meson-install-executable-eperm`
> 来源任务：mmsd-tng 2.6.4 适配（application 类 conan 包；conan create 的 test_package 阶段）

## 错误特征

```
mmsd-tng/2.6.4 (test package): Running test()
PermissionError: [Errno 1] Operation not permitted:
    '/…/p/b/mmsd-f6e50faba39c4/p/bin/mmsdtng'
ERROR: mmsd-tng/2.6.4 (test package): Error in test() method …
	ConanException: Error 1 while executing
```

注意是 **EPERM（Operation not permitted）**，不是 EACCES（Permission denied）。

## 触发条件

- 在 HarmonyOS/OHOS 上打包**可执行文件**（`package_type="application"`、`cpp_info.bindirs` 非空）；
- 产物由 `meson install`（同类：autotools `make install`、cmake `install`）**直接落地**到
  `package_folder/bin`；
- `test_package` 真的去运行被安装的二进制（R34 要求）——就会命中。

## 根因（三步判别链）

1. 直接执行包内二进制 → `Operation not permitted`；
2. `chmod 770` / `chmod 755` 后重试 → **仍然 EPERM** → 排除权限位问题；
3. 用**构建目录里的同名产物覆盖**同一路径后 → **立刻可运行**，且
   `md5sum` 两者**完全相同** → 排除内容/ELF/签名问题，差异只在"这个文件是谁创建的"
   （inode 及其携带的文件系统属性）；
4. 同一路径、同为 0750 的构建目录副本本身可直接执行 → 与路径、mode 都无关。

**结论**：这是 `meson install` 在 OHOS/HMDFS 上引入的文件属性问题，不是代码问题、不是权限问题。
本库与 `account-utils 1.4.0` 配方注释记录的"绕开 meson install 的 HMDFS 落地坑"同族。

## 解决方案（推荐）

在 `package()` 里，`meson.install()` **之后**把可执行产物从构建目录重新 `copy()` 一份：

```python
def package(self):
    meson = Meson(self)
    meson.install()
    bin_dst = os.path.join(self.package_folder, "bin")
    os.makedirs(bin_dst, exist_ok=True)
    for name, src_dir in (("mmsdtng", self.build_folder),                    # build 根
                          ("mmsctl", os.path.join(self.build_folder, "tools"))):  # 子目录
        if os.path.isfile(os.path.join(src_dir, name)):
            copy(self, name, src=src_dir, dst=bin_dst, keep_path=False)
```

要点：
- **只对可执行文件做**。共享库**不要**这么做，更不要 `strip`——OHOS loader 校验链接期写入的
  `.codesign` 段哈希，`strip` 会使哈希失配导致 `dlopen`/exec 报 Permission denied
  （libsoup3 / telemetry 已有铁证）；meson install 会清理/改写 `.so` 的 RUNPATH 的问题也需
  "从 build 目录回拷 .so"来规避，但那属于另一条知识。
- 复制源要用构建目录里的真实路径（本例 `mmsdtng` 在 build 根、`mmsctl` 在 `tools/`）。

## 反例（不要这么做）

- ❌ 只加 `chmod +x` 收尾 —— 已实测无效（EPERM 不是权限位问题），会造成"本地偶发成功、CI 必挂"；
- ❌ `strip` 包内二进制"重造"文件 —— 破坏 `.codesign` 哈希，彻底不可执行/不可 dlopen；
- ❌ 把 test_package 改成不运行二进制（只 print/退出 0）—— 违反 R34，且会放过这类真实缺陷
  （CI 有 PF3/L1e 反向验证兜底）。

## 验证

```bash
# 修复前
$ <pkg>/bin/mmsdtng --version
zsh: operation not permitted: <pkg>/bin/mmsdtng

# 判别链
$ chmod 770 <pkg>/bin/mmsdtng && <pkg>/bin/mmsdtng --version
zsh: operation not permitted: <pkg>/bin/mmsdtng        # 仍失败 → 非权限位
$ md5sum <builddir>/mmsdtng <pkg>/bin/mmsdtng
2f604489ea273a98ab43035c81e05f45  <builddir>/mmsdtng
2f604489ea273a98ab43035c81e05f45  <pkg>/bin/mmsdtng    # 内容一致 → 非内容/签名

# 修复后（package() 重新 copy）
$ conan create archives/m/mmsd-tng/2.6.4 … --build=mmsd-tng/*
[PASS] case1 upstream_mmsdtng_version — exit=0 output='2.6.4, git version: 2.6.4'
== SUMMARY: 4/4 passed ==
conan create exit=0
```

## 证据

- 失败现场：`archives/m/mmsd-tng/2.6.4/reports/03-conan-create.log`（PermissionError 段）
- 修复后：`archives/m/mmsd-tng/2.6.4/reports/conan-create.log`（test_package 4/4 PASS）
- 配方实现：`archives/m/mmsd-tng/2.6.4/conanfile.py` → `package()`
- 适配笔记：`archives/m/mmsd-tng/2.6.4/notes.md` §2/E8
