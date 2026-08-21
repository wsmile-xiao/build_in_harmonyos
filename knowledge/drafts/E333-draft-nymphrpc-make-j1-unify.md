# E333 知识草稿：OHOS 下 make 统一 -j1

> 编号：E333（草稿，待 graph promote 转正式；E321–E330 已占用，按设备端最大 E 编号顺延）
> 文件名：E333-draft-nymphrpc-make-j1-unify
> 实例来源：nymphrpc 0.1.1（make lib -j1）+ 仓库 7zip 模板核验
> 检索字段：library=nymphrpc / build=make / error=jobserver / toolchain=clang15 / platform=ohos

## 背景

鸿蒙 SELinux 策略禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO 在父子进程间
传递并行任务令牌，导致 make -j>1 卡住或报错（E074 已记录，方案 -j1）。

仓库部分 Makefile 型 recipe 模板仍用 make -j$(nproc)：
- archives/7/7zip/23.01/conanfile.py L43: self.run("make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j$(nproc)")
- archives/7/7zip/25.01/conanfile.py 同
与 -j1 惯例（aamath: make -f Makefile.good -j1）不一致，新 recipe 照抄会在 OHOS 踩 FIFO 坑。

## 本次做法（nymphrpc 0.1.1）

nymphrpc 为纯 Makefile 库（无 configure），conanfile.py build()：
- conf dict 整体读取 tools.build:compiler_executables（.get("cpp")）
- self.run("make lib -j1 CXX=%s AR=%s CXXFLAGS=... LIBS=...", cwd=self.source_folder,
  env="conanbuild")
- make lib -j1 编译 PASS，无 FIFO 问题。

## 建议

1. 新 Makefile 型 recipe 统一 make -j1（不照抄 -j$(nproc)）。
2. E074 增补提示：仓库 7zip 模板仍 -j$(nproc)，OHOS 应统一 -j1。
3. 模板（archives/7/7zip/*/conanfile.py）后续由维护者修正为 -j1。

## Do Not

- 不要用 make -j$(nproc)（或任意 -j>1）编译；FIFO 权限是系统级限制，重试无效。
- 不要把 jobserver 报错误判为编译命令错误去改 Makefile 目标。

## 验证

- mkfifo /tmp/test_fifo → Permission denied（E074 验证命令，系统级限制）。
- conan create PASS（nymphrpc，make lib -j1，round-2f all assertions passed）。

## 关联条目

- E074（扩展基础）：make -j FIFO/jobserver 限制根因与 -j1 方案；本稿为模板级统一提示。
- P013：平台限制必须降级而非绕过；P014：环境变量与构建系统语义冲突；
  P020：HMDFS 不支持硬链接和 FIFO。
