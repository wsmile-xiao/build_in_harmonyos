# Test-only concrete backend

The 2019-05-17 package snapshot contains the generic core and utils headers but
no concrete backend. This consumer test compiles the upstream simpleExecutable
backend from the same official repository at commit
40bdec00e99f8ea1b96c3dac0a05eed11c541639, solely as test support. It is not
installed into the Conan package and is not a runtime or package dependency.

The backend header's source-tree-relative include of ../core/operations.h is
rewritten to symfpu/core/operations.h so the test compiles against the packaged
2019 core headers. The test directly instantiates the 2019 unpack, add,
multiply, and pack templates with this concrete traits type.