# DRAFT-exifprobe-2.0.1-conan2-copy-keep-perm

> 草稿知识项 — Conan 2 配方 `package()` 中 `conan.tools.files.copy` 不接受
> `keep_perm` 参数（`TypeError: copy() got an unexpected keyword argument 'keep_perm'`），
> 直接去掉该参数即可，权限由 Conan 2 拷贝语义自动保留。
> 来源：exifprobe 2.0.1 Conan 配方化（feat/exifprobe-2.0.1，task
> exifprobe-2.0.1-r01-pc2-20-20260921T071009Z，2026-09-21）
> 同 stem 配对：`knowledge/drafts/DRAFT-exifprobe-2.0.1-conan2-copy-keep-perm.kv`

## 问题（现象 / error_signature）

- conan create 在 `package()` 阶段失败：
  ```
  ERROR: exifprobe/2.0.1@ohpcd/stable: Error in package() method, line 53
          copy(self, "exifprobe", self.source_folder, os.path.join(self.package_folder, "bin"), keep_perm=True)
          TypeError: copy() got an unexpected keyword argument 'keep_perm'
  ```
- 该错误出现在把可执行文件/脚本拷入 `package_folder/bin` 的 Makefile CLI 工具配方中。

## 根因（root_cause）

- Conan 2 的 `conan.tools.files.copy` 签名**没有** `keep_perm` 参数
  （Conan 1 时代的写法）；传参会抛 `TypeError`，导致 `package()` 阶段失败。
- Conan 2 拷贝（底层 `shutil.copy2` 语义）**天然保留源文件权限位**，
  可执行位无需额外参数即可进入 `bin/`。

## 方案（rec_approach / rec_command）

- 删除 `keep_perm=True`，直接拷贝：
  ```python
  from conan.tools.files import copy
  # ...
  def package(self):
      copy(self, "exifprobe", self.source_folder, os.path.join(self.package_folder, "bin"))
      copy(self, "exifgrep",  self.source_folder, os.path.join(self.package_folder, "bin"))
  ```

## 验证（verification）

- 修复前：`conan-verify G2` FAIL，`conan-create.log` 中
  `TypeError: copy() got an unexpected keyword argument 'keep_perm'`。
- 修复后：`conan-verify G2` PASS（exifprobe/2.0.1@ohpcd/stable 构建+打包成功），
  `bin/exifprobe` 保持可执行位，test_package 消费者 6/6 通过。

## 适用边界 / 反例

- **适用**：任何使用 `conan.tools.files.copy` 打包可执行文件、脚本、带模式权限
  文件的 Conan 2 配方；纯 Makefile CLI 工具（exifprobe/abduco 族）尤其常见。
- **不适用**：不需要在 package() 拷贝文件的配方；使用 `Autotools.install()` /
  `CMake.install()` 的配方（不经过 `copy()`，无此问题）。
- **反例提醒**：不要在 `copy()` 后又逐文件 `os.chmod` 强行设位——源文件权限
  已保留，多余 chmod 只会降低配方可读性。

## 限制与恢复条件

- 若确需"强制可执行"（如源文件本身无 x 位但产物应为可执行），应在构建阶段
  （make install / 源码内）确保产物带 x 位，而不是在 package() 补救。
- 其他 Conan 1 → Conan 2 迁移类 TypeError（如 `settings.os == "Linux"` 未含
  OHOS、`self.conf.get("tools.build:compiler_executables:c")` 子键读取等）
  是同类"API 签名差异"问题，逐一按当前 Conan 2 API 修正即可。
