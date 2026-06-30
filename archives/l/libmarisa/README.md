# libmarisa (marisa-trie)

静态且空间高效的 Trie 数据结构库，用于文本搜索和自动补全。

## 功能概述

- 提供静态 Trie 实现，空间效率高
- 支持前缀搜索、精确匹配、预测搜索
- 提供命令行工具：marisa-build, marisa-lookup 等

## OHOS 适配要点

1. **autoreconf 必需**：项目只提供 configure.ac，需要运行 `autoreconf -i` 生成 configure 脚本
2. **HMDFS 权限问题**：configure 中的 `umask 077` 导致临时文件无法创建，需改为 `umask 022`
3. **平台识别**：config.guess/config.sub 需添加 HarmonyOS 检测分支

## 依赖关系

- 无外部依赖

## 编译步骤

```bash
autoreconf -i
sed -i 's/umask 077/umask 022/g' configure
./configure --prefix=$DEFAULT_PREFIX
make -j$(nproc)
make check  # 5 tests PASS
make install
```

## 参考资料

- 源码：https://github.com/s-yata/marisa-trie