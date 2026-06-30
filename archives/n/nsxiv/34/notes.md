# nsxiv 34 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
make PREFIX=$DEFAULT_PREFIX HAVE_INOTIFY=0
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | inotify 不可用 | OHOS 内核不提供 inotify API | 设置 HAVE_INOTIFY=0 禁用自动重载 |
| 2 | PREFIX 默认 /usr/local | OHOS 安装路径不同 | 修改 config.mk 设置 PREFIX=$DEFAULT_PREFIX |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.mk | 修改 PREFIX 路径，禁用 HAVE_INOTIFY |
| configure | 平台适配 |

---

**编译结束**: 2026-06-01
**最终状态**: built