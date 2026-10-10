cmake_minimum_required(VERSION 3.15)
project(btrfs_consumer C)

find_package(libbtrfs-dev CONFIG REQUIRED)
add_executable(btrfs_consumer consumer.c)
target_link_libraries(btrfs_consumer PRIVATE libbtrfs-dev::libbtrfs-dev)
add_executable(btrfs_ohos_abi ohos_abi.c)
target_link_libraries(btrfs_ohos_abi PRIVATE libbtrfs-dev::libbtrfs-dev)
