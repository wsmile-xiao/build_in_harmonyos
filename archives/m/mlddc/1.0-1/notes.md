# mlddc 1.0-1 适配笔记

## 上游信息
- 上游仓库: https://github.com/OS2World/APP-INTERNET-mlddc
- 上游源码版本: MLDDC 3.2.0（生态补丁版本 1.0-1，上游无官方 tag，取 master）
- 功能: Monolith (ml.org) 动态 DNS 服务客户端（1997 年，纯 C）

## 与 1.0 的差异（本目录自包含，不修改已发布的 1.0）
| 项 | 1.0 | 1.0-1 |
|---|---|---|
| 安装文件 | `bin/mlddc` + 文档 | `bin/mlddc` + `bin/mlupd` + `bin/mymldata` + 文档 |
| 编译器解析 | `os.environ["CC"]` 回退 `clang` | `tools.build:compiler_executables` > `CC` > `clang` |
| 可执行位 | 依赖上游 tarball 权限 | 打包后显式 `chmod 0o755` |
| 消费者测试 | 1 条（退出码 10） | 10 条（见下） |

## 编译环境
- 构建系统: 直接 clang 编译（Makefile 等价），无 configure
- 编译器: clang 15（OHOS 工具链；CI profile `/data/service/hnp/bin/clang`）
- 状态: 成功

## 编译要点
- CFLAGS 追加 `-fgnu89-inline`：netio.h 中 `inline extern void Disconnect(...)`
  在 C99 语义下会被 mlddc.c 与 netio.c 两个 TU 各自实例化，产生
  `ld.lld: error: duplicate symbol: Disconnect`；gnu89-inline 语义下
  inline 定义不产生外部符号，与 1997 年 gcc 编译行为一致。
- 上游 Makefile 的 `-m486 -malign-loops=0 ...` 是 1997 年 i386 gcc 选项，
  aarch64 clang 不识别，故 recipe 绕开 Makefile 直接驱动 clang。
- `SECURE=1` 分支（secure.c + OpenSSL）默认不编译，保持零外部依赖。

## 运行验证
- 无输入运行: 输出版本 banner + "Invalid user data"，退出码 10（预期错误路径）
- deactivate 模式（echo d | mlddc）: 退出码 0

## 测试（test_package，10 条断言）
1. `bin/mlddc` 存在
2. `bin/mlddc` 可执行（`access(X_OK)`）
3. `bin/mlddc` 是 ELF64 LSB 文件（魔数 + EI_CLASS + EI_DATA）
4. `bin/mlddc` 的 `e_machine == 0xB7`（AArch64，目标架构正确）
5. `bin/mlddc` 的 `e_type ∈ {ET_EXEC, ET_DYN}`（合法可执行文件，PIE 时打印提示）
6. 真实执行 `mlddc < /dev/null` 退出码 10（程序可运行，链接正常）
7. `bin/mlupd` 存在且可执行
8. `bin/mlupd` 以 `#!` 开头（shell 脚本，OH 原生 sh 可解析）
9. `bin/mymldata` 存在且为 3 行数据模板
10. `share/doc/mlddc/README` 已安装
