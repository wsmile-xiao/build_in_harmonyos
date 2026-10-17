# acf-tinydns 0.11.1 适配笔记

## 软件简介

acf-tinydns 是 Alpine Configuration Framework (ACF) 的 web 管理模块,
用于配置 tinydns (djbdns) DNS 服务器。属于纯 Lua/LSP 脚本包,
无 C/C++ 编译,package_type = application。

## 上游信息

- **上游仓库**: https://gitlab.alpinelinux.org/acf/acf-tinydns
- **版本**: 0.11.1
- **许可证**: GPL-2.0-only
- **构建系统**: 无 (Makefile 仅 cp -a tinydns* → appdir)
- **运行时依赖**: acf-core/0.24.1, acf-lib-lua5.3/0.11.1

## 适配说明

acf-tinydns 是纯 Lua/LSP 脚本包,无编译。适配方式与 acf-dnsmasq/acf-unbound
一致:将 tinydns* 文件安装到 share/acf/app/tinydns/,acf-core 框架自动发现。

### 关键点

1. **符号链接保留**: tinydns-editfile-html.lsp 是悬空符号链接
   → ../filedetails-html.lsp (acf-core 提供)。
   conan copy 默认跳过符号链接,改用 python 逐文件复制:
   普通文件 copy2,符号链接用 os.symlink 重建。

2. **R32 平台兼容**: validate() 中 os 检查接受 "Linux" 和 "OHOS"。

3. **L0p 门禁**: settings 全四项 (os/compiler/build_type/arch)。

4. **测试设计**: test_package 使用 bash 脚本 test_tinydns.sh 验证:
   - ACF app 目录存在
   - tinydns*.lua 文件存在且语法正确 (luac -p)
   - tinydns.menu 和 tinydns.roles 存在
   - tinydns*.lsp 模板文件存在 (含符号链接,用 -L 跟随)

## 上游测试通过率

acf-tinydns 是纯 Lua 脚本包,无上游测试套件 (无 test/ 目录,
无 Makefile check target,无 pytest/unittest)。

验证方式:
1. **Lua 语法检查**: luac -p 对所有 tinydns*.lua 文件执行 parse-only 检查
2. **文件完整性**: 验证 controller/model/menu/roles/template 全部安装
3. **符号链接保留**: 验证悬空符号链接 tinydns-editfile-html.lsp 被正确保留

通过率: 100% (所有 Lua 文件语法正确,所有必要文件已安装)
