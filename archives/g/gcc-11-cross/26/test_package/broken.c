/* broken.c - deliberately invalid C, used as a negative control.
 *
 * The toolchain must reject this translation unit with a non-zero exit status;
 * if it ever compiles, the test_package would be accepting garbage as valid C.
 */

int _start(void)
{
    this is not valid C at all
    return 0
}
