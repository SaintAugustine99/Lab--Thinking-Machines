import pygame
import numpy as np
from environment import Environment
from config import (
    GRID_WIDTH, GRID_HEIGHT, CELL_SIZE, FPS, COLOR_BG, COLOR_TEXT, MAX_NUTRIENT,
    SUN_MAX_INTENSITY
)

class Camera:
    """Handles converting grid coordinates to screen pixels."""
    def __init__(self, cell_size):
        self.cell_size = cell_size

    def to_screen(self, x, y):
        return x * self.cell_size, y * self.cell_size

class VisualEffect:
    """Transient visual effects like flashes or lines."""
    def __init__(self, x, y, life=10, color=(255, 255, 255), size=1.0, type="circle", end_x=0, end_y=0):
        self.x = x
        self.y = y
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.type = type
        self.end_x = end_x
        self.end_y = end_y

    def draw(self, screen, camera):
        alpha = int((self.life / self.max_life) * 255)
        sx, sy = camera.to_screen(self.x, self.y)
        
        if self.type == "circle":
            radius = int(CELL_SIZE * self.size * (2.0 - (self.life / self.max_life)))
            # Optimization: Create a small surface just for the effect
            s_size = radius * 2 + 4
            s = pygame.Surface((s_size, s_size), pygame.SRCALPHA)
            
            # Draw centered on the small surface
            pygame.draw.circle(s, (*self.color, alpha), (s_size//2, s_size//2), radius, 1)
            
            # Blit centered on the target position
            screen.blit(s, (sx + CELL_SIZE//2 - s_size//2, sy + CELL_SIZE//2 - s_size//2))
            
        elif self.type == "line":
            ex, ey = camera.to_screen(self.end_x, self.end_y)
            
            # Optimization: Calculate bounding box for the line
            min_x = min(sx, ex)
            min_y = min(sy, ey)
            max_x = max(sx, ex)
            max_y = max(sy, ey)
            
            w = max_x - min_x + CELL_SIZE * 2 # Add padding
            h = max_y - min_y + CELL_SIZE * 2
            
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            
            # Calculate local coordinates
            start_pos = (sx - min_x + CELL_SIZE//2, sy - min_y + CELL_SIZE//2)
            end_pos = (ex - min_x + CELL_SIZE//2, ey - min_y + CELL_SIZE//2)
            
            pygame.draw.line(s, (*self.color, alpha), start_pos, end_pos, 1)
            screen.blit(s, (min_x, min_y))
            
        self.life -= 1

def create_legend_surface(font):
    """Pre-renders the legend to a surface."""
    legend_items = [
        ((255, 50, 50), "Breeder (High Repro)"),
        ((50, 255, 50), "Scout (High Sense)"),
        ((50, 50, 255), "Survivor (Low Metab)"),
        ((255, 255, 0), "Producer (Photosynth)"),
        ((128, 0, 128), "Predator (Hunter)")
    ]
    
    # Calculate height needed
    height = len(legend_items) * 15 + 10
    # Create surface with per-pixel alpha for transparency if needed, 
    # but here we just match the background or make it opaque.
    # The side panel is (20, 20, 20).
    surface = pygame.Surface((200, height))
    surface.fill((20, 20, 20)) 
    
    y = 10
    for color, text in legend_items:
        pygame.draw.rect(surface, color, (10, y, 10, 10))
        label = font.render(text, True, COLOR_TEXT)
        surface.blit(label, (25, y - 2))
        y += 15
        
    return surface

def map_value_to_color(value, max_val, color_tint):
    """Helper to darken a color based on a value (0 to max_val)."""
    intensity = min(1.0, value / max_val)
    return (
        int(color_tint[0] * intensity),
        int(color_tint[1] * intensity),
        int(color_tint[2] * intensity)
    )

def main():
    pygame.init()
    
    # Setup Window
    screen_width = GRID_WIDTH * CELL_SIZE + 200 # Extra width for legend
    screen_height = GRID_HEIGHT * CELL_SIZE + 40 # Extra space for stats
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Emergent Life Simulation")
    
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 14)
    
    # Initialize Simulation
    env = Environment()
    camera = Camera(CELL_SIZE)
    
    running = True
    paused = False
    fast_mode = False
    
    effects = []
    ticks = 0

    # Pre-allocate rendering resources
    nutrient_surf = pygame.Surface((GRID_WIDTH, GRID_HEIGHT))
    rgb_array = np.zeros((GRID_WIDTH, GRID_HEIGHT, 3), dtype=np.uint8)
    
    # Cache Legend
    legend_surf = create_legend_surface(font)

    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_s:
                    fast_mode = not fast_mode
                elif event.key == pygame.K_r:
                    env = Environment() # Reset
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Add massive nutrient drop at mouse
                mx, my = pygame.mouse.get_pos()
                gx, gy = mx // CELL_SIZE, my // CELL_SIZE
                if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT:
                    env.nutrients[gx, gy] += 50.0

        if not paused:
            # --- Logic Update ---
            env.update_nutrients()
            events = env.update_agents()
            
            # Process Events
            for ev in events:
                if ev[0] == 'eat':
                    effects.append(VisualEffect(ev[1], ev[2], life=5, color=(255, 255, 255), size=2.0, type="circle"))
                elif ev[0] == 'spawn':
                    effects.append(VisualEffect(ev[1], ev[2], life=10, color=(200, 200, 200), type="line", end_x=ev[3], end_y=ev[4]))
            
            ticks += 1

        # --- Rendering ---
        if not fast_mode or (ticks % 10 == 0): # Render rarely in fast mode
            screen.fill(COLOR_BG)

            # 1. Draw Nutrients (Background)
            # Normalize nutrients to 0-255 for Green channel
            normalized = (env.nutrients / MAX_NUTRIENT) * 255
            
            # Update the pre-allocated RGB array
            # We use np.clip and cast to uint8
            # Note: We can assign directly to the slice
            rgb_array[..., 1] = np.clip(normalized, 0, 255).astype(np.uint8) # Green
            rgb_array[..., 2] = rgb_array[..., 1] // 4 # Slight blue
            
            pygame.surfarray.blit_array(nutrient_surf, rgb_array)
            
            # Scale up to window size
            scaled_surf = pygame.transform.scale(nutrient_surf, (GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE))
            screen.blit(scaled_surf, (0, 0))
            
            # Night Overlay
            if env.is_night:
                night_surf = pygame.Surface((GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), pygame.SRCALPHA)
                night_surf.fill((0, 0, 50, 100)) # Dark blue, semi-transparent
                screen.blit(night_surf, (0, 0))
            else:
                # Sunlight Overlay (Yellow Gradient)
                # We can pre-calculate this or draw it dynamically. 
                # Since it's static, let's just draw a gradient rect.
                # Actually, let's just use the env.sunlight_gradient for accuracy if we want, 
                # but a simple gradient surface is faster.
                sun_surf = pygame.Surface((GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE), pygame.SRCALPHA)
                for y in range(GRID_HEIGHT):
                    intensity = int((1.0 - y / GRID_HEIGHT) * 50) # Max alpha 50
                    pygame.draw.rect(sun_surf, (255, 255, 0, intensity), (0, y * CELL_SIZE, GRID_WIDTH * CELL_SIZE, CELL_SIZE))
                screen.blit(sun_surf, (0, 0))

            # 1.5 Draw Colony Connections
            # We need to find attached agents. This is O(N^2) if we check all pairs, 
            # but we can optimize by only checking neighbors in the grid.
            # For visualization, let's just iterate agents and check their neighbors in the spatial hash.
            # Re-build spatial hash for rendering (or reuse if we passed it out of update, but we didn't)
            occupied = {(a.x, a.y): a for a in env.agents}
            for agent in env.agents:
                if agent.genes['adhesion'] >= 0.5:
                    sx, sy = camera.to_screen(agent.x, agent.y)
                    # Check neighbors
                    for dx in range(0, 2): # Only check positive directions to avoid double drawing
                        for dy in range(0, 2):
                            if dx == 0 and dy == 0: continue
                            nx, ny = agent.x + dx, agent.y + dy
                            if (nx, ny) in occupied:
                                other = occupied[(nx, ny)]
                                if other.genes['adhesion'] >= 0.5:
                                    # Draw connection
                                    ex, ey = camera.to_screen(nx, ny)
                                    pygame.draw.line(screen, (200, 200, 200), 
                                                     (sx + CELL_SIZE//2, sy + CELL_SIZE//2), 
                                                     (ex + CELL_SIZE//2, ey + CELL_SIZE//2), 2)

            # 2. Draw Agents
            for agent in env.agents:
                sx, sy = camera.to_screen(agent.x, agent.y)
                
                # Calculate size based on genes
                size_mult = agent.genes['size']
                draw_size = CELL_SIZE * size_mult
                
                # Center the agent on its grid cell
                offset = (draw_size - CELL_SIZE) / 2
                
                # Draw main body
                pygame.draw.rect(screen, agent.color, (sx - offset, sy - offset, draw_size, draw_size))
                
                # Optional: visual indicator of energy (small white dot in center)
                if agent.energy > 20:
                    pygame.draw.rect(screen, (255, 255, 255), (sx + 3, sy + 3, 2, 2))

            # 3. Draw Effects
            effects = [e for e in effects if e.life > 0]
            for e in effects:
                e.draw(screen, camera)

            # 4. Draw UI / Stats
            # Draw bottom panel
            pygame.draw.rect(screen, (30, 30, 30), (0, GRID_HEIGHT * CELL_SIZE, screen_width, 40))
            
            # Draw Side Panel (Legend)
            pygame.draw.rect(screen, (20, 20, 20), (GRID_WIDTH * CELL_SIZE, 0, 200, screen_height))
            screen.blit(legend_surf, (GRID_WIDTH * CELL_SIZE, 0))
            
            pop_count = len(env.agents)
            predator_count = sum(1 for a in env.agents if a.is_predator)
            avg_energy = sum(a.energy for a in env.agents) / max(1, pop_count)
            avg_metab = sum(a.genes['metabolism'] for a in env.agents) / max(1, pop_count)
            current_fps = clock.get_fps()
            
            current_fps = clock.get_fps()
            
            time_of_day = "NIGHT" if env.is_night else "DAY"
            stats_text = f"Pop: {pop_count} (Pred: {predator_count}) | FPS: {current_fps:.1f} | {time_of_day} | Tick: {ticks}"
            if paused: stats_text += " [PAUSED]"
            if fast_mode: stats_text += " [FAST]"
            
            text_surf = font.render(stats_text, True, COLOR_TEXT)
            screen.blit(text_surf, (10, GRID_HEIGHT * CELL_SIZE + 10))

            pygame.display.flip()

        clock.tick(FPS if not fast_mode else 1000)

    pygame.quit()

if __name__ == "__main__":
    main()
