cmake_minimum_required(VERSION 3.16)
project(netdiscover VERSION 0.21 LANGUAGES C)

if(NOT NETDISCOVER_SOURCE_DIR)
  message(FATAL_ERROR "NETDISCOVER_SOURCE_DIR is required")
endif()

find_package(libpcap CONFIG REQUIRED)
find_package(Threads REQUIRED)

set(NETDISCOVER_SRC "${NETDISCOVER_SOURCE_DIR}/src")
add_executable(netdiscover
  "${NETDISCOVER_SRC}/main.c"
  "${NETDISCOVER_SRC}/ifaces.c"
  "${NETDISCOVER_SRC}/screen.c"
  "${NETDISCOVER_SRC}/fhandle.c"
  "${NETDISCOVER_SRC}/misc.c"
  "${NETDISCOVER_SRC}/data_reply.c"
  "${NETDISCOVER_SRC}/data_request.c"
  "${NETDISCOVER_SRC}/data_unique.c"
)
target_include_directories(netdiscover PRIVATE
  "${NETDISCOVER_SOURCE_DIR}"
  "${NETDISCOVER_SRC}"
)
target_compile_options(netdiscover PRIVATE -fcommon)
target_link_libraries(netdiscover PRIVATE libpcap::libpcap Threads::Threads)
set_target_properties(netdiscover PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED YES)

include(GNUInstallDirs)
install(TARGETS netdiscover RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(
  FILES "${NETDISCOVER_SOURCE_DIR}/doc/netdiscover.8"
  DESTINATION "${CMAKE_INSTALL_MANDIR}/man8"
)
