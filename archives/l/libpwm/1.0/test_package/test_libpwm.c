/* Consumer test for the installed libpwm package.
 *
 * The library talks to /dev/pwmchipN and /sys/class/pwm; the sandbox exposes
 * neither, which makes the "no such chip" paths deterministic.  Note that the
 * upstream library expects a valid chip handle (it does not NULL-check), so the
 * test only calls the opening entry point.
 */
#include <errno.h>
#include <stdio.h>

#include <pwm.h>

static int checks;
static int failures;

static void check(int condition, const char *what)
{
    checks++;
    if (condition) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

int main(void)
{
    struct pwm_chip *chip;

    setvbuf(stdout, NULL, _IOLBF, 0);

    errno = 0;
    chip = pwm_chip_open_by_number(0);
    check(chip == NULL, "opening PWM chip 0 fails without a PWM device");
    check(errno != 0, "errno is set when the chip cannot be opened");

    errno = 0;
    chip = pwm_chip_open_by_number(9999);
    check(chip == NULL, "opening a non-existent PWM chip fails");

    errno = 0;
    chip = pwm_chip_open_by_number(4294967295u);
    check(chip == NULL, "an out of range chip number is rejected");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
