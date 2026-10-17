# gslip

GNU SLIP — C++ 链表处理（SLIP）静态库。提供 SlipDatum/SlipHeader/SlipReader/
SlipWrite 等列表、读写与算子 API，头文件位于 `include/gslip/`，静态库 `libgslip.a`。
上游：https://www.gnu.org/software/gslip/

适配说明：OHOS 上以 clang++/libc++ 构建（-std=gnu++11），上游 TAP 测试套件
（SlipTest，21 个测试点）在配方 build() 内真实执行并通过。
