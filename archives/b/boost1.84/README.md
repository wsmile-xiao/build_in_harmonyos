# boost1.84

Boost 1.84.0 C++ libraries（独立包名归档：boost1.84，与 boost/1.84.0 并行）。

Boost provides portable C++ libraries. This archive republishes the 1.84.0
adaptation under the `boost1.84` package name: the b2 build system is
incompatible with OHOS, so the recipe manually compiles the non-header-only
libraries (filesystem / regex / program_options / iostreams) and installs the
full header set.
