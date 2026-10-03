cmake_minimum_required(VERSION 3.15)
project(test_kunifiedpush CXX)

find_package(KUnifiedPush REQUIRED)

add_executable(test_kunifiedpush test.cpp)
# The project's install(EXPORT KUnifiedPushTargets) does not set a NAMESPACE,
# so the imported target is the plain "KUnifiedPush" (not KUnifiedPush::).
target_link_libraries(test_kunifiedpush KUnifiedPush)

enable_testing()
add_test(NAME test_kunifiedpush COMMAND test_kunifiedpush)
