cmake_minimum_required(VERSION 3.5)
project(test_hoel_package C)

find_package(Hoel 1.4.29 REQUIRED)
# hoel.h includes <jansson.h>/<yder.h>/<orcania.h> in its public API
# surface (upstream HoelConfig does not re-export them).
find_package(jansson 2.14 REQUIRED)
find_package(Yder 1.4.20 REQUIRED)
find_package(Orcania 2.3.3 REQUIRED)
find_package(sqlite3 3.53.4 REQUIRED)

add_executable(test_hoel src/test_hoel.c)
target_link_libraries(test_hoel PRIVATE
    $<IF:$<TARGET_EXISTS:Hoel::Hoel-static>,Hoel::Hoel-static,Hoel::Hoel>
    jansson::jansson
    sqlite3::sqlite3
    $<IF:$<TARGET_EXISTS:Yder::Yder-static>,Yder::Yder-static,Yder::Yder>
    $<IF:$<TARGET_EXISTS:Orcania::Orcania-static>,Orcania::Orcania-static,Orcania::Orcania>)
