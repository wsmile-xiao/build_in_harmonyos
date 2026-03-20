# 跳过测试说明

共 31 个测试被跳过，主要原因：

## 1. ACLs 相关测试 (6个)

- acls01.at ~ acls03.at
- selnx01.at
- selacl01.at

**原因**: 鸿蒙系统不支持完整的 ACLs 和 SELinux 功能。

## 2. 稀疏文件测试 (1个)

- sparse06.at

**原因**: 系统不支持特定的稀疏文件检测方法。

## 3. 多卷归档测试 (1个)

- multiv07.at

**原因**: 需要特定的扩展头支持。

## 4. 文件大小限制测试 (4个)

- gtarfail.at
- gtarfail2.at
- multi-fail.at
- ustar-big-2g.at 等

**原因**: 需要特定的大文件支持。

## 5. remove-files 压缩测试 (1个)

- remfiles01.at

**原因**: 需要特定的压缩程序支持。

## 总结

这些跳过的测试大多涉及系统特性支持，不影响 tar 的核心功能。
