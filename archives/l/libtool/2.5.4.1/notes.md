# libtool 2.5.4 编译笔记（HarmonyOS PC · Conan autotools · 工具包）

## 定位
`package_type = "application"`，构建期工具。仓内已有 2.4.7，本次补 2.5.4。

## 关键适配：libtoolize 的 pkgauxdir 烤死问题
与 automake 同族（详见 automake 1.18 笔记），但 `libtoolize` **没有**
对应的命令行选项可改。上游 `libtoolize.in` 认环境变量 `_lt_pkgdatadir`：
设了就从它派生 `pkgauxdir=$_lt_pkgdatadir/build-aux`、
`pkgltdldir=$_lt_pkgdatadir/libltdl`、`aclocaldir=$_lt_pkgdatadir/m4`。

但它期望的是**源码树形状**的目录布局，与安装后的布局不同。
故在 package 里建一个源码树形状的软链目录（相对软链，不含绝对路径），
再由 `package_info` 把 `_lt_pkgdatadir` 指过去。

## 其他
- `MAKEINFO=true`（设备无 makeinfo）。
- `libtool.m4` 等宏加入 `ACLOCAL_PATH`，让 `autoreconf` 能找到 `libtoolize`。
- 显式三元组，跳过 `config.guess`。

## 状态
built —— 真机 `conan create` 通过；test_package 实际跑 `libtoolize --version`
并在一个最小项目上验证 `autoreconf` 能成功调用它。
