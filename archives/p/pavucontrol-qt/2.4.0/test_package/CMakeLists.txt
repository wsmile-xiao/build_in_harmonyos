cmake_minimum_required(VERSION 3.18)
project(test_pavucontrol_qt C)

add_executable(test_pavucontrol_qt test.c)

enable_testing()
add_test(NAME test_pavucontrol_qt COMMAND test_pavucontrol_qt "${PAVUCONTROL_QT_BIN}")
