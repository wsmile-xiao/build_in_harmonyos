cmake_minimum_required(VERSION 3.16)
project(test_crashme C)

add_executable(test_crashme test_crashme.c)

# 说明: 本测试需要 argv[1]/argv[2] 传入「包内已安装的 crashme / pddet 路径」，
# 该路径在配置期不可知（由 conan test() 阶段提供），故不注册 add_test。
# 真实入口: test_package/conanfile.py 的 test()
