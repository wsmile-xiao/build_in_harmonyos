// SPDX-FileCopyrightText: none
// SPDX-License-Identifier: BSD-2-Clause
// Consumer test for ksanecore (KSaneCore6) on HarmonyOS PC.
// Exercises the public KSaneCore API without requiring real scanner hardware:
//   - Option value/type/unit accessors on a default (detect-failed) option
//   - DeviceInformation name/vendor/model accessors
//   - enum registration sanity checks

#include <KSaneCore/DeviceInformation>
#include <KSaneCore/Option>

#include <QString>
#include <QVariant>

#include <cstdio>

static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::printf("FAIL: %s\n", msg);                                    \
            ++failures;                                                        \
        } else {                                                               \
            std::printf("PASS: %s\n", msg);                                    \
        }                                                                      \
    } while (0)

int main()
{
    // --- Option -----------------------------------------------------------
    KSaneCore::Option option;
    // A default-constructed option has no backing backend option yet: its
    // type must be TypeDetectFail and its name/title/description empty.
    CHECK(option.type() == KSaneCore::Option::TypeDetectFail,
          "default Option::type() == TypeDetectFail");
    CHECK(option.name().isEmpty(), "default Option::name() is empty");
    CHECK(option.title().isEmpty(), "default Option::title() is empty");
    CHECK(option.description().isEmpty(), "default Option::description() is empty");
    CHECK(option.state() == KSaneCore::Option::StateDisabled,
          "default Option::state() == StateDisabled");
    CHECK(!option.value().isValid(), "default Option::value() is invalid");
    CHECK(option.valueUnit() == KSaneCore::Option::UnitNone,
          "default Option::valueUnit() == UnitNone");
    CHECK(option.valueSize() == 0, "default Option::valueSize() == 0");
    CHECK(!option.storeCurrentData(), "storeCurrentData() on empty option returns false");
    CHECK(!option.setValue(QVariant(42)), "setValue() on empty option returns false");

    // Enum registration sanity (values used by the scan UI).
    CHECK(KSaneCore::Option::TypeBool == 1, "OptionType::TypeBool == 1");
    CHECK(KSaneCore::Option::TypeInteger == 2, "OptionType::TypeInteger == 2");
    CHECK(KSaneCore::Option::TypeValueList == 4, "OptionType::TypeValueList == 4");
    CHECK(KSaneCore::Option::UnitDPI == 4, "OptionUnit::UnitDPI == 4");

    // --- DeviceInformation -------------------------------------------------
    KSaneCore::DeviceInformation info;
    CHECK(info.name().isEmpty(), "default DeviceInformation::name() is empty");
    CHECK(info.vendor().isEmpty(), "default DeviceInformation::vendor() is empty");
    CHECK(info.model().isEmpty(), "default DeviceInformation::model() is empty");
    CHECK(info.type().isEmpty(), "default DeviceInformation::type() is empty");

    if (failures == 0) {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
