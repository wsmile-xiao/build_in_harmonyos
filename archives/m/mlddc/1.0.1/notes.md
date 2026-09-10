# mlddc 1.0 适配笔记

## 上游信息
- 上游仓库: https://github.com/OS2World/APP-INTERNET-mlddc
- 上游源码版本: MLDDC 3.2.0（生态补丁版本 1.0，上游无官方 tag）
- 功能: Monolith (ml.org) 动态 DNS 服务客户端（1997 年，纯 C）

## 编译环境
- 构建系统: 直接 clang 编译（Makefile 等价），无 configure
- 编译器: clang（hnp 工具链）
- 状态: 成功

## 编译要点
- CFLAGS 追加 `-fgnu89-inline`：netio.h 中 `inline extern void Disconnect(...)` 
  在 C99 语义下会被 mlddc.c 与 netio.c 两个 TU 各自实例化，产生
  `ld.lld: error: duplicate symbol: Disconnect`；gnu89-inline 语义下
  inline 定义不产生外部符号，与 1997 年 gcc 编译行为一致。

## 运行验证
- 无输入运行: 输出版本 banner + "Invalid user data"，退出码 10（预期错误路径）
- deactivate 模式（echo d | mlddc）: 退出码 0

## 测试
- test_package: fork+exec 运行包内 mlddc，断言无输入退出码 10
  （证明程序可执行、链接正常，非崩溃/加载失败）
---

## 1.0.1 版本说明（适配修复版）

- 上游 MLDDC 3.2.0 未变（生态补丁版本 1.0.1 = 对已发布 1.0 的适配修复）。
- 修复动因（R37/L0j）：制品仓已存在 mlddc/1.0（2026-08-20 发布的旧配方），
  本次按 conan-verify G1 门禁修正配方结构（新增 package_info/export_sources/
  apply_conandata_patches，conandata 改 sources: 段，编译器改从 Conan conf 读取），
  配方内容与已发布 1.0 不同 → 版本号必须递增为 1.0.1（cnb.cool 不支持同版本
  多 recipe revision 并存）。
- 修复点：
  1. G1 结构完整性：补 package_info()（纯 CLI，声明 bin）、export_sources()、
     build() 中调用 apply_conandata_patches()；conandata.yml 改用 sources: 段。
  2. R33：编译器不再从 shell 环境变量（CC/CFLAGS）读取，改从
     self.conf.get("tools.build:compiler_executables") dict 读取，CI 干净环境可复现。
  3. 修复 get() 因 URL 无扩展名导致的 BadZipFile：conandata sources 段显式声明
     filename: "mlddc-master.tar.gz"。
- 验证：conan-verify G0-G4/L2/L4/L5 全过；conan create 从源码构建成功；
  test_package 通过（无输入退出码 10 预期错误路径）。
---

**编译结束**: 2026-09-06 10:23
**最终状态**: published
