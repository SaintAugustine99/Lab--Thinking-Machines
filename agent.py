import random
import numpy as np
from config import (
    GENE_BOUNDS, MUTATION_RATE, MUTATION_STRENGTH, 
    PREDATOR_THRESHOLD_ENERGY, PREDATOR_THRESHOLD_SIZE, 
    PREDATOR_THRESHOLD_ENERGY, PREDATOR_THRESHOLD_SIZE, 
    PREDATOR_THRESHOLD_OFFSPRING, PREDATOR_METABOLISM_PENALTY,
    NIGHT_METABOLISM_FACTOR, NIGHT_MOVE_CHANCE,
    PREDATOR_NIGHT_ACTIVITY, PREDATOR_DAY_ACTIVITY,
    PHOTOSYNTHESIS_RATE, ADHESION_RANGE, COLONY_SHARING_RATE
)

class Agent:
    """
    An autonomous entity with a genome and energy level.
    """
    def __init__(self, x, y, genes=None, energy=20.0, generation=1):
        self.id = random.randint(0, 1000000)
        self.x = x
        self.y = y
        self.energy = energy
        self.age = 0
        self.generation = generation
        self.is_alive = True
        self.is_predator = False
        self.offspring_count = 0
        
        # Color cached for performance, updated only on init or mutation
        self.color = (255, 255, 255) 

        # Initialize Genes
        if genes is None:
            # Random initialization for the first generation
            self.genes = {
                'metabolism': random.uniform(*GENE_BOUNDS['metabolism']),
                'repro_threshold': random.uniform(*GENE_BOUNDS['repro_threshold']),
                'sense_range': random.randint(*GENE_BOUNDS['sense_range']),
                'size': random.uniform(*GENE_BOUNDS['size']),
                'photosynthesis_efficiency': random.uniform(*GENE_BOUNDS['photosynthesis_efficiency']),
                'adhesion': random.uniform(*GENE_BOUNDS['adhesion'])
            }
        else:
            self.genes = genes
        
        self.update_color()

    def update_color(self):
        """
        Maps genome to RGB color for visual analysis of species differentiation.
        Red   = High Reproduction Threshold (needs lots of food to breed)
        Green = High Sensing Range (can find food easily)
        Blue  = Low Metabolism (efficient)
        """
        if self.is_predator:
            self.color = (128, 0, 128) # Purple for Predators
            return

        # Dominant Gene Coloring
        # Normalize genes to comparable 0-1 scale
        norm_repro = self.genes['repro_threshold'] / GENE_BOUNDS['repro_threshold'][1]
        norm_sense = self.genes['sense_range'] / GENE_BOUNDS['sense_range'][1]
        # Metabolism is inverted (lower is better/higher fitness)
        norm_metab = 1.0 - (self.genes['metabolism'] / GENE_BOUNDS['metabolism'][1])
        
        # Find dominant trait
        traits = [
            (norm_repro, (255, 50, 50)),   # Red: High Reproduction (Breeder)
            (norm_sense, (50, 255, 50)),   # Green: High Sense (Scout)
            (norm_metab, (50, 50, 255)),   # Blue: Efficient (Survivor)
            (self.genes['photosynthesis_efficiency'], (255, 255, 0)) # Yellow: Producer
        ]
        
        # Sort by normalized value
        traits.sort(key=lambda x: x[0], reverse=True)
        
        # Base color is the dominant trait
        base_color = traits[0][1]
        
        # Size influence on brightness (Darker = Bigger)
        size_factor = 1.0 - ((self.genes['size'] - GENE_BOUNDS['size'][0]) / (GENE_BOUNDS['size'][1] - GENE_BOUNDS['size'][0])) * 0.4
        
        self.color = (
            int(base_color[0] * size_factor), 
            int(base_color[1] * size_factor), 
            int(base_color[2] * size_factor)
        )

    def check_evolution(self):
        """Checks if the agent meets criteria to become a predator."""
        if not self.is_predator:
            if (self.energy > PREDATOR_THRESHOLD_ENERGY and 
                self.genes['size'] > PREDATOR_THRESHOLD_SIZE and 
                self.offspring_count >= PREDATOR_THRESHOLD_OFFSPRING):
                self.is_predator = True
                self.update_color()

    def mutate_genes(self):
        """Creates a mutated copy of the current genes."""
        new_genes = self.genes.copy()
        for gene, val in new_genes.items():
            if random.random() < MUTATION_RATE:
                # Apply mutation
                change = val * random.uniform(-MUTATION_STRENGTH, MUTATION_STRENGTH)
                new_val = val + change
                
                # Clamp to bounds
                if gene == 'sense_range':
                    new_val = int(round(new_val)) # Integer constraint
                    mn, mx = GENE_BOUNDS[gene]
                    new_val = max(mn, min(mx, new_val))
                else:
                    mn, mx = GENE_BOUNDS[gene]
                    new_val = max(mn, min(mx, new_val))
                
                new_genes[gene] = new_val
        return new_genes

    def photosynthesize(self, sunlight_intensity):
        """Gains energy from sunlight based on efficiency."""
        gain = sunlight_intensity * self.genes['photosynthesis_efficiency'] * PHOTOSYNTHESIS_RATE
        self.energy += gain
        return gain

    def handle_colony(self, neighbors):
        """
        Interacts with nearby agents of the same species (colony).
        Returns True if attached (should limit movement).
        """
        if self.genes['adhesion'] < 0.5:
            return False

        attached = False
        for other in neighbors:
            # Simple species check: similar genes? Or just family?
            # For now, let's assume if they are close and both sticky, they bond.
            if other.genes['adhesion'] >= 0.5:
                # Share Energy
                diff = self.energy - other.energy
                if abs(diff) > 1.0:
                    transfer = diff * COLONY_SHARING_RATE * 0.5 # Each gives/takes half the diff
                    self.energy -= transfer
                    other.energy += transfer
                attached = True
        
        return attached

    def sense_and_move(self, nutrient_grid, grid_w, grid_h, is_night, is_attached=False):
        """
        Decides where to move based on nutrient gradients and time of day.
        """
        # 1. Base metabolic cost just for existing
        metab_cost = self.genes['metabolism']
        
        # --- Day/Night Logic ---
        if self.is_predator:
            metab_cost *= PREDATOR_METABOLISM_PENALTY
            # Predators are dormant during the day (unless configured otherwise)
            if not is_night and not PREDATOR_DAY_ACTIVITY:
                # Dormant: Low energy cost, no movement
                self.energy -= metab_cost * 0.1 
                return self.x, self.y
        else:
            # Prey Logic
            if is_night:
                metab_cost *= NIGHT_METABOLISM_FACTOR
                # Sluggish: Chance to skip movement
                if random.random() > NIGHT_MOVE_CHANCE:
                    self.energy -= metab_cost
                    return self.x, self.y

        self.energy -= metab_cost

        # If attached to a colony, movement is restricted (anchored)
        if is_attached:
            return self.x, self.y

        best_x, best_y = self.x, self.y
        best_val = -1.0
        
        # Look around based on sensing range
        r = self.genes['sense_range']
        
        # Optimization: Don't scan everything if energy is critically low? 
        # (Behavioral adaptation logic could go here)

        found_better = False
        
        # Scan local area using NumPy slicing
        # Define bounds
        x_min = max(0, self.x - r)
        x_max = min(grid_w, self.x + r + 1)
        y_min = max(0, self.y - r)
        y_max = min(grid_h, self.y + r + 1)
        
        # Extract patch
        patch = nutrient_grid[x_min:x_max, y_min:y_max]
        
        if patch.size > 0:
            # Find max value in patch
            # argmax returns flat index, unravel_index converts to 2D
            max_idx = np.argmax(patch)
            local_x, local_y = np.unravel_index(max_idx, patch.shape)
            
            # Convert local patch coords to global grid coords
            best_x = x_min + local_x
            best_y = y_min + local_y
            
            best_val = patch[local_x, local_y]
            
            if best_val > -1.0: # Always true if patch not empty
                found_better = True

        # Movement Logic
        if found_better and (best_x != self.x or best_y != self.y):
            # Move towards the best spot (one step at a time)
            # Calculate direction
            dir_x = np.sign(best_x - self.x)
            dir_y = np.sign(best_y - self.y)
            
            # Additional movement cost (kinetic energy)
            move_cost = self.genes['metabolism'] * 0.5
            self.energy -= move_cost
            
            return self.x + dir_x, self.y + dir_y
        else:
            # Random walk if no food sensed or satiated
            if random.random() < 0.2:
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                nx, ny = self.x + dx, self.y + dy
                if 0 <= nx < grid_w and 0 <= ny < grid_h:
                    self.energy -= self.genes['metabolism'] * 0.2
                    return nx, ny
            
            return self.x, self.y
