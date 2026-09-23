cmake_minimum_required(VERSION 3.16)
project(test_daa2iso C)

add_executable(test_daa2iso test_daa2iso.c)

# 说明: 本测试需要 argv[1] 传入「包内已安装的 daa2iso 路径」，该路径在配置期不可知
# （由 conan test() 阶段提供），故不注册 add_test（注册无参 ctest 用例必然失败且与
# 真实调用方式矛盾）。真实入口: test_package/conanfile.py 的 test()
