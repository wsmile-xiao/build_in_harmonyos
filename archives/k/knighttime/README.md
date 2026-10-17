# knighttime

KDE Plasma KNightTime — helpers for scheduling the dark-light cycle.

Two artifacts:

- **KNightTime library** (`libKNightTime.so`) — `KDarkLightSchedule`
  (forecast for the next N days: fixed-times mode with morning/evening
  times + transition duration, or sun-driven mode via
  `KHolidays::SunEvents` at a given latitude/longitude),
  `KDarkLightCycle` (single-day morning/evening transitions with
  navigation), `KDarkLightScheduleProvider` (live subscription-refreshed
  provider) and D-Bus types for the schedule state.
- **knighttimed daemon** — applies the dark-light schedule (colour
  temperature / theme state) over the `org.kde.NightTime` D-Bus
  interface; driven by `kdarklightsettings.kcfg` (timed mode) or
  `ksolardarklightscheduler` (location mode, Qt6 Positioning).

## Versions

| Version | Notes |
|---------|-------|
| 6.7.2   | First HarmonyOS PC adaptation (task #12875) |

## Consumer

```cmake
find_package(KNightTime REQUIRED)
target_link_libraries(app PRIVATE KNightTime)
```

Key dependency: `kholidays` (KHolidays::SunEvents drives the sun-based
schedule computation).
