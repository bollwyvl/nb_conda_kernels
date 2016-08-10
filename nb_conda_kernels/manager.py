# -*- coding: utf-8 -*-

import entrypoints

from jupyter_client.kernelspec import (
    KernelSpecManager,
)

CACHE_TIMEOUT = 60
ENTRY_POINT = "nb_env_kernels.spec_finder"


class CondaKernelSpecManager(KernelSpecManager):
    """ A custom KernelSpecManager able to search for conda environments and
        create kernelspecs for them.
    """
    def __init__(self, **kwargs):
        super(CondaKernelSpecManager, self).__init__(**kwargs)

        self._cached_kernelspecs = None

        self._finders = dict(self._load_finders_iter())

        self.log.info("[nb_env_kernels] enabled, %s kernels found",
                      len(self._kernelspecs))

    def _load_finders_iter(self):
        for name, ep in entrypoints.get_group_named(ENTRY_POINT).items():
            try:
                yield name, ep.load()(parent=self)
                self.log.debug("[nb_env_kernels] loaded %s spec finder", name)
            except Exception as err:
                self.log.warn("Failed to import finder %s: %s", name, err)

    @property
    def _kernelspecs(self):
        if self._cached_kernelspecs is None:
            kspecs = {}

            for finder_name, finder in self._finders.items():
                # add found kernelspecs
                kspecs.update({
                    "{}-{}".format(finder_name, name): spec
                    for name, spec
                    in finder.find_kernel_specs().items()})

            self._cached_kernelspecs = kspecs

        return self._cached_kernelspecs

    def find_kernel_specs(self):
        """ Returns a dict mapping kernel names to resource directories.

            The update process also adds the resource dir for the found specs.
        """
        kspecs = {
            name: spec.resource_dir
            for name, spec in self._kernelspecs.items()
        }

        # the default kernel specs always win
        kspecs.update(super(CondaKernelSpecManager, self).find_kernel_specs())

        return kspecs

    def get_kernel_spec(self, kernel_name):
        """ Returns a :class:`KernelSpec` instance for the given kernel_name.

            Additionally, other kernelspecs are generated on the fly
            accordingly with the detected envitonments.
        """

        if kernel_name in self._kernelspecs:
            return self._kernelspecs[kernel_name]

        return (
            self._kernelspecs.get(kernel_name) or
            super(CondaKernelSpecManager, self).get_kernel_spec(kernel_name)
        )
