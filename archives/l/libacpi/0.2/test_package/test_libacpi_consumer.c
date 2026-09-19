/* Consumer test for the installed libacpi package.
 *
 * The library parses live kernel interfaces (/proc/acpi or
 * /sys/class/power_supply, /sys/class/thermal), so what a running system
 * exposes differs between machines.  The checks below therefore pin the
 * library's *contract* - the documented constants, the enum values, the
 * exported global arrays and the documented return-code sets of the
 * init/read entry points - and confirm that querying an absent feature is
 * reported rather than fatal.  Upstream's demo test-libacpi is executed by the
 * recipe's build() as behavioural evidence.
 */
#include <stdio.h>
#include <string.h>

#include <libacpi.h>

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

/* the documented outcome sets of the init entry points */
static int documented_status(int status)
{
    return status == SUCCESS || status == NOT_PRESENT
        || status == NOT_SUPPORTED || status == DISABLED;
}

int main(void)
{
    global_t globals;
    int support;
    int batt;
    int thermal;
    int fan;
    int adapt;

    setvbuf(stdout, NULL, _IOLBF, 0);

    check(strcmp(PROC_ACPI, "/proc/acpi/") == 0,
          "PROC_ACPI points at /proc/acpi/");
    check(LINE_MAX == 256, "LINE_MAX is 256");
    check(MAX_ITEMS == 10, "MAX_ITEMS is 10");
    check(MAX_NAME > 0 && MAX_BUF >= MAX_NAME,
          "buffer sizes are internally consistent");

    check(SUCCESS == 0, "SUCCESS is 0");
    check(NOT_SUPPORTED == -1, "NOT_SUPPORTED is -1");
    check(ALLOC_ERR == -2, "ALLOC_ERR is -2");
    check(NOT_PRESENT == -3, "NOT_PRESENT is -3");
    check(DISABLED == -4, "DISABLED is -4");
    check(ITEM_EXCEED == -5, "ITEM_EXCEED is -5");

    check(P_AC == 0 && P_BATT == 1 && P_ERR == 2,
          "power_state_t enumerates AC, battery, error");

    check(sizeof(batteries) == MAX_ITEMS * sizeof(battery_t),
          "batteries[] has MAX_ITEMS entries");
    check(sizeof(thermals) == MAX_ITEMS * sizeof(thermal_t),
          "thermals[] has MAX_ITEMS entries");
    check(sizeof(fans) == MAX_ITEMS * sizeof(fan_t),
          "fans[] has MAX_ITEMS entries");

    support = check_acpi_support();
    check(support == SUCCESS || support == NOT_SUPPORTED,
          "check_acpi_support returns SUCCESS or NOT_SUPPORTED");

    memset(&globals, 0, sizeof(globals));
    batt = init_acpi_batt(&globals);
    thermal = init_acpi_thermal(&globals);
    fan = init_acpi_fan(&globals);
    adapt = init_acpi_acadapt(&globals);

    check(documented_status(batt), "init_acpi_batt returns a documented status");
    check(documented_status(thermal),
          "init_acpi_thermal returns a documented status");
    check(documented_status(fan), "init_acpi_fan returns a documented status");
    check(documented_status(adapt),
          "init_acpi_acadapt returns a documented status");

    check(globals.batt_count >= 0 && globals.batt_count <= MAX_ITEMS,
          "discovered battery count honours MAX_ITEMS");
    check(globals.thermal_count >= 0 && globals.thermal_count <= MAX_ITEMS,
          "discovered thermal zone count honours MAX_ITEMS");
    check(globals.fan_count >= 0 && globals.fan_count <= MAX_ITEMS,
          "discovered fan count honours MAX_ITEMS");
    check(globals.adapt.ac_state == P_AC || globals.adapt.ac_state == P_BATT
          || globals.adapt.ac_state == P_ERR,
          "ac_state stays inside power_state_t");

    if (adapt == SUCCESS) {
        read_acpi_acstate(&globals);
        check(globals.adapt.state_file[0] != '\0',
              "read_acpi_acstate keeps the state file path");
    } else {
        check(adapt == NOT_PRESENT || adapt == NOT_SUPPORTED || adapt == DISABLED,
              "missing AC adapter is reported with a defined status");
    }

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
