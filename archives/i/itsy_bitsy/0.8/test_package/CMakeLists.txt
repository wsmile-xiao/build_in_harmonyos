cmake_minimum_required(VERSION 3.15)
project(test_itsy_bitsy LANGUAGES CXX)

find_package(itsy.bitsy CONFIG REQUIRED)

add_executable(test_itsy_bitsy test_itsy_bitsy.cpp)
target_compile_features(test_itsy_bitsy PRIVATE cxx_std_17)
target_link_libraries(test_itsy_bitsy PRIVATE itsy::bitsy)

enable_testing()

# One CTest entry per behavioural case so a failure names the API that broke.
# The list must stay in sync with the cases in test_itsy_bitsy.cpp.
set(itsy_bitsy_consumer_cases
	binary_digits
	bit_vector
	bit_vector_flip
	popcount
	bit_span)

foreach(case_name IN LISTS itsy_bitsy_consumer_cases)
	add_test(NAME ${case_name} COMMAND test_itsy_bitsy ${case_name})
endforeach()
