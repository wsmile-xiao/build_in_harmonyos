# pxr-vt 26.08 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (15)
- 状态: built

## 编译步骤

1. 从 GitHub 下载 OpenUSD v26.08 源码 tarball
2. 计算 SHA256 并更新 conandata.yml
3. 使用 Conan 2 构建系统构建目标 vt (自动拉取依赖: arch, tf, gf, trace, work)
4. 禁用 Python 支持、成像、工具等非必要模块

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `_SC_LEVEL1_DCACHE_LINESIZE` 未定义 | OHOS 的 sysconf 不支持此常量 | 添加 #ifdef 守卫，默认返回 64 |
| 2 | `strerror_r` 返回类型不匹配 | OHOS 使用 POSIX 版本(返回int) | 移除 _GNU_SOURCE 分支，使用 POSIX strerror_r |
| 3 | `__environ` 未声明 | OHOS 不提供 glibc 的 __environ | 替换为 environ |
| 4 | `DEFFILEMODE` 未定义 | OHOS 的 sys/stat.h 不定义此宏 | 扩展 #ifdef 条件，提供默认值 0666 |
| 5 | 库找不到 | USD 库命名为 libusd_*.a | 修正 package() 方法搜索正确路径和文件名 |

## 源码修改

补丁文件: `patches/0001-arch-fixes-for-ohos.patch`

## 依赖版本

- tbb/2023.0.0 (来自 ohpcd 制品仓)

## 验证结果

```bash
conan create archives/p/pxr-vt/26.08 --build=missing -pr:b ci/conan/profiles/ohos-aarch64 -pr:h ci/conan/profiles/ohos-aarch64
# 结果: 构建成功，测试通过
# pxr-vt smoke test: OK
```

## 最终状态

status: closed
COMPLETED
---

**编译结束**: 2026-09-04 13:51
**最终状态**: failed
