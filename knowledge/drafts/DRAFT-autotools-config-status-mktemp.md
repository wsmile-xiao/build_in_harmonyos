# SKILL: 鸿蒙沙箱下 autotools 库的 config.status mktemp 修复

> 路径 B（贡献创新）——可复用技能
> 主库验证：dpkg/1.23.7 ｜ 辅助验证：commoncpp2/1.8.1、libdebian-installer/0.121

## 相关既有条目（同族，本 skill 的差异化定位）

本技能与既有知识库同族条目**共享同一错误签名与根因族**，但提供
**经三库实测验证的精确增量**，避免重复扩散：

| 既有条目 | 收录状态 | 同族点 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E136** (patch-script) | 正式收录 | `config.status: could not setup config files machinery` + TMPDIR/umask/mktemp 修复 | ①**精确替换点**：必须匹配带引号的完整串 `mktemp -d "./confXXXXXX"`（E136 的 sed 正则方案无法命中无引号/不完整形式——实测踩坑）；②**沙箱可写目录实测路径** `/data/storage/el2/base/cache`（/tmp 只读 + $HOME/.ci_logs 也拒绝）；③**三库实证**（dpkg/commoncpp2/libdebian-installer） |
| **E167** (patch-script) | 正式收录 | `subs1.awk Permission denied` + confXXXXXX + ac_tmp 临时目录 | 同 E136 增量——本 skill 聚焦 configure 侧 mktemp 模板替换（E167 聚焦 config.status 的 ac_tmp） |
| **E060** (use-tmpfs-workaround) | 正式收录 | `mktemp failed / confXXXXXX cannot create / subs1.awk Permission denied` | 本 skill 走"改脚本 + TMPDIR"而非"换构建位置（tmpfs）"——OHOS 沙箱无 tmpfs 可换，实测仅脚本修复可行 |
| **E223**（草稿）| 草稿 | HMDFS secure tmp owner/mode/MAC | 本 skill 不涉及安全扩展——仅在沙箱构建可用性层面 |

> 定位：本 skill 是 E136/E167/E060 同族的**精确化、实测化增量**（替换点准确 + 路径实测 + 三库验证），
> 非重复条目；申报路径 B 时以此差异化定位为准。

## 适用场景

鸿蒙 PC（OHOS）沙箱环境下适配任何 **autotools（configure + config.status）构建的库**，
当出现以下错误时适用：

```
./config.status: line 882: ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

或 configure 阶段的 mktemp 失败：

```
mktemp: Failed to create file /tmp/bitlbee-configure.XXXXXX: Read-only file system
```

## 问题根因

1. **鸿蒙沙箱 /tmp 只读**——`mktemp -d "./confXXXXXX"` 的临时目录创建依赖可写位置；
2. **`$HOME/.ci_logs` 写入也 Permission denied**（实测）——仅设置 TMPDIR 到 $HOME 下不够；
3. **autoconf 生成的 configure/config.status 用相对路径 mktemp**（`mktemp -d "./confXXXXXX"`）
   ——在沙箱的当前目录（conan 构建目录）写入被拒。

## 解法（两步骤，缺一不可）

### 步骤 1：TMPDIR 指向沙箱可写目录

```python
# conanfile.py 的 build() 开头
os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
os.makedirs(os.environ["TMPDIR"], exist_ok=True)
```

> `/data/storage/el2/base/cache` 实测可写（/tmp 只读、$HOME/.ci_logs 也 Permission denied）。

### 步骤 2：configure 的 mktemp 模板改 `${TMPDIR}`（准确替换点）

```python
# configure 执行前打补丁（configure 是 autoconf 生成的脚本）
cfg = os.path.join(self.source_folder, "configure")
if os.path.isfile(cfg):
    src = open(cfg).read()
    if "TMPDIR/confXXXXXX" not in src:
        # 关键：必须是带引号的完整串 "./confXXXXXX"
        src = src.replace(
            'mktemp -d "./confXXXXXX"',
            'mktemp -d "${TMPDIR}/confXXXXXX"')
        open(cfg, "w").write(src)
```

> **踩坑记录**：`mktemp -d ./confXXXXXX`（无引号）或 `confXXXXXX`（不完整）
> 的替换都不命中——autoconf 生成的 configure 里是 **`mktemp -d "./confXXXXXX"`**
> （带引号）——必须精确匹配这一形式。

## 使用说明

1. 在 `build()` 最开头设置 `os.environ["TMPDIR"] = "/data/storage/el2/base/cache"`；
2. 在 `./configure` 执行**之前**对 source 目录的 `configure` 脚本做 mktemp 模板替换；
3. 重新跑 `conan create` 验证——`config.status` 应完整执行（creating xxx / executing libtool commands）。

## 实战案例（三库验证）

| 库 | 角色 | 结果 |
|----|------|------|
| **dpkg/1.23.7** | 主库（最初受阻点——用户曾选 B 保留） | ✅ 解决——`config.status` 完整执行——Package created |
| **commoncpp2/1.8.1** | 辅助（新适配——同问题） | ✅ 解决——configure 通过——构建全过——R34 OK |
| **libdebian-installer/0.121** | 辅助（同问题） | ✅ 解决——`config.status` 执行——Package created + R34 OK |

## 相关已知问题（同族）

- configure 的 `cannot guess build type`（旧版 config.guess/config.sub 不识别 ohos）：
  需另打 config.guess/config.sub 补丁（`linux-ohos*`）——见 commoncpp2 适配记录。
- `make install` 无 install 目标：package() 改手动 copy 二进制/库（dpkg、libdebian-installer 均实测）。
