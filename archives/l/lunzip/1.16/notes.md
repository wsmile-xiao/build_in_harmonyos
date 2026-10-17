# lunzip 1.16 — OpenHarmony 编译记录

## 基本信息
- 软件: lunzip
- 版本: 1.16
- 构建系统: autotools (custom configure + Makefile.in, C)
- 目标: ohos-aarch64 (os=OHOS, arch=armv8, clang 15)
- 上游: https://download.savannah.gnu.org/releases/lzip/lunzip/lunzip-1.16.tar.gz
- SHA256: f13809a1aeaf953f32b07f822c3804bfb11056c08d465b93750b4e45190becda
- License: GPL-2.0-or-later

## 编译指导
lunzip 与 lzip 同作者 (Antonio Diaz Diaz)，使用相同的自定义 configure +
Makefile.in 构建框架，但 lunzip 是纯 C 程序 (CC)，而 lzip 是 C++ (CXX)。

- E095: lunzip 的 configure 脚本 (非 autoconf) 不读取 $CC 环境变量，必须以
  `CC=<compiler>` 命令行参数形式传入。conanfile.py 的 generate() 从 Conan conf
  `tools.build:compiler_executables` 取得 clang 路径，以 `CC=` 参数传入 (R33)。
- configure 默认 CFLAGS='-Wall -W -O2'，适用于 CLI 二进制，无需额外平台标志；
  clang 15 在 OHOS aarch64 上默认产出 PIE/RELRO/NX，满足 L4 安全扫描。
- 上游测试: `make check` 运行 testsuite/check.sh，覆盖解压往返、坏输入、截断、
  多 member 文件、header 变体等，在 build() 中真实执行 (CI L1c 验证)。

## 补丁清单
无补丁 (零 patch)。lunzip 1.16 上游源码在 OHOS aarch64 + clang 15 上原生编译
通过，无需任何源码修改。

## 已知限制
无。

## 功能验证
- make check: 上游测试套件全部通过 (tests completed successfully)。
- test_package: 解压上游固定 fixture (test.txt.lz, 7341B) 与明文 test.txt
  (36301B) 字节级 cmp 完全一致；stdout 解压 (-cd) 结果一致；完整性测试
  (-t) 成功。Fixture 取自上游 lunzip-1.16/testsuite/，无需 host lzip。
