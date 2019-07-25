#!/usr/bin/python

from qcodes.instrument_drivers.cryomagnetics import Cryomagnetics4G
from time import sleep

magpsu = Cryomagnetics4G.CryoMag4G("magpsu", "TCPIP0::192.168.0.187::4444::SOCKET",
                                   pheater_wait_time = 10)

magpsu.remote(True)

magpsu.psu1.units('A')
magpsu.psu2.units('A')

magpsu.psu1.pheater(True)

magpsu.psu2.sweep_to(1.0)
magpsu.psu2.wait_then_pause_sweep()
print(magpsu.psu2.output_current())

magpsu.psu2.sweep_to(-1.0)
magpsu.psu2.wait_then_pause_sweep(duration = 1.0)
print(magpsu.psu2.output_current())

magpsu.psu2.sweep("ZERO")
magpsu.psu2.wait_then_pause_sweep()
print(magpsu.psu2.output_current())

magpsu.close()
