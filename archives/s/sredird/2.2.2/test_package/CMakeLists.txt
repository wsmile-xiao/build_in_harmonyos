cmake_minimum_required(VERSION 3.15)
project(test_sredird C)

# sredird is a command-line tool (no headers or libraries): the consumer program
# below is compiled with the OHOS toolchain and drives the packaged bin/sredird
# over a socketpair (network side) and a pseudo terminal (serial side).
add_executable(rfc2217_client rfc2217_client.c)
