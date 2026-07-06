# libpagemaker

## 简介
libpagemaker 是 Document Liberation Project (DLP) 的一部分，用于导入和转换 Adobe PageMaker 文档。提供 `PMDocument` 库 API 和 `pmd2raw`/`pmd2svg` 命令行转换工具。

## OHOS 适配
- autotools 构建
- 需替换 config.guess/config.sub 为 HarmonyOS-aware 版本（从 libcdr 构建复制）
- config.status umask 077 在 HMDFS 上需用 mktemp wrapper 修复
- `--disable-werror` 必须使用（boost 头文件触发 -Wdeprecated-copy 警告）
- 2 个补丁：config.guess + config.sub
- Conan 配方包含 mktemp wrapper 解决 HMDFS 兼容性问题

## 依赖
- librevenge-0.0 (librevenge/0.0.5)
- boost (headers only)

## 功能验证
```bash
pmd2raw --version    # pmd2raw 0.0.3
pmd2svg --version    # pmd2svg 0.0.3
```

## R26 静态链接
- conanfile.py 使用 `--enable-static --disable-shared` + `-static -Wl,-Bstatic`
- 需修改 librevenge .la 文件 `library_names=""` 强制使用 .a
- LIBS 添加 `-l:libc++.a -l:libc++abi.a` 静态链接 C++ 运行时
