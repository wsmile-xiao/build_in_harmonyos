cmake_minimum_required(VERSION 3.16)
project(shfm_ohos_consumer LANGUAGES C)

# The source lives in the directory that the packaged shfm printed on exit.
if(NOT SHFM_SELECTED_DIR)
  message(FATAL_ERROR "SHFM_SELECTED_DIR (directory printed by shfm) is required")
endif()
add_executable(shfm_ohos_consumer "${SHFM_SELECTED_DIR}/consumer.c")
