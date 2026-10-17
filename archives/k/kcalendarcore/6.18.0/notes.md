# kcalendarcore 6.18.0 notes

## Scope

This package provides `KF6::CalendarCore`, the calendar data model required by
later Akonadi calendar libraries. It is also the first downstream consumer of
the verified `libical/4.0.1` package.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation.
- `BUILD_QCH=OFF` skips optional API documentation generation.
- `BUILD_TESTING=ON` keeps upstream CTest enabled during package creation.
- Upstream CTest is run with a per-test timeout so non-terminating
  timezone-dependent data cases cannot stall package creation.
- The recipe uses upstream `FindLibIcal.cmake` with explicit include/library
  hints so `LibIcal` is the imported target consumed by upstream build files.
- `0001-Use-libical-4-status-string-api.patch` updates the xCal status parser
  to the `libical 4` status-string conversion API.
- Runtime verification prepares compatibility links for OHOS loader behavior
  around relative or cache-path `DT_NEEDED` entries inherited from dependencies.

## Verification

Initial checks:

- Upstream source SHA256:
  `4d2330af35d56c59ee69f08f3845babee9896d00012bccfbb143bdc571bc58e7`.
- The libical 4 parser patch was checked by building the upstream
  `xcalformat.cpp` consumer.
- Conan `test_package` finds `KF6CalendarCore` / `KF6::CalendarCore` and
  links a runtime smoke against `MemoryCalendar` and `ICalFormat`.

OHOS `conan create` verification passed:

- Upstream CTest: 506 entries registered; 496 runnable entries passed.
- Conan `test_package`: 1/1 passed.
- Direct consumer run:
  `PASS: KCalendarCore serialized Akonadi calendar event` and
  `PASS: KCalendarCore parsed event Akonadi calendar event`.
- Full reference:
  `kcalendarcore/6.18.0#d75d0952e71f3e1956cc7a0abaa087a4:1420287553a11fc9466921c48a5a5fcb1a329d01#a0d60b2df299dd8b03a432eb1d819834`.

## Upstream Tests Not Run

Ten upstream CTest entries are excluded on the current OHOS profile:
`testincidence`, `testicalformat`, `testidentical`, `testmemorycalendar`,
`testtimesininterval`, `testreadrecurrenceid`, `testicaltimezones`,
`RecursOn-ConnectDaily2.ics`, `RecursOn-ConnectDaily3.ics`, and
`RecursOn-ConnectDaily6.ics`.

The hard blocker is the missing Qt-consumable IANA/system timezone database in
the current OHOS package profile. These tests require `QTimeZone` to resolve
named zones such as `Europe/Prague` and `Europe/Zurich`, or to compute local
time recurrence boundaries from the system timezone. In the verified
environment, `QTimeZone` reports that the system timezone cannot be
determined; setting `TZ=UTC` did not make those named-zone paths valid. The
affected executable tests fail with invalid `DTSTART`, invalid named-zone
lookups, collapsed timezone comparisons, or local-time recurrence count
mismatches. The three `RecursOn-ConnectDaily*.ics` data rows do not terminate
under the same timezone baseline and were confirmed by CTest timeout.

Optional documentation and metadata checks are separate from the runnable
library CTest set: QCH generation needs Qt documentation tooling, and the
appstream validation test is not registered without `appstreamcli`. Those
optional host tools are unavailable in the OHOS package profile and do not
affect the installed `KF6::CalendarCore` library target.
