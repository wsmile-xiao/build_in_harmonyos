cmake_minimum_required(VERSION 3.15)
project(iir1_consumer LANGUAGES CXX)

find_package(iir CONFIG REQUIRED)

add_executable(iir1_consumer test_package.cpp)
target_compile_features(iir1_consumer PRIVATE cxx_std_11)
target_link_libraries(iir1_consumer PRIVATE iir::iir)

enable_testing()
set(CONSUMER_CASES
  butterworth-lowpass-2
  butterworth-lowpass-4
  butterworth-highpass-2
  butterworth-highpass-4
  butterworth-bandpass-2
  butterworth-bandpass-4
  butterworth-bandstop-2
  butterworth-bandstop-4
  butterworth-lowshelf-2
  butterworth-lowshelf-4
  butterworth-highshelf-2
  butterworth-highshelf-4
  butterworth-bandshelf-2
  butterworth-bandshelf-4
  chebyshev1-lowpass-2
  chebyshev1-lowpass-4
  chebyshev1-highpass-2
  chebyshev1-highpass-4
  chebyshev1-bandpass-2
  chebyshev1-bandpass-4
  chebyshev1-bandstop-2
  chebyshev1-bandstop-4
  chebyshev1-lowshelf-2
  chebyshev1-lowshelf-4
  chebyshev1-highshelf-2
  chebyshev1-highshelf-4
  chebyshev1-bandshelf-2
  chebyshev1-bandshelf-4
  chebyshev2-lowpass-2
  chebyshev2-highpass-2
  chebyshev2-bandpass-2
  chebyshev2-bandstop-2
  chebyshev2-lowshelf-2
  chebyshev2-highshelf-2
  chebyshev2-bandshelf-2
  rbj-lowpass
  rbj-highpass
  rbj-bandpass1
  rbj-bandpass2
  rbj-bandstop
  rbj-notch
  rbj-lowshelf
  rbj-highshelf
  rbj-bandshelf
  rbj-allpass
  invalid-parameters
)

foreach(case IN LISTS CONSUMER_CASES)
  add_test(NAME consumer_${case} COMMAND iir1_consumer ${case})
endforeach()
