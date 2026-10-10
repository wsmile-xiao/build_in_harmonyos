# Yale Bright Star Catalog

Yale Bright Star Catalog (BSC5) is a fixed-width star catalogue with accompanying remarks, distributed here as original data resources.

## Resources and use

- `share/yale/catalog.gz`: CDS V/50 catalogue, 9,110 records.
- `share/yale/notes.gz`: CDS V/50 remarks, 9,190 records.
- `share/yale/ReadMe`: original CDS byte-by-byte field documentation and provenance.

The files stay compressed and byte-for-byte identical to the official CDS archive. Conan exposes their installed directory as `YALE_BSC5_DIR`; consumers can use any gzip-capable reader and the fixed-width layout documented in `ReadMe`.

```sh
conan install --requires=yale/5.0.95 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

The resource package has no binaries, libraries, headers, or package dependencies. The test consumer uses HarmonyOS Python 3's standard-library `gzip` module; applications may use another compatible reader.

## HarmonyOS adaptation

The catalog is architecture-independent data. The Conan package ID is cleared, and the original gzip files are installed without converting, decompressing, or editing star records. A HarmonyOS aarch64 consumer test opens the Conan-installed files through `YALE_BSC5_DIR`, validates the fixed-width records, and reads the catalogue and remarks on the target platform.

## Data rights and attribution

The catalogue data are copyrighted by Dorrit Hoffleit and Wayne H. Warren Jr. Redistribution is permitted with attribution to the Astronomical Data Center and the original authors; the data must not be modified. The package retains the official `ReadMe` and credits the authors here. The data are not covered by the GPL used for the historical packaging scripts and documentation.

## Upstream

- Official CDS record: <https://cdsarc.cds.unistra.fr/viz-bin/cat/V/50>
- Official CDS ReadMe: <https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/V/50?format=html&tex=true>
- Harvard catalogue page: <https://tdc-www.harvard.edu/catalogs/bsc5.html>
- Data authors: Dorrit Hoffleit and Wayne H. Warren Jr. (Astronomical Data Center, NSSDC/ADC, 1991)
