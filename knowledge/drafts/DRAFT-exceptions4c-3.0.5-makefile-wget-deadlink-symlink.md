# DRAFT — Makefile 内 wget 下载回退规则引用失效 URL 时用 tarball 已有文件补齐（exceptions4c 3.0.5）

## 问题

exceptions4c 3.0.5 上游 `test/Makefile` 对缺失源文件声明了 `$(WGET) $(URL_TRUNK)/<file>`
形式的自动下载回退规则，`URL_TRUNK` 指向已关闭的 `http://exceptions4c.googlecode.com/svn/trunk`。
构建测试时只要 `test/` 目录缺少 `e4c_rsc.h` 等文件，make 立即触发 wget 并超时：

```
wget http://exceptions4c.googlecode.com/svn/trunk/etc/e4c_rsc.h
wget: connect: Operation timed out
make: *** [Makefile:382: e4c_rsc.h] Error 1
```

## 根因

历史 era 的 C 库 Makefile 常内嵌"源文件缺失时从远程 svn/trunk 自动下载"的回退规则。
托管服务关闭后该 URL 永久失效，但官方 release tarball 早已把同名文件打包在
`src/`（e4c.c/e4c.h）与 `etc/`（e4c_rsc.c/e4c_rsc.h）目录中——只是 Makefile 期望它们
位于 `test/` 构建目录。等待 wget 必然超时失败，且把失效外链当源码来源会污染 conandata。

## 方案

在构建目录中把 tarball 已有文件软链到 Makefile 期望位置（HMDFS 上软链不能覆盖，
先 `rm -f` 再 `ln -s`）：

```bash
cd test
ln -sf ../src/e4c.c  e4c.c
ln -sf ../src/e4c.h  e4c.h
ln -sf ../etc/e4c_rsc.c e4c_rsc.c
ln -sf ../etc/e4c_rsc.h e4c_rsc.h
make CC=clang && ./e4c_test
```

不修改 Makefile 的 wget 规则本身（R6：只改源不改生成文件；保持上游原貌）。

## 验证

`make CC=clang` 全部编译通过，`./e4c_test` 运行 57 项上游用例（50 通过，7 项为
平台信号行为差异，见 test-report.md），退出码 0。

## 适用边界与反例

- 适用：Makefile 内嵌 `$(WGET) <失效外链>` 回退规则、且 release tarball 已含同名文件的库。
- 不适用：tarball 确实不含该文件（此时应评估该文件是否必需；必需则属真实上游缺失，
  按缺失文件处理，不得伪造）。
- 反例：若 wget URL 仍有效（如 GitHub 直链）则无需软链，直接允许 make 下载。

## 查重关系

- similar_to: DRAFT-commander-1.4.0-makefile-recipe-build-package-traps（同为裸 Makefile
  型库配方陷阱，但该草稿覆盖 basic_layout cwd/keep_path/compiler_executables dict，未覆盖
  wget 死链回退；两者正交，可组合成"Makefile 型库适配"主题）
- caused_by: 无既有条目
- prerequisite_of: 无
- conflicts_with: 无