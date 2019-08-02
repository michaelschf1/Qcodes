from qcodes import VisaInstrument, Parameter, validators

class _EnableOutput(Parameter):
    def set_raw(self, val):
        self.instrument.write_raw('RF1' if val else 'RF0')

class MG3690BBasic(VisaInstrument):
    def __init__(self, name: str, address: str, **kwargs) -> None:
        """ Qcodes wrapper for basic frequency and level setting of an
        Anritsu MG3690 series microwave source.

        Notes:
            - Connecting to this instrument with a USB to GPIB convertor
              automatically enables the output before it is quickly
              disabled below. Check the output power before use to avoid
              damage to equipment.

        Args:
            name:       the name of the insrument
            address:    the visa address of the instrument
        """
        super().__init__(name, address, terminator = '\r\n', **kwargs)

        self.add_parameter('frequency',
                           get_cmd = "OF0",
                           set_cmd = "F0 {} GH; ACW",
                           units = "GHz",
                           get_parser = float,
                           vals = validators.Numbers(2.0, 20.0))

        self.add_parameter('power',
                           get_cmd = "OL0",
                           set_cmd = "L0 {} DM",
                           units = "dBm",
                           get_parser = float,
                           vals = validators.Numbers(-30.0, 19.0))

        self.add_parameter('output_enabled',
                           vals = validators.Bool(),
                           docstring = "enables or disables the output",
                           parameter_class = _EnableOutput)

        self.power(-30)
        self.output_enabled(False)

        self.connect_message()
