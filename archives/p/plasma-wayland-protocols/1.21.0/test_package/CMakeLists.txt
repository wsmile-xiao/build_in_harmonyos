cmake_minimum_required(VERSION 3.16)
project(pwp_consumer_test C)

# cmake_find_mode=none:上游 Config 包不在 CMAKE_PREFIX_PATH,
# 消费者显式加目录(kwayland 6.7.2 配方同款消费方式)
list(PREPEND CMAKE_PREFIX_PATH "${PWP_SHARE_CMAKE}")
find_package(PlasmaWaylandProtocols 1.21 CONFIG REQUIRED)

# Config 包必须设置 PLASMA_WAYLAND_PROTOCOLS_DIR 且指向有效目录
if(NOT DEFINED PLASMA_WAYLAND_PROTOCOLS_DIR)
  message(FATAL_ERROR "PLASMA_WAYLAND_PROTOCOLS_DIR not set by the config package")
endif()
if(NOT IS_DIRECTORY "${PLASMA_WAYLAND_PROTOCOLS_DIR}")
  message(FATAL_ERROR "PLASMA_WAYLAND_PROTOCOLS_DIR is not a directory: ${PLASMA_WAYLAND_PROTOCOLS_DIR}")
endif()

# 32 个 XML = 30 协议 + 2 个向后兼容改名文件
file(GLOB XML_FILES "${PLASMA_WAYLAND_PROTOCOLS_DIR}/*.xml")
list(LENGTH XML_FILES XML_COUNT)
if(NOT XML_COUNT EQUAL 32)
  message(FATAL_ERROR "expected 32 XML files, got ${XML_COUNT}")
endif()

# 改名兼容文件与代表性协议必须在场
foreach(REQ screencast.xml plasma-virtual-desktop.xml
            plasma-window-management.xml org-kde-plasma-virtual-desktop.xml
            kde-output-device-v2.xml)
  if(NOT EXISTS "${PLASMA_WAYLAND_PROTOCOLS_DIR}/${REQ}")
    message(FATAL_ERROR "missing protocol XML: ${REQ}")
  endif()
endforeach()

message(STATUS "pwp consumer check PASS: ${XML_COUNT} XMLs in ${PLASMA_WAYLAND_PROTOCOLS_DIR}")

# 占位可执行文件:校验全部在 configure 阶段完成
add_executable(pwp_consumer_test main.c)
