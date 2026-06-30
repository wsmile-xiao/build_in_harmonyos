# libquvi-scripts 0.9.20131130 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码（从 SourceForge）
2. 配置缓存：预缓存 `am_cv_prog_tar_ustar=pax` 和 `ac_cv_build=aarch64-unknown-linux-ohos`
3. 更新 config.guess/config.sub（2022-01-09 版本）
4. 修改 config.status 使用固定临时目录 `./fixed_tmp`
5. 运行 configure、make、make install DESTDIR

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 缺失 | 项目不在 registry 中 | 从 Alpine APKBUILD 查找到正确 URL |
| 2 | tar 检查卡住 | pax tar 不支持 GNU 格式 | 预缓存 `am_cv_prog_tar_ustar=pax` |
| 3 | config.guess 无法识别平台 | 版本过旧（2012）| 更新到 2022-01-09 版本 |
| 4 | config.status 临时目录权限失败 | HMDFS 特殊权限限制 | 使用固定临时目录 + 预创建 |
| 5 | G0 干净构建失败 | 补丁导致空 build triplet | 需进一步修复补丁 |

## 源码修改

- config.aux/config.guess: 更新到 2022-01-09 版本
- config.aux/config.sub: 更新到 2022-01-09 版本
- configure.ac: 修改 build triplet 设置

## 依赖版本

- pkg-config: 0.29.2
- make: 4.4.1
- gawk: 已安装

## 验证结果

```bash
pkg-config --modversion libquvi-scripts-0.9
# 输出: 0.9.20131130

ls /storage/Users/currentUser/usr/local/share/libquvi-scripts/
# 输出: 0.9 -> 0.9.20131130
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libquvi-scripts-0.9.20131130-ohos-aarch64.tar.gz | 441KB | 预编译包 |

## 注意事项

- libquvi-scripts 是纯 Lua 脚本包，无二进制文件
- 需要配合 libquvi 库使用
- G0 干净构建验证需要额外修复补丁逻辑

---

**编译结束**: 2026-06-11 16:52
**最终状态**: built
---

**编译结束**: 2026-06-11 18:30
**最终状态**: built
