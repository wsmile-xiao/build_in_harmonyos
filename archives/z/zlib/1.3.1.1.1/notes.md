# zlib 1.3.1.1.1

The recipe builds the upstream zlib 1.3.1 source with its configure and Makefile flow.
The upstream `make test` target is executed during `build()`. The consumer test
compresses and restores a string through the installed zlib library.
