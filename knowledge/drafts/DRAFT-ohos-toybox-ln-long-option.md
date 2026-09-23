# DRAFT-ohos-toybox-ln-long-option — OHOS toybox ln 不识别 GNU 长选项，构建系统安装脚本建符号链接失败

> 对应结构化数据：`knowledge/drafts/DRAFT-ohos-toybox-ln-long-option.kv`
> Contributor: A7F3 / Status: DRAFT / Updated: 2026-09-05 / Severity: 2
> 触发事件：kmod/34 HarmonyOS PC 适配（PR #8333）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---|---|---|---|
| E010 | 正式 | toybox sed/expr 对复杂脚本支持不完整 → 安装 GNU coreutils 替换 toybox | 本 skill 是 **ln 的长选项语法**（--symbolic/--force/--relative），修法**不换工具链**：脚本容错 + python os.symlink，无需引入 GNU coreutils |
| E098 | 正式 | toybox **不含 install 命令**（命令缺失）→ 用 cp/mkdir 替代 | 本 skill 是 **ln 命令存在但不认 GNU 长选项**（语法兼容面），非命令缺失 |
| E018 | 正式 | SELinux 策略限制软链接创建（ln -sf 报错/Permission denied）→ wrapper script | 本 skill 报 **"Unknown option"（语法错误）非权限问题**，python os.symlink 在 conan 包目录可直接创建成功 |
| E080 | 正式 | HMDFS 文件系统不支持 os.symlink（venv lib64）→ try/except 降级 | 本 skill 的 os.symlink 用于 **conan 包目录（可写、实测成功）**，问题是 meson 脚本的 ln 长选项，非文件系统能力 |
| E043 | 正式 | /bin/sh 为 toybox ash，不支持 BASH_SOURCE 等 bashism | 命令选项语法（ln），与 shell 变量无关 |
| E037/E049 | 正式 | shebang 解释器解析失败 / 硬编码路径 | 排除项：shebang 与命令选项无关 |

## Scope（何时用）

- **触发特征**：`conan create` 的 package()/meson install 阶段报
  `ln: Unknown option 'symbolic' (see "ln --help")` 或 `--relative`；构建产物含**多路调用工具**（multi-call binary，靠符号链接分发：kmod/depmod、busybox、toybox 等）；安装脚本由构建系统生成且使用 GNU 长选项。
- **典型实例**：kmod 34（libkmod + kmod/depmod/modinfo/insmod/rmmod/lsmod/modprobe），
  `meson.add_install_script('sh','-c', 'ln --symbolic --force --relative ...')` 在 OHOS 直接失败。

## Symptom（真实报错日志）

```
FAILED: install script '/system/bin/sh -c ln --symbolic --force --relative "$DESTDIR/bin/kmod" "$DESTDIR/bin/depmod"' failed with exit code 1.
ln: Unknown option 'symbolic' (see "ln --help")
```

复现命令（OHOS 本机）：

```sh
ln --symbolic --force --relative a b   # → ln: Unknown option 'symbolic' (see "ln --help")
```

## Root Cause

OHOS 用户空间基础命令由 **toybox** 提供（`/bin/sh` 为 toybox ash、`ln` 为 toybox ln），
toybox `ln` 只支持短选项（`-s`/`-f`），**不识别 GNU coreutils 长选项**
`--symbolic`/`--force`/`--relative`。meson/CMake 生成安装脚本时常用 GNU 长选项
（kmod 的 meson.build：`meson.add_install_script('sh','-c', ln --symbolic --force --relative ...)`），
执行即报 `Unknown option` 并退出非零 → meson install 失败 → conan `package()` 失败。

## Recommended Solution（主方案 + 回退）

**主方案（两层，缺一不可）**：

1. **补丁容错**：meson.build 的 ln 安装脚本加 `|| true`（失败不终止 meson install）：

   ```meson
   ln_s = 'ln --symbolic --force --relative "$DESTDIR@0@/kmod" "$DESTDIR@1@" || true'
   ```

2. **配方补齐符号链接**：conanfile.py `package()` 用 python `os.symlink` 创建相对链接（等价 `ln --relative`）：

   ```python
   sbin = os.path.join(self.package_folder, "sbin")
   os.makedirs(sbin, exist_ok=True)
   for tool in ("depmod", "insmod", "lsmod", "modinfo", "modprobe", "rmmod"):
       link = os.path.join(sbin, tool)
       if not os.path.lexists(link):
           os.symlink("../bin/kmod", link)
   ```

⚠️ **禁止只做第 1 步**（只 `|| true` 不补链接）：会静默吞掉失败，包内多路调用符号链接缺失而构建仍"成功"（假成功），下游调用 `command not found`，CI L0k(R38)/运行时才暴露。

**回退方案**：若 HMDFS 上 `os.symlink` 权限受限（E080），改用短选项 `ln -sf` + 相对路径，或用 wrapper script（E018 方案）替代符号链接。

## 单库实证

| 库 | 角色 | 结果 |
|---|---|---|
| kmod/34 | 配方 + 补丁 `0001-musl-compat.patch`（meson.build hunk） | `conan create` exit 0；`sbin/depmod → ../bin/kmod` 相对符号链接存在；test_package R34 PASS |

## 测试覆盖边界

- 声明通过率口径：kmod 上游 testsuite 因需 Linux 内核 kbuild 无法在 OHOS 运行（详见 PR #8333 说明），
  本 skill 的修复以 `conan create` 端到端（CI profile ohos-aarch64）+ test_package R34（1/1 实测）为证据。
- 差异定位表逐条核验：与 E010/E098/E018/E080/E043 均不同符号/问题面，非重复申报。
