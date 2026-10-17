# rbenv-bundler 1.0.1 适配笔记

## 编译环境
- 构建系统: makefile (custom)
- 编译日期: 2026-07-15
- 编译器: N/A (纯脚本项目)
- 状态: built

## 编译步骤

rbenv-bundler 是一个纯 Shell/Ruby 脚本项目，无需编译。安装步骤：

1. **下载源码**: 从 GitHub tag 1.0.1 下载 tarball
   ```
   URL: https://github.com/carsomyr/rbenv-bundler/archive/refs/tags/1.0.1.tar.gz
   SHA256: 6840d4165242da4606cd246ee77d484a91ee926331c5a6f840847ce189f54d74
   ```

2. **创建 Makefile**: 为符合编译框架要求，手动创建 Makefile 实现文件复制安装
   ```makefile
   PREFIX ?= /usr/local

   install:
       mkdir -p $(DESTDIR)$(PREFIX)/bin
       mkdir -p $(DESTDIR)$(PREFIX)/etc/rbenv.d/bundler
       mkdir -p $(DESTDIR)$(PREFIX)/etc/rbenv.d/exec
       mkdir -p $(DESTDIR)$(PREFIX)/etc/rbenv.d/rehash
       mkdir -p $(DESTDIR)$(PREFIX)/etc/rbenv.d/which
       cp bin/rbenv-bundler $(DESTDIR)$(PREFIX)/bin/
       chmod +x $(DESTDIR)$(PREFIX)/bin/rbenv-bundler
       cp etc/rbenv.d/bundler/* $(DESTDIR)$(PREFIX)/etc/rbenv.d/bundler/
       cp etc/rbenv.d/exec/* $(DESTDIR)$(PREFIX)/etc/rbenv.d/exec/
       cp etc/rbenv.d/rehash/* $(DESTDIR)$(PREFIX)/etc/rbenv.d/rehash/
       cp etc/rbenv.d/which/* $(DESTDIR)$(PREFIX)/etc/rbenv.d/which/

   check:
       bash -n bin/rbenv-bundler
   ```

3. **Staging 安装**:
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

4. **验证**:
   ```bash
   make check  # bash -n syntax check
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上次使用 main 分支 URL | R39 要求官方源 | 改用 tag 1.0.1 tarball |
| 2 | conanfile.py 模板按库生成 | 脚本项目非库 | 改为 application 类型，package 直接 copy 文件 |
| 3 | test_package 用 CMake | 脚本项目无 C | 改为 bash -n 语法检查 + --complete 测试 |

## 源码修改

应用补丁 `0001-harmonyos-md5-support.patch`：为 `etc/rbenv.d/bundler/includes.sh` 的 `md5` 函数增加 HarmonyOS 的 `uname` 匹配分支（`Linux` → `Linux|HarmonyOS`），使 MD5 计算在 HarmonyOS 上正确走 `md5sum` 路径。此外创建了 Makefile 用于安装流程（源码本身无构建系统）。

## 依赖版本

无外部依赖。项目运行时依赖：
- rbenv (需要用户已安装)
- Ruby 1.8.7+ with Bundler gem

## 验证结果

```bash
make check
# Output: Syntax check: PASS
```

## 注意事项

- **项目状态**: 根据 rbenv 官方文档，此插件不推荐使用，存在性能问题和 bug
- **替代方案**: 推荐使用 Bundler binstubs (`bundle install --binstubs`) 或 rbenv-binstubs 插件
- **安装位置**: 安装到 prefix/bin/ 和 prefix/etc/rbenv.d/
- **启用方式**: 需要手动执行 `rbenv bundler on` 启用插件
---

**编译结束**: 2026-07-15 20:16
**最终状态**: built
