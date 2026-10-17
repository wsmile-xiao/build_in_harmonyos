# tstools 1.13-git20151030 适配笔记

## 上游信息

- 上游仓库：https://github.com/kynesim/tstools
- 固定提交：db1f79f409818fa0476ecf8593079a7ca3dbafd2
- 下载源：优先使用 gh-proxy 镜像，失败时回退 GitHub
- 构建系统：GNU Makefile
- 产物：`bin/` 下的 MPEG TS/PS/ES 工具与静态库 `lib/libtstools.a`

## 构建

使用 Conan profile 注入的 OHOS clang：

```sh
make -j1 CC=<OHOS clang>
make test CC=<OHOS clang>
```

`make test` 构建并运行上游的 `test_nal_unit_list` 与 `test_es_unit_list`。

## 消费者验证

test_package 将最小的 H.264 ES 样例交给已安装的 `es2ts`，再使用
`tsinfo` 检查生成的 TS。这样可以覆盖安装后的真实命令行工具，而不仅是
检查 `--help`：

1. `es2ts mini.264 mini.ts`
2. `tsinfo mini.ts` 输出 PAT、PMT 和 program 信息。

## OHOS 适配点

- 目前源码在 OHOS clang 下可直接编译；若共享库直接使用 `ld -soname`
  需要平台链接器路径，配方只把工具与静态库作为交付产物，不依赖该共享库。
- 所有工具均使用静态 `libtstools.a` 链接，运行时不依赖构建目录。
