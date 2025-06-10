import pygame
import sys
import math
import random
from PIL import Image

input_img = "Image.jpg"
width, height = 710, 710
accelerationDueToGravity = pygame.math.Vector2(0, 981)  # Gravity acceleration in px/s²
canvasColour = (0, 0, 0)
coefficientOfRestitution = 0.9                          # Wall bounce energy retention factor
collisionElasticity = 0.95                              # Ball-to-ball collision energy retention
Spawn_Interval = 1
FPS_Inverse = 1 / 60.0                                  #1/FPS
SimulationMode = "SPAWN"

# Estimate optimal number of particles based on packing density and object size
def estimate_particle_count(width, height, r_min, r_max, packing_efficiency = 0.9):
    totalArea = width * height
    r_avg = ((r_min + r_max) / 2) + 1
    Area_with_avgRadius = math.pi * (r_avg ** 2)
    est_count = int((packing_efficiency * totalArea) / Area_with_avgRadius)
    while est_count % 100 != 0:     # Rounding off to nearest hundred
        est_count += 1
    return est_count

PhysicsSubsteps = 16       # Physics accuracy tuning (Increase for more precise results)

resolution_mode = input("Enter resolution mode (SD / HD / UHD): ")
if resolution_mode == 'UHD':
    minRadius, maxRadius = 1, 8
    maxParticles = estimate_particle_count(width, height, minRadius, maxRadius, 0.9999)
elif resolution_mode == 'HD':
    minRadius, maxRadius = 2, 12
    maxParticles = estimate_particle_count(width, height, minRadius, maxRadius)
elif resolution_mode == 'SD':
    minRadius, maxRadius = 4, 18
    maxParticles = estimate_particle_count(width, height, minRadius, maxRadius)

spawnSteps = maxParticles

# Grid constants for spatial partitioning
GridCellSize = maxRadius * 2
gridCols = math.ceil(width / GridCellSize)
gridRows = math.ceil(height / GridCellSize)

# Particle class - Each particle is a single circle using Verlet integration
class Particle:
    def __init__(self, position, radius, spawn_step, color=None):
        self.pos = pygame.math.Vector2(position)
        self.prev_pos = pygame.math.Vector2(position)
        self.accel = pygame.math.Vector2(0, 0)
        self.radius = radius
        self.mass = math.pi * radius ** 2
        self.spawn_step = spawn_step
        self.color = color or (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))

    # Applies Verlet integration to compute new position
    def integrate_motion(self, dt):
        velocity = self.pos - self.prev_pos
        self.prev_pos = pygame.math.Vector2(self.pos)
        self.pos += velocity + self.accel * dt * dt
        self.accel = pygame.math.Vector2(0, 0)  # Reset acceleration

    # Adds a force (gravity) to the particle.
    def apply_force(self, force):
        if self.mass > 0:
            self.accel += force / self.mass

    # Handles collisions with the simulation box walls
    def enforce_boundary_conditions(self):
        velocity = self.pos - self.prev_pos
        if self.pos.x - self.radius < 0:
            self.pos.x = self.radius
        elif self.pos.x + self.radius > width:
            self.pos.x = width - self.radius
        if self.pos.y - self.radius < 0:
            self.pos.y = self.radius
        elif self.pos.y + self.radius > height:
            self.pos.y = height - self.radius

    # Draws the particle on the screen
    def render(self, surface):
        draw_coords = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(surface, self.color, draw_coords, int(self.radius))

