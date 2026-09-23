cmake_minimum_required(VERSION 3.15)
project(test_tag_c C CXX)

find_package(taglib CONFIG REQUIRED)

# Pure-C consumer of the official C bindings, exactly like ezstream:
# include <taglib/tag_c.h> and link the tag_c component.
add_executable(test_tag_c test_tag_c.c)
target_link_libraries(test_tag_c PRIVATE taglib::tag_c)
# The source is plain C, but libtag_c/libtag carry the C++ runtime, so the
# link must be driven by the C++ linker (upstream does the equivalent on
# Solaris by linking Crun explicitly for C consumers).
set_target_properties(test_tag_c PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME test_tag_c COMMAND test_tag_c)
