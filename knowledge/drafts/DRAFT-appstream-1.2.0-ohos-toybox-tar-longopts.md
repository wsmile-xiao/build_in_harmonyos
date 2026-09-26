# DRAFT-appstream-1.2.0-ohos-toybox-tar-longopts — OHOS toybox tar 不支持 GNU 长选项（--no-xattrs/--no-acls）

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build / tooling / portability
> **Audience**: 在 OHOS（toybox 工具集）上运行 tar 子进程且传 GNU 长选项的库

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R03）：as_utils_extract_tarball 用
  `tar -x --no-same-owner --no-same-permissions --no-xattrs --no-acls` 提取 zstd tarball。

## 症状（symptom）

```
tar: Unknown option 'no-xattrs' (see "tar --help")   （toybox 0.8.12）
```

toybox tar 仅支持 `--no-same-owner/--no-same-permissions` 等子集选项；
未知长选项直接报错退出（非忽略），tarball 提取失败。

## 机制（root cause）

上游为防 setuid/ACL/xattr 恢复传入多个 GNU tar 长选项；toybox 是精简实现，
不支持 `--no-xattrs`/`--no-acls`。child_setup 已设安全 umask、且保留
--no-same-owner/--no-same-permissions 时，移除不支持的选项不损失安全语义。

## 修复（fix）

0004-tar-no-xattrs-compat.patch：移除 `--no-xattrs/--no-acls`（toybox 本就不恢复
xattr/ACL；安全 umask + --no-same-owner/--no-same-permissions 保留）。

## 验证（verification）

- as-test_basic（含 test_utils_untar）27/27 PASS，rc=0
- `tar --help` 实测不支持 no-xattrs/no-acls；-x --no-same-owner/-C 解压成功。

## 适用边界 / 反例

- 适用：toybox/busybox 类 tar 平台；数组式子进程调用长选项的提取器；
- 反例：GNU tar 平台无需移除；确需防 xattr 恢复且 tar 支持时保留。

## 关系

- 查重：grep "no-xattrs|toybox|--no-same-owner" 无真实命中
  （E010/E043/E076/E098/E106 为 sed/BASH_SOURCE/fstat/install/SIGPIPE，无关）。
- similar_to: []；caused_by: []；prerequisite_of: []；conflicts_with: []

## 证据

- 补丁：archives/a/appstream/1.2.0/patches/0004-tar-no-xattrs-compat.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 7
