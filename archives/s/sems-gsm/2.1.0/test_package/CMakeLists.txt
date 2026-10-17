cmake_minimum_required(VERSION 3.15)
project(test_sems_consumer C)

# sems-gsm is an application package: its deliverables are the SEMS plug-in
# (lib/sems/plug-in/*.so) and the sbin/ tools, none of which are exposed
# through cpp_info.  The consumer therefore opens the package's own plug-in
# with dlopen() at test time (SEMS_PACKAGE_FOLDER is exported by test()).
add_executable(test_sems_consumer test_sems_plugin.c)
target_link_libraries(test_sems_consumer ${CMAKE_DL_LIBS})

# The plug-in imports SEMS core symbols (log_level, log_level2str,
# log_stderr, run_log_hooks).  At runtime the loader resolves them against
# sbin/sems; here the test binary itself provides them, so it must export
# its dynamic symbols (same mechanism, real plug-in relocation check).
target_link_options(test_sems_consumer PRIVATE -Wl,--export-dynamic)

enable_testing()
add_test(NAME sems_consumer COMMAND test_sems_consumer)
