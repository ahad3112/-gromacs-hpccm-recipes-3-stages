FROM ubuntu:18.04 AS dev_stage

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
FROM ubuntu:18.04 AS app_stage

# GNU compiler runtime
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends software-properties-common && \
    apt-add-repository ppa:ubuntu-toolchain-r/test -y && \
    apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

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

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        wget && \
    rm -rf /var/lib/apt/lists/*

# ftp://ftp.gromacs.org/pub/gromacs/gromacs-2020.1.tar.gz
RUN mkdir -p /var/tmp && wget -q -nc --no-check-certificate -P /var/tmp ftp://ftp.gromacs.org/pub/gromacs/gromacs-2020.1.tar.gz && \
    mkdir -p /var/tmp && tar -x -f /var/tmp/gromacs-2020.1.tar.gz -C /var/tmp -z && \
    cd /var/tmp/gromacs-2020.1 && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y perl && \
    mkdir -p /var/tmp/gromacs-2020.1/build.AVX2_256 && cd /var/tmp/gromacs-2020.1/build.AVX2_256 && cmake -DCMAKE_INSTALL_PREFIX=/usr/local/gromacs -DCMAKE_INSTALL_BINDIR=bin.AVX2_256 -DCMAKE_INSTALL_LIBDIR=lib.AVX2_256 -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DGMX_OPENMP=ON -DGMX_MPI=OFF -DGMX_GPU=OFF -DGMX_SIMD=AVX2_256 -DGMX_USE_RDTSCP=OFF -DGMX_DOUBLE=OFF -DGMX_BUILD_OWN_FFTW=ON -DGMX_EXTERNAL_BLAS=OFF -DGMX_EXTERNAL_LAPACK=OFF -DBUILD_SHARED_LIBS=OFF -DGMX_PREFER_STATIC_LIBS=ON -DREGRESSIONTEST_DOWNLOAD=ON -DGMX_DEFAULT_SUFFIX=OFF -DGMX_BINARY_SUFFIX= -DGMX_LIBS_SUFFIX= /var/tmp/gromacs-2020.1 && \
    cmake --build /var/tmp/gromacs-2020.1/build.AVX2_256 --target all -- -j$(nproc) && \
    cmake --build /var/tmp/gromacs-2020.1/build.AVX2_256 --target check -- -j$(nproc) && \
    cmake --build /var/tmp/gromacs-2020.1/build.AVX2_256 --target install -- -j$(nproc) && \
    rm -rf /var/tmp/gromacs-2020.1 /var/tmp/gromacs-2020.1.tar.gz
FROM ubuntu:18.04 AS deploy_stage

# GNU compiler runtime
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends software-properties-common && \
    apt-add-repository ppa:ubuntu-toolchain-r/test -y && \
    apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# ftp://ftp.gromacs.org/pub/gromacs/gromacs-2020.1.tar.gz
COPY --from=app_stage /usr/local/gromacs /usr/local/gromacs

# Python
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        vim && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/local/gromacs/scripts

COPY /scripts/wrapper.py /usr/local/gromacs/scripts/gmx

COPY /scripts/gmx_chooser.py /usr/local/gromacs/scripts/gmx_chooser.py

RUN chmod +x /usr/local/gromacs/scripts/*

COPY config.py /usr/local/gromacs/scripts/config.py

ENV PATH=$PATH:/usr/local/gromacs/scripts
