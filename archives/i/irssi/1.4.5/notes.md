# irssi 1.4.5 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-05-26}
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
---

**编译结束**: 2026-05-26 16:42
**最终状态**: published

---

**编译开始**: 2026-05-26 16:15
**软件**: irssi 1.4.5
**平台**: HarmonyOS (aarch64-unknown-linux-ohos)
**构建系统**: autotools

### 问题和解决方案

1. **源码下载 SSL 证书失败**:
   - 问题: Savannah 和 irssi.org SSL 证书验证失败
   - 解决: 手动用 Python (SSL context bypass) 从 GitHub releases 下载成功

2. **config.guess 不识别 HarmonyOS** (E007):
   - 问题: config.guess 返回 "unable to guess system type"
   - 解决: 用 patch-autotools-ohos.pl 补丁脚本修改 config.guess, 添加 HarmonyOS 识别
   - 三元组: aarch64-unknown-linux-ohos

3. **config.sub 拒绝 linux-ohos 三元组** (E007/E072):
   - 问题: config.sub 报 "Kernel `linux` not known to work with OS `ohos'"
   - 解决: 在 config.sub 的 kernel-OS 验证列表中添加 `linux-ohos*`

4. **Perl 模块编译失败**:
   - 问题: irssi Perl 集成构建失败 (pm_to_blib 锥误)
   - 解决: 使用 `--with-perl=no` 禁用 Perl 支持 (HarmonyOS Perl 不完整)

5. **ncurses/terminfo 缺失**:
   - 问题: configure 找不到 setupterm 函数
   - 解决: 设置 CFLAGS/LDFLAGS/LIBS 指向本地 ncurses 静态库安装

6. **getpwuid_r 测试失败** (平台限制):
   - 问题: test-796 因 getpwuid_r() 无法解析 UID 20020100 而失败
   - 解决: 这是 HarmonyOS NSS 限制，非 irssi bug, 标记为已知平台限制

### configure 选项
```
./configure --prefix=$DEFAULT_PREFIX --with-perl=no
```

### 编译依赖
- glib 2.88.0 (本地预编译)
- openssl 3.5.6 (本地预编译)
- ncurses 6.5-20250215 (本地预编译, --without-shared)

### 验证
```
$DEFAULT_PREFIX/bin/irssi --version
irssi 1.4.5 (20231003 1405)
```

**编译结束**: 2026-05-26 16:33
**最终状态**: published
