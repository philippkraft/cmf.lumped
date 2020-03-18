#!/usr/bin/env python3

import sys



def get_commands():
    """
    Gets a dictionary of allowed commands
    """

    from . import commands
    return {
        n: f
        for n, f in vars(commands).items()
        if not n.startswith('_')
    }


def main():

    commands = get_commands()
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        f = commands[sys.argv[1]]
        if len(sys.argv) == 2 or sys.argv[2] == 'help':
            sys.stderr.write(f.__doc__)
        else:
            args = sys.argv[2:]
            f(*args)
    elif len(sys.argv) > 1 and sys.argv[1]=='help':
        print('Runs a custom build lumped cmf model')
        for n, f in commands.items():
            print()
            print(f'cmf.lumped {n} ...')
            print(f.__doc__)
    else:
        cmd_list = '|'.join(commands)
        sys.stderr.write(f'Usage: cmf.lumped [{cmd_list}] path/to/model.py')


if __name__ == '__main__':
    main()

