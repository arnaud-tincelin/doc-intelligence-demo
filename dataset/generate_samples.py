"""Generate sample electrical schema images for testing."""

from PIL import Image, ImageDraw, ImageFont

# Dimensions
W, H = 800, 600


def _get_font(size: int = 14):
    """Try to load a font, fall back to default."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def draw_resistor(draw: ImageDraw.ImageDraw, x: int, y: int, label: str = "R1"):
    """Draw a resistor symbol."""
    draw.line([(x, y), (x + 10, y)], fill="black", width=2)
    points = []
    for i in range(6):
        px = x + 10 + i * 10
        py = y - 10 if i % 2 == 0 else y + 10
        points.append((px, py))
    draw.line(points, fill="black", width=2)
    draw.line([(x + 70, y), (x + 80, y)], fill="black", width=2)
    font = _get_font(12)
    draw.text((x + 30, y - 25), label, fill="black", font=font)


def draw_battery(draw: ImageDraw.ImageDraw, x: int, y: int, label: str = "V1"):
    """Draw a battery symbol."""
    draw.line([(x, y), (x, y - 20)], fill="black", width=2)
    draw.line([(x - 15, y - 20), (x + 15, y - 20)], fill="black", width=3)
    draw.line([(x - 8, y - 30), (x + 8, y - 30)], fill="black", width=1)
    draw.line([(x, y - 30), (x, y - 50)], fill="black", width=2)
    font = _get_font(12)
    draw.text((x + 18, y - 35), label, fill="black", font=font)


def draw_ground(draw: ImageDraw.ImageDraw, x: int, y: int):
    """Draw a ground symbol."""
    draw.line([(x, y), (x, y + 10)], fill="black", width=2)
    draw.line([(x - 15, y + 10), (x + 15, y + 10)], fill="black", width=2)
    draw.line([(x - 10, y + 15), (x + 10, y + 15)], fill="black", width=2)
    draw.line([(x - 5, y + 20), (x + 5, y + 20)], fill="black", width=2)


def generate_simple_circuit():
    """Generate a simple series circuit image."""
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _get_font(16)

    draw.text((W // 2 - 80, 20), "Simple Series Circuit", fill="black", font=font)

    # Battery
    draw_battery(draw, 150, 350, "9V")

    # Wires
    draw.line([(150, 300), (150, 200), (400, 200)], fill="black", width=2)

    # Resistor
    draw_resistor(draw, 400, 200, "R1=1kΩ")

    # More wire
    draw.line([(480, 200), (600, 200), (600, 400)], fill="black", width=2)

    # LED
    draw.ellipse([(585, 400), (615, 430)], outline="black", width=2)
    draw.text((620, 405), "LED", fill="black", font=_get_font(12))

    # Wire back to battery
    draw.line([(600, 430), (600, 500), (150, 500), (150, 350)], fill="black", width=2)

    # Ground
    draw_ground(draw, 375, 500)

    # Labels
    draw.text((50, 550), "Note: Missing current-limiting resistor for LED", fill="red", font=_get_font(12))

    img.save("dataset/simple_circuit.png")
    return img


def generate_parallel_circuit():
    """Generate a parallel circuit with a deliberate wiring issue."""
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _get_font(16)

    draw.text((W // 2 - 100, 20), "Parallel Circuit - Wiring Issue", fill="black", font=font)

    # Main bus lines
    draw.line([(100, 150), (700, 150)], fill="black", width=3)
    draw.line([(100, 450), (700, 450)], fill="black", width=3)

    # Battery
    draw_battery(draw, 100, 450, "12V")
    draw.line([(100, 400), (100, 150)], fill="black", width=2)

    # Branch 1 - Resistor
    draw.line([(250, 150), (250, 200)], fill="black", width=2)
    draw_resistor(draw, 210, 250, "R1=470Ω")
    draw.line([(250, 280), (250, 450)], fill="black", width=2)

    # Branch 2 - Resistor (ISSUE: broken connection shown as dashed)
    draw.line([(450, 150), (450, 200)], fill="black", width=2)
    # Dashed line to show break
    for i in range(0, 60, 10):
        draw.line([(450, 250 + i), (450, 255 + i)], fill="red", width=2)
    draw_resistor(draw, 410, 320, "R2=1kΩ")

    # Issue marker
    draw.rectangle([(430, 240), (470, 310)], outline="red", width=3)
    draw.text((475, 260), "⚠ BREAK", fill="red", font=_get_font(14))

    draw.line([(450, 350), (450, 450)], fill="black", width=2)

    # Branch 3 - LED
    draw.line([(650, 150), (650, 250)], fill="black", width=2)
    draw.ellipse([(635, 250), (665, 280)], outline="black", width=2)
    draw.text((670, 255), "LED", fill="black", font=_get_font(12))
    draw.line([(650, 280), (650, 450)], fill="black", width=2)

    # Ground
    draw_ground(draw, 700, 450)

    draw.text((50, 550), "Issue: Broken connection in Branch 2 (R2)", fill="red", font=_get_font(12))

    img.save("dataset/parallel_circuit.png")
    return img


def generate_complex_panel():
    """Generate a complex electrical panel schematic."""
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = _get_font(16)

    draw.text((W // 2 - 100, 15), "Electrical Panel Layout", fill="black", font=font)

    # Panel outline
    draw.rectangle([(50, 50), (750, 550)], outline="black", width=3)

    # Main breaker
    draw.rectangle([(80, 70), (200, 130)], outline="black", width=2)
    draw.text((90, 80), "MAIN", fill="black", font=_get_font(14))
    draw.text((90, 100), "200A", fill="black", font=_get_font(12))

    # Bus bars
    draw.line([(140, 130), (140, 520)], fill="black", width=4)
    draw.line([(400, 70), (400, 520)], fill="blue", width=2)
    draw.line([(420, 70), (420, 520)], fill="blue", width=2)

    # Circuit breakers - left side
    breakers_left = [
        ("CB1 - Kitchen", "20A", "black"),
        ("CB2 - Living", "15A", "black"),
        ("CB3 - Bedroom", "15A", "black"),
        ("CB4 - Bathroom", "20A", "red"),  # Issue: should be GFCI
        ("CB5 - Garage", "20A", "black"),
    ]

    for i, (name, amps, color) in enumerate(breakers_left):
        y = 160 + i * 70
        draw.rectangle([(80, y), (200, y + 40)], outline=color, width=2)
        draw.text((90, y + 5), name, fill=color, font=_get_font(11))
        draw.text((90, y + 22), amps, fill=color, font=_get_font(10))
        draw.line([(200, y + 20), (400, y + 20)], fill="black", width=2)

    # Issue highlight on CB4
    y4 = 160 + 3 * 70
    draw.rectangle([(75, y4 - 5), (205, y4 + 45)], outline="red", width=3)
    draw.text((210, y4 + 5), "⚠ Needs GFCI", fill="red", font=_get_font(12))

    # Circuit breakers - right side
    breakers_right = [
        ("CB6 - HVAC", "30A", "black"),
        ("CB7 - Laundry", "20A", "black"),
        ("CB8 - Office", "15A", "orange"),  # Issue: overloaded
        ("CB9 - Outdoor", "20A", "black"),
    ]

    for i, (name, amps, color) in enumerate(breakers_right):
        y = 160 + i * 70
        draw.rectangle([(500, y), (620, y + 40)], outline=color, width=2)
        draw.text((510, y + 5), name, fill=color, font=_get_font(11))
        draw.text((510, y + 22), amps, fill=color, font=_get_font(10))
        draw.line([(420, y + 20), (500, y + 20)], fill="black", width=2)

    # Issue highlight on CB8
    y8 = 160 + 2 * 70
    draw.rectangle([(495, y8 - 5), (625, y8 + 45)], outline="orange", width=3)
    draw.text((630, y8 + 5), "⚠ Overloaded", fill="orange", font=_get_font(12))

    # Ground bar
    draw.rectangle([(650, 400), (730, 520)], outline="green", width=2)
    draw.text((655, 410), "GND", fill="green", font=_get_font(12))
    draw.text((655, 430), "BAR", fill="green", font=_get_font(12))

    draw.text((50, 560), "Issues: CB4 bathroom needs GFCI protection; CB8 office circuit overloaded",
              fill="red", font=_get_font(11))

    img.save("dataset/complex_panel.png")
    return img


if __name__ == "__main__":
    generate_simple_circuit()
    generate_parallel_circuit()
    generate_complex_panel()
    print("Generated 3 sample electrical schema images in dataset/")
