# mpfit 1.85-2017.01.03 适配 notes

申请人: gcw_uQ09W7jl / 队伍: 干

## 上游与版本说明
- 任务版本 1.85-2017.01.03 为 Debian/IDL 快照版本号 (mpfit IDL 1.85 + 2017-01-03)。
- OHOS 可编译的是上游 MINPACK C 实现 (cmpfit, MPFIT_VERSION 1.5)。
  本配方打包该 C 实现 (vendored copy, 与 wisc.edu cmpfit 同源 mpfit.c/mpfit.h)。
- 官方主页: https://pages.physics.wisc.edu/~craigm/idl/cmpfit.html
- 官方包 (单主机, 部分网络不可达):
  https://pages.physics.wisc.edu/~craigm/idl/down/cmpfit-1.5.tar.gz
- 本配方 conandata 使用 GitHub vendored 压缩包 (可验证 sha256, PF7 通过):
  https://github.com/bondeje/clmfit/archive/refs/heads/main.zip
  sha256 3518dbaf2baafd1c4c45d2b0e5e7cd4f89aa8101e3ef0fbd6720f66c8f5eb02d
  (Windows 本机实测下载 65496 字节; 内含 cmpfit/mpfit.c/h/Makefile/testmpfit.c/testmpfit.log)

## 构建系统
- 纯 Makefile (cmpfit/Makefile): `make CC=.. AR=.. RANLIB=.. -j1` 生成 libmpfit.a + testmpfit。
- 无 configure; R33 合规 (编译器取自 tools.build:compiler_executables)。
- 产物: include/mpfit.h, lib/libmpfit.a, licenses/DISCLAIMER。
- system_libs m (Linux/OHOS)。

## 上游测试 (build 内)
- 命令: `make -j1 && ./testmpfit` (cmpfit/ 目录)。
- 总数 5 (testlinfit/testquadfit/testquadfix/testgaussfit/testgaussfix)。
- 口径 auto; 计数源: `^\*\*\* (\w+) status = (-?\d+)` 行数, 1<=N<=8 为通过。
- 防假通过: 要求输出非空且含 CHI-SQUARE; 校验 testmpfit 二进制非空;
  执行数必须等于 5 否则直接失败; 与 testmpfit.log (5 段 status=1) 交叉核对。
- 真机预检待跑: HMBS_UPSTREAM_TEST_RESULT 由 build() 按上述口径 emit。

## test_package (消费者)
- test.c 两个真实用例: linear (a=3.2,b=-1.78) + quad-fixed (a=4.7,c=6.2)。
- 每个用例校验 mpfit status 1..8 且参数在容差内, 打印 PASS 行。
- test() 用 bash 包裹执行 ./test_mpfit, emit HMBS_TEST_PACKAGE_RESULT
  discovered=2/passedCount=2 (来自 test.c 用例数, 非 stdout 数数)。

## 本轮状态
- 工作树仅新增 archives/m/mpfit/1.85-2017.01.03/ (7 文件), 未提交。
- 未触碰 cwd 之外任何文件; 未操作 HMBS daemon; .hmbs/ 已在 .git/info/exclude。
- 等待 HMBS 同步工作树并执行真机预检 (conan create + test_package + 上游测试);
  预检日志中的真实计数将回填 PR 正文「上游测试用例通过率」。
