FROM ubuntu:18.04 AS dev_stage

# CMake version 3.17.1
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        make \
        wget && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/tmp && wget -q -nc --no-check-certificate -P /var/tmp https://cmake.org/files/v3.17/cmake-3.17.1-Linux-x86_64.sh && \
    mkdir -p /usr/local && \
    /bin/sh /var/tmp/cmake-3.17.1-Linux-x86_64.sh --prefix=/usr/local --skip-license && \
    rm -rf /var/tmp/cmake-3.17.1-Linux-x86_64.sh
ENV PATH=/usr/local/bin:$PATH

# GNU compiler
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends software-properties-common && \
    apt-add-repository ppa:ubuntu-toolchain-r/test -y && \
    apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        g++-9 \
        gcc-9 && \
    rm -rf /var/lib/apt/lists/*
RUN update-alternatives --install /usr/bin/g++ g++ $(which g++-9) 30 && \
    update-alternatives --install /usr/bin/gcc gcc $(which gcc-9) 30 && \
    update-alternatives --install /usr/bin/gcov gcov $(which gcov-9) 30

# OpenMPI version 3.0.0
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bzip2 \
        file \
        hwloc \
        libnuma-dev \
        make \
        openssh-client \
        perl \
        tar \
        wget && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/tmp && wget -q -nc --no-check-certificate -P /var/tmp https://www.open-mpi.org/software/ompi/v3.0/downloads/openmpi-3.0.0.tar.bz2 && \
    mkdir -p /var/tmp && tar -x -f /var/tmp/openmpi-3.0.0.tar.bz2 -C /var/tmp -j && \
    cd /var/tmp/openmpi-3.0.0 &&  CC=gcc CXX=g++ ./configure --prefix=/usr/local/openmpi --disable-getpwuid --enable-orterun-prefix-by-default --without-cuda --without-verbs && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /var/tmp/openmpi-3.0.0.tar.bz2 /var/tmp/openmpi-3.0.0
ENV LD_LIBRARY_PATH=/usr/local/openmpi/lib:$LD_LIBRARY_PATH \
    PATH=/usr/local/openmpi/bin:$PATH

# FFTW version 3.3.7
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        file \
        make \
        wget && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/tmp && wget -q -nc --no-check-certificate -P /var/tmp ftp://ftp.fftw.org/pub/fftw/fftw-3.3.7.tar.gz && \
    mkdir -p /var/tmp && tar -x -f /var/tmp/fftw-3.3.7.tar.gz -C /var/tmp -z && \
    cd /var/tmp/fftw-3.3.7 &&  CC=gcc CXX=g++ ./configure --prefix=/usr/local/fftw --disable-static --enable-avx --enable-avx2 --enable-avx512 --enable-shared --enable-sse2 && \
    make -j$(nproc) && \
    make -j$(nproc) install && \
    rm -rf /var/tmp/fftw-3.3.7.tar.gz /var/tmp/fftw-3.3.7
ENV LD_LIBRARY_PATH=/usr/local/fftw/lib:$LD_LIBRARY_PATH
FROM ubuntu:18.04 AS app_stage

# GNU compiler runtime
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends software-properties-common && \
    apt-add-repository ppa:ubuntu-toolchain-r/test -y && \
    apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# OpenMPI
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        hwloc \
        openssh-client && \
    rm -rf /var/lib/apt/lists/*
COPY --from=dev_stage /usr/local/openmpi /usr/local/openmpi
ENV LD_LIBRARY_PATH=/usr/local/openmpi/lib:$LD_LIBRARY_PATH \
    PATH=/usr/local/openmpi/bin:$PATH

# FFTW
COPY --from=dev_stage /usr/local/fftw /usr/local/fftw
ENV LD_LIBRARY_PATH=/usr/local/fftw/lib:$LD_LIBRARY_PATH

# ftp://ftp.gromacs.org/pub/gromacs/gromacs-2020.1.tar.gz
RUN mkdir -p /var/tmp && wget -q -nc --no-check-certificate -P /var/tmp ftp://ftp.gromacs.org/pub/gromacs/gromacs-2020.1.tar.gz && \
    mkdir -p /var/tmp && tar -x -f /var/tmp/gromacs-2020.1.tar.gz -C /var/tmp -z && \
    cd /var/tmp/gromacs-2020.1 && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y perl && \
    mkdir -p /var/tmp/gromacs-2020.1/build.AVX2_256 && cd /var/tmp/gromacs-2020.1/build.AVX2_256 && CMAKE_PREFIX_PATH='/usr/local/fftw' cmake -DCMAKE_INSTALL_PREFIX=/usr/local/gromacs -DCMAKE_INSTALL_BINDIR=bin.AVX2_256 -DCMAKE_INSTALL_LIBDIR=lib.AVX2_256 -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DGMX_OPENMP=ON -DGMX_MPI=ON -DGMX_GPU=OFF -DGMX_SIMD=AVX2_256 -DGMX_USE_RDTSCP=OFF -DGMX_DOUBLE=ON -DGMX_FFT_LIBRARY=fftw3 -DGMX_EXTERNAL_BLAS=OFF -DGMX_EXTERNAL_LAPACK=OFF -DBUILD_SHARED_LIBS=OFF -DGMX_PREFER_STATIC_LIBS=ON -DREGRESSIONTEST_DOWNLOAD=ON -DGMX_DEFAULT_SUFFIX=OFF -DGMX_BINARY_SUFFIX=_mpi_d -DGMX_LIBS_SUFFIX=_mpi_d -DMPIEXEC_PREFLAGS='--allow-run-as-root;--oversubscribe' /var/tmp/gromacs-2020.1 && \
    cmake --build /var/tmp/gromacs-2020.1/build.AVX2_256 --target all -- -j$(nproc) && \
    cmake --build /var/tmp/gromacs-2020.1/build.AVX2_256 --target check -- -j$(nproc) && \
    cmake --build /var/tmp/gromacs-2020.1/build.AVX2_256 --target install -- -j$(nproc) && \
    rm -rf /var/tmp/gromacs-2020.1 /var/tmp/gromacs-2020.1.tar.gz

