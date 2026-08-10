/*
 * test_package/stubs.c — Link-time stubs for pikaCompiler-generated bindings.
 *
 * PikaPython's upstream build runs the pikaCompiler pre-processor (Rust tool,
 * from tools/pikaCompiler) which generates stdlib binding symbols
 * (New_builtins_object, New_PikaStdData_*, __pikaMain, ...) from .pyi files.
 * These generated bindings are NOT part of the release tarball and are only
 * needed at runtime for VM/builtins execution paths.
 *
 * This test_package only exercises the core data-layer API of libpika-core
 * (arg/stack/strs/memory), which never calls into the VM/builtins paths, so
 * these stubs are provided purely to satisfy static linking. They are never
 * invoked by the assertions in test.c.
 */
#include <stddef.h>

/* Standard-library module constructors (generated upstream by pikaCompiler) */
void* New_PikaStdData_ByteArray(void* args) { (void)args; return NULL; }
void* New_PikaStdData_Dict(void* args) { (void)args; return NULL; }
void* New_PikaStdData_FILEIO(void* args) { (void)args; return NULL; }
void* New_PikaStdData_List(void* args) { (void)args; return NULL; }
void* New_PikaStdData_String(void* args) { (void)args; return NULL; }
void* New_PikaStdData_Tuple(void* args) { (void)args; return NULL; }
void* New_PikaStdLib_SysObj(void* args) { (void)args; return NULL; }
void* New_builtins(void* args) { (void)args; return NULL; }
void* New_builtins_RangeObj(void* args) { (void)args; return NULL; }
void* New_builtins_object(void* args) { (void)args; return NULL; }

/* Stdlib module init methods */
int PikaStdData_Dict___init__(void* self, void* args) { (void)self; (void)args; return 0; }
int PikaStdData_FILEIO_init(void* self, void* args) { (void)self; (void)args; return 0; }
int PikaStdData_List___init__(void* self, void* args) { (void)self; (void)args; return 0; }
int PikaStdData_Tuple___init__(void* self, void* args) { (void)self; (void)args; return 0; }
void __pikaMain(void* args) { (void)args; }

/* PikaStdData_String helpers */
int strGetSizeUtf8(const char* s) { (void)s; return 0; }
void* string_slice(const char* s, int a, int b) { (void)s; (void)a; (void)b; return NULL; }
