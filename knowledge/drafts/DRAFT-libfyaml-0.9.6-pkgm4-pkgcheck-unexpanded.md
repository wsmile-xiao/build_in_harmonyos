# DRAFT: pkg.m4 缺失导致 PKG_CHECK_MODULES 宏未展开（libfyaml 0.9.6）

## 问题

适配 libfyaml 0.9.6（Autotools）时，官方 tag 压缩包**不含生成的 configure**，需要先
运行 `bootstrap.sh`（autoreconf）。第一次 bootstrap 后执行 `./configure` 直接报 shell
语法错误：

```
./configure[20204]: syntax error: unexpected 'LIBYAML,'
```

错误点位于 configure 第 20204 行，残留了未展开的宏文本：

```
PKG_CHECK_MODULES(LIBYAML,  yaml-0.1 , HAVE_LIBYAML=1, HAVE_LIBYAML=0)
```

## 真实证据（libfyaml 0.9.6）

- 命令: `cd <work> && ./bootstrap.sh && ./configure --prefix=<prefix>`
- 首个错误: `./configure: syntax error: unexpected 'LIBYAML,'`（configure 内未展开的
  `PKG_CHECK_MODULES(LIBYAML, ...)` 残留）
- 退出码: configure_exit=1
- 日志: `.oh-executor/libfyaml-r01-adaptation-validation.log`

## 根因

`PKG_CHECK_MODULES` 宏定义在 pkg-config 自带的 `pkg.m4` 中（`AC_DEFUN` 形式）。autoreconf
生成 configure 时，aclocal 需要在宏搜索路径（`m4/` 目录、系统 aclocal 目录）中找到
`pkg.m4` 才能展开该宏。本机 pkg-config 0.29.2 装在 `/data/service/hnp/pkg-config.org/...`，
其 aclocal 目录（`share/aclocal/pkg.m4`）不在 autoreconf 的隐式搜索路径内，源码树
`m4/` 也没有 pkg.m4 —— 结果 PKG_CHECK_MODULES 原样留在 configure 文本里，被 /bin/sh
当作语法错误。

注意与既有知识条目区分：
- E089（`@am_AUTOM4TE@` 占位符未替换）是另一类 aclocal 故障，根因不同；
- E468（pkg-config 找不到包）是运行时探测失败，根因不同；
- DRAFT-pkgm4-preset-nonempty-gate（预置变量空串判定）是配方侧绕过门禁，根因不同。

## 修复

把 pkg.m4 复制进源码树 m4/ 后重新 bootstrap，宏即正确展开：

```bash
cp <pkg-config-aclocal-dir>/pkg.m4 m4/pkg.m4
sh bootstrap.sh           # 重新生成 configure
grep -c PKG_CHECK_MODULES configure   # 期望 0：宏已全部展开
./configure --prefix=<prefix>
```

验证：configure 通过（本次 3 处 PKG_CHECK_MODULES 全部展开），make 通过，`conan create`
G2 干净构建通过（配方在 bootstrap 后 `shutil.copy` m4-pkg.m4 到 m4/ 再应用补丁）。

## 适用边界

- 上游 tag 压缩包**不含生成的 configure**（需 bootstrap/autoreconf 现场生成）的 Autotools
  项目；
- configure.ac 使用了任意 pkg-config 宏系列（PKG_CHECK_MODULES 等）；
- 构建环境的 pkg-config 不在 autoreconf/aclocal 隐式搜索路径中（常见于 /data/service/hnp
  等非标准安装根）。

不适用：release tarball 自带 configure 的项目（宏已展开）；系统 pkg-config 已把
`share/aclocal` 纳入默认搜索路径的环境。

## 查重差异

- 正式知识（knowledge/graph/）：E007/E072（config.guess/sub OHOS）无关；E089（am_AUTOM4TE
  占位符）不同根因；E468（pkg-config 包缺失）不同根因——未命中。
- 草稿（knowledge/drafts/）：DRAFT-pkgm4-preset-nonempty-gate（预置变量空串）不同根因
  ——未命中。
- 结论：新增（path B），与 libfyaml 0.9.6 归档同 PR。