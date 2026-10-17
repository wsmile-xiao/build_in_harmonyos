# kholidays

KDE Frameworks 6 — holiday calendars and astronomical events.

`libKF6Holidays.so` provides:

- **Holiday region data** — a large set of regional holiday definitions
  (plan language, parsed at build time by bison/flex into
  `holidayparserplan.cpp` / `holidayscannerplan.cpp`)
- **Astronomy** — `KHolidays::SunRiseSet` (classic sunrise/sunset for a
  date/location), `KHolidays::SunEvents` (all solar event times around the
  closest solar noon: astronomical/nautical/civil dawn & dusk, sunrise,
  solar noon, sunset), lunar phases, zodiac signs, astro seasons
- **QML plugin** — `org.kde.kholidays` declarative registration
  (holiday regions model)

## Versions

| Version | Notes |
|---------|-------|
| 6.28.0  | First HarmonyOS PC adaptation (knighttime dependency) |

## Consumer

```cmake
find_package(KF6Holidays REQUIRED)
target_link_libraries(app PRIVATE KF6::Holidays)
```

Primary consumer on this platform: `knighttime` (Plasma dark-light
schedule helper), which uses `KHolidays::SunEvents` to compute the
day/night transition schedule.
