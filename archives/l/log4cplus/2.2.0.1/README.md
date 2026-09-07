# log4cplus 2.2.0.1 HarmonyOS PC adaptation

This recipe builds log4cplus with Conan and CMake for Linux/OHOS. The recipe
keeps the core `Threads` dependency and disables optional Qt and iconv
backends so the OHOS binary closure stays task-local and auditable.

The upstream test suite is compiled with CTest enabled. Runtime execution of
cross-built tests is deferred to target validation; the consumer test exercises
the installed CMake package and the public logger API.
