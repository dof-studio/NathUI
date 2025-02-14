# socks.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################


import socket

# Next port available
def next_port(starting_port: int) -> int:
    """
    Returns the smallest available port number starting from starting_port.
    If no available port is found in the range [starting_port, 65535], a RuntimeError is raised.
    """
    # Iterate over port numbers from starting_port to 65535
    for port in range(starting_port, 65536):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Set SO_REUSEADDR to allow immediate reuse of the port
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # Attempt to bind to the port
                s.bind(('', port))
                # Binding succeeded, so the port is available
                return port
            except OSError:
                # Binding failed, meaning the port is likely in use, continue to the next port
                continue
    # No available port was found in the specified range
    raise RuntimeError(f"No available port found in the specified range starting from {starting_port}.")
    
    