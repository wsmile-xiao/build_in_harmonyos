/* test_lcc: minimal C source compiled via `lcc -S` in test_package.
 * Kept free of <stdio.h> etc. because lcc's 2002-era C parser cannot
 * consume modern OHOS sysroot headers (see notes.md, paranoia/yacc case).
 */
int cube(int x) { return x * x * x; }

int main(void) {
    int i;
    for (i = 0; i < 3; i++)
        if (cube(i) != i * i * i)
            return 1;
    return 0;
}