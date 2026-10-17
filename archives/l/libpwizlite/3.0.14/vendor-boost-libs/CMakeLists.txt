# Vendored boost thread/chrono compiled sources (boostorg/thread and
# boostorg/chrono, tag boost-1.84.0 — matching the boost/1.84.0 registry
# headers) for the libpwizlite recipe.
#
# The ohpcd registry boost packages ship only filesystem/iostreams/
# program_options/regex compiled archives; pwiz's SpectrumWorkerThreads
# uses boost::thread/chrono compiled symbols (enter_once_region,
# thread::start_thread_noexcept, chrono::steady_clock::now, ...). These
# few upstream sources are compiled into the package to close the gap.
cmake_minimum_required(VERSION 3.15)
project(boost_vendored_libs CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Boost REQUIRED)   # headers from the conan boost dependency
find_package(Threads REQUIRED)

add_library(boost_thread_vendored STATIC
    src/pthread/once.cpp
    src/pthread/once_atomic.cpp
    src/pthread/thread.cpp
    src/future.cpp
    src/tss_null.cpp
)
target_include_directories(boost_thread_vendored PUBLIC ${Boost_INCLUDE_DIRS})
target_link_libraries(boost_thread_vendored PUBLIC Threads::Threads)
target_compile_definitions(boost_thread_vendored PUBLIC
    BOOST_THREAD_USE_LIB
    # OHOS musl has no pthread_setcancelstate; boost provides this escape
    # hatch (same as the boost/1.85.0 recipe's R8 note).
    BOOST_SP_NO_PTHREAD_SETCANCELSTATE)

add_library(boost_chrono_vendored STATIC
    chrono/chrono.cpp
    chrono/process_cpu_clocks.cpp
    chrono/thread_clock.cpp
)
target_include_directories(boost_chrono_vendored PUBLIC ${Boost_INCLUDE_DIRS})
target_compile_definitions(boost_chrono_vendored PUBLIC
    BOOST_CHRONO_STATIC_LINK
    BOOST_SP_NO_PTHREAD_SETCANCELSTATE)
