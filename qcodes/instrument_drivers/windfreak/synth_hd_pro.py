from qcodes import VisaInstrument, Instrument, Parameter, validators
from qcodes.instrument.channel import InstrumentChannel

class SynthHdPro(VisaInstrument):
    def __init__(self, name: str, address: str, **kwargs) -> None:
        super().__init__(name, address, terminator = '\n', **kwargs)

        for ch in [0, 1]:
            self.write_raw(f'C{ch};T1') # use auto-calibration
            self.add_submodule(f'RF{ch}', SynthHdProChannel(self, f'RF{ch}', ch))

        self.connect_message()

    def get_idn(self):
        """Returns device metadata for this non-visa device"""
        return {
            'vendor':'WindFreak',
            'model': self.ask_raw('+'),
            'serial': None,
            'firmware': self.ask_raw('v0'),
        }

class SynthHdProChannel(InstrumentChannel):
    def __init__(self, parent: Instrument, name: str, ch: str) -> None:
        """
        Args:
            parent: The Instrument instance to which the channel is
                to be attached.
            name: The 'colloquial' name of the channel
            channel: The name used by the microwave source, i.e. either 1 or 2
        """
        super().__init__(parent, name)

        self.add_parameter('frequency',
                           units = 'Hz',
                           set_cmd = f'C{ch};f{{}}',
                           get_cmd = f'C{ch};f?',
                           set_parser = lambda x : '%5.7f' % (x/1e6),
                           get_parser = lambda x : 1e6*float(x),
                           vals = validators.Numbers(53e6, 24e9))

        self.add_parameter('power',
                           units = 'dBm',
                           set_cmd = f'C{ch};W{{}}',
                           get_cmd = f'C{ch};W?',
                           set_parser = lambda x : '%2.3f' % x,
                           get_parser = float,
                           vals = validators.Numbers(-60, 20))

        self.add_parameter('calibration_success',
                           get_cmd = f'C{ch};V',
                           get_parser = lambda x : bool(int(x)))

        self.add_parameter('mute',
                           set_cmd = f'C{ch};h{{}}',
                           get_cmd = f'C{ch};h?',
                           set_parser = int,
                           get_parser = lambda x : bool(int(x)),
                           vals = validators.Bool())

        trig_tbl = ['none', 'fsweep', 'fstep', 'stop']

        self.add_parameter('trigger_mode',
                           set_cmd = f'C{ch};w{{}}',
                           get_cmd = f'C{ch};w?',
                           set_parser = trig_tbl.index,
                           get_parser = lambda x : trig_tbl[x],
                           vals = validators.Enum(*trig_tbl))

        self.add_parameter('freqlo',
                           units = 'Hz',
                           set_cmd = f'C{ch};l{{}}',
                           get_cmd = f'C{ch};l?',
                           set_parser = lambda x : '%5.7f' % (x/1e6),
                           get_parser = lambda x : 1e6*float(x),
                           vals = validators.Numbers(53e6, 24e9))

        self.add_parameter('freqhi',
                           units = 'Hz',
                           set_cmd = f'C{ch};u{{}}',
                           get_cmd = f'C{ch};u?',
                           set_parser = lambda x : '%5.7f' % (x/1e6),
                           get_parser = lambda x : 1e6*float(x),
                           vals = validators.Numbers(53e6, 24e9))

        self.add_parameter('powerlo',
                           units = 'dBm',
                           set_cmd = f'C{ch};[{{}}',
                           get_cmd = f'C{ch};[?',
                           set_parser = lambda x : '%2.3f' % x,
                           get_parser = float,
                           vals = validators.Numbers(-60, 20))

        self.add_parameter('powerhi',
                           units = 'dBm',
                           set_cmd = f'C{ch};]{{}}',
                           get_cmd = f'C{ch};]?',
                           set_parser = lambda x : '%2.3f' % x,
                           get_parser = float,
                           vals = validators.Numbers(-60, 20))

        self.add_parameter('freqstep',
                           units = 'Hz',
                           set_cmd = f'C{ch};s{{}}',
                           get_cmd = f'C{ch};s?',
                           set_parser = lambda x : '%5.7f' % (x/1e6),
                           get_parser = lambda x : 1e6*float(x))

        self.add_parameter('steptime',
                           units = 'ms',
                           set_cmd = f'C{ch};t{{}}',
                           get_cmd = f'C{ch};t?',
                           set_parser = lambda x : '%5.3f' % x,
                           get_parser = float,
                           vals = validators.Numbers(4, 10e3))

        self.add_parameter('sweepdir',
                           units = 'ms',
                           set_cmd = f'C{ch};^{{}}',
                           get_cmd = f'C{ch};^?',
                           set_parser = lambda x : '1' if x == 'up' else '0',
                           get_parser = lambda x : 'up' if x == '1' else 'down',
                           vals = validators.Enum('up', 'down'))

        self.add_parameter('sweeptype',
                           units = 'ms',
                           set_cmd = f'C{ch};X{{}}',
                           get_cmd = f'C{ch};X?',
                           set_parser = lambda x : '1' if x == 'tabular' else '0',
                           get_parser = lambda x : 'tabular' if x == '1' else 'linear',
                           vals = validators.Enum('tabular', 'linear'))
