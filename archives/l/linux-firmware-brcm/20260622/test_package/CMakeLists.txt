cmake_minimum_required(VERSION 3.15)
project(linux_firmware_brcm_test LANGUAGES NONE)

# 25 项固件资源完整性断言入口：
# 由 test_package/conanfile.py 通过 bash test_resources.sh "<package>/res/brcm" 执行。
add_custom_target(test_resources
    COMMAND bash "${CMAKE_CURRENT_SOURCE_DIR}/test_resources.sh"
    COMMENT "Run 25 firmware resource integrity assertions"
)
