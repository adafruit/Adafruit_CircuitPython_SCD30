# SPDX-FileCopyrightText: 2020 by Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time

import board
import busio

import adafruit_scd30

# SCD-30 has tempremental I2C with clock stretching, datasheet recommends
# starting at 50KHz
i2c = busio.I2C(board.SCL, board.SDA, frequency=50000)
scd = adafruit_scd30.SCD30(i2c)

while True:
    # since the measurement interval is long (2+ seconds) we check for new data before reading
    # the values, to ensure current readings.
    if scd.data_available:
        print("Data Available!")
        print(f"CO2: {scd.CO2:d} PPM")
        print(f"Temperature: {scd.temperature:0.2f} degrees C")
        print(f"Humidity: {scd.relative_humidity:0.2f} % rH")
        print("")
        print("Waiting for new data...")
        print("")

    time.sleep(0.5)
