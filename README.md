![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# PFW Tensor Processing Unit

A 2x2 systolic array Tensor Processing Unit (TPU) designed for the [Tiny Tapeout](https://tinytapeout.com) ASIC flow.

- [Read the documentation for project](docs/info.md)

## Overview

This project implements a hardware-efficient TPU that performs 2x2 signed 8-bit matrix multiplications using a systolic array of Multiply-Accumulate (MAC) processing elements. It produces 16-bit results and supports pipelined streaming, fused matrix transpose, and ReLU activation.

## Architecture

| Module | Description |
|--------|-------------|
| `project.v` | Top-level Tiny Tapeout wrapper (`tt_um_example`) |
| `PE.v` | Processing Element: multiply-accumulate unit |
| `systolic_array_2x2.v` | 2x2 grid of PEs wired in systolic fashion |
| `memory.v` | 8-byte unified register bank for weights and inputs |
| `control_unit.v` | FSM for load/compute/output sequencing |
| `mmu_feeder.v` | Data scheduler between memory, array, and output |
| `delay_cell.v` | Buffer cells for timing closure |

## Running Tests

```bash
cd test
pip install -r requirements.txt
make
```

Tests use [cocotb](https://www.cocotb.org/) with Icarus Verilog and cover:
- Identity matrix multiplication
- General 2x2 matrix multiplication
- Signed (negative) value handling
- ReLU activation

## Resources

- [Tiny Tapeout FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)
