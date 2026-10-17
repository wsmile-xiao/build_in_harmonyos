# mdurl

mdurl is a pure Python library that implements the URL encoding, decoding,
parsing, and formatting behavior used by Markdown tooling.

## Package contents

- Public Python package: `mdurl`
- Type marker: `py.typed`
- License: MIT

## OpenHarmony adaptation

- Packages the architecture-independent Python sources directly.
- Runs all 188 upstream pytest cases from the official `0.1.2` GitHub tag.
- Runs a separate 20-assertion consumer test against the packaged module.
- Requires no source patch and no Conan runtime dependency.

## Usage

```python
from mdurl import decode, encode, format, parse

encoded = encode("my url")
parsed = parse("https://example.com/path?q=1")
assert decode(encoded) == "my url"
assert format(parsed) == "https://example.com/path?q=1"
```

Upstream: https://github.com/executablebooks/mdurl
