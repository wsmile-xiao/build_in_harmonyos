#include <X11/Xlib.h>
#include <X11/extensions/sync.h>

#include <stdio.h>

int main(void)
{
    XSyncValue zero;
    XSyncValue one;
    XSyncValue two;
    XSyncValue negative;
    XSyncValue wide;
    XSyncValue result;
    XSyncValue maximum;
    XSyncValue minimum;
    int overflow = -1;

    XSyncIntToValue(&zero, 0);
    XSyncIntToValue(&one, 1);
    XSyncIntToValue(&two, 2);
    XSyncIntToValue(&negative, -1);
    XSyncIntsToValue(&wide, 0x89abcdefU, 0x12345678);

    if (!XSyncValueIsZero(zero) || !XSyncValueIsPositive(one) ||
        !XSyncValueIsNegative(negative)) {
        return 1;
    }
    if (!XSyncValueGreaterThan(two, one) || !XSyncValueLessThan(one, two) ||
        !XSyncValueGreaterOrEqual(one, one) ||
        !XSyncValueLessOrEqual(one, one) || !XSyncValueEqual(one, one)) {
        return 2;
    }
    if (XSyncValueLow32(wide) != 0x89abcdefU ||
        XSyncValueHigh32(wide) != 0x12345678) {
        return 3;
    }

    XSyncValueAdd(&result, one, one, &overflow);
    if (overflow != 0 || !XSyncValueEqual(result, two)) {
        return 4;
    }
    overflow = -1;
    XSyncValueSubtract(&result, two, one, &overflow);
    if (overflow != 0 || !XSyncValueEqual(result, one)) {
        return 5;
    }

    XSyncMaxValue(&maximum);
    XSyncMinValue(&minimum);
    if (!XSyncValueIsPositive(maximum) || !XSyncValueIsNegative(minimum) ||
        !XSyncValueGreaterThan(maximum, two) ||
        !XSyncValueLessThan(minimum, negative)) {
        return 6;
    }

    overflow = -1;
    XSyncValueAdd(&result, maximum, one, &overflow);
    if (overflow == 0 || !XSyncValueEqual(result, minimum)) {
        return 7;
    }
    overflow = -1;
    XSyncValueSubtract(&result, one, two, &overflow);
    if (!XSyncValueEqual(result, negative)) {
        return 8;
    }
    puts("LIBXEXT_TEST sync_value_contract PASS");
    return 0;
}
