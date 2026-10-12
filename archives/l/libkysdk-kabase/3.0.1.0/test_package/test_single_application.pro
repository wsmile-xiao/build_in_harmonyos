# test_single_application.pro — 消费者测试工程（qmake）
# INCLUDEPATH / LIBS 由 test_package/conanfile.py build() 通过 qmake 命令行注入
# （被测包 include/ 与 lib/ 目录）。
QT += core network widgets
TEMPLATE = app
TARGET = test_single_application
CONFIG += console c++11
CONFIG -= app_bundle
SOURCES += test_single_application.cpp
