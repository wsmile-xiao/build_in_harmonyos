# photopc 3.07 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (OHOS SDK 26.0.0.18)
- Conan 2.29.1 (CONAN_HOME=~/tmp/ch/home-ds12-photopc)

## Verification

- `conan-verify photopc 3.07`: exit 0（G0/G1/G2/G3 + L2/L4/L5 全 PASS）
- 探索构建（真机 -j1）：CONFIGURE_RC=0 / MAKE_RC=0 / INSTALL_RC=0
- W3 本地 CI 模拟（finish step [5/10]）：通过
- 源码: sha256=b42824a7cf7ce76e8e8e81345463d25b8dadd16799920da062aa36aa6ed8489c
  （https://downloads.sourceforge.net/project/photopc/photopc/3.07/photopc-3.07.tar.gz）

## 上游测试

上游无测试套件（Makefile.am 无 TESTS/check_PROGRAMS，树内无测试目录/框架）：
N_static=0 / N_registered=0 / N_executed=0，未执行分类=0（上游本来就没有）。
行为验证由消费者测试承担（赛道二消费者测试硬门禁）。

## test_package

消费者测试（consumer_test.py）对打包后的 photopc/epinfo 二进制做 4 组行为
断言（ELF 签名后真机执行）：

1. `epinfo -V` → rc=0 且输出含 "version 3.07"；
2. `epinfo <非EPSON文件>` → 解析路径执行，rc=1 且报
   "No camera-specific information in the file"；
3. `epinfo` 无参数 → 输出 usage；
4. `photopc` 无参数 → 设备 open/termios 错误路径（"open ... /dev/photopc" +
   "eph_open failed"）。

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Result

PASS — 可进入提交流程（当前 HEAD 绑定的 conan create 与测试证据）。
