import json
import subprocess
import sys
import time

from os.path import exists, join, split, dirname, abspath

from jupyter_client.kernelspec import (
    KernelSpec,
)

from nb_conda_kernels.spec_finders.base import BaseSpecFinder

CACHE_TIMEOUT = 60


class CondaSpecFinder(BaseSpecFinder):
    def __init__(self, *args, **kwargs):
        super(CondaSpecFinder, self).__init__(*args, **kwargs)
        raise Exception(self.config)
        self._conda_info_cache = None
        self._conda_info_cache_expiry = None

        self._conda_kernels_cache = None
        self._conda_kernels_cache_expiry = None

    def find_kernel_specs(self):
        return self._conda_kspecs

    @property
    def _conda_info(self):
        """ Get and parse the whole conda information output

            Caches the information for CACHE_TIMEOUT seconds, as this is
            relatively expensive.
        """

        expiry = self._conda_info_cache_expiry

        if expiry is None or expiry < time.time():
            self.log.debug("[nb_conda_kernels] refreshing conda info")
            try:
                p = subprocess.check_output(["conda", "info", "--json"]
                                            ).decode("utf-8")
                conda_info = json.loads(p)
            except Exception as err:
                conda_info = None
                self.log.error("[nb_conda_kernels] couldn't call conda:\n%s",
                               err)
            self._conda_info_cache = conda_info
            self._conda_info_cache_expiry = time.time() + CACHE_TIMEOUT

        return self._conda_info_cache

    def _all_envs(self):
        """ Find the all the executables for each env where jupyter is
            installed.

            Returns a dict with the env names as keys and info about the kernel
            specs, including the paths to the lang executable in each env as
            value if jupyter is installed in that env.

            Caches the information for CACHE_TIMEOUT seconds, as this is
            relatively expensive.
        """
        # play safe with windows
        if sys.platform.startswith('win'):
            python = join("python.exe")
            r = join("Scripts", "R.exe")
            jupyter = join("Scripts", "jupyter.exe")
        else:
            python = join("bin", "python")
            r = join("bin", "R")
            jupyter = join("bin", "jupyter")

        def get_paths_by_env(display_prefix, language_key, language_exe, envs):
            """ Get a dict with name_env:info for kernel executables
            """
            language_envs = {}
            for base in envs:
                exe_path = join(base, language_exe)
                if exists(join(base, jupyter)) and exists(exe_path):
                    env_name = split(base)[1]
                    name = 'env-{}-{}'.format(env_name, language_key)
                    language_envs[name] = {
                        'display_name': '{} [conda env:{}]'.format(
                            display_prefix, env_name),
                        'executable': exe_path,
                        'language_key': language_key,
                    }
            return language_envs

        # Collect all the envs in one dict
        all_envs = {}

        # Get the python envs
        python_envs = get_paths_by_env("Python", "py", python,
                                       self._conda_info["envs"])
        all_envs.update(python_envs)

        # Get the R envs
        r_envs = get_paths_by_env("R", "r", r, self._conda_info["envs"])
        all_envs.update(r_envs)

        # We also add the root prefix into the soup
        root_prefix = join(self._conda_info["root_prefix"], jupyter)
        if exists(root_prefix):
            all_envs.update({
                'root-py': {
                    'display_name': 'Python [conda root]',
                    'executable': join(self._conda_info["root_prefix"],
                                       python),
                    'language_key': 'py',
                }
            })

        return all_envs

    @property
    def _conda_kspecs(self):
        """ Get (or refresh) the cache of conda kernels
        """
        if self._conda_info is None:
            return {}

        if (
            self._conda_kernels_cache_expiry is None or
            self._conda_kernels_cache_expiry < time.time()
           ):
            self.log.debug("[nb_conda_kernels] refreshing conda kernelspecs")
            self._conda_kernels_cache = self._load_conda_kspecs()
            self._conda_kernels_cache_expiry = time.time() + CACHE_TIMEOUT

        return self._conda_kernels_cache

    def _load_conda_kspecs(self):
        """ Create a kernelspec for each of the envs where jupyter is installed
        """
        kspecs = {}
        for name, info in self._all_envs().items():
            executable = info['executable']
            display_name = info['display_name']

            if info['language_key'] == 'py':
                kspec = {
                    "argv": [executable, "-m", "ipykernel", "-f",
                             "{connection_file}"],
                    "display_name": display_name,
                    "language": "python",
                    "env": {},
                    "resource_dir": join(dirname(abspath(__file__)), "logos",
                                         "python")
                 }
            elif info['language_key'] == 'r':
                kspec = {
                    "argv": [executable, "--slave", "-e", "IRkernel::main()",
                             "--args", "{connection_file}"],
                    "display_name": display_name,
                    "language": "R",
                    "env": {},
                    "resource_dir": join(dirname(abspath(__file__)), "logos",
                                         "r")
                }

            kspecs.update({
                name: KernelSpec(**kspec)
            })

        return kspecs
