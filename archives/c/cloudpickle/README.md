# cloudpickle

## Overview

[cloudpickle](https://github.com/cloudpipe/cloudpickle) is a pure-Python
library providing extended pickling support for Python object graphs not
serializable by the standard `pickle` module.

**Type**: pure Python package — not a C/C++ library.

## Package layout

- `$PREFIX/lib/python3.12/site-packages/cloudpickle/`

## Runtime

Requires Python 3.12 site-packages on `PYTHONPATH`:

```python
import cloudpickle
data = cloudpickle.dumps({"a": 1})
obj = cloudpickle.loads(data)
```

## License

BSD-3-Clause