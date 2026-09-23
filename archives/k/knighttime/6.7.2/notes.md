# knighttime 6.7.2 notes

## Scope

First HarmonyOS PC adaptation of KDE Plasma knighttime 6.7.2 (task
#12875). Initial task framing assumed a pure QML plasmoid (data-package
mode, kicad-demos precedent); source inspection showed knighttime 6.7.2
is actually a **C++ library (KNightTime) + daemon**:

- `src/` — `kdarklightschedule.{h,cpp}`, `kdarklightscheduleprovider.*`,
  `kdarklightschedulesubscription.*` (library, linked on Qt6::Core with
  private Qt6::DBus + KF6::Holidays)
- `src/daemon/` — `knighttimed` executable (Qt6 Positioning/DBus, KF6
  Config/CoreAddons/DBusAddons) + D-Bus interface/systemd unit/desktop
  file installs
- `autotests/` — 3 upstream tests (transition/cycle/schedule), Qt Test
- `examples/monitor` — small consumer example

## W0 dependency check

| Dependency | Published form used |
|---|---|
| Qt6 Core | qtbase/6.11.1 |
| Qt6 DBus (library private link + daemon) | qtbase-sql-dbus/6.11.1 (plain qtbase is built with FEATURE_dbus=OFF; the two qtbase variants coexist by design) |
| Qt6 Positioning (daemon solar scheduler) | qtpositioning/6.11.1 |
| KF6::Holidays | kholidays/6.28.0 (companion PR, task #7826) |
| KF6 Config/CoreAddons/I18n (daemon) | kconfig/6.26.0 / kcoreaddons/6.26.0 / ki18n/6.26.0 |
| KF6 DBusAddons (daemon KDBusService) | kdbusaddons/6.18.0 (qtbase-sql-dbus ecosystem) |
| ECM >= 6.26.0 | extra-cmake-modules/6.29.0 (tool) |

kholidays was the only missing piece in the registry; it was adapted and
published first (R36 topological order) before this recipe was built.

### The qtbase ecosystem split (why kdbusaddons 6.18.0 + patch 0002)

The OHOS registry has two mutually exclusive KF6/Qt ecosystems:

- qtbase/6.11.1 (no DBus) — used by kconfig/kcoreaddons/ki18n 6.26.0,
  kholidays 6.28.0, qtpositioning 6.11.1
- qtbase/6.11.1.1 — used by kdbusaddons 6.29.0 (conan forbids both
  qtbase versions in one graph)

Qt6::DBus lives only in qtbase-sql-dbus/6.11.1 (a separate package name
that coexists with qtbase). kdbusaddons 6.18.0 is the DBusAddons build on
that ecosystem. Choosing it means the upstream find_package(KF6 6.26.0)
version gate rejects the 6.18.0 package — hence patch 0002 relaxes
KF6_MIN_VERSION to 6.18.0. KDBusService (the only DBusAddons API used,
for unique D-Bus service registration in the daemon) has been
API-stable since KF5, so the older kdbusaddons is functionally
sufficient.

## Adaptation decisions

1. **KF_IGNORE_PLATFORM_CHECK=TRUE** — OHOS not in the KDE platform list
   (kconfig/kdbusaddons/kholidays precedent).
2. **C++20 instead of upstream C++23** — upstream sets
   `CMAKE_CXX_STANDARD 23`; the OHOS toolchain is clang 15 + libc++ and
   the 6.7.2 sources use no C++23-specific features (verified: no
   std::expected/print/mdspan; the `auto operator<=>` uses are C++20).
   The recipe removes the conan cppstd block and pins
   CMAKE_CXX_STANDARD=20 (kholidays/baloo precedent; profile pins 17).
3. **Patch 0002: KF6_MIN_VERSION 6.26.0 -> 6.18.0** — see the ecosystem
   split above.
4. **QT_ADDITIONAL_PACKAGES_PREFIX_PATH -> qtpositioning** — Qt6Config
   resolves components relative to its own prefix; the split Qt module
   packages need to be registered as additional Qt prefixes (same
   mechanism as qtdeclarative in the kholidays recipe).
5. **Daemon built and installed as-is** — the daemon binary requires a
   live D-Bus session at runtime to be useful, but it links and installs
   cleanly on OHOS. The autotests link the library only, so the ctest
   suite is fully deterministic here.
6. **BUILD_TESTING=ON** — the 3 autotests are computation-only (no
   D-Bus, no display).

## Upstream tests

Executed during `conan create` via ctest: **3/3 passed (100%)** —
transition-test, cycle-test, schedule-test.

## Consumer test

`test_package/test_knighttime.cpp` links `KNightTime` and exercises the
core API with 16 assertions. Output on this machine:

```
knighttime consumer probe OK: fixed schedule 8 cycles (7 days + anchor),
sun-driven Beijing schedule 8 cycles, round-trip state preserved
```

Two API semantics discovered while writing the probe (documented here
for future consumers):

- `forecast(..., cycleCount=N)` returns **N+1** cycles (N full days plus
  the in-progress anchor cycle) — see upstream schedule_test.cpp.
- `KDarkLightTransition::test()` has a built-in **60-second tolerance**;
  assertions should use offsets well clear of the boundary.
