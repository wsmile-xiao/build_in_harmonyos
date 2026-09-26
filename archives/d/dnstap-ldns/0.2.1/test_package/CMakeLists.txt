cmake_minimum_required(VERSION 3.15)
project(test_dnstap_ldns C)

# L0c 测试源：编译 test_dnstap_ldns.c（运行时以 <bin 路径> 参数调用已安装的
# dnstap-ldns 解码真实 dnstap 帧并断言输出；由 test_package/conanfile.py test()
# 以 absolute bin 路径执行）。不链接库目标，纯 CLI 消费者验证。
add_executable(test_dnstap_ldns test_dnstap_ldns.c)

enable_testing()
add_test(NAME test_dnstap_ldns COMMAND test_dnstap_ldns)