#!/usr/bin/python
from qcodes.instrument_drivers.anritsu import MG3690B
from time import sleep

src = MG3690B.MG3690BBasic("mw-src", "GPIB1::4::INSTR")

src.frequency(8.0)
src.power(-15)

sleep(5.0)

src.output_enabled(True)

sleep(5.0)

src.frequency(16.0)
src.power(-5.0)

sleep(5.0)

src.output_enabled(False)
src.close()