# Physics Simulation engine
class ParticleSimulator:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pixel/Particle Physics: Visuals with Verlet Integration")
        self.particles = []
        self.font = pygame.font.Font(None, 30)
        self.current_step = 0
        self.clock = pygame.time.Clock()
        self.spatial_grid = {}
        random.seed(42)

        try:
            self.input_image = Image.open(input_img).convert('RGB').resize((width, height))
        except:
            print("Input image not found; skipping color mapping.")
            self.input_image = None

    # Add a particle, and replaces oldest if limit exceeded
    def add_particle(self, particle):
        if len(self.particles) < maxParticles:
            self.particles.append(particle)
        else:
            self.particles.pop(0)
            self.particles.append(particle)

    def apply_gravity(self):
        for p in self.particles:
            p.apply_force(accelerationDueToGravity)

    def integrate(self, dt):
        for p in self.particles:
            p.integrate_motion(dt)

    def enforce_boundaries(self):
        for p in self.particles:
            p.enforce_boundary_conditions()

    def compute_cell_index(self, position):
        return int(position.x / GridCellSize), int(position.y / GridCellSize)   # To map position to spatial grid cell coordinates

    # Rebuild the spatial hash grid from current particle positions
    def rebuild_spatial_grid(self):
        self.spatial_grid.clear()
        for p in self.particles:
            cell = self.compute_cell_index(p.pos)
            if cell not in self.spatial_grid:
                self.spatial_grid[cell] = []
            self.spatial_grid[cell].append(p)

    # Fetch nearby particles from adjacent cells
    def get_neighbors(self, particle):
        cx, cy = self.compute_cell_index(particle.pos)
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                key = (cx + dx, cy + dy)
                if key in self.spatial_grid:
                    neighbors.extend(self.spatial_grid[key])
        return neighbors

    # To handle pairwise collision resolution using spatial hashing
    def resolve_collisions(self):
        self.rebuild_spatial_grid()
        for p1 in self.particles:
            for p2 in self.get_neighbors(p1):
                if p1 is p2:
                    continue
                offset = p1.pos - p2.pos
                dist_sq = offset.length_squared()
                min_dist = p1.radius + p2.radius
                if 0 < dist_sq < min_dist ** 2:
                    distance = math.sqrt(dist_sq)
                    overlap = (min_dist - distance) * 0.5
                    direction = offset / distance
                    total_mass = p1.mass + p2.mass
                    m1_ratio = p2.mass / total_mass if total_mass else 0.5
                    m2_ratio = p1.mass / total_mass if total_mass else 0.5
                    correction = direction * overlap
                    p1.pos += correction * m1_ratio * collisionElasticity
                    p2.pos -= correction * m2_ratio * collisionElasticity

    # To perform one physics frame with substeps
    def simulate_step(self, dt):
        sub_dt = dt / PhysicsSubsteps
        for _ in range(PhysicsSubsteps):
            self.apply_gravity()
            self.resolve_collisions()
            self.enforce_boundaries()
            self.integrate(sub_dt)

    def render_frame(self):
        self.screen.fill(canvasColour)
        for p in self.particles:
            p.render(self.screen)
        stats = self.font.render(f"Step {self.current_step}/{spawnSteps} | Count {len(self.particles)}/{maxParticles}", True, (200, 200, 200))
        self.screen.blit(stats, (10, 10))
        pygame.display.flip()

    # Maps final particle positions to pixel colors from image and saves it as CSV
    def save_particle_map_to_image(self):
        if SimulationMode != "SPAWN" or not self.input_image:
            return
        with open('Spawns.csv', 'r') as f:
            lines = f.readlines()

        sorted_particles = sorted(self.particles, key=lambda p: p.spawn_step)
        updated_lines = []

        for i, line in enumerate(lines):
            if i >= len(sorted_particles):
                break
            p = sorted_particles[i]
            x, y = int(p.pos.x), int(p.pos.y)
            r, g, b = self.input_image.getpixel((min(x, width - 1), min(y, height - 1)))
            parts = list(map(float, line.strip().split(',')))
            new_line = f"{int(parts[0])},{parts[1]},{parts[2]},{parts[3]},{parts[4]},{parts[5]},{r},{g},{b}\n"
            updated_lines.append(new_line)

        with open('Spawns.csv', 'w') as f:
            f.writelines(updated_lines)

    # To precompute the motion of all particles and store in CSV
    def run_precalculation(self):
        self.current_step = 0
        particles_spawned = 0
        csv_data = []

        while self.current_step < spawnSteps:
            if self.current_step % Spawn_Interval == 0 and particles_spawned < maxParticles:
                pos = (width / 2, height / 2)
                radius = random.uniform(minRadius, maxRadius)
                particle = Particle(pos, radius, self.current_step)

                angle = random.uniform(0, 2 * math.pi)
                velocity = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * 40
                particle.prev_pos = particle.pos - velocity * FPS_Inverse

                csv_data.append(f"{self.current_step},{particle.pos.x},{particle.pos.y},{particle.radius},{particle.prev_pos.x},{particle.prev_pos.y},{particle.color[0]},{particle.color[1]},{particle.color[2]}\n")

                self.add_particle(particle)
                particles_spawned += 1

            self.simulate_step(FPS_Inverse)
            self.current_step += 1
            if self.current_step % 100 == 0:
                print(f"Progress: {self.current_step}/{spawnSteps}")

        with open('Spawns.csv', 'w') as f:
            f.writelines(csv_data)
        self.save_particle_map_to_image()

    # To visualize precomputed particle data from CSV
    def playback_simulation(self):
        self.particles = []
        self.current_step = 0
        spawned_count = 0
        running = True

        while running:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            with open('Spawns.csv', 'r') as f:
                for _ in range(spawned_count):
                    next(f)
                line = next(f, None)
                if line:
                    parts = list(map(float, line.strip().split(',')))
                    if int(parts[0]) == self.current_step:
                        new_particle = Particle((parts[1], parts[2]), parts[3], int(parts[0]), (int(parts[6]), int(parts[7]), int(parts[8])))
                        new_particle.prev_pos = pygame.math.Vector2(parts[4], parts[5])
                        self.add_particle(new_particle)
                        spawned_count += 1

            self.simulate_step(FPS_Inverse)
            self.render_frame()
            self.current_step += 1

        pygame.quit()
        sys.exit()

    def run(self):
        self.run_precalculation()
        self.playback_simulation()

if __name__ == "__main__":
    simulator = ParticleSimulator()
    simulator.run()
