cmake_minimum_required(VERSION 3.15)
project(achilles_consumer C)

# SDL (windowless video surface), GLU + OSMesa (the offscreen GL stack the
# simulator renders through).  The packaged application is tested separately by
# the Python consumer scripts.
find_package(SDL CONFIG REQUIRED)
find_package(glu CONFIG REQUIRED)
find_package(mesa CONFIG REQUIRED)

add_executable(test_gl_stack test_gl_stack.c)
target_link_libraries(test_gl_stack PRIVATE sdl::sdl glu::glu mesa::mesa)
