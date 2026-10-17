# bibtex 0.99e 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (from Conan profile ohos-aarch64)
- 状态: published

## 编译步骤

bibtex 从 TeX Live 源码树构建，需要三层 configure：

1. **构建 kpathsea**（texk/kpathsea/）:
   ```bash
   ./configure --prefix=$PREFIX
   bash config.status
   make -j2
   make install
   ```

2. **配置 web2c**（texk/web2c/）:
   ```bash
   ./configure --prefix=$PREFIX --no-create \
     --without-x --disable-tex --disable-mf \
     --disable-mf-nowin --disable-aleph --disable-hitex \
     --disable-pdftex --disable-luatex --disable-texprof \
     --disable-xetex --disable-mflua --disable-mfluajit \
     --disable-euptex --disable-uptex --disable-etex \
     --disable-ipc --disable-dump-share
   bash config.status
   ```

3. **配置 web2c/web2c**（texk/web2c/web2c/）:
   ```bash
   ./configure --prefix=$PREFIX --no-create
   bash config.status
   ```

4. **编译 bibtex**:
   ```bash
   make -C texk/web2c/lib
   make bibtex -C texk/web2c
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "cannot guess build type" | config.guess 不包含 HarmonyOS 检测 | 0001-build-aux-config.guess.patch: 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别 case 分支 |
| 2 | config.status 运行时 mktemp -d 失败 | HMDFS 文件系统不支持 mktemp -d 创建临时目录 | 0002-configure-mktemp-fix.patch: 将 mktemp -d 替换为 mkdir-based 临时目录创建 |
| 3 | Makefile SHELL=/bin/sh 导致兼容性问题 | configure 检测的 shell 不正确 | CONFIG_SHELL 由 Conan profile 设置为 /data/service/hnp/bin/bash，configure 自动用 bash |
| 4 | libtool wrapper 问题 | libtool 使用 /bin/sh 不兼容 | CONFIG_SHELL=bash 从 profile 传递，无需 runtime wrapper |

## 源码修改

### 0001-build-aux-config.guess.patch
- 修改 `build-aux/config.guess`
- 添加 `#elif defined(__OHOS__)` LIBC=ohos 检测（在 __ANDROID__ 之后）
- 添加 `*:HarmonyOS:*:*)` case 分支，输出三元组 `aarch64-unknown-linux-ohos`

### 0002-configure-mktemp-fix.patch
- 修改 3 个 configure 脚本: texk/kpathsea/configure, texk/web2c/configure, texk/web2c/web2c/configure
- 将 `mktemp -d "./confXXXXXX"` 替换为 `mkdir "./conf$$-$$"` 临时目录创建
- 将 `$RANDOM` 替换为 `$$`（POSIX 兼容）

## 依赖版本

- 无外部 Conan 依赖
- kpathsea 库在 TeX Live 源码树内嵌（in-tree 构建）
- 编译器: clang 15（from Conan profile ohos-aarch64）

## 验证结果

```bash
# Conan 配方验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify bibtex 0.99e
# → G1-G4 + L2/L4/L5 全部 PASS

# W3 本地 CI
python3 $SKILL_ROOT/scripts/ohc-run.py finish bibtex 0.99e published
# → .ci-result.json exit_code=0

# bibtex --version
bibtex (TeX Live 2026)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（AutotoolsToolchain，无 os.environ） |
| conandata.yml | 源码 + 补丁声明（官方 GitHub URL） |
| patches/0001-build-aux-config.guess.patch | HarmonyOS 平台检测补丁 |
| patches/0002-configure-mktemp-fix.patch | HMDFS mktemp 修复补丁 |
| test_package/ | 功能测试（bibtex --version + .aux 处理） |
| commands.json | 命令行工具声明（binary=true） |

## 注意事项

- texlive-source trunk 版本的 config.sub 已包含 ohos* 和 linux-ohos* 支持，无需额外补丁
- 三层 configure 是 TeX Live 构建系统的标准流程：kpathsea → web2c → web2c/web2c
- bash config.status 需要显式用 bash 执行，因为 config.status 是 configure 生成的脚本

## 构建完成
- bibtex 0.99e 编译成功
- 功能测试通过（--version + .aux 文件处理）
- conan-verify 全部门禁通过
- W3 本地 CI 通过
---

**编译结束**: 2026-08-24 14:44
**最终状态**: published
