# draft-hamlib-4.7.1-packagebuilder-relative-project-dir-tar-fail

## 症状

`PackageBuilder`（10 步打包流水线）Step 9 报 `打包失败`，但 Step 1–8 全部成功：

```
  ✅   修复 20 个文件权限
  ℹ️ Step 9/9: 打包 tar.gz...
  ❌   打包失败: archives/h/hamlib/4.7.1/packaging/hamlib-4.7.1-ohos-aarch64.tar.gz
  ✅ ✅ 打包完成: hamlib 4.7.1        <-- 仍写 .packaged 标记，掩盖失败
```

tar 的真实 stderr（`subprocess.run(..., capture_output=True)` 吞掉了）：

```
tar: archives/h/hamlib/4.7.1/packaging/hamlib-4.7.1-ohos-aarch64.tar.gz: No such file or directory
```

## 根因

`step9_tarball()` 用 `subprocess.run(["tar","czf",str(tar_gz), ...], cwd=self.pkgdir)`，
而 `tar_gz = self.packaging_dir / name` 是**相对路径**（当调用方传
`--project-dir .` 或 `find_project_dir()` 返回相对路径时）。
cwd 已切到 `.../packaging/pkg-<name>/`，相对输出路径被解析成
`.../packaging/pkg-<name>/archives/h/...`（不存在）→ tar 失败。

## 修复

1. 调用方：`--project-dir "$(pwd)"`（绝对路径）即可绕过；实测立即成功
   （`hamlib-4.7.1-ohos-aarch64.tar.gz: 78880KB`）。
2. 框架侧建议：`PackageBuilder.__init__` 中 `self.pdir = Path(pdir or ...).resolve()`，
   或 `step9_tarball()` 用 `tar_gz.resolve()` / `cwd` 与输出路径都取绝对路径。
3. 顺带：`step9` 失败仍写 `.packaged` 并打印 `✅ 打包完成`，会让上游
   `finish`/`submit` 的 `packaging_present` 检查与事实不一致（本该失败却标记完成）。
   建议 tar 返回码非 0 时不写 `.packaged`，并把 stderr 打到日志。

## 验证

```bash
# 复现（相对 project-dir）
python3 -c "import sys;sys.path.insert(0,'scripts');
from ohc.package_builder import package_cli; package_cli(['hamlib','4.7.1','--project-dir','.'])"
#   ❌ 打包失败: archives/.../hamlib-4.7.1-ohos-aarch64.tar.gz

# 修复（绝对 project-dir）
python3 -c "...package_cli(['hamlib','4.7.1','--project-dir','/abs/path/to/repo'])"
#   ✅ hamlib-4.7.1-ohos-aarch64.tar.gz: 78880KB
#   ✅ hamlib-4.7.1-ohos-aarch64-debug.tar.gz: 36335035B
```

## 相关

- 触发实例：hamlib/4.7.1（2026-09-28），`ohc-run.py submit` 的
  `packaging_present` 自检项要求 `packaging/*.tar.gz` 存在。
