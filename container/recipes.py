'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>
'''

from __future__ import print_function
import os
import sys
from distutils.version import StrictVersion

import hpccm

import config
from utilities.cli import tools_order


class StageMixin:
    '''This is a Mixin class contains common features of DevelopmentStage, ApplicationStage and
    DeploymentStage. such as, _prepare, _build, _runtime, _cook methods
    '''

    def __init__(self, *, args, previous_stage):
        self.args = args
        self.previous_stage = previous_stage
        self._build(previous_stage=previous_stage)

    def _prepare(self):
        '''
        We need to keep track of precision and cuda for, that will be used in build some other tools.
        Such as fftw, gromacs etc.:
            * double : need to delete it from the args, as there will be no method for double
            * cuda   : Will not delete it as we will add cuda method later
        '''

        if 'double' in self.args:
            self.double_precision_enabled = self.args.get('double', False)
            del self.args['double']

        self.cuda_enabled = True if self.args.get('cuda', None) else False

    def _build(self, *, previous_stage):
        '''
        This method perform the preparation for the recipes and
        Then generate the recipes and finally cook the recipes
        '''

        self.stage = hpccm.Stage()

        self._prepare()

        for tool in tools_order:
            if tool in self.args:
                try:
                    method = getattr(self, tool)
                except AttributeError as error:
                    pass
                    # print(error)
                else:
                    # print('method', method)
                    method(self.args[tool])

        # Recipe has been prepared. Now, it is time to cook .....
        self._cook()

    def format(self, spec):
        hpccm.config.set_container_format(spec)

    def _runtime(self):
        '''
        Return the runtime for this stage
        '''
        return self.stage.runtime()

    def ubuntu(self, version):
        '''
        Choose base image based on Linux ubuntu distribution
        '''
        if self.cuda_enabled:
            # base image will be created in method cuda
            return
        else:
            self.stage += hpccm.primitives.baseimage(image='ubuntu:' + version, _as=self.stage_name)
            if self.previous_stage:
                self.stage += self.previous_stage._runtime()

    def centos(self, version):
        '''
        Choose base image based on Linux centos distribution
        '''
        if self.cuda_enabled:
            # base image will be created in method cuda
            return
        else:
            self.stage += hpccm.primitives.baseimage(image='centos:centos' + version, _as=self.stage_name)
            if self.previous_stage:
                self.stage += self.previous_stage._runtime()

    def cuda(self, version):
        '''
        Choose base image from nvidia
        '''
        raise RuntimeError('Cuda : not implemented yet...')

    def cmake(self, version):
        '''
        cmake : need to check minimum version requirement
        '''
        if StageMixin.version_checked('CMake', config.CMAKE_MIN_REQUIRED_VERSION, version):
            self.stage += hpccm.building_blocks.cmake(eula=True, version=version)

    def gcc(self, version):
        '''
        gcc compiler
        '''
        self.compiler = hpccm.building_blocks.gnu(extra_repository=True,
                                                  fortran=False,
                                                  version=version)
        self.stage += self.compiler

    def _cook(self):
        '''
        This method will print all recipes for this stage
        '''
        print(self.stage)
        # pass

    @staticmethod
    def version_checked(tool, required, given):
        '''
        Static method to check the software verion
        '''
        if StrictVersion(given) < StrictVersion(required):
            raise RuntimeError('{tool} version not fulfilled: {given}. Minimum required version: {required}.'.format(
                tool=tool,
                given=given,
                required=required
            ))
        return True


class DevelopmentStage(StageMixin):
    def __init__(self, *, args, previous_stage):
        self.stage_name = 'dev_stage'
        StageMixin.__init__(self, args=args, previous_stage=previous_stage)

    def _prepare(self):
        StageMixin._prepare(self)

    def fftw(self, version):
        '''
        Add fftw building blocks
        '''
        configure_opts = ['--enable-shared', '--disable-static', '--enable-sse2',
                          '--enable-avx', '--enable-avx2', '--enable-avx512']
        if not self.double_precision_enabled:
            configure_opts.append('--enable-float')

        if hasattr(self.compiler, 'toolchain'):
            self.stage += hpccm.building_blocks.fftw(toolchain=self.compiler.toolchain,
                                                     configure_opts=configure_opts,
                                                     version=version)
        else:
            raise RuntimeError('Implementation Error: compiler is not an HPCCM building block')

    def openmpi(self, version):
        if StageMixin.version_checked('openmpi', config.OPENMPI_MIN_REQUIRED_VERSION, version):
            if hasattr(self.compiler, 'toolchain'):
                self.stage += hpccm.building_blocks.openmpi(cuda=self.cuda_enabled, infiniband=False,
                                                            toolchain=self.compiler.toolchain,
                                                            version=version)
            else:
                raise RuntimeError('Implementation Error: compiler is not an HPCCM building block')

    def impi(self, version):
        raise RuntimeError('impi : not implemented yet...')


class ApplicationStage(StageMixin):
    _os_packages = ['wget']
    _cmake_opts = "\
                -DCMAKE_INSTALL_BINDIR=bin.$simd$ \
                -DCMAKE_INSTALL_LIBDIR=lib.$simd$ \
                -DCMAKE_C_COMPILER=$c_compiler$ \
                -DCMAKE_CXX_COMPILER=$cxx_compiler$ \
                -DGMX_OPENMP=ON \
                -DGMX_MPI=$mpi$ \
                -DGMX_GPU=$cuda$ \
                -DGMX_SIMD=$simd$ \
                -DGMX_USE_RDTSCP=$rdtscp$ \
                -DGMX_DOUBLE=$double$ \
                -D$fft$ \
                -DGMX_EXTERNAL_BLAS=OFF \
                -DGMX_EXTERNAL_LAPACK=OFF \
                -DBUILD_SHARED_LIBS=OFF \
                -DGMX_PREFER_STATIC_LIBS=ON \
                -DREGRESSIONTEST_DOWNLOAD=$regtest$ \
                -DGMX_DEFAULT_SUFFIX=OFF \
                -DGMX_BINARY_SUFFIX=$bin_suffix$ \
                -DGMX_LIBS_SUFFIX=$libs_suffix$ \
                "

    def __init__(self, *, args, previous_stage):
        self.stage_name = 'app_stage'
        StageMixin.__init__(self, args=args, previous_stage=previous_stage)

    def _prepare(self):
        self.regtest_enabled = self.args.get('regtest', False)
        # del self.args['regtest']
        self.mpi_enabled = True if self.args.get('openmpi', None) or self.args.get('impi', None) else False
        self.fftw_installed = True if self.args.get('fftw', None) else False

        for key in ['openmpi', 'impi', 'fftw']:
            if key in self.args:
                del self.args[key]

        StageMixin._prepare(self)

    def gromacs(self, version):
        # adding os_packages required for this stage application
        self.stage += hpccm.building_blocks.packages(ospackages=self._os_packages)
        # relative to /var/tmp
        self.source_directory = 'gromacs-{version}'.format(version=version)
        # relative to source_directory
        self.build_directory = 'build.{simd}'
        # installation directotry
        self.prefix = config.GMX_INSTALLATION_DIRECTORY
        # environment variables to be set prior to Gromacs build
        self.build_environment = {}
        # url to download Gromacs
        self.url = 'ftp://ftp.gromacs.org/pub/gromacs/gromacs-{version}.tar.gz'.format(version=version)

        self.gromacs_cmake_opts = self._get_gromacs_cmake_opts()
        self.wrapper = 'gmx' + self._get_wrapper_suffix()

    def regtest(self, enabled):
        # update cmake_opts in case mpi was enabled
        if self.mpi_enabled:
            regtest_mpi_cmake_variables = " -DMPIEXEC_PREFLAGS='--allow-run-as-root;--oversubscribe'"
            self.gromacs_cmake_opts = self.gromacs_cmake_opts + regtest_mpi_cmake_variables

        # preinstall
        self.preconfigure = ['apt-get update',
                             'apt-get upgrade -y',
                             'apt-get install -y perl', ]
        self.check = True

    def engines(self, engine_list):
        # TODO : Deal with default engine. Move default engine chooser here or in config
        for engine in engine_list:
            # binary and library suffix for gmx
            parsed_engine = self._parse_engine(engine)
            bin_libs_suffix = self._get_bin_libs_suffix(parsed_engine['rdtscp'])
            engine_cmake_opts = self.gromacs_cmake_opts.replace('$bin_suffix$', bin_libs_suffix)
            engine_cmake_opts = engine_cmake_opts.replace('$libs_suffix$', bin_libs_suffix)

            # simd, rdtscp
            for key in parsed_engine:
                value = parsed_engine[key] if key == 'simd' else parsed_engine[key].upper()
                engine_cmake_opts = engine_cmake_opts.replace('$' + key + '$', value)

            self.stage += hpccm.building_blocks.generic_cmake(cmake_opts=engine_cmake_opts.split(),
                                                              directory=self.source_directory,
                                                              build_directory=self.build_directory.format(simd=parsed_engine['simd']),
                                                              prefix=self.prefix,
                                                              build_environment=self.build_environment,
                                                              url=self.url,
                                                              preconfigure=self.preconfigure,
                                                              check=self.check)

    def _parse_engine(self, engine):
        if engine:
            engine_args = map(lambda x: x.strip(), engine.split(':'))
            engine_args_dict = {}
            for engine_arg in engine_args:
                key, value = map(lambda x: x.strip(), engine_arg.split('='))

                # TODO : Check arguments value
                # self.__check_gromacs_engine_argument(key=key, value=value)

                engine_args_dict[key] = config.SIMD_MAPPER[value] if key == 'simd' else value
            return engine_args_dict

    def _get_gromacs_cmake_opts(self):
        '''
        Configure the common cmake_opts for different Gromacs build
        based on sind instruction
        '''
        gromacs_cmake_opts = self._cmake_opts[:]
        # Compiler and mpi
        if self.mpi_enabled:
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$c_compiler$', 'mpicc')
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$cxx_compiler$', 'mpicxx')
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$mpi$', 'ON')
        else:
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$c_compiler$', 'gcc')
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$cxx_compiler$', 'g++')
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$mpi$', 'OFF')

        #  fftw
        if self.fftw_installed:
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$fft$', 'GMX_FFT_LIBRARY=fftw3')
            self.build_environment['CMAKE_PREFIX_PATH'] = '\'/usr/local/fftw\''
        else:
            gromacs_cmake_opts = gromacs_cmake_opts.replace('$fft$', 'GMX_BUILD_OWN_FFTW=ON')

        # cuda, regtest, double
        for (option, enabled) in zip(['cuda', 'regtest', 'double'], [self.cuda_enabled, self.regtest_enabled, self.double_precision_enabled]):
            if enabled:
                gromacs_cmake_opts = gromacs_cmake_opts.replace('$' + option + '$', 'ON')
            else:
                gromacs_cmake_opts = gromacs_cmake_opts.replace('$' + option + '$', 'OFF')

        return gromacs_cmake_opts

    def _get_wrapper_suffix(self):
        '''
        Set the wrapper suffix based on mpi enabled/disabled and
        double precision enabled and disabled
        '''
        return config.WRAPPER_SUFFIX_FORMAT.format(mpi=config.GMX_ENGINE_SUFFIX_OPTIONS['mpi'] if self.mpi_enabled else '',
                                                   double=config.GMX_ENGINE_SUFFIX_OPTIONS['double'] if self.double_precision_enabled else '')

    def _get_bin_libs_suffix(self, rdtscp):
        '''
        Set tgmx binaries and library suffix based on mpi enabled/disabled,
        double precision enabled and disabled and
        rdtscp enabled/disabled
        '''
        return config.BINARY_SUFFIX_FORMAT.format(mpi=config.GMX_ENGINE_SUFFIX_OPTIONS['mpi'] if self.mpi_enabled else '',
                                                  double=config.GMX_ENGINE_SUFFIX_OPTIONS['double'] if self.double_precision_enabled else '',
                                                  rdtscp=config.GMX_ENGINE_SUFFIX_OPTIONS['rdtscp'] if rdtscp.lower() == 'on' else '')


class DeploymentStage(StageMixin):
    _os_packages = ['vim']

    def __init__(self, *, args, previous_stage):
        self.stage_name = 'deploy_stage'
        StageMixin.__init__(self, args=args, previous_stage=previous_stage)

    def _prepare(self):
        StageMixin._prepare(self)

    def _configure(self):
        '''
        Add some required packages, create the wrapper binaries and the gmx_chooser script
        '''
        # Adding python module
        self.stage += hpccm.building_blocks.python(python3=True,
                                                   python2=False,
                                                   devel=False)

        # os packages
        self.stage += hpccm.building_blocks.packages(ospackages=self._os_packages)

        # wrapper and gmx_chooser scripts
        scripts_directory = os.path.join(config.GMX_INSTALLATION_DIRECTORY, 'scripts')

        self.stage += hpccm.primitives.shell(commands=['mkdir -p {}'.format(scripts_directory)])

        # setting arapper sctipt
        wrapper = os.path.join(scripts_directory, self.previous_stage.wrapper)
        self.stage += hpccm.primitives.copy(src='/scripts/wrapper.py', dest=wrapper)

        # copying the gmx_chooser script
        self.stage += hpccm.primitives.copy(src='/scripts/gmx_chooser.py',
                                            dest=os.path.join(scripts_directory, 'gmx_chooser.py'))
        # chmod for files scripts_directory
        self.stage += hpccm.primitives.shell(commands=['chmod +x {}'.format(
            os.path.join(scripts_directory, '*')
        )])

        # copying config file
        self.stage += hpccm.primitives.copy(src='config.py',
                                            dest=os.path.join(scripts_directory, 'config.py'))
        # setting environment variable so to make wrapper available to PATH
        self.stage += hpccm.primitives.environment(variables={'PATH': '$PATH:{}'.format(scripts_directory)})

    def format(self, spec):
        self._configure()
        StageMixin.format(self, spec)
