import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import array
import time


class Display:
    def __init__(self, scroll_speed=0.02, scrolling_enabled=False):
        displayio.release_displays()

        self.scroll_speed = scroll_speed
        self.scrolling_enabled = scrolling_enabled

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

    def update_display(self, text1, colors1, text2, colors2, scroll_times=5):
        """Update display with text either statically or with scrolling based on configuration."""
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
