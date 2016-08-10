from traitlets.config import LoggingConfigurable


class BaseSpecFinder(LoggingConfigurable):
    """
    A base class for spec finders
    """
    def find_kernel_specs(self):
        raise NotImplementedError(
            "{} didn't implement find_kernel_specs".format(self))
