# test_package/CMakeLists.txt
#
# ttf-cousine 是纯字体资源包，test_package 不需要 CMake 编译验证。
# 实质性依赖验证（R34）由 conanfile.py 的 test() 方法直接执行：
#   - 检查 resdirs 下至少 12 个 .ttf 文件
#   - 验证每个 TTF 文件的 TrueType/OpenType 魔数 (0x00010000 / 'true' / 'OTTO')
#   - 验证文件大小 >= 12 字节
#
# 此 CMakeLists.txt 仅用于满足 CI L0c 结构检查（test_package 需有构建脚本），
# 不产生任何构建目标。

cmake_minimum_required(VERSION 3.15)
project(test_ttf_cousine NONE)

# 无构建目标 — 字体验证在 conan test 阶段由 Python test() 完成
message(STATUS "ttf-cousine test_package: font validation handled by conanfile.py test()")
