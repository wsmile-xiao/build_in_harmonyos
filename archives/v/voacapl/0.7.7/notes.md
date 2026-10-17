# voacapl 0.7.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-25
- 编译器: flang-ohos/20.1.0（LLVM Flang，作 F77/FC 驱动）+ clang 15.0.4（SDK）
- 状态: built

## 编译步骤

```bash
# 1. configure（flang 参数注入）
./configure \
  F77=<flang>/bin/flang FC=<flang>/bin/flang \
  "FFLAGS=--target=aarch64-unknown-linux-ohos --sysroot=$SDK/sysroot -resource-dir=$SDK/llvm/lib/clang/15.0.4" \
  "FCFLAGS=同上" "LDFLAGS=-L$SDK/llvm/lib/aarch64-linux-ohos -L<flang>/lib -lm"

# 2. 编译 + 安装
make -j1 && make install DESTDIR=$PREFIX

# 3. 测试
make check        # 上游无自动化测试注册（check 目标为空）
# p2p 实测：voacapl <itshfbc_root> 处理 tests/p2p/test01.dat EXIT=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建临时目录 Permission denied | E114：HMDFS 上 `umask 077 && mktemp -d` 产生不可写 `drwx--S---` 目录 | 补丁 0001：configure 移除 umask 077 |
| 2 | flang: unknown argument '-fno-sign-zero' | gfortran 专用选项 | 补丁 0002-0006：Makefile 移除该 flag |
| 3 | flang: Could not parse FORMAT(1H,...) | FORTRAN 66 Hollerith 编辑描述符，flang 不支持 | build() 内联适配：替换为 1X / 字符常量 |
| 4 | undefined symbol: unlink_ | 源码调用 gfortran 扩展过程 call unlink()，flang 无内建 | build() 内联适配：新增 ohos_unlink_shim.for（OPEN/CLOSE STATUS='DELETE' 等价实现） |
| 5 | install-data-hook 内 fof2bin 打不开 .asc | DESTDIR 长路径赋给 len=128 变量被截断 | build() 内联适配：working_dir/filein 扩至 len=512 |
| 6 | conan create test_package: voacapl: inaccessible or not found | 二进制运行期缺 libc++_shared.so（SDK target_lib）与 flang 包 lib | 配方 package_info() 静态注入 runenv LD_LIBRARY_PATH |
| 7 | automake all-am: No rule to make target news/config.txt | out-of-source 构建时 dist 数据文件在 source 目录 | 配方 build() 复制数据树到 build 目录 |

## 源码修改

补丁文件（patches/ 0001-0006，conandata.yml 已声明）：
- 0001-configure.patch：移除 config.status 临时目录创建中的 umask 077（E114）
- 0002-0006：Makefile.in/.am 移除 -fno-sign-zero、接入 ohos_unlink_shim.for

build() 内联适配（conanfile.py `_apply_source_adaptations()`，因 CRLF 行尾
补丁会被 refresh-patch 重建清走，参照 4ti2 先例）：
- Hollerith 编辑描述符替换（hfmufs.for/hfmufs2.for/outant.for：`FORMAT(1H`→`1X`、`2h`→字符常量）
- 新增 src/voacapw/ohos_unlink_shim.for（gfortran 扩展过程 `call unlink` 的等价实现）
- coeffs 工具路径变量 len=128→512（coeffbin/coefbinw/fof2bin/fof2binw.f）

## 依赖版本

- tool_requires: flang-ohos/20.1.0（制品仓已有，netcdf-fortran/blas 先例）

## 验证结果

- conan create：G1-G4 全 PASS（配方验证通过，可标记 published）
- make check：上游无自动化测试注册
- p2p 实测：voacapl 处理 test01.dat EXIT=0；与参考输出差异为平台性
  （参考为 Windows 生成：`\SAMPLE.00` 路径/CRLF/VOACAP 无 L；本机 `/sample.00`、LF、
  VOACAP L 标记；数值差异 ≤1dB 属浮点/平台差异）

## 注意事项

- 纯 Fortran 项目：无外部第三方库依赖，全部为自研源码。
- flang 编译与运行期都依赖 SDK 与 flang 包运行库，LD_LIBRARY_PATH 必须注入完整。
- 上游 tag 为 `v0.7.7`（非 `0.7.7`），conandata.yml URL 已指向 tag 名。
---

**编译结束**: 2026-09-25 19:34
**最终状态**: built
