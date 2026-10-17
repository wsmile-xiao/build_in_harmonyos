# gtkdatabox

gtkdatabox is a GTK+ widget for displaying large numeric datasets as graphs.

## Official resources

- Homepage: https://sourceforge.net/projects/gtkdatabox/
- Source archive: https://downloads.sourceforge.net/gtkdatabox/
- License: LGPL-2.1-or-later

## OpenHarmony PC status

### 1.0.0

Status: partial

The package builds the upstream Autotools project as a GTK+ 3 consumer library. The current OHPCD Conan remote does not publish the complete GTK+ dependency chain as Conan recipes, so the recipe consumes the previously installed OpenHarmony system prefix through `pkg-config`.

Default system prefix:

```bash
/storage/Users/currentUser/usr/local
```

Override it with `GTK_PREFIX` or `DEFAULT_PREFIX` when the GTK+ stack is installed elsewhere.
