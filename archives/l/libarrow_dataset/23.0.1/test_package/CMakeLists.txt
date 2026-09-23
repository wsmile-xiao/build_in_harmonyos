cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(Arrow REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)

# The dataset scanner projection ("Project({"values"})" internally builds a
# make_struct() compute expression) requires libarrow_compute's kernel
# registration (RegisterComputeKernels in initialize.cc of arrow_compute).
# For static linkage the consumer must link arrow_compute explicitly, matching
# upstream's arrow-dataset.pc "Requires: arrow-acero arrow-compute".
if (TARGET Arrow::arrow_shared)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_shared)
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_static)
endif()

# Link compute component (arrow_compute) - provides make_struct & friends
if (TARGET Arrow::arrow_compute_shared)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_compute_shared)
elseif(TARGET Arrow::arrow_compute_static)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_compute_static)
endif()

# Link acero component (arrow_acero) - hard dependency of dataset
if (TARGET Arrow::arrow_acero_shared)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_acero_shared)
elseif(TARGET Arrow::arrow_acero_static)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_acero_static)
endif()

# Link dataset component (arrow_dataset) - primary component under test
if (TARGET Arrow::arrow_dataset_shared)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_dataset_shared)
elseif(TARGET Arrow::arrow_dataset_static)
    target_link_libraries(${PROJECT_NAME} PRIVATE Arrow::arrow_dataset_static)
endif()

target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_20)
