cmake_minimum_required(VERSION 3.15)
project(wren_cli C)

# 本文件由 conan 配方导出（不是上游文件）。上游用 premake 生成的
# projects/make/wren_cli.make 构建，但那份 makefile 把 -m64 / -L/usr/lib64 这类
# x86 开关写死在 64 位配置里，且把 deps/wren、deps/libuv 两份 vendored 源码一起
# 编进来；aarch64/OHOS 上改为用 CMake 编译 CLI 自身源码，虚拟机与 libuv 走制品仓
# 的发布包（wren::wren / libuv::libuv），避免同一份 libwren.a 以两个制品名交付。

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(wren REQUIRED)
find_package(libuv REQUIRED)

# util/test.py 固定到 <源码根>/bin/wren_cli 找被测程序（WREN_DIR 由自身路径反推），
# 所以输出目录要钉死在源码根 bin/，不能落到 CMake 默认构建目录。
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin")
foreach(_cfg DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${_cfg} "${CMAKE_CURRENT_SOURCE_DIR}/bin")
endforeach()

# 源文件清单 == 上游 projects/make/wren_cli.make 的 OBJECTS（逐条列出，不用 glob，
# 保证与上游一致且构建可复现）。
set(WREN_CLI_SOURCES
  src/cli/main.c
  src/cli/modules.c
  src/cli/path.c
  src/cli/vm.c
  src/module/io.c
  src/module/os.c
  src/module/repl.c
  src/module/scheduler.c
  src/module/timer.c)

add_executable(wren_cli ${WREN_CLI_SOURCES})
target_include_directories(wren_cli PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cli"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/module")
# 与上游 release_64bit 的 DEFINES 一致（NDEBUG 由 CMAKE_BUILD_TYPE=Release 提供）
target_compile_definitions(wren_cli PRIVATE _GNU_SOURCE)
# 上游 LIBS += -lpthread -ldl -lm（libuv 的事件循环/动态模块与 VM 的数学函数）
target_link_libraries(wren_cli PRIVATE wren::wren libuv::libuv pthread dl m)

# RUNPATH：制品仓的 libuv 是 shared（NEEDED = libuv.so.1），它落在 conan 缓存里的
# 依赖包目录，既不在包目录也不在系统搜索路径；不带 RUNPATH 时真机 musl 报
# "Error loading shared library libuv.so.1" + "Error relocating ... uv_*: symbol
# not found"。目录由配方通过 WREN_CLI_RPATH_DIRS 显式传入（conan 生成的 imported
# target 取不到 IMPORTED_LOCATION，而 CMake 交叉编译下的 BUILD_RPATH/INSTALL_RPATH
# 属性在本环境不落地），这里直接给链接器 -Wl,-rpath，与 archives/l/libe-book-tools
# 把 RUNPATH 指向 libxml2 包目录是同一种做法。
if(NOT WREN_CLI_RPATH_DIRS)
  message(FATAL_ERROR "WREN_CLI_RPATH_DIRS 为空：RUNPATH 无处可烧，请检查配方")
endif()
set(WREN_CLI_RPATH_FLAGS "")
foreach(_dir ${WREN_CLI_RPATH_DIRS})
  list(APPEND WREN_CLI_RPATH_FLAGS "-Wl,-rpath,${_dir}")
endforeach()
target_link_options(wren_cli PRIVATE ${WREN_CLI_RPATH_FLAGS})
set_target_properties(wren_cli PROPERTIES
  BUILD_RPATH "${WREN_CLI_RPATH_DIRS}"
  INSTALL_RPATH "${WREN_CLI_RPATH_DIRS}"
  BUILD_WITH_INSTALL_RPATH ON
  INSTALL_RPATH_USE_LINK_PATH OFF)

install(TARGETS wren_cli RUNTIME DESTINATION bin)

# 上游单元测试套件 test/unit（main.c + test.c + path_test.c），只依赖 src/cli/path.c。
# 输出单独放构建目录，避免混进 bin/ 被一起打包。
set(WREN_CLI_UNIT_DIR "${CMAKE_BINARY_DIR}/upstream-unit")
add_executable(path_test
  "${CMAKE_CURRENT_SOURCE_DIR}/test/unit/main.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/test/unit/test.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/test/unit/path_test.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cli/path.c")
target_include_directories(path_test PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cli"
  "${CMAKE_CURRENT_SOURCE_DIR}/test/unit")
target_link_libraries(path_test PRIVATE m)
set_target_properties(path_test PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${WREN_CLI_UNIT_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_RELEASE "${WREN_CLI_UNIT_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_DEBUG "${WREN_CLI_UNIT_DIR}")
