cmake_minimum_required(VERSION 3.15)
project(test_polkit C)

find_package(polkit CONFIG REQUIRED)

# Consumer of the upstream polkit-gobject-1 module (polkit-gobject-1.pc),
# i.e. the component that already existed in polkit/124.
add_executable(test_polkit test_polkit.c)
target_link_libraries(test_polkit PRIVATE polkit::gobject)

# Consumer of the upstream polkit-agent-1 module (polkit-agent-1.pc), the
# artifact this recipe provides on top of polkit/124: it must be reachable
# through the generated CMake component target polkit::agent.
add_executable(test_polkit_agent test_polkit_agent.c)
target_link_libraries(test_polkit_agent PRIVATE polkit::agent)
