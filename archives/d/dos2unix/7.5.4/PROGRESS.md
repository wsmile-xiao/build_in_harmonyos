# PROGRESS.md - dos2unix 7.5.4

## 当前状态

- **阶段**: Phase 4 完成
- **更新时间**: 2026-04-02 18:55
- **源码路径**: /storage/Users/currentUser/tmp/builds/dos2unix-7.5.4
- **状态**: 编译成功，归档完成

## 编译问题记录

### E1: ENABLE_NLS 导致链接失败 (libintl_gettext undefined)

- **阶段**: link
- **错误信息**: `ld.lld: error: undefined symbol: libintl_gettext`
- **根因分析**: Makefile 默认 `ENABLE_NLS = 1`，但 HarmonyOS 没有 libintl。注意 `ENABLE_NLS = 0` 也会被 `ifdef` 视为 true（"0" 非空），必须设为空值
- **解决方案**: `ENABLE_NLS =` （空值）
- **知识库更新**: 无（软件特定配置）
- **跨软件通用性评估**: L3 - 仅本软件

### E2: ln -sf 在构建目录受限

- **阶段**: install
- **错误信息**: `ln: cannot create symbolic link: Permission denied`
- **根因分析**: HarmonyOS SELinux 限制 `ln -sf` 在部分目录（$HOME/tmp/builds/）的使用。测试框架中 mac2unix/unix2mac 是软链接到 dos2unix/unix2dos，导致 24 个测试失败
- **解决方案**: Makefile 中 `LINK = ln -s`（去掉 -f 参数）
- **知识库更新**: knowledge/environment.md（L1: HarmonyOS symlink 限制）
- **跨软件通用性评估**: L1 - 任何使用 ln -sf 的 Makefile 项目都可能遇到

## 源码修改清单

| 文件 | 修改原因 | 补丁状态 |
|------|---------|---------|
| Makefile (ENABLE_NLS) | 禁用 NLS，无 libintl | ✅ 0001 |
| Makefile (LINK) | ln -sf → ln -s 兼容 HarmonyOS | ✅ 0001 |

## 待办

- [x] Phase 0: 源码获取
- [x] Phase 1.5: 档案骨架
- [x] Phase 2: 环境检查
- [x] Phase 3: 编译执行
- [x] Phase 4: 验证与归档

---

## 编译结束

- **结束时间**: 2026-04-02 18:54:12
- **最终状态**: ✅ 编译成功
- **关闭操作**: 由 close-archive.sh 执行

