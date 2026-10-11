cmake_minimum_required(VERSION 3.5)
project(ydotool_consumer_test C)

# mock_daemon.c is a userspace AF_UNIX datagram peer implementing the
# ydotoold-side wire protocol, so the packaged client can be verified without
# /dev/uinput (which HarmonyOS PC restricts for ordinary user processes).
add_executable(mock_daemon mock_daemon.c)
