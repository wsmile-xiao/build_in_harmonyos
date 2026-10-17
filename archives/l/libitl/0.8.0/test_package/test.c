#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <itl/hijri.h>
#include <itl/prayer.h>

int main(void) {
    sDate hdate;
    /* G2H(sDate*, day, month, year) — returns 1 on success (Umm Al-Qura) */
    if (G2H(&hdate, 28, 7, 2026) != 1) {
        fprintf(stderr, "G2H failed\n");
        return 1;
    }
    if (hdate.year < 1400 || hdate.month < 1 || hdate.month > 12 || hdate.day < 1) {
        fprintf(stderr, "G2H produced invalid date: %d/%d/%d\n",
                hdate.day, hdate.month, hdate.year);
        return 1;
    }
    printf("G2H 28/7/2026 -> %d/%d/%d H\n", hdate.day, hdate.month, hdate.year);

    Location loc;
    memset(&loc, 0, sizeof(loc));
    loc.degreeLat = 24.4667;
    loc.degreeLong = 54.3667;
    loc.gmtDiff = 4.0;
    loc.dst = 0;
    loc.seaLevel = 0;
    loc.pressure = 1010;
    loc.temperature = 10;

    Method method;
    getMethod(4, &method); /* Umm Al-Qura */

    Date date;
    date.day = 3;
    date.month = 9;
    date.year = 2014;

    Prayer pt[6];
    getPrayerTimes(&loc, &method, &date, pt);
    if (pt[0].hour < 0 || pt[0].hour > 23) {
        fprintf(stderr, "getPrayerTimes returned invalid Fajr hour\n");
        return 1;
    }
    printf("Abu Dhabi Fajr ~ %02d:%02d:%02d\n",
           pt[0].hour, pt[0].minute, pt[0].second);

    printf("test libitl 0.8.0: OK\n");
    return 0;
}
