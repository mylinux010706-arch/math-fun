import pygame
import random
import sys
import math
import numpy as np

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)

WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mental Math Flash")
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
PANEL = (20, 20, 20)
PANEL_LIGHT = (34, 34, 34)
WHITE = (255, 255, 255)
TEXT_DIM = (150, 150, 150)
DANGER = (255, 99, 99)
SUCCESS = (110, 231, 150)

FONT_HUGE = pygame.font.SysFont("segoeui", 96, bold=True)
FONT_BIG = pygame.font.SysFont("segoeui", 48, bold=True)
FONT_MED = pygame.font.SysFont("segoeui", 30, bold=True)
FONT_SMALL = pygame.font.SysFont("segoeui", 20)
FONT_TINY = pygame.font.SysFont("segoeui", 16)


def make_tone(freq, duration, volume=0.4, wave="sine"):
    sample_rate = 44100
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, False)
    if wave == "sine":
        tone = np.sin(freq * t * 2 * np.pi)
    elif wave == "square":
        tone = np.sign(np.sin(freq * t * 2 * np.pi))
    else:
        tone = np.sin(freq * t * 2 * np.pi)
    fade = min(400, n // 4)
    envelope = np.ones(n)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    tone = tone * envelope * volume
    audio = np.int16(tone * 32767)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(stereo)


SND_TICK = make_tone(880, 0.06, 0.25)
SND_CLICK = make_tone(600, 0.05, 0.2)
SND_COUNTDOWN = make_tone(440, 0.15, 0.3)
SND_GO = make_tone(1046, 0.2, 0.35)
SND_CORRECT = make_tone(784, 0.35, 0.4)
SND_WRONG = make_tone(160, 0.4, 0.4, wave="square")


def draw_background():
    screen.fill(BLACK)


def draw_rounded_panel(rect, color, radius=18, border=None, border_width=2):
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, surf.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, surf.get_rect(), width=border_width, border_radius=radius)
    screen.blit(surf, rect.topleft)


def draw_text(text, font, color, center):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    screen.blit(surf, rect)
    return rect


