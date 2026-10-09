cmake_minimum_required(VERSION 3.16)
project(qmc VERSION 0.94 LANGUAGES CXX)

add_executable(qmc
    analyse.cc
    bool.cc
    compare.cc
    core.cc
    createmin.cc
    eval_dub.cc
    inputpr.cc
    main.cc
    msg.cc
    parameter.cc
    table.cc
)
target_include_directories(qmc PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
install(TARGETS qmc RUNTIME DESTINATION bin)
