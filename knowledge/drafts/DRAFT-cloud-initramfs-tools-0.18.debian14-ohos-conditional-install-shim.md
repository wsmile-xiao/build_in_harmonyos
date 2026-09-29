# DRAFT-cloud-initramfs-tools-0.18.debian14-ohos-conditional-install-shim

> 草稿知识项 — OHOS install(1) 可见性随 PATH 组成变化，构建期条件化 busybox install shim
> 来源：cloud-initramfs-tools 0.18.debian14 适配（feat/cloud-initramfs-tools-0.18.debian14，2026-09-26）
> 同 stem 配对：`knowledge/drafts/DRAFT-cloud-initramfs-tools-0.18.debian14-ohos-conditional-install-shim.kv`

## 问题（现象 / error_signature）

同一份 recipe，在不同终端里结论相反：

```
# 裁剪 PATH 的交互 shell（PATH 不含 /system/bin）
$ command -v install ; echo rc=$?
rc=1
$ make install DESTDIR=/tmp/staging
/bin/sh: install: inaccessible or not found
make: *** [Makefile:10: install] Error 127        # rc=2

# 默认进程 PATH（首段 /system/bin）
$ python3 -c "import shutil; print(shutil.which('install'))"
/system/bin/install
```

## 根因（root_cause）

1. OHOS 用户态由 Toybox 提供，`install(1)` 实际由 **`/system/bin`** 提供；该目录**对普通用户不可 `ls`**，
   只有在 PATH 查找命中时可执行，因此 `ls /system/bin/install` → `Permission denied`，
   但 `shutil.which('install')` 可命中。
2. **进程默认 PATH 首段就是 `/system/bin`**（实测 agent 进程 PATH：
   `/system/bin:/usr/bin:/bin:…`），所以多数构建环境能解析 `install`；
3. 但**交互 shell / 受限环境常把 `/system/bin` 裁掉**，此时上游 `Makefile` 第一条 `install` 语句
   即报 `inaccessible or not found`，并以 `Error 127` 中断整个 `make install`。
4. 结论：这是 **PATH 组成差异**，不是源码缺陷，也不是「OHOS 没有 install」这样的一刀切结论。

## 可复用方案（rec_approach: conditional-busybox-install-shim-in-build）

在 `conanfile.py` 的 `build()` 中**条件化**生成 shim：

```python
def _install_shim_dir(self):
    if shutil.which("install"):          # 平台已提供 → 绝不启用（保持行为不变）
        return None
    busybox = shutil.which("busybox") or next(
        (p for p in ("/usr/bin/busybox", "/bin/busybox",
                     "/data/service/hnp/bin/busybox") if os.path.isfile(p)), None)
    if busybox is None:
        raise ConanException("既无 install(1) 也无 busybox —— 无法执行 make install")
    shim_dir = os.path.join(self.build_folder, "install-shim")
    os.makedirs(shim_dir, exist_ok=True)
    shim = os.path.join(shim_dir, "install")
    if not os.path.lexists(shim):        # HMDFS 软链不可覆盖 → 只建一次
        os.symlink(busybox, shim)
    return shim_dir

def build(self):
    ...
    shim = self._install_shim_dir()
    prefix = f'export PATH="{shim}:$PATH"; ' if shim else ""
    self.run(f"{prefix}make install DESTDIR={staging}", cwd=self.source_folder)
```

要点：
- **条件化**（`shutil.which` 守卫）：平台已有 install(1) 时不改任何行为；
- **只影响本 recipe 的这一次调用**（shim 目录在 build_folder，PATH 前置仅作用于该 `self.run`）；
- 使用前应验证上游 Makefile 实际用到的全部 `install` 形式，busybox applet 实测支持
  `-m 644 <src> <dir>`、`-m 755 -d <dir>`、`-m 644 -t <dir> <src>`、`-m 755 <src> <dst>`。

## 适用条件

- OHOS 上以 Makefile/autotools 打包、依赖 `install(1)` 安装文件的软件；
- 构建进程 PATH 可能不含 `/system/bin` 的环境（交互终端、部分 CI 包装、容器化 worker）。

## 反例（不适用场景）

- 平台已提供可用 `install(1)`（`shutil.which` 命中）→ 不应启用，避免遮蔽系统工具；
- CMake/Meson 项目（安装不经 PATH 上的 `install`）；
- 平台既无 install 也无 busybox → 应显式报错，而不是伪造产物。

## 验证证据（真实命令 + 结果）

- 复现（裁剪 PATH）：`make install DESTDIR=<staging>` → `/bin/sh: install: inaccessible or not found`，
  `make: *** [Makefile:10: install] Error 127`，rc=2（日志 `10-make-install-first.log`）。
- 修复后：同一命令前置 shim → **rc=0**，落地 **14 个文件**（日志 `14-make-install-fixed.log`、
  清单 `14a-staging-tree.txt`）。
- 机制复核（test_package 用例 C4/PASS）：在「PATH 仅含 `install`→busybox」的场景下，
  四种上游 `install` 调用形式全部成功，产物与源**字节一致**、可执行位正确；
  并观测到默认 PATH 下 `install` 解析为 `/system/bin/install`（条件 shim 不启用）。
- 端到端：`conan create` rc=0，test_package 16/16 通过。

## 限制与恢复条件

- shim 依赖平台存在 busybox；不存在时显式抛错（不静默降级）。
- 若未来 OHOS 统一把 `/system/bin` 纳入所有构建环境 PATH，`shutil.which` 守卫会使本 shim
  自动失效，无需回退改动。
- 与既有知识的关系：错误面与 E098（install 缺失需替代）、E188（toybox install 选项差异）
  相关；本条补充的是**PATH 组成视角**与**条件化构建期 shim 的落地方式**。
