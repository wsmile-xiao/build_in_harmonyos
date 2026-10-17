# DRAFT: HMDFS 大小写不敏感导致 tarball 根级 PATCHES 文件与配方 patches/ 目录冲突

- **id**: DRAFT-liboggz-1.1.1-hmdfs-patches-collision
- **软件**: liboggz 1.1.1（任何 tarball 根含大写 `PATCHES` 且配方导出 `patches/` 目录的 Conan 包）
- **门禁**: conan create `source()` 解压阶段
- **状态**: UNMATCHED — 待人工/AI 审核提升为 E 条目
- **时间**: 2026-09-08
- **来源事件**: liboggz 1.1.1 OHOS 适配 `conan create` 在 `source()` 报 `IsADirectoryError: [Errno 21] Is a directory: './PATCHES'`

## 问题

HarmonyOS 设备文件系统 **HMDFS 大小写不敏感**。上游 tarball（如 liboggz 1.1.1，2009 年 Xiph 发布）
根级存在名为 `PATCHES` 的普通文件（上游补丁说明，611 字节，非构建必需）。Conan 配方通过
`export_conandata_patches` 把 `patches/` 目录导出进源码目录。`conan get(strip_root=True)` 解压时
尝试创建 `PATCHES` 文件，与已存在的 `patches/` 目录在大小写不敏感 FS 上视为同名冲突，
抛出 `IsADirectoryError: [Errno 21] Is a directory: './PATCHES'`，`conan create` 在 `source()` 阶段失败。

## 根因

1. HMDFS 大小写不敏感是平台硬约束（与 E193/E416/E470 同属 HMDFS 大小写语义坑，触发点不同）。
2. Conan `export_conandata_patches` 自动导出 `patches/` 目录到源码/导出目录。
3. tarball 根级 `PATCHES` 文件（大写）与 `patches/` 目录（小写）在大小写不敏感 FS 上同名冲突。

## 方案

在配方 `source()` 的 `get()` 调用中通过 `excludes` 参数排除 tarball 根级 `PATCHES` 文件：

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True, excludes=["*PATCHES"])
```

`PATCHES` 是上游补丁说明文件（非构建必需），排除后不影响构建与测试。

### 备选方案

- 改名导出补丁目录并在 conandata.yml 同步 `patch_file` 路径（需保留 PATCHES 文件时）。
- 解压后删除 PATCHES 文件（post-extract 处理清单）。

## 验证

- `conan create`（ohos-aarch64 profile）`source()` 通过，G2 conan create 干净构建 PASS。
- 上游 `make check` 23/23 通过，test_package 消费者测试 1/1 通过。
- 复现手段：在 HMDFS 上 `cp` 同名大小写文件即报 `cp: 'ABC.txt' is 'abc.txt'`（大小写不敏感确认）。

## 适用边界

- 仅作用于 HMDFS/大小写不敏感文件系统上的 Conan 构建。
- tarball 根级存在大写 `PATCHES`（或与导出目录大小写同名的根级文件）且配方声明 `patches/` 的包。
- xiph/GNU 系老 autotools 项目（liboggz、libogg 系）常见根级 PATCHES 说明文件，跨库可复用。

## 反例与限制

- 若上游根级文件是构建必需（如 config.guess/config.sub 改名方案），不得直接排除，需保留并改名导出目录。
- `excludes` 匹配的是 tarball 成员名（如 `liboggz-1.1.1/PATCHES`），用 `*PATCHES` 通配覆盖。
- 不在大小写不敏感 FS 上构建时无此问题，补丁仍安全（excludes 仅为幂等过滤）。

## 关联条目

- E193：HMDFS 大小写不敏感致测试失败（不同触发点）
- E416：大小写不敏感 FS 双 case 目录共存（slug 冲突）
- E470：NotADirectoryError 构建目录冲突（Bazel BUILD 文件）
