# =============================================================================
# CONFIGURATION & PARAMETERS
# =============================================================================

# -- World Settings --
GRID_WIDTH = 100
GRID_HEIGHT = 100
CELL_SIZE = 8       # Pixel size of each grid cell
FPS = 60            # Target frames per second for rendering

# -- Colors (R, G, B) --
COLOR_BG = (10, 10, 10)
COLOR_TEXT = (200, 200, 200)

# -- Nutrient Settings --
MAX_NUTRIENT = 10.0         # Maximum nutrient value per cell
NUTRIENT_SPAWN_RATE = 0.05  # Probability of a cell regenerating nutrients per tick
NUTRIENT_DECAY = 0.995      # Multiplier per tick (e.g., 0.99 = 1% decay)
DIFFUSION_FACTOR = 0.1      # How fast nutrients spread to neighbors (0.0 - 0.25)
DEAD_BODY_NUTRIENT = 5.0    # Energy converted to nutrient when an agent dies


# -- Sunlight & Photosynthesis --
SUN_MAX_INTENSITY = 10.0    # Max energy gain from sun at surface
SUN_PENETRATION_DEPTH = 0.7 # Light intensity at bottom relative to top (0.0 = pitch black)
PHOTOSYNTHESIS_RATE = 0.5   # Base multiplier for energy gain

# -- Colony & Multicellularity --
ADHESION_RANGE = 1.5        # Distance to connect to other agents
COLONY_SHARING_RATE = 0.5   # % of energy difference shared per tick

# -- Agent Defaults & Evolution --
INITIAL_POPULATION = 100
MUTATION_RATE = 0.05        # Chance per gene to mutate
MUTATION_STRENGTH = 0.1     # Magnitude of mutation (relative to current value)

# Gene Constraints (Min, Max)
# 0: Metabolism (Energy cost per tick)
# 1: Reproduction Threshold (Energy needed to split)
# 2: Sensing Range (Distance to detect food)
# 3: Size (Visual & Predation)
# 4: Photosynthesis (Efficiency of solar energy collection)
# 5: Adhesion (Tendency to stick to others)
GENE_BOUNDS = {
    'metabolism': (0.1, 2.0),
    'repro_threshold': (10.0, 60.0),
    'sense_range': (1, 5),
    'size': (1.0, 3.0),
    'photosynthesis_efficiency': (0.0, 1.0),
    'adhesion': (0.0, 1.0)
}

# -- Predator Evolution --
PREDATOR_THRESHOLD_ENERGY = 40.0    # Energy required to trigger evolution check
PREDATOR_THRESHOLD_SIZE = 2.5       # Size gene required to become predator
PREDATOR_THRESHOLD_OFFSPRING = 3    # Successful offspring required
PREDATOR_METABOLISM_PENALTY = 1.5   # Multiplier for predator metabolism cost

# -- Day/Night Cycle --
CYCLE_LENGTH = 600          # Ticks per full day/night cycle
DAY_RATIO = 0.5             # Fraction of cycle that is day (0.0 - 1.0)
NIGHT_METABOLISM_FACTOR = 1.5 # Multiplier for prey metabolism at night (stress)
NIGHT_MOVE_CHANCE = 0.3     # Probability for prey to move at night (sluggish)

# -- Hyperconsumer Predator Settings --
PREDATOR_NIGHT_ACTIVITY = True # Predators are active at night
PREDATOR_DAY_ACTIVITY = False  # Predators are dormant during day
PREDATOR_EAT_EFFICIENCY = 0.8  # % of prey energy converted to predator energy (High)

