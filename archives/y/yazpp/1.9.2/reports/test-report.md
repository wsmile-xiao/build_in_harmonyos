# yazpp 1.9.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (OHOS SDK 26.0.0.18)
- Conan 2.29.1 (CONAN_HOME=~/tmp/ch/home-ds12-yazpp)

## Verification

- `conan-verify yazpp 1.9.2`: exit 0（G0/G1/G2/G3 + L2/L4/L5 全 PASS）
- 探索构建（真机 -j1）：CONFIGURE_RC=0 / MAKE_RC=0 / INSTALL_RC=0 / CHECK_RC=0
- W3 本地 CI 模拟（finish step [5/10]）：通过
- 源码: sha256=92516d1d889dd6ff617d92b3af0ba28861dbd1fc436cfcadd0fde65ca9f34fe9
  （https://download.indexdata.com/pub/yazpp/yazpp-1.9.2.tar.gz）

## 上游测试（make -C src check，配方 build() 内真实执行）

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static | 2 | src/Makefile.am：check_PROGRAMS = test_query test_gdu；TESTS = $(check_PROGRAMS) |
| N_registered | 2 | 与 N_static 同口径 |
| N_executed | 2 | PASS: 2 / FAIL: 0（VirtualRunEnv 注入依赖库路径） |
| 未执行分类 | 2 处 | zlint/ 与 zoom/ 为 noinst 样例（上游无 TESTS 注册）；doc/ 无测试目标 |
| N_consumer | 1 | consumer_test：链接静态 libyazpp.a+libyaz.a，Yaz_Z_Query 解析/拷贝/回印 3 组断言，签名后真机运行退出码 0 |

## test_package

消费者程序 `consumer_test` 以库使用者身份链接 libyazpp/libyaz，调用
`yazpp_1::Yaz_Z_Query` 完成 Type-1 查询解析、对象拷贝与 print 回印，断言
三组输出（"@and a b"、"x"、空查询）逐字符相等，退出码 0 判定通过。

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Result

PASS — 可进入提交流程（当前 HEAD 绑定的 conan create 与测试证据）。
