# SPDX-FileCopyrightText: 2026 SCD30 driver review
# SPDX-License-Identifier: MIT
"""
Minimal hw_test for adafruit_scd30 — presence + one live measurement.

For reviewers who don't want the state-changing checks in 00_scd30.py (which
issues a soft reset and writes settings). This one only reads.
"""

import time

import board
import busio

import adafruit_scd30

passed = 0
failed = 0


def test(name, condition):
    global passed, failed  # noqa: PLW0603
    if condition:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name}")
        failed += 1


# First try the STEMMA_I2C on Feathers and QtPy among others
if hasattr(board, "STEMMA_I2C"):
    i2c = board.STEMMA_I2C()
else:
    i2c = board.I2C()  # uses board.SCL and board.SDA

try:
    scd = adafruit_scd30.SCD30(i2c)

    fw = scd.firmware_version
    test("sensor present / firmware reads as 'major.minor'", isinstance(fw, str) and "." in fw)
    print(f"     firmware_version = {fw}")

    co2 = temp = rh = None
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if scd.data_available:
            co2 = scd.CO2
            # Sometimes CO2 takes time to become available after MI reset
            if int(co2) == 0:
                continue
            temp = scd.temperature
            rh = scd.relative_humidity
            break
        time.sleep(0.5)

    test("a measurement became available within 15s", co2 is not None)
    test("CO2 in plausible range", co2 is not None and 0 < co2 < 40000)
    test("temperature in range (-40..125 C)", temp is not None and -40 <= temp <= 125)
    test("relative_humidity in range (0..100 %)", rh is not None and 0 <= rh <= 100)
    if co2 is not None:
        print(f"     CO2={co2:.1f}ppm  T={temp:.2f}C  RH={rh:.1f}%")

except Exception as e:
    print(f"FAIL: Unhandled exception: {e}")
    failed += 1

print(f"=== Summary: {passed} passed, {failed} failed ===")
print("ALL TESTS PASSED" if passed > 0 and failed == 0 else "SOME TESTS FAILED")
print("~~END~~")
