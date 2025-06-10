# Visuals-with-Verlet-Integration
A particle simulation framework using Verlet integration and spatial hashing used to visualize input images using particles

This project simulates 2D particle dynamics using a physics engine inspired by real world kinematics and computational geometry, and can support thousands of particles with efficient real time rendering and accurate physics.

Particles behave as physical entities within a 2D simulation box, influenced by gravity and mutual collisions. Instead of Euler integration, we use Verlet integration, which provides higher stability and more natural motion (explained in the other explanation focused on physics). In a nutshell, Verlet integration is used for predicting the position (and indirectly the velocity, acceleration, jerk etc.) of a system where external factors are dynamic (if a variable varies with time or varies with some term f(t) which in turn varies with time). This is mostly used in molecular dynamics simulations and other multiparticle systems as the external factors change based on the position of other bodies.

# Stage wise splitup
1. We start with determining the particle size and the maximum number of particles based on packing density estimation.
2. We load an input image and resize it to match the simulation resolution.
3. We initialize a particle list and a simulation clock
4. For each timestep, we start an initialisation phase where we spawn a new particle at the center with a random radius within range, an initial velocity in a random direction and stores initial state to CSV with the columns - step_added (the simulation step at which the ball was spawned), x, y, radius, old_x, old_y, RGB components of the circle's colour.
5. We executes a simulation step where we simulate the substeps (physics subdivisions per frame), applies gravity as a force to all particles in each of these substep, use spatial hashing to group particles by grid cell
6. We also performs pairwise collision resolution using overlap correction and enforce boundary constraints with edges.
7. Then we integrate motion using Verlet integration, and increment the current step and prints progress.
8. After this, we open the CSV file and sorts particles by spawn step.
9. For each particle, we map its final position to the corresponding pixel in the loaded image, update its RGB color values in the CSV and saves updated CSV with final color-mapped particle data.
10. This is where we begin the visulisation process - we loads simulation window using Pygame
11. For each frame, we read the next particle from the CSV based on current timestep, reconstructs the particle using stored position, velocity, radius, and RGB color. This simulates motion forward in time using the same physics loop. Here is where we renders the scene where we draw each particle as a colored circle
