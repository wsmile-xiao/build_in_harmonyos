/* warn.c — two deliberate defects splint must report (see test.sh check 4).
 *
 *  - uninit_value is read before it is initialised
 *  - unused_value is declared but never used */

int main (void)
{
    int uninit_value;
    int unused_value = 0;
    int result = uninit_value + 1;

    return result;
}