class Button:
    def __init__(self, rect, label, sub=None, accent=False, danger=False, key_hint=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.sub = sub
        self.accent = accent
        self.danger = danger
        self.key_hint = key_hint
        self.hover = False

    def draw(self):
        self.hover = self.rect.collidepoint(pygame.mouse.get_pos())
        if self.accent:
            base = WHITE
        elif self.danger:
            base = (50, 18, 18)
        else:
            base = PANEL_LIGHT
        color = tuple(min(255, c + 22) for c in base) if self.hover else base
        border = DANGER if self.danger else (WHITE if not self.accent else None)
        draw_rounded_panel(self.rect, color, radius=14, border=border, border_width=2 if self.hover else 1)
        if self.accent:
            text_color = BLACK
        elif self.danger:
            text_color = DANGER
        else:
            text_color = WHITE
        if self.sub:
            draw_text(self.label, FONT_MED, text_color, (self.rect.centerx, self.rect.centery - 12))
            draw_text(self.sub, FONT_TINY, text_color if self.accent else TEXT_DIM, (self.rect.centerx, self.rect.centery + 16))
        else:
            draw_text(self.label, FONT_MED, text_color, self.rect.center)
        if self.key_hint:
            badge_rect = pygame.Rect(self.rect.right - 30, self.rect.top - 10, 26, 26)
            draw_rounded_panel(badge_rect, WHITE, radius=13)
            draw_text(self.key_hint, FONT_TINY, BLACK, badge_rect.center)

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class TextBox:
    def __init__(self, rect, placeholder="", allow_negative=True, allow_float=False):
        self.rect = pygame.Rect(rect)
        self.text = ""
        self.placeholder = placeholder
        self.active = False
        self.allow_negative = allow_negative
        self.allow_float = allow_float

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                pass
            elif event.unicode.isdigit():
                self.text += event.unicode
            elif event.unicode == "-" and self.allow_negative and self.text == "":
                self.text += event.unicode
            elif event.unicode == "." and self.allow_float and "." not in self.text:
                self.text += event.unicode

    def draw(self):
        color = WHITE if self.active else PANEL_LIGHT
        draw_rounded_panel(self.rect, PANEL_LIGHT, radius=10, border=color, border_width=2)
        display = self.text if self.text else self.placeholder
        col = WHITE if self.text else TEXT_DIM
        surf = FONT_MED.render(display, True, col)
        r = surf.get_rect(midleft=(self.rect.x + 16, self.rect.centery))
        screen.blit(surf, r)

    def value_int(self, default=0):
        try:
            return int(self.text)
        except ValueError:
            return default

    def value_float(self, default=1.0):
        try:
            return float(self.text)
        except ValueError:
            return default


STATE_DIFFICULTY = "difficulty"
STATE_CUSTOM_RANGE = "custom_range"
STATE_LENGTH = "length"
STATE_SPEED = "speed"
STATE_CUSTOM_SPEED = "custom_speed"
STATE_COUNTDOWN = "countdown"
STATE_PLAYING = "playing"
STATE_ANSWER = "answer"
STATE_RESULT = "result"

state = STATE_DIFFICULTY

difficulty_ranges = {
    "Easy": (0, 10),
    "Medium": (10, 20),
    "Hard": (20, 30),
    "Expert": (30, 40),
}
selected_range = None
selected_length = 10
selected_delay = 1.0

digits = []
digit_index = 0
digit_timer = 0.0
countdown_value = 3
countdown_timer = 0.0

total = 0
was_correct = False

custom_from_box = TextBox((0, 0, 200, 56), placeholder="From")
custom_to_box = TextBox((0, 0, 200, 56), placeholder="To")
custom_speed_box = TextBox((0, 0, 220, 56), placeholder="Seconds", allow_float=True)
answer_box = TextBox((0, 0, 320, 70), placeholder="Your answer")

NUMBER_KEYS = {
    pygame.K_1: 0, pygame.K_KP1: 0,
    pygame.K_2: 1, pygame.K_KP2: 1,
    pygame.K_3: 2, pygame.K_KP3: 2,
    pygame.K_4: 3, pygame.K_KP4: 3,
    pygame.K_5: 4, pygame.K_KP5: 4,
    pygame.K_6: 5, pygame.K_KP6: 5,
    pygame.K_7: 6, pygame.K_KP7: 6,
    pygame.K_8: 7, pygame.K_KP8: 7,
    pygame.K_9: 8, pygame.K_KP9: 8,
}


def layout_grid_buttons(labels, subs=None, cols=2, top=220, width=360, height=90, gap_x=40, gap_y=26, key_hints=True):
    buttons = []
    total_w = cols * width + (cols - 1) * gap_x
    start_x = WIDTH // 2 - total_w // 2
    for i, label in enumerate(labels):
        row = i // cols
        col = i % cols
        x = start_x + col * (width + gap_x)
        y = top + row * (height + gap_y)
        sub = subs[i] if subs else None
        hint = str(i + 1) if key_hints else None
        buttons.append(Button((x, y, width, height), label, sub, key_hint=hint))
    return buttons


difficulty_buttons = layout_grid_buttons(
    ["Easy", "Medium", "Hard", "Expert", "Custom"],
    ["0 - 10", "10 - 20", "20 - 30", "30 - 40", "Pick your range"],
    cols=2, top=190, width=360, height=90
)

length_buttons = layout_grid_buttons(
    ["10", "20", "30", "40", "50"],
    ["digits"] * 5,
    cols=3, top=200, width=230, height=90, gap_x=30, gap_y=24
)

speed_buttons = layout_grid_buttons(
    ["Slow", "Fast", "Faster", "Impossible", "Custom"],
    ["2.0 sec", "1.5 sec", "1.0 sec", "0.5 sec", "Set seconds"],
    cols=2, top=190, width=360, height=90
)

continue_button = Button((WIDTH // 2 - 110, 420, 220, 64), "Continue", accent=True)
back_button = Button((30, 30, 110, 46), "Back")
submit_button = Button((WIDTH // 2 - 110, 420, 220, 64), "Submit", accent=True)
play_again_button = Button((WIDTH // 2 - 260, 460, 220, 64), "Play Again", accent=True)
quit_button = Button((WIDTH - 140, 30, 110, 46), "Quit", danger=True)


def start_length_selection(rng):
    global selected_range, state
    selected_range = rng
    state = STATE_LENGTH


def start_speed_selection(length):
    global selected_length, state
    selected_length = length
    state = STATE_SPEED


def start_countdown(delay):
    global selected_delay, state, countdown_value, countdown_timer
    selected_delay = delay
    countdown_value = 3
    countdown_timer = 0.0
    state = STATE_COUNTDOWN


def begin_game():
    global digits, digit_index, digit_timer, state, total
    lo, hi = selected_range
    digits = [random.randint(lo, hi) for _ in range(selected_length)]
    total = sum(digits)
    digit_index = 0
    digit_timer = 0.0
    state = STATE_PLAYING
    SND_GO.play()


def go_to_answer():
    global state
    answer_box.text = ""
    answer_box.active = True
    state = STATE_ANSWER


def submit_answer():
    global was_correct, state
    if answer_box.text == "":
        return
    ans = answer_box.value_int(default=0)
    was_correct = ans == total
    (SND_CORRECT if was_correct else SND_WRONG).play()
    state = STATE_RESULT


def reset_to_start():
    global state
    state = STATE_DIFFICULTY


def select_difficulty(index):
    if index >= len(difficulty_buttons):
        return
    SND_CLICK.play()
    label = difficulty_buttons[index].label
    if label == "Custom":
        custom_from_box.text = ""
        custom_to_box.text = ""
        global state
        state = STATE_CUSTOM_RANGE
    else:
        start_length_selection(difficulty_ranges[label])


def select_length(index):
    if index >= len(length_buttons):
        return
    SND_CLICK.play()
    start_speed_selection(int(length_buttons[index].label))


def select_speed(index):
    if index >= len(speed_buttons):
        return
    SND_CLICK.play()
    label = speed_buttons[index].label
    if label == "Custom":
        custom_speed_box.text = ""
        global state
        state = STATE_CUSTOM_SPEED
    else:
        preset = {"Slow": 2.0, "Fast": 1.5, "Faster": 1.0, "Impossible": 0.5}
        start_countdown(preset[label])


running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if state == STATE_CUSTOM_RANGE:
            custom_from_box.handle_event(event)
            custom_to_box.handle_event(event)
        if state == STATE_CUSTOM_SPEED:
            custom_speed_box.handle_event(event)
        if state == STATE_ANSWER:
            answer_box.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                submit_answer()

        if event.type == pygame.KEYDOWN and event.key in NUMBER_KEYS:
            idx = NUMBER_KEYS[event.key]
            if state == STATE_DIFFICULTY:
                select_difficulty(idx)
            elif state == STATE_LENGTH:
                select_length(idx)
            elif state == STATE_SPEED:
                select_speed(idx)

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos

            if quit_button.clicked(pos):
                running = False
                continue

            if state == STATE_DIFFICULTY:
                for i, b in enumerate(difficulty_buttons):
                    if b.clicked(pos):
                        select_difficulty(i)

            elif state == STATE_CUSTOM_RANGE:
                if back_button.clicked(pos):
                    SND_CLICK.play()
                    state = STATE_DIFFICULTY
                if continue_button.clicked(pos):
                    lo = custom_from_box.value_int(0)
                    hi = custom_to_box.value_int(10)
                    if hi < lo:
                        lo, hi = hi, lo
                    SND_CLICK.play()
                    start_length_selection((lo, hi))

            elif state == STATE_LENGTH:
                if back_button.clicked(pos):
                    SND_CLICK.play()
                    state = STATE_DIFFICULTY
                for i, b in enumerate(length_buttons):
                    if b.clicked(pos):
                        select_length(i)

            elif state == STATE_SPEED:
                if back_button.clicked(pos):
                    SND_CLICK.play()
                    state = STATE_LENGTH
                for i, b in enumerate(speed_buttons):
                    if b.clicked(pos):
                        select_speed(i)

            elif state == STATE_CUSTOM_SPEED:
                if back_button.clicked(pos):
                    SND_CLICK.play()
                    state = STATE_SPEED
                if continue_button.clicked(pos):
                    val = custom_speed_box.value_float(1.0)
                    if val <= 0:
                        val = 0.1
                    SND_CLICK.play()
                    start_countdown(val)

            elif state == STATE_ANSWER:
                if submit_button.clicked(pos):
                    submit_answer()

            elif state == STATE_RESULT:
                if play_again_button.clicked(pos):
                    SND_CLICK.play()
                    reset_to_start()

    draw_background()

    if state == STATE_DIFFICULTY:
        draw_text("Mental Math Flash", FONT_BIG, WHITE, (WIDTH // 2, 100))
        draw_text("Choose your difficulty", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 150))
        for b in difficulty_buttons:
            b.draw()

    elif state == STATE_CUSTOM_RANGE:
        back_button.draw()
        draw_text("Custom Range", FONT_BIG, WHITE, (WIDTH // 2, 130))
        draw_text("Enter the minimum and maximum number", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 180))
        custom_from_box.rect.center = (WIDTH // 2 - 120, 280)
        custom_to_box.rect.center = (WIDTH // 2 + 120, 280)
        custom_from_box.draw()
        custom_to_box.draw()
        continue_button.draw()

    elif state == STATE_LENGTH:
        back_button.draw()
        draw_text("How Many Numbers?", FONT_BIG, WHITE, (WIDTH // 2, 100))
        lo, hi = selected_range
        draw_text(f"Range selected: {lo} to {hi}", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 150))
        for b in length_buttons:
            b.draw()

    elif state == STATE_SPEED:
        back_button.draw()
        draw_text("Choose Speed", FONT_BIG, WHITE, (WIDTH // 2, 100))
        draw_text(f"{selected_length} numbers per round", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 150))
        for b in speed_buttons:
            b.draw()

    elif state == STATE_CUSTOM_SPEED:
        back_button.draw()
        draw_text("Custom Speed", FONT_BIG, WHITE, (WIDTH // 2, 150))
        draw_text("Seconds between each number", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 200))
        custom_speed_box.rect.center = (WIDTH // 2, 300)
        custom_speed_box.draw()
        continue_button.draw()

    elif state == STATE_COUNTDOWN:
        countdown_timer += dt
        if countdown_timer >= 1.0:
            countdown_timer = 0.0
            countdown_value -= 1
            if countdown_value > 0:
                SND_COUNTDOWN.play()
            elif countdown_value == 0:
                pass
            else:
                begin_game()
        label = str(countdown_value) if countdown_value > 0 else "Go!"
        draw_text("Get Ready", FONT_MED, TEXT_DIM, (WIDTH // 2, 200))
        draw_text(label, FONT_HUGE, WHITE, (WIDTH // 2, HEIGHT // 2))

    elif state == STATE_PLAYING:
        panel_rect = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 130, 440, 260)
        draw_rounded_panel(panel_rect, PANEL, radius=28, border=WHITE, border_width=2)
        draw_text(f"{digit_index + 1} / {len(digits)}", FONT_SMALL, TEXT_DIM, (WIDTH // 2, panel_rect.top - 30))
        draw_text(str(digits[digit_index]), FONT_HUGE, WHITE, panel_rect.center)

        digit_timer += dt
        if digit_timer >= selected_delay:
            digit_timer = 0.0
            SND_TICK.play()
            digit_index += 1
            if digit_index >= len(digits):
                go_to_answer()

    elif state == STATE_ANSWER:
        draw_text("What's the total?", FONT_BIG, WHITE, (WIDTH // 2, 180))
        draw_text(f"You saw {selected_length} numbers", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 230))
        answer_box.rect.center = (WIDTH // 2, 320)
        answer_box.draw()
        submit_button.draw()

    elif state == STATE_RESULT:
        icon_color = SUCCESS if was_correct else DANGER
        headline = "Correct!" if was_correct else "Not Quite"
        draw_text(headline, FONT_BIG, icon_color, (WIDTH // 2, 180))
        draw_text(f"The answer was {total}", FONT_MED, WHITE, (WIDTH // 2, 250))
        if not was_correct:
            draw_text(f"You answered {answer_box.text}", FONT_SMALL, TEXT_DIM, (WIDTH // 2, 300))
        play_again_button.draw()

    quit_button.draw()

    pygame.display.flip()

pygame.quit()
sys.exit()