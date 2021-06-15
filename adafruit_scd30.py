# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_scd30`
================================================================================

Helper library for the SCD30 CO2 sensor


* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SCD30 Breakout <https://www.adafruit.com/product/4867>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases


 * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
 * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports
import time
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
_CMD_SOFT_RESET = const(0xD304)


class SCD30:
    """
    CircuitPython helper class for using the SCD30 CO2 sensor

    :param ~busio.I2C i2c_bus: The I2C bus the SCD30 is connected to.
    :param int ambient_pressure: Ambient pressure compensation. Defaults to :const:`0`
    :param int address: The I2C device address for the sensor. Default is :const:`0x61`

    **Quickstart: Importing and using the SCD30**

        Here is an example of using the :class:`SCD30` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_scd30

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            scd = adafruit_scd30.SCD30(i2c)

        Now you have access to the CO2, temperature and humidity using
        the :attr:`CO2`, :attr:`temperature` and :attr:`relative_humidity` attributes

        .. code-block:: python

            temperature = scd.temperature
            relative_humidity = scd.relative_humidity
            co2_ppm_level = scd.CO2

    """

    def __init__(self, i2c_bus, ambient_pressure=0, address=SCD30_DEFAULT_ADDR):
        if ambient_pressure != 0:
            if ambient_pressure < 700 or ambient_pressure > 1400:
                raise AttributeError("`ambient_pressure` must be from 700-1400 mBar")

        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        self._buffer = bytearray(18)
        self._crc_buffer = bytearray(2)

        # set continuous measurement interval in seconds
        self.measurement_interval = 2
        # trigger continuous measurements with optional ambient pressure compensation
        self.ambient_pressure = ambient_pressure

        # cached readings
        self._temperature = None
        self._relative_humidity = None
        self._co2 = None

    def reset(self):
        """Perform a soft reset on the sensor, restoring default values"""
        self._send_command(_CMD_SOFT_RESET)
        time.sleep(0.1)  # not mentioned by datasheet, but required to avoid IO error

    @property
    def measurement_interval(self):
        """Sets the interval between readings in seconds. The interval value must be from 2-1800

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.

        """

        return self._read_register(_CMD_SET_MEASUREMENT_INTERVAL)

    @measurement_interval.setter
    def measurement_interval(self, value):
        if value < 2 or value > 1800:
            raise AttributeError("measurement_interval must be from 2-1800 seconds")
        self._send_command(_CMD_SET_MEASUREMENT_INTERVAL, value)

    @property
    def self_calibration_enabled(self):
        """Enables or disables automatic self calibration (ASC). To work correctly, the sensor must
        be on and active for 7 days after enabling ASC, and exposed to fresh air for at least 1 hour
        per day. Consult the manufacturer's documentation for more information.

        .. note::
            Enabling self calibration will override any values set by specifying a
            `forced_recalibration_reference`

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.

        """

        return self._read_register(_CMD_AUTOMATIC_SELF_CALIBRATION) == 1

    @self_calibration_enabled.setter
    def self_calibration_enabled(self, enabled):
        self._send_command(_CMD_AUTOMATIC_SELF_CALIBRATION, enabled)
        if enabled:
            time.sleep(0.01)

    @property
    def data_available(self):
        """Check the sensor to see if new data is available"""
        return self._read_register(_CMD_GET_DATA_READY)

    @property
    def ambient_pressure(self):
        """Specifies the ambient air pressure at the measurement location in mBar. Setting this
        value adjusts the CO2 measurement calculations to account for the air pressure's effect on
        readings. Values must be in mBar, from 700 to 1400 mBar"""
        return self._read_register(_CMD_CONTINUOUS_MEASUREMENT)

    @ambient_pressure.setter
    def ambient_pressure(self, pressure_mbar):
        pressure_mbar = int(pressure_mbar)
        if pressure_mbar != 0 and (pressure_mbar > 1400 or pressure_mbar < 700):
            raise AttributeError("ambient_pressure must be from 700 to 1400 mBar")
        self._send_command(_CMD_CONTINUOUS_MEASUREMENT, pressure_mbar)

    @property
    def altitude(self):
        """Specifies the altitude at the measurement location in meters above sea level. Setting
        this value adjusts the CO2 measurement calculations to account for the air pressure's effect
        on readings.

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.


        """
        return self._read_register(_CMD_SET_ALTITUDE_COMPENSATION)

    @altitude.setter
    def altitude(self, altitude):
        self._send_command(_CMD_SET_ALTITUDE_COMPENSATION, int(altitude))

    @property
    def temperature_offset(self):
        """Specifies the offset to be added to the reported measurements to account for a bias in
        the measured signal. Value is in degrees Celsius with a resolution of 0.01 degrees and a
        maximum value of 655.35 C

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.

        """

        raw_offset = self._read_register(_CMD_SET_TEMPERATURE_OFFSET)
        return raw_offset / 100.0

    @temperature_offset.setter
    def temperature_offset(self, offset):
        if offset > 655.35:
            raise AttributeError(
                "Offset value must be less than or equal to 655.35 degrees Celsius"
            )

        self._send_command(_CMD_SET_TEMPERATURE_OFFSET, int(offset * 100))

    @property
    def forced_recalibration_reference(self):
        """Specifies the concentration of a reference source of CO2 placed in close proximity to the
        sensor. The value must be from 400 to 2000 ppm.

        .. note::
            Specifying a forced recalibration reference will override any calibration values
            set by Automatic Self Calibration

        """
        return self._read_register(_CMD_SET_FORCED_RECALIBRATION_FACTOR)

    @forced_recalibration_reference.setter
    def forced_recalibration_reference(self, reference_value):
        self._send_command(_CMD_SET_FORCED_RECALIBRATION_FACTOR, reference_value)

    @property
    def CO2(self):  # pylint:disable=invalid-name
        """Returns the CO2 concentration in PPM (parts per million)

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_available:
            self._read_data()
        return self._co2

    @property
    def temperature(self):
        """Returns the current temperature in degrees Celsius

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_available:
            self._read_data()
        return self._temperature

    @property
    def relative_humidity(self):
        """Returns the current relative humidity in %rH.

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_available:
            self._read_data()
        return self._relative_humidity

    def _send_command(self, command, arguments=None):
        # if there is an argument, calculate the CRC and include it as well.
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
        time.sleep(0.05)  # 3ms min delay

    def _read_register(self, reg_addr):
        self._buffer[0] = reg_addr >> 8
        self._buffer[1] = reg_addr & 0xFF
        with self.i2c_device as i2c:
            i2c.write(self._buffer, end=2)
            # separate readinto because the SCD30 wants an i2c stop before the read
            # (non-repeated start)
            time.sleep(0.005)  # min 3 ms delay
            i2c.readinto(self._buffer, end=3)
        if not self._check_crc(self._buffer[:2], self._buffer[2]):
            raise RuntimeError("CRC check failed while reading data")
        return unpack_from(">H", self._buffer[0:2])[0]

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

        self._co2 = unpack(">f", self._buffer[0:2] + self._buffer[3:5])[0]
        self._temperature = unpack(">f", self._buffer[6:8] + self._buffer[9:11])[0]
        self._relative_humidity = unpack(
            ">f", self._buffer[12:14] + self._buffer[15:17]
        )[0]

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
