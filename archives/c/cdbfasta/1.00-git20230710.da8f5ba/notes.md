# cdbfasta 1.00-git20230710.da8f5ba 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure/install 目标）
- 编译日期: 2026-09-06
- 编译器: clang++ 15.0.4（OHOS armv8, libc++）
- 状态: built
- 依赖: zlib/1.3.1.1（制品仓已发布；ENABLE_COMPRESSION=1 硬编码 -lz）

## 编译步骤

1. `apply_conandata_patches`（当前无补丁，G1 显式要求）
2. `generate()`：从依赖图取 zlib include/lib 绝对路径，经 buildenv_info 注入环境 CXXFLAGS/LDFLAGS（R33）
3. `make -j1 CXX=<clang++>`（上游 Makefile 用 `CXX ?= g++` 尊重外部变量；其对 CXXFLAGS/LDFLAGS 为 `+=`，环境注入值与上游自有旗标叠加）
4. build() 内行为验证（R51：上游无测试套件，改用文档化工作流真实验证）：构造 2 条记录的 FASTA → cdbfasta 建索引（断言 .cidx 产出）→ cdbyank -a s1/s2 检索（断言完整记录内容）
5. package()：无 install 目标，从构建目录拷贝 cdbfasta/cdbyank 到 <pkg>/bin（abduco 同族先例）
6. test_package 消费者测试（conan create 自动触发）：python 驱动安装后的两个工具

## 上游测试清点（R51）

- 上游**无自动化测试套件**：无 `make check`/CTest/pytest；tarball 内 `perltest.pl` 为用法示例脚本，非测试入口；Makefile 无 test 目标。静态计数如实为 **0**
- 补偿验证：
  - build() 行为流 3 步（索引创建、s1 键检索、s2 键检索）全部通过
  - test_package 消费者测试 5 项断言全部通过（索引退出码、.cidx 产出、按键检索记录内容 ×2、不存在键返回空）

## 消费者测试

- `test_package/test_cdbfasta.py`（test_type=explicit，abduco 先例）：python subprocess 驱动安装到包内的真实二进制，5/5 断言通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认 `CXX ?= g++`，OHOS 无 g++ | Makefile 默认编译器 | 以 make 变量 `CXX=<clang++>` 显式传入（profile tools.build:compiler_executables 解析） |
| 2 | ENABLE_COMPRESSION=1 硬编码 -lz | 压缩功能必需 zlib | 声明 requires zlib/1.3.1.1 并注入 include/lib 路径 |
| 3 | 上游树无任何许可声明 | GitHub 仓库 license=None，源码无 LICENSE/版权头 | 配方 license 字段如实填 `Unknown`（aces_container 等先例），notes 说明 |

## 源码修改

- 无补丁、无源码修改

## 依赖版本

- zlib/1.3.1.1（制品仓二进制）

## 验证结果

```bash
conan create archives/c/cdbfasta/1.00-git20230710.da8f5ba -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# G2 通过：双工具编译、build() 行为流 3 步通过、test_package 5/5 断言通过
```

## 注意事项

- 上游无测试套件，行为验证由配方内工作流与消费者测试承担，已如实申报
- package_type=application，软件级 commands.json 已声明（cdbfasta/cdbyank 双命令）
- 版本目录 status 为 built：conan-verify/本地验证通过，未发布
---

**编译结束**: 2026-09-06 02:36
**最终状态**: built
