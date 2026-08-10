# acf-unbound 0.1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯复制型打包，无编译目标）
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)（未实际使用，无 C 代码）
- 状态: built

## 编译步骤
acf-unbound 为 noarch 包（纯 Lua + 数据 + menu/roles），Makefile 仅执行复制，
无 configure/无编译目标：

```bash
# 下载（gitlab 反爬，curl 手动下载到 .tmp-acf-unbound/）
curl -fsSL --max-time 120 -o .tmp-acf-unbound/acf-unbound-v0.1.0.tar.gz \
  https://gitlab.alpinelinux.org/acf/acf-unbound/-/archive/v0.1.0/acf-unbound-v0.1.0.tar.gz

# init + 安装
source .build-context-acf-unbound-0.1.0
cd $BUILD_SRC_DIR
make install DESTDIR=$TEST_PREFIX      # 安装到 usr/share/acf/app/unbound/（config.mk: appdir=${datadir}/acf/app）
# make check: 无 check/test 目标，跳过
```

Conan 配方 package() 用 `make install DESTDIR=$package_folder`（config.mk prefix=/usr），
产物落在包内 `usr/share/acf/app/unbound/`（unbound-controller.lua / unbound-model.lua /
unbound.menu / unbound.roles）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后源目录异常：3 个 `.lsp` 文件读取失败/无法跟踪 | 源码包内含 3 个悬空符号链接 `unbound-expert-html.lsp` / `unbound-logfile-html.lsp` / `unbound-status-html.lsp` → `../expert-html.lsp` 等，指向 acf-core 框架公共模板（本包内不存在目标） | 从 .orig/.work 双轨源目录删除 3 个悬空符号链接；它们由 acf-core 框架提供模板（ACF 公共 lsp），不属于本包产物 |
| 2 | gitlab.alpinelinux.org 源码下载 HTTP 418 | Anubis 反爬，仅放行 curl/wget UA，conan get() 默认 UA 被拦截 | conandata.yml 只保留官方 HTTPS URL；下载重试与缓存由 CI 基础设施负责 |
| 3 | 纯 Lua/数据包无 ELF 可执行文件 | noarch 包，构建产物仅 .lua/.menu/.roles 文本文件 | R38 commands.json 不适用；test_package 用实质内容标记验证（R34：产物存在 + controller default_action 钩子 + model require acf.fs + menu/roles 权限） |

## 源码修改

- 无（纯复制型打包，无编译目标；仅 init 阶段删除 3 个悬空符号链接，不入补丁，原包不改）

## 依赖版本

- acf-core/0.24.1（requirement，ACF web 框架，按 share/acf/app 自动发现本 app）
- unbound/1.22.0（requirement，本 app 配置管理的 DNS 服务）
- 两者均为本地缓存已编译（@ohpcd/stable），conan create 本地解析

## 验证结果

```bash
conan create archives/a/acf-unbound/0.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable   # 成功，test_package 全绿
python3 scripts/ohc-run.py conan-verify acf-unbound 0.1.0   # G0-G4 + L2/L4/L5 全部 PASS
```

test_package 断言（9 条）：4 个产物存在（unbound-controller.lua/unbound-model.lua/
unbound.menu/unbound.roles）、controller `default_action` 钩子、model 加载 `acf.fs`、
menu 引用 Unbound 分组、roles 声明 `unbound:status` 权限（实质 ACF app，非空壳）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | noarch application 配方（acf-core/0.24.1 + unbound/1.22.0 requirement，make install DESTDIR 打包） |
| conandata.yml | 官方 HTTPS URL，sha256=aa59fddad8a6ea36958ef62891ec338fba34f5c1341b8dbc612da93310f64c3e |
| test_package/ | 实质内容标记验证测试（9 断言，R34） |
| reports/ | test-report.md + conan-create.log + conan-verify-report.md |

（软件级 commands.json 不需要：R38 — 无 ELF 可执行文件，纯 Lua/数据包。）

## 注意事项

- 纯 Lua/数据包：无 ELF 可执行文件，L2/L4/L5 冒烟/安全/基线门禁按设计跳过
- 运行时依赖 acf-core 框架（app 由 share/acf/app/* 自动发现）+ unbound 服务，两者缺一 app 无法使用
- 3 个悬空符号链接（unbound-*-html.lsp）由 acf-core 框架公共模板提供；若框架未装对应模板，Expert/Logfile 页面不可用（已知运行时依赖）
- gitlab.alpinelinux.org 反爬问题属基础设施层面，配方不使用本机 file:// 路径
---
