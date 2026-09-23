# pit

pit 是与 Git 集成的命令行项目管理工具（"project manager from hell"），用纯 C 实现并编译为单个可执行文件。

## 功能概述

- 项目/任务/便签三级实体管理（创建、查询、更新、删除、移动）
- `log` 按时间顺序展示操作历史，`info` 展示数据库摘要
- 通过 `tools/commit-msg` 钩子与 Git 分支/提交集成
- `PITFILE` 环境变量可切换数据库文件位置

## OHOS 适配

- 构建系统为裸 Makefile，无 configure、无第三方依赖，仅需系统 libc
- 上游 Makefile 硬编码 `CC = gcc`，配方经 `tools.build:compiler_executables` 注入真机 clang
- 上游 `make install` 直接拷贝到 `$(PREFIX)/bin` 且不支持 `DESTDIR`，配方改为从 `bin/pit` 直接打包，不调用 install 目标
- 上游 0.1.0 有两个已知行为 quirks（上游在 0.1.0 之后已修复，本适配刻意保留上游行为、零补丁）：
  - 绝对路径 PITFILE 可能触发段错误（上游 issue #4），test.sh 因此 `cd` 进临时目录后使用相对 `PITFILE`
  - 成功时退出码为 1 而非 0（上游 PR #6），test.sh 只断言输出内容、不断言退出码

## 依赖关系

- 编译依赖：无（纯 C + 系统 libc）
- 测试依赖：系统 Ruby（运行上游 `test/pit_test.rb`，真机由 HNP 提供）

## 参考资料

- 上游仓库：https://github.com/michaeldv/pit
- 源码包：https://github.com/michaeldv/pit/archive/refs/tags/0.1.0.tar.gz
