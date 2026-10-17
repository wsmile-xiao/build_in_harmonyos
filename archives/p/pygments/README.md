# Pygments

Pygments is a mature syntax-highlighting library and command-line tool written
in Python.

## Package contents

- Public Python package: `pygments`
- Command-line tool: `pygmentize`
- License: BSD-2-Clause

## OpenHarmony adaptation

- Packages the architecture-independent Python sources directly.
- Runs the complete 5224-case upstream pytest suite.
- Runs a separate 20-assertion consumer test against the packaged API and CLI.
- Requires no source patch and no Conan runtime dependency.

## Usage

```python
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

html = highlight("print('hello')", PythonLexer(), HtmlFormatter())
```

```sh
pygmentize -l python -f html example.py
```

Upstream: https://github.com/pygments/pygments
