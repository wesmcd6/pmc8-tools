# Third-Party Notices

This file lists code and assets in this project that come from third-party
sources, along with their license terms. The project as a whole remains
under its own license (see README.md). The notices below apply to specific
subsets of the source.

---

## Propeller P1 boot protocol — port of `p1load` by dbetz

`Pmc8FirmwareLoader.vb` is a VB.NET re-implementation of the Parallax
Propeller P1 boot protocol (LFSR handshake, long encoding, EEPROM write +
verify ACK loops). The protocol logic is ported from `p1load` by dbetz:

- Upstream source: https://github.com/dbetz/p1load
- License: MIT
- Copyright: Copyright (c) 2015 dbetz

The bit-level protocol code in `Pmc8FirmwareLoader.vb` is a derivative work
of the upstream. The MIT license permits this port and re-distribution under
the present project's own license, provided the upstream notice is preserved.
The full upstream MIT license text follows.

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

The LFSR algorithm (taps 7, 5, 4, 1, seeded with the ASCII value of `P`) and
the bit-encoded long format (11 bytes per 32-bit long, base byte `0x92`, end
marker `0x60`) are adapted from Chip Gracey's PNut IDE / Propeller Tool boot
loader, the same source the upstream `p1load` references.
