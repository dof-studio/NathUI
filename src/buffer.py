# buffer.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

class Buffer:
    def __init__(self):
        self.buffer = ''
    
    def __call__(self, *objects, sep=' ', end='\n', file=None, flush=False):
        self.buffer_print(*objects, sep=sep, end=end, file=file, flush=flush)
        
    def _clear(self):
        self.buffer = ''
    
    def _print(self, *objects, sep=' ', end='\n', file=None, flush=False):
        parts = map(str, objects)
        joined = sep.join(parts)
        final_output = joined + end
        self.buffer += final_output
    