import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import array
import time
import rtc
import wifi
import socketpool
import adafruit_ntp


class Display:
    def __init__(self, scroll_speed=0.02, scrolling_enabled=False):
        displayio.release_displays()

        self.scroll_speed = scroll_speed
        self.scrolling_enabled = scrolling_enabled
        
        # Define quiet hours (8 PM to 3:30 AM)
        self.quiet_start_hour = 20    # 8 PM
        self.quiet_start_minute = 0
        self.quiet_end_hour = 3       # 3 AM
        self.quiet_end_minute = 30    # 30 minutes
        self.display_enabled = True
        self.night_mode = False

        # Try to sync time with NTP
        self.sync_time()

        # Initialize the RGB matrix
        matrix = rgbmatrix.RGBMatrix(
            width=128,
            height=32,
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
        self.char_width = 6
        self.char_height = 12
        self.line_length = (128 // self.char_width) + 2

        self.setup_display_groups()
        self.setup_character_map()
        self.setup_line_resources()
        self.setup_night_mode()

        self.display.root_group = self.main_group

    def draw_logo_bitmap(self, bitmap):
        """
        Draws an L in a circle on the given bitmap.
        Bitmap is 12x12 pixels with 2 colors (0=off, 1=on).
        Creates a circular design that fills the 12x12 space with a thin L cutout.
        """
        # First clear the bitmap
        for x in range(12):
            for y in range(12):
                bitmap[x, y] = 0

        # Draw a circle that fills the 12x12 space
        # First fill the main circle body
        for x in range(1, 11):
            for y in range(1, 11):
                bitmap[x, y] = 1

        # Add the four middle edge pixels
        bitmap[0, 5] = 1
        bitmap[0, 6] = 1
        bitmap[11, 5] = 1
        bitmap[11, 6] = 1
        bitmap[5, 0] = 1
        bitmap[6, 0] = 1
        bitmap[5, 11] = 1
        bitmap[6, 11] = 1

        # Add corner pieces for roundness
        bitmap[1, 1] = 0  # Top-left corner
        bitmap[1, 10] = 0  # Bottom-left corner
        bitmap[10, 1] = 0  # Top-right corner
        bitmap[10, 10] = 0  # Bottom-right corner

        # Cut out a thinner L shape
        # Vertical part of L
        for y in range(3, 9):
            for x in range(4, 6):  # Made thinner (just 1 pixel wide)
                bitmap[x, y] = 0
        # Horizontal part of L
        for x in range(5, 9):  # Same length
            for y in range(7, 9):  # Made thinner (just 1 pixel tall)
                bitmap[x, y] = 0

    def draw_moon_bitmap(self, bitmap):
        """
        Draws a simple crescent moon shape on the given bitmap.
        Bitmap is 8x8 pixels with 2 colors (0=off, 1=on).
        """
        # First clear the bitmap
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

    def setup_display_groups(self):
        self.main_group = displayio.Group()
        self.line1 = displayio.Group()
        self.line2 = displayio.Group()

        # Create a bitmap for the circular logo (12x12)
        self.logo_bitmap = displayio.Bitmap(12, 12, 2)  # 2 colors: off and on
        self.logo_palette = displayio.Palette(2)
        self.logo_palette[0] = 0x000000  # Off (black)
        self.logo_palette[1] = 0xFFFFFF  # On (white)

        # Draw the L-circle logo
        self.draw_logo_bitmap(self.logo_bitmap)

        # Create tile grids for the logo
        self.logo_grid = displayio.TileGrid(
            self.logo_bitmap, pixel_shader=self.logo_palette
        )

        # Create groups for the logos
        self.logo1 = displayio.Group()
        self.logo2 = displayio.Group()
        self.logo1.append(self.logo_grid)
        self.logo2.append(
            displayio.TileGrid(self.logo_bitmap, pixel_shader=self.logo_palette)
        )

        # Add everything to main group
        self.main_group.append(self.logo1)
        self.main_group.append(self.logo2)
        self.main_group.append(self.line1)
        self.main_group.append(self.line2)

        # Position all elements
        self.logo1.y = 0  # Centered vertically in the 32px height
        self.logo2.y = 16
        self.logo1.x = 0
        self.logo2.x = 0
        self.line1.y = 1
        self.line2.y = 16
        self.line1.x = 14  # Move text right to make room for 12px wide logo
        self.line2.x = 14

    def setup_character_map(self):
        self.charmap = (
            array.array("b", [terminalio.FONT.get_glyph(32).tile_index]) * 256
        )
        for ch in range(256):
            glyph = terminalio.FONT.get_glyph(ch)
            if glyph is not None:
                self.charmap[ch] = glyph.tile_index

    def create_tilegrid(self, palette):
        return displayio.TileGrid(
            bitmap=terminalio.FONT.bitmap,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=self.char_width,
            tile_height=self.char_height,
            default_tile=32,
        )

    def setup_line_resources(self):
        self.palettes1 = [displayio.Palette(2) for _ in range(self.line_length)]
        self.palettes2 = [displayio.Palette(2) for _ in range(self.line_length)]

        self.grids1 = [self.create_tilegrid(p) for p in self.palettes1]
        self.grids2 = [self.create_tilegrid(p) for p in self.palettes2]

        for idx, grid in enumerate(self.grids1):
            grid.x = self.char_width * idx
            self.line1.append(grid)

        for idx, grid in enumerate(self.grids2):
            grid.x = self.char_width * idx
            self.line2.append(grid)

    def set_text_with_colors(self, text, colors, line_num):
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

    def sync_time(self):
        """Synchronize time with NTP server"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # Ensure WiFi is connected
                if not wifi.radio.connected:
                    print("WiFi not connected, skipping time sync")
                    return

                # Create a socket pool for NTP
                pool = socketpool.SocketPool(wifi.radio)
                
                # Connect to NTP server
                ntp = adafruit_ntp.NTP(pool, tz_offset=-5)  # EST offset (-5 for EST)
                
                # Update the RTC
                rtc.RTC().datetime = ntp.datetime
                print("Time synchronized with NTP server")
                current_time = time.localtime()
                print(f"Current time: {current_time.tm_hour:02d}:{current_time.tm_min:02d}:{current_time.tm_sec:02d}")
                return True
            except Exception as e:
                print(f"Time sync attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Time sync failed after all retries")
        return False

    def is_quiet_hours(self):
        """Check if current time is within quiet hours (10 PM - 3:30 AM)"""
        current_time = time.localtime()
        current_hour = current_time.tm_hour
        current_minute = current_time.tm_min
        
        # Convert all times to minutes since midnight for easier comparison
        current_minutes = current_hour * 60 + current_minute
        quiet_start_minutes = self.quiet_start_hour * 60 + self.quiet_start_minute
        quiet_end_minutes = self.quiet_end_hour * 60 + self.quiet_end_minute
        
        # If we're after 10 PM (22:00)
        if current_hour >= self.quiet_start_hour:
            return True
        # If we're before 3:30 AM
        elif current_hour < self.quiet_end_hour or (current_hour == self.quiet_end_hour and current_minute < self.quiet_end_minute):
            return True
        
        # Otherwise, not in quiet hours
        return False

    def setup_night_mode(self):
        """Setup the night mode display elements"""
        # Create a bitmap for the moon icon (8x8)
        self.night_bitmap = displayio.Bitmap(8, 8, 2)
        self.night_palette = displayio.Palette(2)
        self.night_palette[0] = 0x000000  # Off (black)
        self.night_palette[1] = 0x222222  # Very dim white

        # Draw the moon shape
        self.draw_moon_bitmap(self.night_bitmap)

        # Create tile grid for the night icon
        self.night_grid = displayio.TileGrid(
            self.night_bitmap,
            pixel_shader=self.night_palette,
            x=60,  # Center horizontally
            y=12   # Center vertically
        )

        # Create a group for night mode
        self.night_group = displayio.Group()
        self.night_group.append(self.night_grid)

    def show_night_mode(self):
        """Switch display to night mode"""
        if not self.night_mode:
            self.display.brightness = 0.1  # Very dim
            self.main_group.hidden = True
            self.display.root_group = self.night_group
            self.night_mode = True
            self.display.refresh(minimum_frames_per_second=0)

    def show_normal_mode(self):
        """Switch display to normal mode"""
        if self.night_mode:
            self.display.brightness = 1
            self.main_group.hidden = False
            self.display.root_group = self.main_group
            self.night_mode = False

    def update_display(self, text1, colors1, text2, colors2, scroll_times=5):
        """Update display with text either statically or with scrolling based on configuration."""
        # Check if we're in quiet hours
        in_quiet_hours = self.is_quiet_hours()
        print(f"Current time: {time.localtime().tm_hour}:{time.localtime().tm_min}")
        print(f"In quiet hours: {in_quiet_hours}")
        
        if in_quiet_hours:
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

            for j in range(self.char_width):
                self.line1.x = -j
                self.line2.x = -j
                self.display.refresh(minimum_frames_per_second=0)
                time.sleep(self.scroll_speed)
