cmake_minimum_required(VERSION 3.15)
project(test_pcapplusplus CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PcapPlusPlus REQUIRED)

if(TARGET PcapPlusPlus::PcapPlusPlus)
  set(PCAPPLUSPLUS_LINK_TARGET PcapPlusPlus::PcapPlusPlus)
elseif(TARGET PcapPlusPlus::Pcap++)
  set(PCAPPLUSPLUS_LINK_TARGET PcapPlusPlus::Pcap++)
else()
  message(FATAL_ERROR "PcapPlusPlus CMake target not found in the installed package")
endif()

add_executable(test_pcapplusplus test_pcapplusplus.cpp)
target_link_libraries(test_pcapplusplus PRIVATE ${PCAPPLUSPLUS_LINK_TARGET})

enable_testing()
add_test(NAME test_pcapplusplus COMMAND test_pcapplusplus)
