# libsrtp 2.8.0 编译笔记

## 编译环境
- 系统: HarmonyOS NEXT
- 构建系统: cmake

## 编译步骤
1. cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
2. make && make test (12 passed)
3. make install

## 测试结果
aes_calc_128, aes_calc_256, sha1_driver, datatypes_driver, cipher_driver, kernel_driver, rdbx_driver, replay_driver, roc_driver, srtp_driver, test_srtp, rtpw_test 全部通过

## 交付物
- 静态库: libsrtp2.a
