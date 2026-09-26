# multirun 1.1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-24
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built（制品仓尚未发布，待合并后 Release CI 上传）

## 编译步骤

multirun 是单文件 C99 程序（multirun.c，约 240 行），构建系统为 CMake，无任何外部依赖（仅 POSIX/libc）；为 CLI 长选项添加了一个补丁。

```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build
cmake --install build --prefix $TEST_PREFIX
```

- 上游源码 URL: https://github.com/nicolas-van/multirun/archive/refs/tags/1.1.3.tar.gz
- sha256: 35d6bf959cae79d5ff1bad06e34c753ffb1fb90d66ee1796bc0fd76eb2384e75

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 源码报 SSL CERTIFICATE_VERIFY_FAILED | 本机 /etc/ssl/cert.pem 缺失，Python urllib 无 CA 可用（curl 用 /etc/ssl/certs/cacert.pem 正常） | 设 SSL_CERT_FILE=/etc/ssl/certs/cacert.pem 后重试 |
| 2 | ohc-run.py 默认把归档建到 skill 安装目录 | find_project_dir() 从脚本所在目录向上找 SKILL.md，命中 skill 安装副本 | 显式设 OHC_PROJECT_DIR=<仓库根> 运行所有 ohc-run.py 命令 |
| 3 | conan-init 误判构建系统为 autotools 生成错误模板 | 构建系统猜测基于 URL 关键字，GitHub 归档 URL 命中默认值 | 手工改写为 CMake 配方（conanfile-cmake 模板），package_type=application |

## 源码修改

补丁 1 个（patches/0001-multirun.c.patch，portability 型）：

| 补丁 | 背景 | 内容 |
|------|------|------|
| 0001-multirun.c.patch | L2 冒烟门禁（R38 工具质量）要求 CLI 支持 --version/--help；multirun 的 getopt 只认短选项 -v/-h，--version/--help 落入未知选项分支 exit(-2) | main() 在 getopt 循环前显式扫描长选项：--version 打印 `multirun <版本>`、--help 走 print_help()，均 exit(0)；遇到首个位置参数即停止扫描（与 getopt 语义一致，不影响正常命令调用） |

上游代码使用 `#if __linux__ || __unix__` + `PR_SET_CHILD_SUBREAPER` 守卫，兼容 OHOS；`PR_SET_CHILD_SUBREAPER` 不可用时自动降级（仅警告），无需平台宏改动。CMakeLists.txt 已用 add_compile_definitions 把正确版本号传给 PROJECT_VERSION（源码里 `"0.0.0"` 只是兜底值）。

## 依赖版本

无第三方依赖（仅 C 标准库 + POSIX：stdio/stdlib/unistd/string/errno/sys-wait/signal/prctl）。

## 验证结果

```bash
# 上游测试: tests.bats (bats-core 1.11.1)，4/4 通过
$HOME/tmp/bats/bats-core-1.11.1/bin/bats tests.bats
1..4
ok 1 simple command invocation
ok 2 multiple commands invocation
ok 3 returns 0
ok 4 returns -1

# 冒烟验证
./build/multirun -h   # Version: 1.1.3
multirun "sh -c 'echo test > resultfile'; sleep 1" "sh -c 'echo test2 > resultfile2'"  # 并发执行
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（application） |
| conandata.yml | 官方源 + sha256 |
| test_package/ | test.sh 镜像上游 4 个 bats 用例真实执行 |
| commands.json | CLI 工具声明（R38） |

## 注意事项

- multirun 内部用 `execlp("sh", ...)` 执行子命令，OHOS 上 /system/bin/sh 可用即可正常工作。
- 本机为 aarch64（华为 KirinX90），OHOS 交叉产物可原生运行，test_package 无需 qemu。
- 上游只在 Alpine 发行版打包；无 configure/make check 目标，测试入口为 tests.bats。
---

**编译结束**: 2026-09-24 18:01
**最终状态**: built（待合并后 Release CI 发布）
