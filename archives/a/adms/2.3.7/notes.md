# ADMS 2.3.7

The recipe builds the upstream `admsXml` generator with CMake. The upstream
testcase inputs that do not require external simulator checkouts are executed
during `build()`. The packaged tool is exercised again by `test_package`.
