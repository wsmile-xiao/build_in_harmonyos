cmake_minimum_required(VERSION 3.15)
project(crazywa LANGUAGES C)
add_executable(crazywa upstream/dropper.c)
set_target_properties(crazywa PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
