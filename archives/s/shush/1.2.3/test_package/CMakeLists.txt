cmake_minimum_required(VERSION 3.15)
project(test_shush C)

# Consumer program: drives the packaged bin/shush and also serves as the
# sendmail stand-in and the supervised job (see test_shush.c).
add_executable(test_shush test_shush.c)
