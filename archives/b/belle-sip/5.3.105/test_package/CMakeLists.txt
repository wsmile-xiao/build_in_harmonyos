cmake_minimum_required(VERSION 3.15)
project(test_belle_sip C)

# belle-sip links the Belledonne dependencies through the generated CMakeDeps
# configs; the crypto backend archives come with the bzrtp package, which is
# declared as a requirement of belle-sip.
find_package(belle-sip REQUIRED)
find_package(bctoolbox REQUIRED)
find_package(bzrtp REQUIRED)

add_executable(test_belle_sip test_belle_sip.c)
target_link_libraries(test_belle_sip PRIVATE belle-sip::belle-sip bctoolbox::bctoolbox bzrtp::bzrtp)
