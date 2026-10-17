cmake_minimum_required(VERSION 3.16)
project(test_boost_compiled_components LANGUAGES CXX)

find_package(
    Boost 1.91.0.1 CONFIG REQUIRED
    COMPONENTS atomic date_time regex filesystem graph program_options iostreams system thread
)

enable_testing()

function(add_boost_component_test target source)
    add_executable(${target} ${source})
    target_compile_features(${target} PRIVATE cxx_std_17)
    add_test(NAME ${target} COMMAND ${target})
endfunction()

add_boost_component_test(boost_component_unit unit.cpp)
target_link_libraries(
    boost_component_unit
    PRIVATE Boost::regex Boost::filesystem Boost::program_options
)

add_boost_component_test(boost_redex_iostreams integration.cpp)
target_link_libraries(boost_redex_iostreams PRIVATE Boost::iostreams)

add_boost_component_test(boost_atomic_contract atomic.cpp)
target_link_libraries(boost_atomic_contract PRIVATE Boost::atomic)

add_boost_component_test(boost_date_time_contract date_time.cpp)
target_link_libraries(boost_date_time_contract PRIVATE Boost::date_time)

add_boost_component_test(boost_graph_contract graph.cpp)
target_link_libraries(boost_graph_contract PRIVATE Boost::graph)

add_boost_component_test(
    boost_graph_upstream_disjoint_set
    upstream/disjoint_set_test.cpp
)
target_link_libraries(boost_graph_upstream_disjoint_set PRIVATE Boost::graph)

add_boost_component_test(boost_ohos_portability ohos_portability.cpp)
target_link_libraries(
    boost_ohos_portability
    PRIVATE Boost::filesystem Boost::thread
)
