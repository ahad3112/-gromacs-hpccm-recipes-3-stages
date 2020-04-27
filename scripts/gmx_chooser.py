#!/usr/bin/env python3
import sys
import os
import config


RDTSCP = 'rdtscp'


# Checking whether a file is executable or not
def is_executable(file):
    acl = os.popen('ls -l ' + file).read()[0:10]
    if acl.count('x') == 3:
        return True

    return False


# Choose the best possible GROMACS based on cpu's SIMD instruction
def get_binary_directory(flags, gmx):
    for (arch, bin_suffix) in zip(config.ARCHITECTURES, config.GMX_BINARY_DIRECTORY_SUFFIX):
        bin_dir = config.GMX_BINARY_DIRECTORY.format(bin_suffix)
        if arch in flags and os.path.exists(bin_dir):
            fileshere = os.listdir(bin_dir)
            try:
                idx = fileshere.index(gmx)
            except ValueError:
                continue
            else:
                file = fileshere[idx]
                if is_executable(os.path.join(bin_dir, file)):
                    return bin_dir
                else:
                    continue
    return None


def run(binary_directory, gmx, args):
    binary_path = os.path.join(binary_directory, gmx)
    os.system(binary_path + ' ' + ' '.join(args))


if __name__ == '__main__':
    sys.argv[1] = os.path.split(sys.argv[1])[1]

    pipe = os.popen('cat /proc/cpuinfo | grep ^flags | head -1')
    flags = pipe.read()

    rdtscp_enabled = True if RDTSCP in flags else False

    gmx = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    if rdtscp_enabled:
        gmx += config.GMX_ENGINE_SUFFIX_OPTIONS[RDTSCP]

    gmx_binary_directory = get_binary_directory(flags, gmx)

    if not gmx_binary_directory:
        print('No appropriate GROMACS installaiton available. Exiting...')
        os._exit(-1)

    # running the binary
    run(binary_directory=gmx_binary_directory, gmx=gmx, args=args)
