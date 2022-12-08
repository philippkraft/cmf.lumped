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


def main(*args, **kwargs):

    if not (args or kwargs):
        # if no args or kwargs are given, parse them from sys.argv
        # allowed usage: cmf.lumped <command> model.py value1 param2=value2 --param3=value3
        args = []
        kwargs = {}
        for arg in sys.argv[1:]:
            if '=' in arg:
                k, v = arg.strip().lstrip('-').split('=', 1)
                kwargs[k.lower()] = v
            else:
                args.append(arg)

    commands = get_commands()

    # If still no args or kwargs or first arg is no command
    if not (args or kwargs) or args[0] not in commands:
        cmd_list = '|'.join(commands)
        sys.stderr.write(f'Usage: cmf.lumped [{cmd_list}] path/to/model.py')
        exit(1)
    f = commands[args.pop(0)]

    if 'help' in args or 'help' in kwargs:
        sys.stderr.write(f.__doc__)
    else:
        f(*args, **kwargs)


if __name__ == '__main__':
    main()

