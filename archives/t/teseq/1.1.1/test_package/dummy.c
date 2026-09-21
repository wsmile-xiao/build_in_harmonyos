/* Placeholder translation unit for the teseq test_package CMake project.
 *
 * teseq is a command-line package: all consumer assertions run the packaged
 * `teseq` and `reseq` binaries from test_package/conanfile.py::test() (see
 * MANIFEST.yml for the assertion inventory).  This file exists so the CMake
 * build system required by the archive spec has a real source to compile.
 */
int teseq_test_package_placeholder(void) { return 0; }
