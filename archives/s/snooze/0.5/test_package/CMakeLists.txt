cmake_minimum_required(VERSION 3.16)
project(test_snooze C)

add_executable(test_snooze test_snooze.c)

# 说明: 本测试需要 argv[1] 传入「包内已安装的被测二进制路径」，该路径在配置期
# 不可知（由 conan test() 阶段提供）。因此这里**不注册 add_test** —— 注册一个
# 无参数的 ctest 用例必然失败（被测程序要求 argv[1]），且与本测试的真实调用
# 方式矛盾。
# 真实执行入口: test_package/conanfile.py 的 test():
#   self.run(f'"{test_exe}" "{bin_path}"')
