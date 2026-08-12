# knock 0.8.2-r2 适配笔记

## 编译环境
- 构建系统: autotools（上游；CI worker 无 automake/aclocal，实际由 build() 直接编译单文件）
- 编译日期: 2026-08-05
- 编译器: Conan conf `tools.build:compiler_executables.c` 指定（R33，不硬编码）
- 状态: built

## 编译步骤

1. `source()` 从 conandata.yml 声明的 URL 下载源码 tarball 并 strip_root 解压。
2. `generate()` 使用 `AutotoolsToolchain` 生成 conanbuildenv，并声明 `--disable-knockd` 语义（knockd 依赖 libpcap，OHOS 无此库，不构建）。
3. `build()`：先 `apply_conandata_patches()`（当前无补丁），然后直接调用编译器编译 `src/knock.c` 生成 `knock` 可执行文件：
   - 编译器路径从 Conan conf 获取，缺失时抛 `ConanException`（不静默 fallback）。
   - 生成最小化 `config.h`（仅标准头文件检测宏 HAVE_*），满足 knock.c 对 configure 产物宏的依赖。
   - `-DHAVE_CONFIG_H -I. -D_DEFAULT_SOURCE -D_BSD_SOURCE`，优化级别跟随 build_type。
4. `package()` 将 `knock` 安装到 `bin/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 上 `autoreconf -fi` 失败（Can't exec "aclocal"） | CI worker 未安装 automake/aclocal，上游 tarball 不预带 configure 脚本 | build() 绕过 autotools，直接编译 knock 客户端单文件 |
| 2 | CI L0c 门禁 no_test_sources | test_package 缺少测试源文件 | 恢复 test_knock.sh 测试源文件 |
| 3 | CI test() 失败：knock --help 退出码为 1 | 上游 knock.c 的 usage() 打印后 exit(1)，属上游设计 | 测试只断言 --help 输出含 usage，不要求退出码为 0 |
| 4 | CI test() 交叉编译架构不匹配 | 构建机与目标架构不同，二进制不可执行 | test_package/conanfile.py 用 can_run() 守卫，不可执行时仅验证二进制存在 |
| 5 | test_knock.sh 在 set -e 下捕获退出码 | `cmd; rc=$?` 写法在 set -e 下会提前退出 | 改用 `rc=0; out=$(cmd 2>&1) || rc=$?` 安全捕获 |

## 源码修改

当前无补丁（patches/ 为空，conandata.yml patches 为空）。

## 依赖版本

- 无运行时依赖（requirements 为空；knockd 因 libpcap 依赖被禁用，不构建）。

## 验证结果

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify knock 0.8.2-r2
# 结果：通过（G0-G4 + L2/L4/L5 8 道门禁全 PASS，含 conan create 干净构建）
python3 $SKILL_ROOT/scripts/ohc-run.py finish knock 0.8.2-r2 built
# 结果：EXIT 0（finish_success），W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过，manifest → built
```

> 注：以上验证证明配方可构建、CI 可复现；源码身份（来源）确认仍为阻塞项，见下方注意事项。

## 注意事项

- **源码来源待确认（阻塞项）**：当前 conandata.yml 使用
  `https://distfiles.alpinelinux.org/distfiles/v3.24/knock-0.8.2.tar.gz`
  （sha256 a5814eac3d8337c64be88520300d56396256186522445e904ad51d14ba0e922f，
  已实测与 tarball 一致）。经核实，jvinet/knock 官方仓库仅存在 tag v0.8
  （2021-04-23，release 0.8），**官方源不存在 0.8.2 或 0.8.2-r2**；该 tarball 内容与
  TDFKAOlli/knock（jvinet/knock 的 fork）的 0.8.2 tag tarball sha256 完全一致
  （a5814eac...），即 0.8.2 版本身份来自个人 fork，非官方上游版本。按规则 R39
  （源码须为官方正式源或权威镜像源）与用户指令，此版本源码身份与官方上游不一致，
  **需 reviewer 或任务平台确认来源**，确认前不更新 conandata.yml 的 URL/sha256，
  也不改为个人 fork URL。
- knock --help 退出码为 1 是上游行为，测试只校验输出内容。
---

**编译结束**: 2026-08-06 11:06
**最终状态**: built
