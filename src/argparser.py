# argparser.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# It is a FREE and OPEN SOURCED software
# See github.com/dof-studio/NathUI

# Backend #####################################################################


import sys

class ArgParser:
    def __init__(self, argv=None):
        # If no arguments are passed, sys.argv[1:] is used by default (ignoring the script name)
        if argv is None:
            argv = sys.argv[1:]
        self.args = {}
        self._parse_args(argv)

    def _parse_args(self, argv):
        i = 0
        while i < len(argv):
            arg = argv[i]
            # If the parameter starts with '--' or '-', it is considered a key
            if arg.startswith("--"):
                key = arg[2:]
            elif arg.startswith("-"):
                key = arg[1:]
            else:
                # If it does not start with '-', skip it directly
                i += 1
                continue

           # If the next parameter exists and does not start with '-', it is considered to be the value corresponding to the key
            value = True
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                value = argv[i + 1]
                i += 1  # skip this value
            self.args[key] = value
            i += 1

    def get_args(self):
        return self.args

if __name__ == '__main__':
    
    # Takes the python input args
    parser = ArgParser()
    print(parser.get_args())

    # Takes additional args in a list
    test_args = ["--name", "Alice", "-age", "30", "--flag"]
    test_parser = ArgParser(test_args)
    print(test_parser.get_args())
