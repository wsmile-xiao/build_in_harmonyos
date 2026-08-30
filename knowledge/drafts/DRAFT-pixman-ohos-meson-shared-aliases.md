# pixman: OHOS 上 Meson shared library alias 需要物化

## 触发场景

pixman 0.46.4 在 HarmonyOS PC 真机 shadow CI 中，核心库 37/37 编译成功，`meson install` 也安装了 `libpixman-1.so.0.46.4`，但日志显示：

```text
Symlink creation does not work on this platform. Skipping all symlinking.
```

这会导致包内没有 `libpixman-1.so.0` 和 `libpixman-1.so`。

## 根因

OHOS/HMDFS 路径可能拒绝 symlink。Meson 遇到 symlink 创建失败时会跳过，真实版本库仍会安装成功，因此问题会延后到消费者链接或运行期加载阶段暴露。

## 修法

在 Conan recipe 的 `package()` 中，`Meson(self).install()` 后检查真实版本库是否存在，并在 OHOS shared 包中复制出 alias：

```python
for alias in ("libpixman-1.so.0", "libpixman-1.so"):
    if not os.path.exists(alias_path):
        shutil.copy2(versioned, alias_path)
```

## 验证

`CI_PACKAGES="archives/p/pixman/0.46.4" zsh ci/conan/build_and_test.sh` 通过，包内包含版本库、SONAME alias 和 linker alias，`test_package` 输出 `pixman 0.46.4: API smoke + dlopen ok`。
