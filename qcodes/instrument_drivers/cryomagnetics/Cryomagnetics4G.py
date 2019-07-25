from qcodes import VisaInstrument, Instrument, Parameter, validators
from qcodes.instrument.channel import InstrumentChannel

import re
import numpy as np
from time import time

class _Rates(Parameter):
    def get_raw(self) -> float:
        cmd = f"CHAN {self.instrument.name[-1]}; RATE? "
        return [float(self.instrument.parent.ask_raw(cmd + str(i))) for i in range(6)]

class _Ranges(Parameter):
    def get_raw(self) -> float:
        cmd = f"CHAN {self.instrument.name[-1]}; RANGE? "
        return [float(self.instrument.parent.ask_raw(cmd + str(i))) for i in range(5)]

class _PersistentHeater(Parameter):
    def get_raw(self) -> float:
        cmd = f"CHAN {self.instrument.name[-1]}; PSHTR?"
        return True if self.instrument.parent.ask_raw(cmd) == "1" else False
    
    def set_raw(self, val) -> None:
        self.instrument.sweep("PAUSE") # make sure we aren't sweeping
        if val and not(self.instrument.output_close_to(self.instrument.magnet_current())):
            raise RuntimeError("Refused! Output and magnet currents must match.")
    
        state = "ON" if val else "OFF"
        self.instrument.parent.write_raw(f"CHAN {self.instrument.name[-1]}; PSHTR {state}")

class CryoMagChannel(InstrumentChannel):
    def __init__(self, parent: Instrument, name: str, ch: str, pheater_wait_time) -> None:
        """
        Args:
            parent: The Instrument instance to which the channel is
                to be attached.
            name: The 'colloquial' name of the channel
            channel: The name used by the magnet power supply, i.e. either 1 or 2
        """
        super().__init__(parent, name)

        if ch not in [1, 2]:
            raise ValueError('channel must be either 1 or 2')

        self.add_parameter('rates', parameter_class = _Rates, units = 'A/s')
        self.add_parameter('ranges', parameter_class = _Ranges, units = 'A')

        self.add_parameter('units',
                           set_cmd = f'CHAN {ch}; UNITS {{}}',
                           get_cmd = f'CHAN {ch}; UNITS?',
                           set_parser = lambda x : x[-1],
                           vals = validators.Enum('A', 'kG'))
        
        parser = lambda x : float(re.sub("[^0-9.\-]", "", x.strip()))

        self.add_parameter('magnet_current',
                           get_cmd = f'CHAN {ch}; IMAG?',
                           units = self.units(),
                           get_parser = parser)

        self.add_parameter('magnet_voltage',
                           get_cmd = f'CHAN {ch}; VMAG?',
                           units = 'V',
                           get_parser = parser)
        
        self.add_parameter('output_current',
                           get_cmd = f'CHAN {ch}; IOUT?',
                           units = self.units(),
                           get_parser = parser)

        self.add_parameter('output_voltage',
                           get_cmd = f'CHAN {ch}; VOUT?',
                           units = 'V',
                           get_parser = parser)
        
        self.add_parameter('llim',
                           set_cmd = f'CHAN {ch}; LLIM {{}}',
                           get_cmd = f'CHAN {ch}; LLIM?',
                           get_parser = parser,
                           vals = validators.Numbers(-100, 100))
        
        self.add_parameter('ulim',
                           set_cmd = f'CHAN {ch}; ULIM {{}}',
                           get_cmd = f'CHAN {ch}; ULIM?',
                           get_parser = parser,
                           vals = validators.Numbers(-100, 100))
        
        self.add_parameter('vlim',
                           set_cmd = f'CHAN {ch}; VLIM {{}}',
                           get_cmd = f'CHAN {ch}; VLIM?',
                           get_parser = parser,
                           vals = validators.Numbers(0, 10))
        
        if ch == 1: 
            self.add_parameter('pheater',
                               vals = validators.Bool(),
                               parameter_class = _PersistentHeater,
                               post_delay = pheater_wait_time)
        
        # NOTE: post_delay required as instrment locks up for short period after setting
        #       sweep.
        self.add_parameter('sweep',
                           get_cmd = f'CHAN {ch}; SWEEP?',
                           set_cmd = f'CHAN {ch}; SWEEP {{}}',
                           post_delay = 0.5,
                           vals = validators.Enum("UP", "DOWN", "PAUSE", "ZERO",
                                                  "UP FAST", "DOWN FAST", "ZERO FAST"))

        self.sweep("PAUSE")

    def sweep_to(self, target):
        """ initiate sweep from self.output_current() to target """
        if hasattr(self, 'pheater'): # then we can sweep fast if its on
            if not(self.pheater()):
                raise RuntimeError("Persistent heater must be active to use this channel")
            
        for name, ch in self.parent.submodules.items():
            if ch.sweep() not in ["Pause", "Standby"]:
                raise RuntimeError(f"Sweep on {name} is active!")

        if target == 0:
            direction = "ZERO"
        elif target < self.output_current():
            self.llim(target)
            self.ulim(self.output_current())
            direction = "DOWN"
        else:
            self.llim(self.output_current())
            self.ulim(target)
            direction = "UP"

        if hasattr(self, 'pheater'): # then we can sweep fast if its on
            if self.pheater():
                direction += " FAST"

        self.sweep(direction)
        self.sweep(direction) # XXX: sometimes requires a second set to initiate sweep

    def wait_then_pause_sweep(self, duration = 'auto'):
        """ wait for 'duration' or for the sweep to finish and then pause the sweep

        Args:
            duration:   time to wait in seconds or 'auto'. 'auto' waits until the
                        sweep is complete before pausing.
        """
        if self.sweep() in ["Pause", "Standby"]:
            return

        words = self.sweep().split()
        direction = words[1]

        if direction == 'down':
            target = self.llim()
        elif direction == 'up':
            target = self.ulim()
        else:
            target = 0.0
        
        if duration == 'auto':
            if words[-1] == 'fast':
                duration = 2*(self.ulim() - self.llim())/self.rates()[-1]
            else:
                # use the slowest rate to define the timeout period
                # TODO: intelligently detect the present range and adapt to rate associated
                #       with it
                duration = 2*(self.ulim() - self.llim())/np.min(self.rates()[:-1])

        start = time()
        while (time() - start) < duration:
            if self.output_close_to(target):
                break
    
        self.sweep("PAUSE")
    
    def output_close_to(self, target):
        if self.units() == 'A':
            return (np.abs((self.output_current() - target)) < 1e-3)
        else:
            return (np.abs((self.output_current() - target)) < 1e-5)

class CryoMag4G(VisaInstrument):
    def __init__(self, name: str, address: str, pheater_wait_time = 300, **kwargs) -> None:
        super().__init__(name, address, terminator = '\r\n', **kwargs)

        if 'TCPIP' not in address:
            raise NotImplementedError("USB/GPIB interfaces are not yet supported")

        self.add_parameter('remote',
                           set_cmd = '{}',
                           set_parser = lambda b : 'REMOTE' if b else 'LOCAL',
                           vals = validators.Bool(),
                           docstring = 'sets mode to either local or remote')

        for ch in [1, 2]:
            self.add_submodule(f'psu{ch}', CryoMagChannel(self, f'psu{ch}', ch,
                                                          pheater_wait_time = pheater_wait_time))

        self.connect_message()
