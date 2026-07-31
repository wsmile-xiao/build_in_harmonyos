# xmodem

xmodem is a pure Python implementation of the XMODEM and XMODEM-1k file
transfer protocols.

## Package contents

- Public Python package: `xmodem`
- Protocol documents: `share/xmodem/doc`
- License: MIT

## OpenHarmony adaptation

- Packages the architecture-independent Python sources directly.
- Runs all 16 dependency-free upstream protocol tests.
- Runs the 8 optional upstream integration cases when `lrzsz` is available.
- Runs a separate 20-assertion consumer test against the packaged module.
- Requires no source patch and no Conan runtime dependency.

## Usage

```python
from xmodem import XMODEM

modem = XMODEM(getc, putc)
ok = modem.send(input_stream)
```

Upstream: https://github.com/tehmaze/xmodem
