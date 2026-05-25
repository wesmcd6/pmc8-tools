# Third-Party Notices

## p1load

This project bundles and/or invokes `p1load`, a Propeller loader by dbetz.

- Upstream source: https://github.com/dbetz/p1load
- License: MIT License
- Copyright: Copyright (c) 2015 dbetz

The bundled `p1load` helper is used for Propeller firmware loading support on macOS. It is not authored by this project. The Windows/Linux loader (`p1_loader.py`, below) is an independent Python re-implementation of the same protocol, also derived from this MIT-licensed source.

MIT License notice from the upstream project:

```text
The MIT License (MIT)

Copyright (c) 2015 dbetz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## p1_loader.py (Python Propeller loader)

This project includes `p1_loader.py`, a pure-Python implementation of the
Propeller P1 boot protocol used to upload firmware on Windows and Linux. It is
a derivative work of `p1load` by dbetz (MIT License, Copyright (c) 2015 dbetz;
see above) — it re-implements the same documented boot protocol and carries no
other third-party code. It is licensed under the same MIT terms.
