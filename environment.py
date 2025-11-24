import numpy as np
import random
from agent import Agent
from config import (
    GRID_WIDTH, GRID_HEIGHT, MAX_NUTRIENT, NUTRIENT_SPAWN_RATE,
    NUTRIENT_DECAY, DIFFUSION_FACTOR, INITIAL_POPULATION, DEAD_BODY_NUTRIENT,
    NUTRIENT_DECAY, DIFFUSION_FACTOR, INITIAL_POPULATION, DEAD_BODY_NUTRIENT,
    CYCLE_LENGTH, DAY_RATIO, SUN_MAX_INTENSITY, SUN_PENETRATION_DEPTH, ADHESION_RANGE
)

class Environment:
    """
    Manages the grid state, nutrients, and agent population.
    """
    def __init__(self):
        # Nutrient Grid (Float 32 for performance)
        self.nutrients = np.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=np.float32)
        
        # Sunlight Grid (Pre-calculated gradient, modulated by time)
        self.sunlight_gradient = np.linspace(SUN_MAX_INTENSITY, SUN_MAX_INTENSITY * SUN_PENETRATION_DEPTH, GRID_HEIGHT)
        self.sunlight_gradient = np.tile(self.sunlight_gradient, (GRID_WIDTH, 1)).T # Shape: (Height, Width) -> Transpose to (Width, Height)? 
        # Wait, numpy is (Row, Col) usually, but here we access [x, y]. 
        # If x is width, y is height.
        # linspace gives a 1D array of size GRID_HEIGHT.
        # We want [x, y] to have the same value for all x at a given y.
        # So we want shape (GRID_WIDTH, GRID_HEIGHT).
        self.sunlight_gradient = np.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=np.float32)
        for y in range(GRID_HEIGHT):
            intensity = SUN_MAX_INTENSITY * (1.0 - (y / GRID_HEIGHT) * (1.0 - SUN_PENETRATION_DEPTH))
            self.sunlight_gradient[:, y] = intensity
        
        # Agent Occupancy Grid (Stores Agent IDs or None)
        # Using a set of coordinates for fast lookup of empty spaces
        self.agents = []
        
        # Initialize Random Nutrients
        self.randomize_nutrients()
        
        # Initialize Population
        for _ in range(INITIAL_POPULATION):
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            self.agents.append(Agent(x, y))
            
        # Time Tracking
        self.global_time = 0
        self.is_night = False

    def randomize_nutrients(self):
        """Seeds the map with initial nutrient clusters."""
        for _ in range(int(GRID_WIDTH * GRID_HEIGHT * 0.1)):
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            self.nutrients[x, y] = random.uniform(0, MAX_NUTRIENT)

    def update_nutrients(self):
        """
        Handles diffusion, decay, and regeneration using NumPy vectorization.
        This is much faster than Python loops.
        """
        # 1. Spontaneous Regeneration
        # Create a mask of random spawns
        spawn_mask = np.random.random((GRID_WIDTH, GRID_HEIGHT)) < NUTRIENT_SPAWN_RATE
        self.nutrients[spawn_mask] += 2.0
        
        # 2. Diffusion (Simple Box Blur)
        # Use np.pad to handle wrap-around (toroidal world) efficiently
        # This creates one copy instead of 4 from np.roll
        padded = np.pad(self.nutrients, 1, mode='wrap')
        
        # Slices from the padded array (views)
        # center is [1:-1, 1:-1] which matches self.nutrients size
        # left   is [0:-2, 1:-1]
        # right  is [2:,   1:-1]
        # up     is [1:-1, 0:-2]
        # down   is [1:-1, 2:]
        
        center = padded[1:-1, 1:-1]
        left   = padded[0:-2, 1:-1]
        right  = padded[2:,   1:-1]
        up     = padded[1:-1, 0:-2]
        down   = padded[1:-1, 2:]
        
        # Apply diffusion formula
        # self.nutrients is the target, we can update it in place or assign
        # new = old * (1-4k) + sum(neighbors) * k
        neighbor_sum = left + right + up + down
        self.nutrients *= (1 - 4 * DIFFUSION_FACTOR)
        self.nutrients += neighbor_sum * DIFFUSION_FACTOR
        
        # 3. Decay (Entropy)
        self.nutrients *= NUTRIENT_DECAY
        
        # 4. Clamping
        np.clip(self.nutrients, 0, MAX_NUTRIENT, out=self.nutrients)

    def update_agents(self):
        """
        Updates logic for all agents: Move, Eat, Reproduce, Die.
        Updates logic for all agents: Move, Eat, Reproduce, Die.
        Returns a list of events for visual effects: ['type', data...]
        """
        # Update Time
        self.global_time += 1
        cycle_pos = self.global_time % CYCLE_LENGTH
        self.is_night = cycle_pos > (CYCLE_LENGTH * DAY_RATIO)
        
        # Spatial hashing for collision detection (Agent x,y -> Agent Object)
        # Rebuilt every frame. For 100x100 grid, this is efficient enough.
        occupied = {(a.x, a.y): a for a in self.agents}
        
        new_borns = []
        dead_agents = []
        events = []

        # Iterate over a copy of the list to allow modification
        for agent in self.agents:
            # --- 0. COLONY & PHOTOSYNTHESIS ---
            # Photosynthesis
            sun_intensity = 0.0
            if not self.is_night:
                sun_intensity = self.sunlight_gradient[agent.x, agent.y]
            
            agent.photosynthesize(sun_intensity)

            # Colony Logic (Adhesion & Sharing)
            is_attached = False
            # Check neighbors for adhesion
            # Optimization: Only check if agent is sticky
            if agent.genes['adhesion'] >= 0.5:
                # Get neighbors from hash map
                neighbors = []
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if dx == 0 and dy == 0: continue
                        nx, ny = agent.x + dx, agent.y + dy
                        if (nx, ny) in occupied:
                            neighbors.append(occupied[(nx, ny)])
                
                is_attached = agent.handle_colony(neighbors)

            # --- 1. MOVEMENT ---
            # Ask agent where it wants to go
            target_x, target_y = agent.sense_and_move(self.nutrients, GRID_WIDTH, GRID_HEIGHT, self.is_night, is_attached)
            target_x, target_y = int(target_x), int(target_y)
            
            # Check collision
            if (target_x, target_y) not in occupied:
                # Empty spot, move there
                if occupied.get((agent.x, agent.y)) == agent:
                    del occupied[(agent.x, agent.y)]
                
                agent.x = target_x
                agent.y = target_y
                occupied[(agent.x, agent.y)] = agent
            else:
                # Occupied spot, check for predation
                other = occupied[(target_x, target_y)]
                if (agent.is_predator and not other.is_predator and 
                    other.is_alive and agent.genes['size'] > other.genes['size']):
                    # EAT THE PREY
                    # Hyperconsumer efficiency
                    from config import PREDATOR_EAT_EFFICIENCY
                    eat_gain = other.energy * PREDATOR_EAT_EFFICIENCY + DEAD_BODY_NUTRIENT
                    agent.energy += eat_gain
                    other.is_alive = False # Mark as dead immediately
                    
                    events.append(['eat', agent.x, agent.y])
                    
                    # Move into the spot
                    if occupied.get((agent.x, agent.y)) == agent:
                        del occupied[(agent.x, agent.y)]
                    
                    agent.x = target_x
                    agent.y = target_y
                    occupied[(agent.x, agent.y)] = agent
                    
                    # Remove other from occupied map so others can't eat it again?
                    # Actually, we just overwrote it in the map, so it's gone from collision checks.
                    pass

            # --- 2. EATING (Nutrients) ---
            # Predators don't eat standard nutrients (or very inefficiently)
            if not agent.is_predator:
                available_food = self.nutrients[agent.x, agent.y]
                eat_amount = min(available_food, 2.0) # Max eat rate per tick
                
                agent.energy += eat_amount
                self.nutrients[agent.x, agent.y] -= eat_amount
            
            # --- 3. REPRODUCTION ---
            if agent.energy > agent.genes['repro_threshold']:
                # Find empty neighbor
                neighbors = [
                    (agent.x+1, agent.y), (agent.x-1, agent.y),
                    (agent.x, agent.y+1), (agent.x, agent.y-1)
                ]
                random.shuffle(neighbors)
                
                for nx, ny in neighbors:
                    # Bounds check
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if (nx, ny) not in occupied:
                            # Create Offspring
                            split_energy = agent.energy / 2
                            agent.energy = split_energy
                            
                            child_genes = agent.mutate_genes()
                            child = Agent(nx, ny, genes=child_genes, 
                                          energy=split_energy, 
                                          generation=agent.generation + 1)
                            
                            new_borns.append(child)
                            occupied[(nx, ny)] = child
                            
                            # Track success
                            agent.offspring_count += 1
                            
                            events.append(['spawn', agent.x, agent.y, nx, ny])
                            break # Only one child per tick

            # --- 4. EVOLUTION & DEATH ---
            agent.check_evolution()
            agent.age += 1
            # Die from starvation or extreme age (optional age cap, here just energy)
            if agent.energy <= 0:
                agent.is_alive = False
                dead_agents.append(agent)

        # Remove dead, add living
        self.agents = [a for a in self.agents if a.is_alive] + new_borns
        
        # Recycle nutrients from bodies
        for corpse in dead_agents:
            self.nutrients[corpse.x, corpse.y] += DEAD_BODY_NUTRIENT
            
        return events
