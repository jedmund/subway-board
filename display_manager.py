import board
import displayio
import digitalio
import framebufferio
import rgbmatrix
import terminalio
import array
import time


class Display:
    # Constants
    CHAR_WIDTH = 6
    CHAR_HEIGHT = 12
    MATRIX_WIDTH = 128
    MATRIX_HEIGHT = 32

    from config import QUIET_START_HOUR, QUIET_START_MIN, QUIET_END_HOUR, QUIET_END_MIN, SCROLL_SPEED

    def __init__(self, scroll_speed=SCROLL_SPEED, scrolling_enabled=False):
        displayio.release_displays()

        self.scroll_speed = scroll_speed
        self.scrolling_enabled = scrolling_enabled
        self.display_enabled = True
        self.night_mode = False

        # Initialize the matrix display
        self._init_display()
        
        # Setup display elements
        self._setup_display_groups()
        self._setup_character_map()
        self._setup_line_resources()
        self._setup_night_mode()

        # Add manual night mode toggle flag
        self.manual_night_mode = False
        
        # Setup button
        self._setup_button()

        # Set initial root group
        self.display.root_group = self.main_group

    def _init_display(self):
        """Initialize the RGB matrix display."""
        matrix = rgbmatrix.RGBMatrix(
            width=self.MATRIX_WIDTH,
            height=self.MATRIX_HEIGHT,
            bit_depth=3,
            rgb_pins=[
                board.MTX_R1,
                board.MTX_G1,
                board.MTX_B1,
                board.MTX_R2,
                board.MTX_G2,
                board.MTX_B2,
            ],
            addr_pins=[
                board.MTX_ADDRA,
                board.MTX_ADDRB,
                board.MTX_ADDRC,
                board.MTX_ADDRD,
            ],
            clock_pin=board.MTX_CLK,
            latch_pin=board.MTX_LAT,
            output_enable_pin=board.MTX_OE,
        )

        self.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
        self.line_length = (self.MATRIX_WIDTH // self.CHAR_WIDTH) + 2

    def _setup_display_groups(self):
        """Setup display groups for main content and logos."""
        self.main_group = displayio.Group()
        self.line1 = displayio.Group()
        self.line2 = displayio.Group()

        # Create logo bitmap and palette
        self.logo_bitmap = displayio.Bitmap(12, 12, 2)
        self.logo_palette = displayio.Palette(2)
        self.logo_palette[0] = 0x000000  # Off (black)
        self.logo_palette[1] = 0xFFFFFF  # On (white)

        # Draw the L-circle logo
        self._draw_logo_bitmap(self.logo_bitmap)

        # Create groups for logos
        self.logo1 = displayio.Group()
        self.logo2 = displayio.Group()
        self.logo1.append(displayio.TileGrid(
            self.logo_bitmap, pixel_shader=self.logo_palette
        ))
        self.logo2.append(displayio.TileGrid(
            self.logo_bitmap, pixel_shader=self.logo_palette
        ))

        # Add everything to main group
        self.main_group.append(self.logo1)
        self.main_group.append(self.logo2)
        self.main_group.append(self.line1)
        self.main_group.append(self.line2)

        # Position all elements
        self.logo1.y = 0
        self.logo2.y = 16
        self.logo1.x = 0
        self.logo2.x = 0
        self.line1.y = 1
        self.line2.y = 16
        self.line1.x = 14  # Move text right to make room for logo
        self.line2.x = 14

    def _setup_character_map(self):
        """Setup character mapping for text display."""
        # Create a mapping from ASCII to font tile indices
        self.charmap = array.array("b", [terminalio.FONT.get_glyph(32).tile_index]) * 256
        for ch in range(256):
            glyph = terminalio.FONT.get_glyph(ch)
            if glyph is not None:
                self.charmap[ch] = glyph.tile_index
    
    def _create_tilegrid(self, palette):
        """Create a tile grid for displaying a character."""
        return displayio.TileGrid(
            bitmap=terminalio.FONT.bitmap,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=self.CHAR_WIDTH,
            tile_height=self.CHAR_HEIGHT,
            default_tile=32,
        )
    
    def _setup_line_resources(self):
        """Setup resources for displaying text lines."""
        # Create palettes and grids for each character position
        self.palettes1 = [displayio.Palette(2) for _ in range(self.line_length)]
        self.palettes2 = [displayio.Palette(2) for _ in range(self.line_length)]

        self.grids1 = [self._create_tilegrid(p) for p in self.palettes1]
        self.grids2 = [self._create_tilegrid(p) for p in self.palettes2]

        # Position grids for line 1
        for idx, grid in enumerate(self.grids1):
            grid.x = self.CHAR_WIDTH * idx
            self.line1.append(grid)

        # Position grids for line 2
        for idx, grid in enumerate(self.grids2):
            grid.x = self.CHAR_WIDTH * idx
            self.line2.append(grid)

    def _setup_night_mode(self):
        """Setup the night mode display elements."""
        # Create a bitmap for the moon icon (8x8)
        self.night_bitmap = displayio.Bitmap(8, 8, 2)
        self.night_palette = displayio.Palette(2)
        self.night_palette[0] = 0x000000  # Off (black)
        self.night_palette[1] = 0x222222  # Very dim white

        # Draw the moon shape
        self._draw_moon_bitmap(self.night_bitmap)

        # Create tile grid for night icon
        self.night_grid = displayio.TileGrid(
            self.night_bitmap,
            pixel_shader=self.night_palette,
            x=60,  # Center horizontally
            y=12   # Center vertically
        )

        # Create a group for night mode
        self.night_group = displayio.Group()
        self.night_group.append(self.night_grid)

    def _setup_button(self):
        """Setup the UP button for night mode toggle."""
        self.button_up = digitalio.DigitalInOut(board.BUTTON_UP)
        self.button_up.direction = digitalio.Direction.INPUT
        self.button_up.pull = digitalio.Pull.UP
        self.last_button_state = True  # Pulled up = not pressed
        self.debounce_time = 0.1  # 100ms debounce


    def _draw_logo_bitmap(self, bitmap):
        """Draw an L in a circle on the given bitmap."""
        # First clear the bitmap
        for x in range(12):
            for y in range(12):
                bitmap[x, y] = 0

        # Draw a circle that fills the 12x12 space
        for x in range(1, 11):
            for y in range(1, 11):
                bitmap[x, y] = 1

        # Add the four middle edge pixels
        bitmap[0, 5] = bitmap[0, 6] = 1
        bitmap[11, 5] = bitmap[11, 6] = 1
        bitmap[5, 0] = bitmap[6, 0] = 1
        bitmap[5, 11] = bitmap[6, 11] = 1

        # Add corner pieces for roundness
        bitmap[1, 1] = bitmap[1, 10] = bitmap[10, 1] = bitmap[10, 10] = 0

        # Cut out the L shape
        # Vertical part of L
        for y in range(3, 9):
            for x in range(4, 6):
                bitmap[x, y] = 0
        # Horizontal part of L
        for x in range(5, 9):
            for y in range(7, 9):
                bitmap[x, y] = 0

    def _draw_moon_bitmap(self, bitmap):
        """Draw a simple crescent moon shape on the given bitmap."""
        # Clear the bitmap
        for x in range(8):
            for y in range(8):
                bitmap[x, y] = 0

        # Draw a simple crescent moon shape
        # Outer circle
        for x in range(1, 7):
            for y in range(1, 7):
                if (x-3.5)**2 + (y-3.5)**2 <= 12:
                    bitmap[x, y] = 1

        # Inner circle (shifted right to create crescent)
        for x in range(2, 7):
            for y in range(1, 7):
                if (x-4.5)**2 + (y-3.5)**2 <= 8:
                    bitmap[x, y] = 0

    def check_button(self):
        """Check if button was pressed and toggle night mode."""
        # Read current button state (False = pressed, True = not pressed)
        button_pressed = not self.button_up.value
        
        # Check for button state change from not pressed to pressed
        button_newly_pressed = self.last_button_state and not button_pressed
        
        # Update stored button state BEFORE debounce delay
        self.last_button_state = button_pressed
        
        # Handle button press
        if button_newly_pressed:
            print("BUTTON PRESSED!")
            # Toggle manual night mode
            self.manual_night_mode = not self.manual_night_mode
            
            # Simple debounce after handling the press
            time.sleep(self.debounce_time)
            
            if self.manual_night_mode:
                print("Manual night mode ON")
                self.show_night_mode()
                return 1  # Button turned night mode ON
            else:
                print("Manual night mode OFF")
                self.show_normal_mode()
                return 2  # Button turned night mode OFF
        
        return 0  # No button press

    def set_text_with_colors(self, text, colors, line_num):
        """Set text with specific colors for each character."""
        grids = self.grids1 if line_num == 0 else self.grids2
        palettes = self.palettes1 if line_num == 0 else self.palettes2

        # If text is shorter than line_length, pad with spaces
        if len(text) < self.line_length:
            text += " " * (self.line_length - len(text))

        # For each character in text
        for i in range(min(len(text), self.line_length)):
            # Use the color at index i (or the last color if i >= len(colors))
            color_index = min(i, len(colors) - 1)
            palettes[i][1] = colors[color_index]

            # Map the character to a glyph
            glyph_code = ord(text[i])
            grids[i][0] = self.charmap[glyph_code]

    def is_quiet_hours(self):
        """Check if current time is within quiet hours."""
        current_time = time.localtime()
        current_hour = current_time.tm_hour
        current_minute = current_time.tm_min

        print(f"Current time: {current_hour}:{current_minute}")
        print(f"Quiet hours: {self.QUIET_START_HOUR}:{self.QUIET_START_MIN} to {self.QUIET_END_HOUR}:{self.QUIET_END_MIN}")
        
        # If we're after start hour
        if current_hour > self.QUIET_START_HOUR or (
            current_hour == self.QUIET_START_HOUR and 
            current_minute >= self.QUIET_START_MIN
        ):
            return True
            
        # If we're before end hour/minute
        if current_hour < self.QUIET_END_HOUR or (
            current_hour == self.QUIET_END_HOUR and 
            current_minute < self.QUIET_END_MIN
        ):
            return True
        
        # Otherwise, not in quiet hours
        return False
    
    def show_night_mode(self):
        """Switch display to night mode."""
        if not self.night_mode:
            self.display.brightness = 0.1  # Very dim
            self.main_group.hidden = True
            self.display.root_group = self.night_group
            self.night_mode = True
            self.display.refresh(minimum_frames_per_second=0)


    def show_normal_mode(self):
        """Switch display to normal mode."""
        if self.night_mode or self.manual_night_mode:  # Check both flags
            self.display.brightness = 1
            self.main_group.hidden = False
            self.display.root_group = self.main_group
            self.night_mode = False
            # Note: we don't modify manual_night_mode here as it's controlled by button
            self.display.refresh(minimum_frames_per_second=0)

    def update_display(self, text1, colors1, text2, colors2, scroll_times=5):
        """Update display with text either statically or with scrolling."""
        # Check button first
        self.check_button()
        
        # If manual night mode is enabled, stay in night mode regardless of time
        if self.manual_night_mode:
            self.show_night_mode()
            return
            
        # Check if we're in quiet hours (only applies when not in manual mode)
        if self.is_quiet_hours():
            self.show_night_mode()
            return
        
        # If we were in night mode, switch back to normal mode
        self.show_normal_mode()
            
        # Continue with normal display update
        if self.scrolling_enabled:
            self._scroll_text(text1, colors1, text2, colors2, scroll_times)
        else:
            self._static_display(text1, colors1, text2, colors2)


    def _static_display(self, text1, colors1, text2, colors2):
        """Display text without scrolling."""
        self.set_text_with_colors(text1, colors1, 0)
        self.set_text_with_colors(text2, colors2, 1)
        self.display.refresh(minimum_frames_per_second=0)

    def _scroll_text(self, text1, colors1, text2, colors2, scroll_times=5):
        """Scroll text across the display."""
        padding = " " * self.line_length
        full_text1 = padding + text1 + padding
        full_text2 = padding + text2 + padding

        max_pos = max(len(full_text1), len(full_text2)) - self.line_length

        for i in range(max_pos * scroll_times):
            pos = i % max_pos
            text1_window = full_text1[pos : pos + self.line_length]
            text2_window = full_text2[pos : pos + self.line_length]

            self.set_text_with_colors(text1_window, colors1, 0)
            self.set_text_with_colors(text2_window, colors2, 1)

            for j in range(self.CHAR_WIDTH):
                self.line1.x = -j
                self.line2.x = -j
                self.display.refresh(minimum_frames_per_second=0)
                time.sleep(self.scroll_speed)