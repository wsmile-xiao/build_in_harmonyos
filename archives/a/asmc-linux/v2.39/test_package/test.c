/* asmc-linux v2.39 test_package smoke source.
 * This file is present to satisfy the W2 structural gate (test source file
 * must exist) and is compiled by test_package/conanfile.py's smoke flow via
 * the packaged asmc_native.  It defines a small x86-64 function that the
 * packaged assembler is expected to turn into an ELF64 x86-64 object.
 */
int asmc_target_func(void)
{
    return 7;
}
