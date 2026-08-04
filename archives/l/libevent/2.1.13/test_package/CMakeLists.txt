cmake_minimum_required(VERSION 3.15)
project(test_libevent LANGUAGES C)

find_package(Libevent CONFIG REQUIRED)
enable_testing()

function(add_libevent_consumer target source component)
    add_executable(${target} ${source})
    target_link_libraries(${target} PRIVATE ${component})
    add_test(NAME ${target} COMMAND ${target})
    set_tests_properties(${target} PROPERTIES TIMEOUT 60)
endfunction()

add_libevent_consumer(libevent_core_consumer core.c libevent::core)
add_libevent_consumer(libevent_extra_consumer extra.c libevent::extra)
add_libevent_consumer(libevent_combined_consumer combined.c libevent::event)

if(NOT WIN32)
    add_libevent_consumer(libevent_pthreads_consumer pthreads.c libevent::pthreads)
endif()
