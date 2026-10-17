# tap-plugins

TAP-plugins is a collection of LADSPA audio-processing plug-ins by Tom
Szilagyi, including filters, dynamics processors, delays, modulation effects,
pitch processing, and reverberation.

## HarmonyOS adaptation

The package builds the upstream C sources as 19 independent LADSPA modules on
HarmonyOS PC arm64.  The modules retain the standard `ladspa_descriptor`
entry point and are installed below `lib/ladspa`, together with the LADSPA API
header and upstream RDF metadata.  No Linux-only service or desktop component
is required.

## Dependencies

The source is self-contained and uses only the C runtime, the math library,
and the dynamic-loader API supplied by HarmonyOS.

## References

- Upstream homepage: <https://tomscii.sig7.se/tap-plugins/>
- Upstream source: <https://git.hq.sig7.se/tap-plugins.git>
- Version recipe: `1.0.0/`
