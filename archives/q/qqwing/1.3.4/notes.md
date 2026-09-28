# qqwing 1.3.4 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4（OHOS dev）+ GNU ld/ar 2.45
- 状态: built（本机前置 + 真机 shadow CI 全部通过，待 conan upload）

## 编译步骤

1. 源码: 官网 release tarball `https://qqwing.com/qqwing-1.3.4.tar.gz`
   （SHA256 `1753736c31feea0085f5cfac33143743204f8a7e66b81ccd17e249ecafba802f`）
2. 应用补丁 `patches/0001-config.sub-ohos.patch`（config.sub 识别 linux-ohos）
3. configure（用 CONFIG_SHELL 执行，注入 LD/AR/RANLIB，绕过 mktemp 权限问题）:
   ```bash
   bash ./configure --disable-shared --enable-static \
     --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
     --prefix="$PREFIX" --libdir="$PREFIX/lib" --includedir="$PREFIX/include"
   make -j1 && make install
   ```
4. 产物: `libqqwing.a`（静态库）+ `qqwing`（命令行工具）+ `qqwing.hpp`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不识别 linux-ohos triplet | 上游 config.sub (2014) kernel-os 验证列表缺 linux-ohos | `patches/0001-config.sub-ohos.patch` |
| 2 | 默认只建共享库 | configure.ac 用 `LT_INIT([disable-static])` | `--enable-static --disable-shared` |
| 3 | configure 无执行权限 | HMDFS 源码解压 owner 非当前用户、chmod 不生效（E087） | CONFIG_SHELL 显式执行 configure |
| 4 | libtool 找不到 ld | PATH 无 /data/service/hnp/bin，clang -print-prog-name=ld 返回相对名 | 命令内 `export LD=/data/service/hnp/bin/ld` |
| 5 | printenv Argument list too long | Environment.save_script 与 AutotoolsToolchain 聚合产生递归 source、环境无限累积 | 改为命令内 export，不用 Environment |
| 6 | config.status subs1.awk Permission denied | HMDFS mktemp -d 目录被剥夺 group 权限（E112/E011） | configure 前把 `(umask 077 &&` 改为 `(umask 022 &&` |
| 7 | libtool `false cru .libs/libqqwing.a` | libtool 找不到 ar（E012），AR 落为 false | 命令内 `export AR=/data/service/hnp/bin/ar RANLIB=.../ranlib` |
| 8 | test_package 找不到 cmake | cmake 不在 PATH | `self.conf.define("tools.cmake:cmake_program", "/data/service/hnp/bin/cmake")` |
| 9 | test 解验证失败 | countSolutions() 内部 reset() 清空 solution | test.cpp 在 hasUniqueSolution/countSolutionsLimited 前先读解 |

## 源码修改

- `patches/0001-config.sub-ohos.patch`: config.sub 两处 kernel-os 验证列表添加 `linux-ohos*`。对非 OHOS 平台透明。

## 依赖版本

无外部依赖（纯 C++ 标准库）。

## 验证结果

### 本机前置验证（W4）
- 补丁 `git apply --check` 通过；Python/YAML/JSON 结构检查通过
- OHOS aarch64 交叉编译（DevEco clang++ 15.0.4）: qqwing.cpp/main.cpp/test.cpp 语法通过，
  libqqwing.a + qqwing + test_qqwing 编译链接为 AArch64 ELF

### 真机 shadow CI（W5，10.62.178.77）
- conan create 成功（exit 0），L0/L1/L2/L4/L5 全部 pass
- L1e 破坏性反向验证通过（test 实质依赖 qqwing，R34）
- test_package 13/13 断言通过：
  getVersion/setPuzzle/solve/isSolved/getSolution/解逐格一致/解满足约束/
  hasUniqueSolution/countSolutionsLimited/generatePuzzle/生成解约束/生成解一致
- L2: `qqwing --version` OK；L5: bin/ 有内容

## 注意事项

1. 上游 C++ 无单元测试，`test/` 为 shell 集成测试（依赖 bash/perl），未在真机执行，
   test_package 用 C++ 程序直接验证核心 API
2. 静态库 + 静态链接工具，避免 .so 签名（E077）与运行时加载问题
3. 本库适配沉淀了 autotools 在 OHOS 上的完整避坑链（E087/E266/E112/E012 + cmake 路径），
   见 `_patch_configure_mktemp` 与 `_toolchain_prefix` 方法
