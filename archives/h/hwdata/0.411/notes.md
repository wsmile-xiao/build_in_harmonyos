# hwdata 0.411 — 适配记录（HarmonyOS PC / arm64）

## 为什么需要这个包（不是重复适配 hwdata-usb）

R37 查重时**必须同时搜变体名**——本任务实测踩过这个坑：只搜 `hwdata` 会得出
"仓内全无"的错误结论，实际仓内已有 `hwdata-usb/0.409`。

| 包名 | 打包范围 | 谁在用 |
|---|---|---|
| `hwdata-usb/0.409`（既有，已发布 ohpcd）| **仅** `usb.ids` | `gusb/0.4.9` 自测 |
| **`hwdata/0.411`（本包）** | 上游完整 IDFILES + `hwdata.pc` | `libdisplay-info`（需 `pnp.ids`）等 |

两者同 upstream 仓库（vcrhonek/hwdata），但**包名与打包范围不同**，不是重复适配。

### 它替代的手工绕过

`libdisplay-info/0.3.0` 的配方里记着一段绕过（因其时无 hwdata 包）：

```python
# 从 raw.githubusercontent.com 下载 pnp.ids 到 generators/hwdata，
# 再自造一个 hwdata.pc（Version 硬写 0.366）塞进 generators 目录
```

本包发布后，该场景只需 `self.requires("hwdata/0.411")`，meson 的
`dependency('hwdata')` 即可通过包内 `.pc` 解析——无需联网下载、无需手写 `.pc`。

## 适配路径

纯数据包，**无需编译**（`data_only: true`）：

1. `source()` 取官方 tag `v0.411` tarball（sha256 已校验）；
2. `build()` 跑上游 `make check` 中**可复现的部分**（见下）；
3. `package()` 把 IDFILES 装到 `share/hwdata/`，并生成上游同款 `hwdata.pc`；
4. `package_id()` 清空（数据与架构无关，避免多份无意义二进制包）。

## 打包契约（关键）

上游 `make install` 的实际布局：

```
$(datadir)/hwdata/{pci.ids,usb.ids,oui.txt,iab.txt,pnp.ids}
$(datadir)/pkgconfig/hwdata.pc
```

本包按同样布局落位（`share/` 前缀）。**被下游真正消费的是 `.pc` 里的
`pkgdatadir`** —— meson 的 `dependency('hwdata')` 正是用它定位 `pnp.ids`：

```
prefix=<package_folder>
datadir=${prefix}/share
pkgdatadir=<package_folder>/share/hwdata      ← meson 据此找 pnp.ids

Name: hwdata
Description: Hardware identification and configuration data
Version: 0.411
URL: https://github.com/vcrhonek/hwdata
```

> **关于 `${pc_sysrootdir}`（实测结论，非推断）**：上游 `hwdata.pc.in` 的
> `pkgdatadir` 带 `${pc_sysrootdir}` 前缀——该变量是 pkg-config 内置的
> sysroot 前缀，由环境变量 `PKG_CONFIG_SYSROOT_DIR` 控制（默认 `/`）。
> 本包生成 `.pc` 时**不**采用它，直接写包内绝对路径。两种写法的实测对比：
>
> | 消费方环境 | 照抄 `${pc_sysrootdir}` | 本包（绝对路径）|
> |---|---|---|
> | 无 `PKG_CONFIG_SYSROOT_DIR`（conan/PkgConfigDeps 场景）| ✅ 可用（解析为 `//…`，双斜杠等价单斜杠）| ✅ 可用 |
> | 设置了 `PKG_CONFIG_SYSROOT_DIR`（交叉编译工具链常见）| ❌ **定位失败**（解析为 `${SYSROOT}/…`）| ✅ 可用 |
>
> 即：照抄并**非在 conan 场景下必现失败**，仅在消费方设置 sysroot 时出问题。
> 本包选择绝对路径，两种场景均正确。
> （另实测确认：conan 的 `PkgConfigDeps` 既不生成 `${pc_sysrootdir}`、也不设置
> `PKG_CONFIG_SYSROOT_DIR`，故 conan 消费链路上该风险不触发。）

## 上游测试：`make check` 的 6 类步骤逐项处置

上游 `check` 目标（实测清点）：

| # | 步骤 | 依赖 | 本配方处置 |
|---|---|---|---|
| 1 | `lspci -A dump -O dump.name=... -i pci.ids` | pciutils（宿主工具）| ⚠️ 无 lspci → **显式 warning 申报未执行** |
| 2 | `./check-pci-ids.py` | 纯 Python | ✅ **build() 内实跑**，失败即中止 |
| 3 | `./check-usb-ids.sh` | podman（宿主工具）| ⚠️ 无 podman → **显式 warning 申报未执行** |
| 4 | `for f in $(IDFILES); iconv -f UTF-8 $f` | iconv | ✅ **build() 内实跑**（Python 解码校验，5 个文件）|
| 5 | `grep "Date:" pci.ids / usb.ids` | grep | ✅ **build() 内实跑**（校验 Date 头存在）|
| 6 | `tests/`（ids-files / python-hwdata / syntax）| Fedora/RPM 集成环境 | ⚠️ 面向发行版安装环境，非本包范围 |

**未用 skip/xfail 掩盖**：需宿主工具的两项以 `self.output.warning` **显式申报**
（R51 要求写明具体技术原因，而非静默跳过）。

额外增加一条上游没有的检查：`pnp.ids` 逐记录结构校验（`<PNP_ID>\t<Vendor>`，
2557 条，无空字段）——因为这是本包存在的理由，须确保数据真的可用。

## 验证

```bash
# 手动复现上游可复现检查
cd <source> && python3 check-pci-ids.py
for f in pci.ids usb.ids oui.txt iab.txt pnp.ids; do iconv -f UTF-8 $f >/dev/null; done

# 本包构建与消费者验证
conan create archives/h/hwdata/0.411 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

消费者测试（`test_package/test_hwdata.py`）验证：
- 5 个 IDFILES 均存在且非空壳（>1000 字节）；
- `pnp.ids` 逐记录解析通过、>1000 条、含稳定锚点 `AAA` = Avolites Ltd；
- `pci.ids` / `usb.ids` 含 `Date:` 头与真实 vendor 记录（正则）；
- `hwdata.pc` 含 Name/Version/pkgdatadir，且 **pkgdatadir 指向的目录确实含
  `pnp.ids`**（即 libdisplay-info 式消费路径可用）。

## 消费方迁移提示（供后续 PR）

`libdisplay-info` 若要把手工绕过换成正式依赖，需：
1. `self.requires("hwdata/0.411")`；
2. 删除 `_setup_hwdata_env()` 的下载 + 手写 `.pc` 逻辑；
3. 用 `PkgConfigDeps`（或让 meson 走包内 `.pc`）替代 generators 目录里的自造 `.pc`。
