/*
    Consumer-side test for libksysguard 6.7.2 on HarmonyOS PC.

    Exercises the KSysGuard::Formatter C++ API shipped by the libksysguard
    package (value formatting + unit symbols) through the upstream
    KSysGuardConfig.cmake package config, which also validates that the
    exported KSysGuard::* imported targets and their dependency chain
    (Qt6, KF6Config, KF6I18n) resolve on the consumer side.
*/

#include <formatter/Formatter.h>
#include <formatter/Unit.h>

#include <QVariant>
#include <QString>

#include <cstdio>

int main()
{
    // 1. Formatter::formatValue — a byte-count must render to a non-empty,
    //    localized display string.
    const QString formatted = KSysGuard::Formatter::formatValue(
        QVariant(1024.0), KSysGuard::UnitByte);
    if (formatted.isEmpty()) {
        std::fprintf(stderr,
                     "FAIL: Formatter::formatValue(1024.0, UnitByte) returned "
                     "an empty string\n");
        return 1;
    }

    // 2. Formatter::symbol — the unit symbol must render to a non-empty
    //    string.
    const QString symbol = KSysGuard::Formatter::symbol(KSysGuard::UnitByte);
    if (symbol.isEmpty()) {
        std::fprintf(stderr,
                     "FAIL: Formatter::symbol(UnitByte) returned an empty "
                     "string\n");
        return 1;
    }

    std::printf(
        "PASS: Formatter::formatValue(1024.0, UnitByte) = \"%s\", "
        "symbol(UnitByte) = \"%s\"\n",
        qPrintable(formatted), qPrintable(symbol));
    return 0;
}
