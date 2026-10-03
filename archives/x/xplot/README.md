# xplot

XPlot is a small XForms application for plotting tabulated one- or two-column data. The HarmonyOS package installs the `xplot` command, its help data, and its manual page.

- Upstream version: 1.19
- Source archive: [Ubuntu archive copy](https://archive.ubuntu.com/ubuntu/pool/universe/x/xplot/xplot_1.19.orig.tar.gz)
- License: GPL-2.0-or-later; see the upstream `COPYING` and `GPL` files for the XForms linking exception.
- Dependency: `libforms/1.2.4`

## HarmonyOS notes

The package is built for aarch64 and signed with the HarmonyOS SDK signing tool. XPlot opens an XForms window, so plotting requires a working X11 display server. A headless SSH session can run its command-line parser but cannot verify graph rendering.

## Usage

```sh
printf '0 0\n1 1\n2 4\n' > data.txt
xplot data.txt
```

The data file accepts one value per line or whitespace-separated X/Y pairs. Use `xplot -h` only when a display is available; the upstream program's no-argument path opens its usage form.
