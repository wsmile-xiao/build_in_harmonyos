cmake_minimum_required(VERSION 3.15)
project(libfaketime_test_package C)

# libfaketime is an LD_PRELOAD payload: nothing links against it, so these four
# programs are compiled against libc only and the assertions happen at run time
# once the recipe has injected the preloaded library.
foreach(probe clock_probe cond_probe abi_probe misc_probe)
  add_executable(${probe} ${probe}.c)
  target_link_libraries(${probe} PRIVATE dl)
endforeach()
