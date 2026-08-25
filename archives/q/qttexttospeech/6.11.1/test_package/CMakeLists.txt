cmake_minimum_required(VERSION 3.15)
project(test_qttexttospeech CXX)

# QtTextToSpeech 组件（QTextToSpeech API 编译链接验证）
# Qt6TextToSpeechConfig.cmake 未随包安装——绝对路径链接（见 conanfile.py 的 Qt6TextToSpeech_LIB_DIR）

add_executable(test_texttospeech test.cpp)
target_include_directories(test_texttospeech PRIVATE ${Qt6_INCLUDE_DIR} ${Qt6_INCLUDE_DIR}/QtCore ${Qt6TextToSpeech_INCLUDE_DIR} ${Qt6TextToSpeech_INCLUDE_DIR}/QtTextToSpeech)
target_link_libraries(test_texttospeech "${Qt6TextToSpeech_LIB_DIR}/libQt6TextToSpeech.so" "${Qt6Core_LIB_DIR}/libQt6Core.so")

enable_testing()
add_test(NAME test_texttospeech COMMAND test_texttospeech)
