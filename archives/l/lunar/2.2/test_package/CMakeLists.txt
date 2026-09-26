cmake_minimum_required(VERSION 3.16)
project(test_lunar C)

add_executable(test_lunar test_lunar.c)

# 说明: 本测试需要 argv 传入「包内已安装的被测二进制路径」（必需）与
# 「share/lunar 数据目录」（可选，用于 -b bitmap 用例）。这两个路径在 CMake
# 配置期不可知，由 conan test() 阶段提供。因此这里**不注册 add_test** ——
# 注册一个无参数的 ctest 用例必然失败（被测程序要求 argv[1]），且与本测试的
# 真实调用方式矛盾。
# 真实执行入口: test_package/conanfile.py 的 test():
#   self.run(f'"{test_exe}" "{bin_path}" "{data_dir}"')
