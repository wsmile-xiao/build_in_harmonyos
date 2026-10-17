# OHOS 缺独立 `install(1)`：用 busybox applet 建 PATH shim 通过安装步骤（草稿，通用）

> **Status**: Draft（待审核 promote）｜ **severity**: `2`（medium）｜ **category**: `platform|toolchain|build-system|install`
> **对应 kv**: `knowledge/drafts/chkboot-1.3-ohos-install-shim-for-make-install.kv`
> **来源实例**: chkboot 1.3（纯 shell 包）｜ **方案通用性**: 与软件名无关，适用于**任何**调用 `install(1)` 的安装路径

---

## 一、问题（错误特征）

```
$ make install DESTDIR=$PWD/staging
install -D -m644 chkboot.conf /…/staging/etc/default/chkboot.conf
make: install: No such file or directory
make: *** [Makefile:10: install] Error 127
```

同族表现：`install: command not found`、`/usr/bin/install: not found`、`*** [Makefile:N: install] Error 127`。

## 二、根因

OHOS 用户态**没有**把 GNU coreutils 的 `install(1)` 暴露为独立命令，但平台自带 busybox 是**多调用二进制**，其 applet 表**包含 install**：

```
$ command -v install ; echo rc=$?
rc=1                                                   # 无 install 命令
$ /data/service/hnp/bin/busybox --list | grep -x install
install                                                # applet 存在
$ /data/service/hnp/bin/busybox install --help
Usage: install [-cdDsp] [-o USER] [-g GRP] [-m MODE] [-t DIR] [SOURCE]... DEST
```

因此脚本在“命令解析”阶段就失败（不是参数不兼容、也不是权限问题）。注意与 **E188**（toybox install 选项不兼容）区分：本机 PATH 中根本没有 install 命令。

## 三、使用说明（HOW-TO）

1. **探测**：`command -v install` → 空则走本方案；非空（常规 Linux）无需处理。
2. **定位 busybox**：`command -v busybox` → 空则依次探测 `/usr/bin/busybox`、`/bin/busybox`，最后才用平台私有路径 `/data/service/hnp/bin/busybox`（私有路径只作兜底，不写死为首选）。
3. **建 shim**：`mkdir -p .shim && ln -s <busybox> .shim/install`（busybox 按 `argv[0]` 分派 applet，链接名即子命令名）。
4. **注入 PATH 后执行原命令**：`export PATH="$PWD/.shim:$PATH"; make install DESTDIR=<staging>`。
   - Conan 场景：`ConanFile.run(env=…)` 只接受环境文件名列表（传 dict 会 `assert isinstance(env, list)` 失败）→ 在命令串里 `export PATH=…; ` 前缀，或把 shim 目录并入 profile `[buildenv]` 的 PATH。
   - shim 放在 **build_folder** 内，随构建目录清理，不碰源码树。
5. **验证**：安装命令 rc=0 **且**产物清单与上游声明逐项一致（不要只看 rc）。

## 四、适用范围

✅ **适用**
- 上游 `Makefile` 的 `install:` 目标、autotools 生成的 install 规则、安装脚本里的 `install -D -m755 …`
- 纯脚本包与 C/C++ 包均适用（与构建系统无关，只看是否调用 `install(1)`）
- 需要 `-D`（自动建父目录）与 `-m`（设权限）语义的安装

❌ **不适用 / 需换方案**
- 平台连 busybox 都没有 → 用 **E174** 的 manual-install（`cp`+`chmod` 复刻布局）或打 Makefile 补丁
- 用到 busybox 未实现的选项（`-Z`/`--context`/`--preserve-context`）→ 退化为 manual-install（口径见 E188）
- 上游安装需要写 `/etc` 等只读系统目录 → 属于另一类问题（见本仓只读系统路径类条目），本方案不解决

## 五、输入 / 输出定义

| 项 | 定义 |
|---|---|
| **输入·平台能力** | `command -v install`（空/非空）；busybox 可执行路径及其 applet 表（须含 install） |
| **输入·构建** | 上游安装命令（如 `make install DESTDIR=<staging>`）、staging 目标目录 |
| **输入·recipe** | Conan `build()` 的 `build_folder`（承载 shim） |
| **输出** | ① PATH 中可见的 `install`（→ busybox 符号链接）；② 上游安装命令 rc=0；③ staging/package 内文件清单与上游声明**逐项一致**，权限语义同 install(1)（HMDFS 上 `-m` 落盘可能为 660，属 E046 平台限制） |
| **失败边界** | 既无 install 也无 busybox → **显式报错停止**（不得跳过安装继续打包，否则产生空包）；安装 rc≠0 → 构建失败，禁止 `\|\| true` 吞错 |

## 六、示例

**示例 1 — 通用（任意 Makefile 包）**
```bash
command -v install || { mkdir -p .shim && ln -s "$(command -v busybox || echo /data/service/hnp/bin/busybox)" .shim/install; }
export PATH="$PWD/.shim:$PATH"
make install DESTDIR=$PWD/staging        # install -D -m755 tool …/staging/usr/bin/tool → rc=0
```

**示例 2 — Conan recipe（通用写法）**
```python
def _install_shim_dir(self):
    if shutil.which("install"):
        return None                                     # 常规 Linux
    busybox = shutil.which("busybox")
    if busybox is None:
        for c in ("/usr/bin/busybox", "/bin/busybox", "/data/service/hnp/bin/busybox"):
            if os.path.isfile(c):
                busybox = c; break
    if busybox is None:
        raise ConanException("neither install(1) nor busybox available")
    shim = os.path.join(self.build_folder, "install-shim"); os.makedirs(shim, exist_ok=True)
    os.symlink(busybox, os.path.join(shim, "install"))
    return shim
# build(): self.run(f'export PATH="{shim}:$PATH"; make install DESTDIR={staging}', cwd=self.source_folder)
```

**示例 3 — 本次来源实例（chkboot 1.3）**
- 现象：`make install` → `make: install: No such file or directory` / `Error 127`（命令 rc=127）
- 处理后：`install` / `install-systemd` / `install-pacman` / `install-initcpio` **全 rc=0**，staging 产出 10 个文件，与 `Makefile:9-25` 声明逐项一致
- 证据：`chkboot-1.3-evidence/14b-make-install-adapted.log`、`13-install-shim-probe.log`

## 七、禁止做法

- ❌ `apt-get/yum/opkg install coreutils` —— OHOS 无这些包管理器（E174 forbid 条款）
- ❌ 安装步骤 `|| true` 吞错 —— 会产生“空包但构建成功”的假绿
- ❌ 把 busybox 私有绝对路径写死为首选 —— 先用 PATH 与通用路径，私有路径只兜底
