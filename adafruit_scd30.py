# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_scd30`
================================================================================

Helper library for the SCD30 e-CO2 sensor


* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* Adafruit SCD30 Breakout <https://www.adafruit.com/product/48xx>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases


 * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
 * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports
from struct import unpack_from, unpack
import adafruit_bus_device.i2c_device as i2c_device
from micropython import const

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_SCD30.git"
SCD30_DEFAULT_ADDR = 0x61

_CMD_CONTINUOUS_MEASUREMENT = const(0x0010)
_CMD_SET_MEASUREMENT_INTERVAL = const(0x4600)
_CMD_GET_DATA_READY = const(0x0202)
_CMD_READ_MEASUREMENT = const(0x0300)
_CMD_AUTOMATIC_SELF_CALIBRATION = const(0x5306)
_CMD_SET_FORCED_RECALIBRATION_FACTOR = const(0x5204)
_CMD_SET_TEMPERATURE_OFFSET = const(0x5403)
_CMD_SET_ALTITUDE_COMPENSATION = const(0x5102)


class SCD30:
    """CircuitPython helper class for using the SCD30 e-CO2 sensor"""

    def __init__(self, i2c_bus, address=SCD30_DEFAULT_ADDR):
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        self._buffer = bytearray(18)
        self._crc_buffer = bytearray(2)
        self._send_command(_CMD_CONTINUOUS_MEASUREMENT, 0)
        self.measurement_interval = 2
        self.self_calibration_enabled = True
        self._temperature = None
        self._relative_humitidy = None
        self._co2 = None

    @property
    def measurement_interval(self):
        """Sets the interval between readings"""
        raise RuntimeError("NOT WORKING")

    @measurement_interval.setter
    def measurement_interval(self, value):
        self._send_command(_CMD_SET_MEASUREMENT_INTERVAL, value)

    @property
    def self_calibration_enabled(self):
        """Enables or disables self calibration"""
        raise RuntimeError("NOT IMPLEMENTED")

    @self_calibration_enabled.setter
    def self_calibration_enabled(self, enabled):
        self._send_command(_CMD_AUTOMATIC_SELF_CALIBRATION, enabled)

    def _send_command(self, command, arguments=None):
        if arguments is not None:
            self._crc_buffer[0] = arguments >> 8
            self._crc_buffer[1] = arguments & 0xFF
            self._buffer[2] = arguments >> 8
            self._buffer[3] = arguments & 0xFF
            crc = self._crc8(self._crc_buffer)
            self._buffer[4] = crc
            end_byte = 5
        else:
            end_byte = 2

        self._buffer[0] = command >> 8
        self._buffer[1] = command & 0xFF

        with self.i2c_device as i2c:
            i2c.write(self._buffer, end=end_byte)

    @property
    def _data_available(self):
        """
    Check the sensor to see if new data is available
    """

        return self._read_register(_CMD_GET_DATA_READY)

    def _read_register(self, reg_addr):
        self._buffer[0] = reg_addr >> 8
        self._buffer[1] = reg_addr & 0xFF
        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._buffer, self._buffer, out_end=2, in_end=2)
        return unpack_from(">H", self._buffer)[0]

    @property
    def co2(self):
        """Returns the CO2 concentration in PPM (parts per million)"""
        return self._read_data()

    def _read_data(self):
        self._send_command(_CMD_READ_MEASUREMENT)
        with self.i2c_device as i2c:
            i2c.readinto(self._buffer)

        crcs_good = True

        for i in range(0, 18, 3):
            crc_good = self._check_crc(self._buffer[i : i + 2], self._buffer[i + 2])
            if crc_good:
                continue
            crcs_good = False
        if not crcs_good:
            raise RuntimeError("CRC check failed while reading data")

        co2 = unpack(">f", self._buffer[0:2] + self._buffer[3:5])[0]
        temp = unpack(">f", self._buffer[6:8] + self._buffer[9:11])[0]
        hum = unpack(">f", self._buffer[12:14] + self._buffer[15:17])[0]
        self._temperature = temp
        self._relative_humitidy = hum
        return co2

    def _check_crc(self, data_bytes, crc):
        return crc == self._crc8(bytearray(data_bytes))

    @staticmethod
    def _crc8(buffer):
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits
