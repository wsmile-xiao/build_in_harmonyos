# Draft 12002 — CMake `FindCurses` finds the archive but not the include dir

Found while adapting **tmatrix 1.4** to HarmonyOS PC (OHOS aarch64) against the
published **ncurses/6.6** package.

## Symptom 1: the find itself fails

Upstream `CMakeLists.txt` does the usual:

```cmake
set(CURSES_NEED_NCURSES TRUE)
find_package(Curses REQUIRED)
link_libraries(${CURSES_LIBRARIES})
```

In a Conan cross build the toolchain declares `CMAKE_SYSTEM_NAME=Linux` with an
OHOS `clang++` from the profile conf. FindCurses has no sysroot notion, so it
searches the *build host's* library paths and finds nothing:

```
CMake Error at .../FindPackageHandleStandardArgs.cmake:230 (message):
  Could NOT find Curses (missing: CURSES_LIBRARY)
Call Stack (most recent call first):
  .../FindCurses.cmake:268 (FIND_PACKAGE_HANDLE_STANDARD_ARGS)
  CMakeLists.txt:23 (find_package)
```

## Symptom 2: fixing the find is not enough

Handing it the archive via the cache variable gets the configure step to pass:

```
$ cmake ... -DCURSES_LIBRARY=<ncurses>/lib/libncursesw.a
-- Looking for cbreak in .../libncursesw.a
-- Looking for cbreak in .../libncursesw.a - found
-- Found Curses: .../libncursesw.a
-- Configuring done
```

and then the build fails anyway:

```
src/Terminal.cpp:8:10: fatal error: 'ncurses.h' file not found
#include <ncurses.h>
```

`link_libraries()` propagates **link flags, not include directories**.
`${CURSES_LIBRARIES}` expands to a bare archive path, so the target gets the
library and none of its headers. This is the part that makes the bug look like
a configure problem when it is really a compile-interface problem.

## The fix

Let Conan generate the dependency's config target and link that:

```cmake
find_package(ncurses CONFIG REQUIRED)
link_libraries(ncurses::ncurses)
```

The `ncurses` recipe already declares

```python
self.cpp_info.set_property("cmake_file_name", "ncurses")
self.cpp_info.set_property("cmake_target_name", "ncurses::ncurses")
```

so `CMakeDeps` emits the CONFIG file with no extra wiring, and
`ncurses::ncurses` carries the include directory, the static `libncursesw.a`
and the correct link order together. This also pins the link to the exact
`ncursesw` flavour this ecosystem publishes, instead of whatever a sysroot probe
happens to find.

The `CURSES_*` cache variables then become dead weight and should be removed —
otherwise CMake reports:

```
CMake Warning:
  Manually-specified variables were not used by the project:
    CURSES_INCLUDE_PATH
    CURSES_LIBRARY
    CURSES_NCURSES_INCLUDE_PATH
    CURSES_NCURSES_LIBRARY
```

## If you must keep FindCurses

The fallback is to supply **both** halves explicitly — the library *and* the
include path:

```cmake
find_package(Curses REQUIRED)
target_include_directories(tmatrix PRIVATE ${CURSES_INCLUDE_PATH})
link_libraries(${CURSES_LIBRARIES})
```

Seeding only `CURSES_LIBRARY` is what produces the confusing
"configures fine, does not compile" split.

## Related

`cmatrix/2.0` in this repository hits a *different* symptom of the same module —
its `configure.ac` uses `AC_CHECK_LIB(ncurses, tgetent)`, so that recipe
symlinks `libncurses.a -> libncursesw.a` to satisfy detection. Both are
cross-build gaps in FindCurses; only the `find_package(ncurses CONFIG)` route
avoids the module entirely.
