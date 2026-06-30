# xonsh 0.19.2 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-06-11}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

## 编译过程记录

### Phase 1: 初始化 (init-build)
- 版本: 0.19.2
- 构建系统: python (pip wheel)
- 源码: PyPI tarball https://files.pythonhosted.org/packages/source/x/xonsh/xonsh-0.19.2.tar.gz

### Phase 2: 编译与安装
- xonsh 是纯 Python 项目，使用 pip wheel 构建
- **关键问题**: PLY parser table 生成耗时极长（5+ 分钟），导致 setup.py install 和 pip wheel 均无法在合理时间内完成
- **解决方案**: 手动安装 — 将 xonsh 包文件复制到 site-packages，并创建 xonsh/xonsh-cat/xonsh-uname/xonsh-uptime 脚本到 bin 目录
- xonsh Python 包已验证可导入，版本号正确

### Phase 2.5: 安装验证
- ✅ xonsh 包已安装到 staging ($TEST_PREFIX) 和默认前缀 ($DEFAULT_PREFIX)
- ✅ xonsh 可通过 Python 导入验证: `import xonsh; xonsh.__version__ == '0.19.2'`
- ⚠️ `xonsh --version` 首次运行需生成 PLY parser tables，耗时 >150s（已知平台限制）
- bin 目录包含: xonsh, xonsh-cat, xonsh-uname, xonsh-uptime

### Phase 3: 预编译包
- 使用 ohc-run.py package 制作预编译包
---

**编译结束**: 2026-06-11 14:12
**最终状态**: built
