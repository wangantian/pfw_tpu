# SPDX-FileCopyrightText: © 2025 PFW Tiny Tapeout Team
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


async def reset_dut(dut):
    """Apply reset for 5 cycle then release."""
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def load_matrix(dut, matrix, transpose=0, relu=0):
    """Load a 2x2 matrix (4 elements) with load_en asserted."""
    for i in range(4):
        dut.ui_in.value = matrix[i] & 0xFF
        dut.uio_in.value = (transpose << 1) | (relu << 2) | 1
        await RisingEdge(dut.clk)


async def parallel_load_read(dut, A, B, transpose=0, relu=0):
    """
    Pipelined operation: read previous result while loading next matrices.
    During 8 load cycles (4 for A, 4 for B), the previous result streams
    out on uo_out as high/low byte pairs for each of the 4 output elements.
    If A/B are empty, feeds zeros (flush read only).
    """
    results = []
    dut.uio_in.value = (transpose << 1) | (relu << 2) | 1

    for inputs in [A, B]:
        for i in range(2):
            idx0 = i * 2
            idx1 = i * 2 + 1
            dut.ui_in.value = inputs[idx0] if inputs else 0
            await ClockCycles(dut.clk, 1)
            high = dut.uo_out.value.integer

            dut.ui_in.value = inputs[idx1] if inputs else 0
            await ClockCycles(dut.clk, 1)
            low = dut.uo_out.value.integer

            combined = (high << 8) | low
            if combined >= 0x8000:
                combined -= 0x10000

            results.append(combined)
    return results


def expected_matmul(A, B, transpose=False, relu=False):
    """Compute expected 2x2 matrix multiply result."""
    a = [A[0], A[1], A[2], A[3]]
    b = [B[0], B[1], B[2], B[3]]
    if transpose:
        b = [b[0], b[2], b[1], b[3]]  # transpose 2x2

    def s8(x):
        """Interpret as signed 8-bit."""
        return x - 256 if x > 127 else x

    a = [s8(x & 0xFF) for x in a]
    b = [s8(x & 0xFF) for x in b]

    c00 = a[0]*b[0] + a[1]*b[2]
    c01 = a[0]*b[1] + a[1]*b[3]
    c10 = a[2]*b[0] + a[3]*b[2]
    c11 = a[2]*b[1] + a[3]*b[3]

    result = [c00, c01, c10, c11]
    if relu:
        result = [max(0, x) for x in result]
    return result


@cocotb.test()
async def test_basic_multiply(dut):
    """Test basic 2x2 matrix multiplication: [[1,2],[3,4]] * [[5,6],[7,8]]."""
    dut._log.info("=== Test: Basic Matrix Multiplication ===")

    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # Load first pair
    A1 = [1, 2, 3, 4]
    B1 = [5, 6, 7, 8]
    await load_matrix(dut, A1)
    await load_matrix(dut, B1)

    expected = expected_matmul(A1, B1)

    # Read results of first pair while loading second pair (dummy)
    A2 = [79, 246, 7, 8]   # 246 = -10 in unsigned 8-bit
    B2 = [2, 6, 5, 8]
    results = await parallel_load_read(dut, A2, B2)

    dut._log.info(f"Results: {results}, Expected: {expected}")
    for i in range(4):
        assert results[i] == expected[i], \
            f"C[{i//2}][{i%2}] = {results[i]} != expected {expected[i]}"

    dut._log.info("=== PASSED ===")

    # Now verify second pair
    expected2 = expected_matmul(A2, B2)
    results2 = await parallel_load_read(dut, [], [])

    dut._log.info(f"Results2: {results2}, Expected2: {expected2}")
    for i in range(4):
        assert results2[i] == expected2[i], \
            f"C[{i//2}][{i%2}] = {results2[i]} != expected {expected2[i]}"

    dut._log.info("=== Second pair PASSED ===")


@cocotb.test()
async def test_signed_values(dut):
    """Test with signed (negative) values."""
    dut._log.info("=== Test: Signed Values ===")

    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # W = [[-1, 2], [3, -4]] -> unsigned: [0xFF, 2, 3, 0xFC]
    # I = [[1, -1], [-1, 1]] -> unsigned: [1, 0xFF, 0xFF, 1]
    A = [0xFF, 2, 3, 0xFC]
    B = [1, 0xFF, 0xFF, 1]

    await load_matrix(dut, A)
    await load_matrix(dut, B)

    expected = expected_matmul(A, B)
    dut._log.info(f"Expected: {expected}")

    results = await parallel_load_read(dut, [], [])

    dut._log.info(f"Results: {results}")
    for i in range(4):
        assert results[i] == expected[i], \
            f"C[{i//2}][{i%2}] = {results[i]} != expected {expected[i]}"

    dut._log.info("=== PASSED ===")


@cocotb.test()
async def test_extreme_values(dut):
    """Test with extreme signed 8-bit values: -128 * 127."""
    dut._log.info("=== Test: Extreme Values ===")

    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # A = [[-128, -128], [-128, -128]]
    # B = [[127, 127], [127, 127]]
    A = [0x80, 0x80, 0x80, 0x80]
    B = [127, 127, 127, 127]

    await load_matrix(dut, A)
    await load_matrix(dut, B)

    expected = expected_matmul(A, B)
    dut._log.info(f"Expected: {expected}")

    results = await parallel_load_read(dut, [], [])

    dut._log.info(f"Results: {results}")
    for i in range(4):
        assert results[i] == expected[i], \
            f"C[{i//2}][{i%2}] = {results[i]} != expected {expected[i]}"

    dut._log.info("=== PASSED ===")


@cocotb.test()
async def test_relu_activation(dut):
    """Test ReLU activation with transpose."""
    dut._log.info("=== Test: ReLU + Transpose ===")

    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    A = [5, 250, 7, 8]  # 250 = -6 in signed 8-bit
    B = [8, 9, 6, 8]

    await load_matrix(dut, A, transpose=0, relu=1)
    await load_matrix(dut, B, transpose=0, relu=1)

    expected = expected_matmul(A, B, transpose=False, relu=True)
    dut._log.info(f"Expected (relu): {expected}")

    # Load next pair with transpose
    A2 = [1, 2, 3, 4]
    B2 = [5, 6, 7, 8]
    results = await parallel_load_read(dut, A2, B2, transpose=1, relu=1)

    dut._log.info(f"Results: {results}")
    for i in range(4):
        assert results[i] == expected[i], \
            f"C[{i//2}][{i%2}] = {results[i]} != expected {expected[i]}"

    dut._log.info("=== ReLU part PASSED ===")

    # Read transpose results
    expected2 = expected_matmul(A2, B2, transpose=True, relu=True)
    results2 = await parallel_load_read(dut, [], [], transpose=1, relu=1)

    dut._log.info(f"Transpose results: {results2}, Expected: {expected2}")
    for i in range(4):
        assert results2[i] == expected2[i], \
            f"C[{i//2}][{i%2}] = {results2[i]} != expected {expected2[i]}"

    dut._log.info("=== PASSED ===")
