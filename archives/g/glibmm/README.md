# glibmm

glibmm is the official C++ binding for GLib and GIO.

## OpenHarmony PC status

### 2.66.7

Status: built

The package builds the upstream Meson project. `libsigc/2.10.8` is consumed from Conan; the GLib/GIO stack is consumed from the OpenHarmony system prefix through pkg-config because the full GLib dependency chain is not published as Conan recipes in the current OHPCD remote.

### 2.66.7.1

Status: built

HarmonyOS PC registry revision for the upstream 2.66.7 source; it keeps the same Conan recipe and pkg-config boundary as 2.66.7 while allowing the updated recipe to be published without colliding with the existing registry revision.
