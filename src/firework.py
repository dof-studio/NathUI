# firework.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Memetls #####################################################################

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import time

# Number of particles for each firework
n_particles = 100
# Gravity acceleration
gravity = -9.81
# Time step
dt = 0.05
# Number of time steps
n_steps = 200
# Initial velocities and positions arrays
velocities = np.zeros((n_particles, 2))
positions = np.zeros((n_particles, 2))
colors = ["red", "green", "blue", "yellow", "cyan"]

def init():
    # Initialize the plot
    ax.set_xlim(-10, 10)
    ax.set_ylim(0, 30)
    return scat,

def update(frame):
    global velocities, positions
    # Update velocities and positions for all particles
    velocities[:, 1] += gravity * dt
    positions += velocities * dt
    # Set the new data to the scatter plot
    scat.set_offsets(positions)
    return scat,

def launch_firework():
    global velocities, positions
    # Random initial velocities (angle and magnitude)
    angles = np.random.uniform(0, 2*np.pi, n_particles)
    magnitudes = np.random.uniform(15, 30, n_particles)
    velocities = np.column_stack((magnitudes * np.cos(angles), magnitudes * np.sin(angles)))
    # Reset positions to the origin
    positions.fill(0)
    # Change the color of the firework
    scat.set_color(np.random.choice(colors))

# Create a figure and axis object
fig, ax = plt.subplots()
scat = ax.scatter([], [])
ani = FuncAnimation(fig, update, frames=range(n_steps), init_func=init, blit=True)

# Launch new fireworks at regular intervals
for _ in range(10):  # Change the number of fireworks here
    launch_firework()
    time.sleep(0.5)

# Show the animation
plt.show()
