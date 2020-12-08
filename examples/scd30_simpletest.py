# SPDX-FileCopyrightText: 2020 by Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
# pylint:disable=protected-access
import time
import board
import busio
import adafruit_scd30

i2c = busio.I2C(board.SCL, board.SDA)
scd = adafruit_scd30.SCD30(i2c)

while True:
    data = scd._data_available
    if data:
        print("Data Available!")
        print("CO2:", scd.co2, "PPM")
        print("Temperature:", scd._temperature, "degrees C")
        print("Humidity::", scd._relative_humitidy, "%%rH")
    else:
        print("no data")
    time.sleep(0.5)
