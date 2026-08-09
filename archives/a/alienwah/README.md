# alienwah

AlienWah is a LADSPA audio effect plugin implementing an alien-wah style
feedback delay.

## Version

- 1.13

## Build notes

The package builds the upstream `aw.so` LADSPA plugin and installs it under
`lib/ladspa`. It depends on `ladspa/1.17` for the LADSPA SDK header.
