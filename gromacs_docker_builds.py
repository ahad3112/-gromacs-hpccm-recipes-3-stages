#!/usr/bin/env python

'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>

Usage:
    $ python3 gromacs_docker_builds.py -h/--help
'''

import argparse
from utilities.cli import CLI
import container.recipes as recipes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HPCCM recipes for GROMACS container')
    stages = CLI(parser=parser).get_stages()

    previous_stage = None
    for (stage, args) in stages.items():
        # print(stage, args)
        try:
            previous_stage = getattr(recipes, stage)(args=args, previous_stage=previous_stage)
        except AttributeError as error:
            # print(error)
            pass

    # GromacsRecipes(cli=cli)

    # print(parser.parse_args().__dict__)
