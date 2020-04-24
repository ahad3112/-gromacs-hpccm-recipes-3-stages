# GROMACS 2020.1
HPCCM recipes for GROMACS build and installation

####Usage:

    $ ./gromacs_docker_builds.py -h/--help

## Building Image
##### Sample Commands
    ./gromacs_docker_builds.py --gromacs 2020.1 --ubuntu 18.04 --gcc 9 --cmake 3.17.1 --engines simd=sse2:rdtscp=off simd=sse2:rdtscp=on  --openmpi 3.0.0 --regtest --fftw 3.3.7 --cuda 6 --double > Dockerfile
    ./gromacs_docker_builds.py --format docker --ubuntu 18.04 --engines simd=sse2:rdtscp=off:mdrun=off simd=avx2:rdtscp=on:mdrun=on simd=avx2:rdtscp=off:mdrun=on  --gromacs 2020.1> Dockerfile


## Running Image
The Available GROMACS wrapper binaries will be the followings based on `mpi` enabled or disabled and `mdrun` value:
option on `docker_build.py`:

* `gmx`
* `gmx_mpi`
* `mdrun`
* `mdrun_mpi`

Wrapper binaries `mdrun` and `mdrun_mpi` represent `mdrun_only` installation of GROMACS.
To use other GROMACS tools such as `pdb2gmx`, `grompp`, `editconf` etc. full installation
of GROMACS are required. Full installation of GROMACS are wrapped within `gmx` and `gmx_mpi`.


#### Without Singularity

Bind the directory that you want Docker to get access to. Below is an example of running `mdrun` module using `gmx` wrapper:

    mkdir $HOME/data
    docker run -v $HOME/data:/data -w /data -it <image_name> gmx mdrun -s <.tpr file> -deffnm <ouput_file_name>


## Dependencies

* `python3`
