"""Tactile dossier presentation. All controls and labels remain live widgets."""
import json
from pathlib import Path
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk

from .backend import Session, load_settings, save_settings, tail_log, installation_present
from .desktop import ICONS, install_icon, load_icon

ASSETS = Path(__file__).resolve().parent / 'assets'
INK = '#15202d'
RED = '#8e201e'
IVORY = '#eee7d6'
PALE = '#c1c9cc'
MONO = 'DejaVu Sans Mono'
SERIF = 'DejaVu Serif'
INSTALLATION_STATES = {
    'missing': ('Import required', '#485766', 'download'),
    'pending': ('Waiting for check…', '#765524', 'clock'),
    'checking': ('Checking files…', '#765524', 'clock'),
    'importing': ('Importing game…', '#765524', 'clock'),
    'ready': ('Ready to play', '#3e633e', 'check'),
    'running': ('Game running', '#485766', 'play'),
    'attention': ('Needs attention', RED, 'alert'),
    'import_failed': ('Import failed', RED, 'alert'),
}


class Artwork:
    def __init__(self):
        self.images = {}

    def get(self, name):
        if name not in self.images:
            with Image.open(ASSETS / name) as source:
                image = source.convert('RGBA')
            if image.getextrema()[3][0] == 0:
                image = image.crop(image.getbbox())
            self.images[name] = image
        return self.images[name]

    def paste(self, canvas, name, box, *, angle=0, contain=False, opacity=1):
        x, y, w, h = map(round, box)
        source = self.get(name)
        if contain:
            # Fit the rotated silhouette as well as the image itself. Expanding
            # a fitted photo afterwards can push its border out of the viewport.
            if angle:
                source = source.rotate(angle, Image.Resampling.BICUBIC, expand=True)
            image = ImageOps.contain(source, (w, h), Image.Resampling.LANCZOS)
        else:
            image = source.resize((w, h), Image.Resampling.LANCZOS)
        if opacity != 1:
            image.putalpha(image.getchannel('A').point(lambda a: round(a * opacity)))
        if angle and not contain:
            image = image.rotate(angle, Image.Resampling.BICUBIC, expand=True)
        canvas.alpha_composite(image, (round(x + (w - image.width) / 2),
                                       round(y + (h - image.height) / 2)))


class ArtButton(tk.Canvas):
    """Focusable keyboard/mouse control, painted over its actual paper surface."""
    def __init__(self, view, key, label, command, box, *, kind='paper',
                 size=23, detail='', selected=False, enabled=True, inset=18):
        super().__init__(view.canvas, highlightthickness=0, bd=0,
                         takefocus=enabled, cursor='hand2' if enabled else '',
                         background='#0d1820')
        self.view = view
        self.hover, self.pressed = False, False
        self.bind('<Enter>', lambda e: self.feedback(True))
        self.bind('<Leave>', lambda e: self.feedback(False))
        self.bind('<FocusIn>', lambda e: self.draw())
        self.bind('<FocusOut>', lambda e: self.draw())
        self.bind('<ButtonPress-1>', self.press)
        self.bind('<ButtonRelease-1>', self.release)
        self.bind('<Return>', self.activate)
        self.bind('<space>', self.activate)
        self.update_control(key, label, command, box, kind=kind, size=size,
                            detail=detail, selected=selected, enabled=enabled, inset=inset)

    def update_control(self, key, label, command, box, *, kind='paper',
                       size=23, detail='', selected=False, enabled=True, inset=18):
        self.key, self.label, self.command = key, label, command
        self.kind, self.size, self.detail, self.selected = kind, size, detail, selected
        self.enabled, self.inset = enabled, inset
        self.configure(takefocus=enabled, cursor='hand2' if enabled else '')
        x, y, w, h = self.view.box(box)
        surface = self.view.background.crop((x, y, x + w, y + h)).convert('RGB')
        self.surface = ImageTk.PhotoImage(surface)
        self.highlight = ImageTk.PhotoImage(Image.blend(
            surface, Image.new('RGB', surface.size, '#526779' if kind in ('nav', 'footer', 'play', 'primary') else RED), .09))
        self.place(x=x, y=y, width=w, height=h)
        self.w, self.h = w, h
        self.draw()

    def feedback(self, hover):
        self.hover = hover
        self.pressed = False
        self.draw()

    def press(self, event):
        if self.enabled:
            self.focus_set()
            self.pressed = True
            self.draw()

    def release(self, event):
        pressed = self.pressed
        self.pressed = False
        self.draw()
        if pressed and 0 <= event.x < self.w and 0 <= event.y < self.h:
            self.invoke()

    def activate(self, event=None):
        self.invoke()
        return 'break'

    def invoke(self):
        if self.enabled:
            return self.command()

    def draw(self):
        self.delete('all')
        self.create_image(0, 0, image=self.surface, anchor='nw')
        s, w, h = self.view.scale, self.w, self.h
        dark = self.kind in ('nav', 'footer', 'play', 'primary')
        color = IVORY if dark else INK
        active = self.enabled and (self.hover or self.pressed)
        if self.selected or active:
            self.create_image(0, 0, image=self.highlight, anchor='nw')
        if self.kind in ('outline', 'primary', 'filter', 'icon'):
            if self.kind == 'primary':
                self.create_rectangle(1, 1, w - 2, h - 2, fill=RED, outline=RED)
            else:
                self.create_rectangle(1, 1, w - 2, h - 2,
                                      outline=RED if self.selected else '#8f9290',
                                      width=2 if self.selected else 1)
        if self.kind == 'nav' and self.selected:
            self.create_rectangle(10 * s, h - 3 * s, w - 10 * s, h,
                                  fill='#b22a26', outline='')
        if self.kind == 'row':
            self.create_line(0, h - 1, w, h - 1, fill='#96958c')
            if self.selected:
                self.create_rectangle(0, 6 * s, 3 * s, h - 6 * s, fill=RED, outline='')
        if not self.enabled:
            color = '#a0a4a1' if dark else '#747974'
        if self.kind == 'play':
            label = 'P L A Y' if self.label == 'Play' else self.label
            self.create_text(w / 2 + (26 * s if self.label == 'Play' else 0), h / 2, text=label, fill=color,
                             font=self.view.font(self.size))
            if self.label == 'Play':
                x = w / 2 - 112 * s
                self.create_polygon(x, h / 2 - 17 * s, x, h / 2 + 17 * s,
                                    x + 29 * s, h / 2, fill=color, outline='')
        elif self.kind == 'icon':
            self.create_text(w / 2, h - 14 * s, text=self.label,
                             font=self.view.font(self.size), fill=color)
        elif self.kind == 'row':
            self.create_text(self.inset * s, h * .32, text=self.label, anchor='w',
                             font=self.view.font(self.size), fill=color)
            self.create_text(self.inset * s, h * .64, text=self.detail, anchor='w',
                             font=self.view.font(16), fill=color,
                             width=max(1, w - (self.inset + 16) * s))
        else:
            left = self.kind in ('paper', 'footer')
            inset_scale = self.view.scale_x if self.kind == 'footer' else s
            self.create_text(self.inset * inset_scale if left else w / 2, h / 2,
                             text=self.label, anchor='w' if left else 'center',
                             font=self.view.font(self.size), fill=color)
            if self.kind == 'paper':
                self.create_text(w - 25 * s, h / 2, text='›',
                                 font=self.view.font(30), fill=color)
        if self.focus_get() == self:
            self.create_rectangle(3, 3, w - 4, h - 4,
                                  outline=IVORY if dark else RED, width=2, dash=(4, 3))


class Launcher:
    def __init__(self, window, binary, dirs):
        self.window = window
        self.session = Session(binary, dirs)
        self.art = Artwork()
        self.catalog = json.loads((ASSETS.parent / 'achievements.json').read_text())['achievements']
        self.page, self.category, self.offset, self.selected = 'overview', 'all', 0, 0
        self.controls, self.entries = {}, []
        self.button_pool = {}
        self.scale = self.scale_x = 1
        self.body_origin = (0, 48)
        self.viewport = (1440, 810)
        self.scene_key, self.scene_background = None, None
        self.resize_job = None
        self.wheel_job, self.wheel_remainder = None, 0
        self.launcher_fullscreen = False
        self.windowed_geometry = None
        self.closing, self.stop_deadline = False, None
        self.log_window, self.log_text = None, None
        self.log_snapshot = None
        self.settings_error = None
        try:
            self.preferences = load_settings(dirs)
        except (OSError, ValueError, TypeError, OverflowError) as error:
            self.preferences = {'Fullscreen': False, 'TouchMode': False, 'Volume': 1.0}
            self.settings_error = str(error)
        self.fullscreen = tk.BooleanVar(value=self.preferences['Fullscreen'])
        self.touch = tk.BooleanVar(value=self.preferences['TouchMode'])
        self.volume = tk.IntVar(value=round(self.preferences['Volume'] * 100))
        try:
            self.desktop_icon = load_icon(dirs)
        except (OSError, ValueError) as error:
            self.desktop_icon = ICONS[0][0]
            self.session.transcript.append(f'Desktop icon preference: {error}\n')
        window.title('Resident Evil · Degeneration')
        self.update_window_icon()
        window.geometry(f'{min(1440, window.winfo_screenwidth())}x{min(810, window.winfo_screenheight())}')
        window.minsize(1000, 620)
        window.configure(bg='#0b151d')
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.canvas = tk.Canvas(window, highlightthickness=0, bd=0, bg='#0b151d')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', self.schedule_render)
        window.bind('<Escape>', self.escape)
        window.bind('<Alt-Left>', lambda e: self.navigate('overview'))
        window.bind('<Control-l>', lambda e: self.show_logs())
        window.bind('<Left>', lambda e: self.move_selection(-1))
        window.bind('<Right>', lambda e: self.move_selection(1))
        window.bind('<Up>', lambda e: self.move_selection(-1))
        window.bind('<Down>', lambda e: self.move_selection(1))
        window.bind('<Prior>', lambda e: self.paginate(-1))
        window.bind('<Next>', lambda e: self.paginate(1))
        window.bind('<F11>', self.toggle_fullscreen)
        window.bind('<MouseWheel>', self.scroll_achievements)
        window.bind('<Button-4>', self.scroll_achievements)
        window.bind('<Button-5>', self.scroll_achievements)
        self.tick_job = window.after(100, self.tick)
        if installation_present(dirs):
            window.after(150, self.verify)

    def font(self, size, family=SERIF, weight='normal'):
        return family, -max(10, round(size * self.scale)), weight

    def box(self, bounds):
        x, y, w, h = bounds
        left, top = self.point(x, y)
        # Pick one coordinate space for the whole element, including paper
        # edges that extend slightly past the body's nominal bottom boundary.
        sx = self.scale if 48 <= y <= 762 else self.scale_x
        return left, top, max(1, round(w * sx)), max(1, round(h * self.scale))

    def point(self, x, y):
        # Only the desk and chrome span the viewport. Keep the dossier and its
        # controls on one proportional, centered surface when the window resizes.
        if y < 48:
            py = y * self.scale
        elif y > 762:
            py = self.viewport[1] - (810 - y) * self.scale
        else:
            return (round(self.body_origin[0] + x * self.scale),
                    round(self.body_origin[1] + (y - 48) * self.scale))
        return round(x * self.scale_x), round(py)

    def text(self, x, y, label, size=20, *, family=SERIF, color=INK, width=None, anchor='nw', weight='normal'):
        px, py, _, _ = self.box((x, y, 1, 1))
        return self.canvas.create_text(px, py, text=label, fill=color, anchor=anchor,
                                       font=self.font(size, family, weight),
                                       width=round(width * (self.scale if 48 <= y <= 762 else self.scale_x)) if width else 0)

    def line(self, x1, y1, x2, y2, color='#96958c'):
        x, y, _, _ = self.box((x1, y1, 1, 1))
        xx, yy, _, _ = self.box((x2, y2, 1, 1))
        self.canvas.create_line(x, y, xx, yy, fill=color)

    def button(self, key, label, command, box, *, slot=None, **options):
        slot = slot or key
        button = self.button_pool.get(slot)
        if button is None:
            button = ArtButton(self, key, label, command, box, **options)
            self.button_pool[slot] = button
        else:
            button.update_control(key, label, command, box, **options)
        self.used_buttons.add(slot)
        self.controls[key] = button
        return button

    def schedule_render(self, event=None):
        if self.resize_job:
            self.window.after_cancel(self.resize_job)
        self.resize_job = self.window.after(60, self.render)

    def scene(self):
        key = (self.page, self.viewport)
        if self.scene_key != key:
            self.scene_background = self.static_scene()
            self.scene_key = key
        image = self.scene_background.copy()
        if self.page == 'achievements':
            selected = self.filtered()[self.selected]
            self.paste(image, Path(selected['asset']).name, (968, 119, 285, 170))
            for row, entry in enumerate(self.filtered()[self.offset:self.offset + 4]):
                self.paste(image, Path(entry['asset']).name, (76, 300 + row * 96, 116, 75))
        return image

    def paste(self, image, name, box, **options):
        material = name in ('dossier-folder.png', 'detail-paper.png', 'paper.png',
                            'case-paper.png', 'play-plate.png')
        # Borders are part of each photograph: preserve the complete artwork.
        options.setdefault('contain', not material)
        self.art.paste(image, name, self.box(box), **options)

    def static_scene(self):
        image = ImageOps.fit(self.art.get('desk-background.png'), self.viewport, Image.Resampling.LANCZOS)
        self.paste(image, 'airport-blueprint.png', (630, 30, 830, 730), angle=-5, opacity=.47)
        if self.page == 'overview':
            self.paste(image, 'dossier-folder.png', (8, 60, 734, 714))
            self.paste(image, 'quarantine-stamp.png', (466, 109, 208, 84), angle=4)
            self.paste(image, 'title-logo.png', (94, 216, 532, 182), contain=True)
            self.paste(image, 'play-plate.png', (87, 426, 554, 80))
            for name, y in [('achievements', 518), ('settings', 576), ('import', 634)]:
                self.paste(image, f'icon-{name}.png', (100, y, 49, 49), contain=True)
            self.paste(image, 'photo-airport.png', (740, 117, 676, 454), angle=-7)
            self.paste(image, 'paperclip.png', (775, 103, 48, 100), angle=-14, contain=True)
            self.paste(image, 'photo-protagonists.png', (972, 442, 415, 234), angle=-8)
            self.paste(image, 'paper.png', (792, 690, 430, 62))
        else:
            self.paste(image, 'case-paper.png', (25, 71, 817, 677), angle=.6)
            self.paste(image, 'case-paper.png', (18, 76, 824, 666))
            self.paste(image, 'airport-stamp.png', (597, 98, 191, 89), angle=4, contain=True)
            if self.page == 'achievements':
                self.paste(image, 'detail-paper.png', (866, 72, 528, 397))
                self.paste(image, 'photo-airport.png', (868, 481, 529, 259), angle=3)
            elif self.page == 'settings':
                self.paste(image, 'detail-paper.png', (866, 72, 528, 666))
                self.paste(image, 'icon-settings.png', (1285, 120, 70, 70), contain=True)
                for index, (key, label) in enumerate(ICONS):
                    self.paste(image, f'desktop-icons/{key}.png',
                               (939 + index * 149, 534, 90, 90), contain=True)
            else:
                self.paste(image, 'photo-airport.png', (868, 108, 529, 356), angle=-4)
                self.paste(image, 'detail-paper.png', (866, 489, 528, 249))
        draw = ImageDraw.Draw(image)
        w, h = self.viewport
        top, bottom = round(48 * self.scale), round(h - 48 * self.scale)
        draw.rectangle((0, 0, w, top), fill=(5, 14, 21, 255))
        draw.rectangle((0, bottom, w, h), fill=(5, 14, 21, 255))
        draw.line((0, top, w, top), fill='#41515b')
        draw.line((0, bottom, w, bottom), fill='#41515b')
        self.paste(image, 'icon-logs.png', (40, 773, 20, 24), contain=True)
        return image

    def render(self):
        if self.resize_job:
            self.window.after_cancel(self.resize_job)
        self.resize_job = None
        if self.wheel_job:
            self.window.after_cancel(self.wheel_job)
            self.wheel_job = None
        focused = next((key for key, value in self.controls.items() if value == self.window.focus_get()), None)
        for widget in self.entries:
            widget.destroy()
        self.controls, self.entries = {}, []
        self.used_buttons = set()
        self.canvas.delete('all')
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.viewport = w, h
        self.scale = min(w / 1440, h / 810)
        self.scale_x = w / 1440
        self.body_origin = ((w - 1440 * self.scale) / 2,
                            48 * self.scale + (h - 810 * self.scale) / 2)
        self.background = self.scene()
        self.photo = ImageTk.PhotoImage(self.background)
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.text(38, 13, 'r e d e g p c', 21, color=IVORY)
        for name, label, x, width in [('overview', 'Overview', 209, 151),
                                       ('achievements', 'Achievements', 373, 183),
                                       ('settings', 'Settings & controls', 568, 243),
                                       ('installation', 'Installation', 825, 170)]:
            self.line(x - 7, 10, x - 7, 37, '#41515b')
            self.button('nav-' + name, label, lambda p=name: self.navigate(p),
                        (x, 0, width, 48), kind='nav', size=19, selected=self.page == name)
        self.button('launcher-fullscreen', '↙' if self.launcher_fullscreen else '⛶', self.toggle_fullscreen,
                    (1277, 0, 49, 48), kind='nav', size=24)
        self.button('minimize', '−', self.minimize, (1329, 0, 49, 48), kind='nav', size=26)
        self.button('close', '×', self.close, (1381, 0, 49, 48), kind='nav', size=27)
        getattr(self, 'draw_' + self.page)()
        self.button('logs', 'View logs', self.show_logs, (39, 768, 150, 35), kind='footer', size=18, inset=34)
        self.status_item = self.text(1410, 786, self.session.status, 15, family=MONO, color=PALE, anchor='e', width=1000)
        for slot in list(self.button_pool):
            if slot not in self.used_buttons:
                self.button_pool.pop(slot).destroy()
        if focused in self.controls and self.controls[focused].enabled:
            self.controls[focused].focus_set()

    def draw_overview(self):
        self.text(110, 155, 'H A R V A R D V I L L E  I N C I D E N T', 14, family=MONO)
        self.line(110, 180, 385, 180)
        busy = self.session.child is not None
        running = self.session.operation == 'run'
        self.button('play', 'Game running' if running else 'Play', self.play,
                    (87, 426, 554, 80), kind='play', size=38,
                    enabled=self.session.verified and not busy)
        for key, label, y, page in [('achievements', 'Achievements', 514, 'achievements'),
                                   ('settings', 'Settings & controls', 572, 'settings'),
                                   ('import', 'Import game', 630, 'installation')]:
            self.button(key, label, lambda p=page: self.navigate(p),
                        (84, y, 558, 58), size=26, inset=91)
            self.line(85, y + 58, 641, y + 58)
        state, color, _ = INSTALLATION_STATES[self.session.installation_state]
        self.text(100, 705, '●', 20, color=color)
        installed = self.session.verified and self.session.operation not in ('check', 'import')
        self.text(129, 708, 'Game installed' if installed else state, 16, family=MONO)
        self.draw_installation_badge()

    def draw_installation_badge(self):
        label, color, symbol = INSTALLATION_STATES[self.session.installation_state]
        # Live vector marks stay crisp at every dossier scale and do not rely
        # on a font's coverage of status glyphs.
        x, y = self.point(824, 721)
        s = self.scale
        stroke = max(1, round(2 * s))
        self.canvas.create_line(*self.point(805, 703), *self.point(805, 740),
                                fill=color, width=max(2, round(3 * s)))
        self.canvas.create_oval(x - 12 * s, y - 12 * s, x + 12 * s, y + 12 * s,
                                outline=color, width=stroke, tags='installation-badge')

        def mark(points):
            coordinates = [value for px, py in points for value in (x + px * s, y + py * s)]
            self.canvas.create_line(*coordinates, fill=color, width=stroke,
                                    capstyle='round', joinstyle='round', tags='installation-badge')

        if symbol == 'check':
            mark([(-6, 0), (-2, 4), (6, -5)])
        elif symbol == 'clock':
            mark([(0, -7), (0, 0), (5, 3)])
        elif symbol == 'alert':
            mark([(0, -6), (0, 1)])
            mark([(0, 5), (0, 6)])
        elif symbol == 'play':
            self.canvas.create_polygon(x - 3 * s, y - 6 * s, x + 6 * s, y,
                                       x - 3 * s, y + 6 * s, fill=color,
                                       tags='installation-badge')
        else:
            mark([(0, -6), (0, 5)])
            mark([(-5, 0), (0, 5), (5, 0)])
        heading = self.text(850, 699, 'INSTALLATION', 12, family=MONO, color='#48505a')
        status = self.text(850, 718, label, 22, color=color, weight='bold')
        self.canvas.addtag_withtag('installation-badge', heading)
        self.canvas.addtag_withtag('installation-badge', status)

    def filtered(self):
        return [a for a in self.catalog if self.category == 'all' or a['category'] == self.category]

    def draw_achievements(self):
        entries = self.filtered()
        selected = entries[self.selected]
        self.text(66, 108, 'H A R V A R D V I L L E  I N C I D E N T', 13, family=MONO)
        self.text(64, 146, 'Achievements', 61)
        self.text(68, 220, 'Your survival record.', 23)
        self.text(790, 227, f'{len(self.catalog)} goals', 17, family=MONO, anchor='ne')
        for category, label, x, width in [('all', 'All', 67, 64), ('story', 'Story', 141, 95),
                                           ('weapons', 'Weapons', 246, 126),
                                           ('challenge', 'Challenge', 382, 137),
                                           ('difficulty', 'Difficulty', 529, 131),
                                           ('completion', 'Completion', 670, 124)]:
            self.button('filter-' + category, label, lambda c=category: self.filter_category(c),
                        (x, 259, width, 29), kind='filter', size=14, selected=self.category == category)
        for row, entry in enumerate(entries[self.offset:self.offset + 4]):
            index = self.offset + row
            self.button('achievement-' + entry['id'], entry['title'], lambda i=index: self.select(i),
                        (65, 296 + row * 96, 728, 96), kind='row', size=27, inset=155,
                        detail=entry['description'], selected=index == self.selected,
                        slot=f'achievement-row-{row}')
        self.text(69, 705, f'{self.offset + 1}–{min(self.offset + 4, len(entries))} of {len(entries)}', 14, family=MONO)
        self.button('previous', '‹ Previous', lambda: self.paginate(-1), (513, 697, 128, 31),
                    kind='outline', size=15, enabled=self.offset > 0)
        self.button('next', 'Next ›', lambda: self.paginate(1), (652, 697, 141, 31),
                    kind='outline', size=15, enabled=self.offset + 4 < len(entries))
        self.text(906, 299, selected['title'], 29, width=438)
        self.line(907, 344, 1345, 344)
        self.text(907, 356, 'GOAL  /  NOT TRACKED', 14, family=MONO, color=RED)
        self.text(907, 384, selected['description'], 18, width=430)
        self.text(907, 427, 'Gameplay tracking is not available yet.', 12, family=MONO, width=440)

    def draw_settings(self):
        self.text(66, 108, 'H A R V A R D V I L L E  I N C I D E N T', 13, family=MONO)
        self.text(64, 155, 'Settings & controls', 46)
        self.text(68, 219, 'Prepare for deployment.', 23)
        self.line(68, 265, 791, 265)
        self.text(71, 298, 'Display', 27)
        self.text(71, 338, 'Game display on the next launch.', 16)
        self.button('windowed', 'Windowed', lambda: self.set_toggle(self.fullscreen, False),
                    (445, 300, 158, 47), kind='outline', size=19, selected=not self.fullscreen.get())
        self.button('fullscreen', 'Fullscreen', lambda: self.set_toggle(self.fullscreen, True),
                    (616, 300, 173, 47), kind='outline', size=19, selected=self.fullscreen.get())
        self.line(68, 377, 791, 377)
        self.text(71, 406, 'Input', 27)
        self.text(71, 449, 'Desktop hides the original touch controls.', 16)
        self.button('desktop', 'Desktop', lambda: self.set_toggle(self.touch, False),
                    (445, 408, 158, 47), kind='outline', size=19, selected=not self.touch.get())
        self.button('touch', 'Touch', lambda: self.set_toggle(self.touch, True),
                    (616, 408, 173, 47), kind='outline', size=19, selected=self.touch.get())
        self.line(68, 484, 791, 484)
        self.text(71, 517, 'Master volume', 27)
        self.volume_item = self.text(785, 528, f'{self.volume.get()}%', 17, family=MONO, anchor='ne')
        slider = tk.Scale(self.canvas, from_=0, to=100, orient='horizontal',
                          variable=self.volume, showvalue=False, bd=0,
                          highlightthickness=1, highlightbackground='#92978f',
                          background='#c9c7bd', troughcolor='#939a98',
                          activebackground=RED, command=self.volume_changed)
        self.place_entry(slider, (445, 560, 344, 31))
        self.text(71, 562, '0 = muted · 100 = full', 16)
        self.button('save-settings', 'Save settings', self.save_preferences,
                    (71, 642, 235, 51), kind='primary', size=22,
                    enabled=self.session.child is None and self.settings_error is None)
        if not self.settings_error:
            self.text(327, 653, 'Applied on your next launch.', 16, width=450)
        if self.settings_error:
            self.text(71, 600, 'Settings could not be read. Reset defaults to repair them.', 15, color=RED, width=700)
            self.button('reset-settings', 'Reset defaults', self.reset_preferences,
                        (552, 642, 237, 51), kind='outline', size=20, enabled=self.session.child is None)
        self.text(978, 125, 'FIELD CONTROLS', 17, family=MONO)
        for index, (key, action) in enumerate([
                ('WASD / arrows', 'Move'), ('Right mouse', 'Hold to aim'),
                ('Left mouse', 'Fire / select'), ('R', 'Reload'), ('E', 'Interact'),
                ('Tab', 'Inventory'), ('Escape', 'Pause / back'), ('Space', 'Shake off a grab'),
                ('F11', 'Toggle fullscreen')]):
            y = 179 + index * 29
            self.text(911, y, key, 15, family=MONO)
            self.text(1165, y, action, 17, width=192)
        self.text(911, 450, 'Touch mode keeps the original pointer input.', 14, width=420)
        self.line(911, 480, 1357, 480)
        self.text(911, 491, 'Desktop icon', 25)
        for index, (key, label) in enumerate(ICONS):
            self.button('icon-' + key, label, lambda k=key: self.select_desktop_icon(k),
                        (917 + index * 149, 528, 134, 119), kind='icon', size=16,
                        selected=self.desktop_icon == key)
        self.text(911, 654, 'Updates your desktop and applications menu.', 13, width=440)
        self.button('apply-desktop-icon', 'Apply desktop icon', self.apply_desktop_icon,
                    (917, 681, 432, 38), kind='outline', size=19)

    def draw_installation(self):
        busy = self.session.child is not None
        self.text(66, 108, 'H A R V A R D V I L L E  I N C I D E N T', 13, family=MONO)
        self.text(64, 155, 'Installation', 58)
        self.text(68, 229, 'Import once. Play from this computer.', 23)
        self.line(68, 272, 791, 272)
        for number, y, title, detail in [
                ('01', 298, 'Prepare your game archive',
                 'Use your own Resident Evil: Degeneration IPA: English, iPhone, v1.03.00. The game is not included.'),
                ('02', 376, 'Choose the .ipa file below',
                 'Keep the archive intact. It must be unencrypted; an App Store copy protected by DRM cannot be imported.'),
                ('03', 454, 'Wait for “Ready to play”',
                 'Import copies and verifies the files. Return to Overview and choose Play. The source drive can then be disconnected.')]:
            self.text(72, y + 3, number, 17, family=MONO, color=RED)
            self.text(118, y, title, 23)
            self.text(118, y + 33, detail, 17, width=662)
        self.button('choose-ipa', 'Choose game IPA…', self.choose_ipa,
                    (71, 548, 321, 51), kind='primary', size=23, enabled=not busy)
        self.button('verify-installation', 'Verify installation', self.verify,
                    (417, 548, 369, 51), kind='outline', size=23,
                    enabled=not busy and installation_present(self.session.dirs))
        self.text(71, 620, self.session.status, 21, width=690)
        self.text(71, 661, 'Import failed? Open View logs for the reason. Check the version and encryption of your archive before trying again.', 16, width=695)
        self.text(71, 708, 'Rejected imports keep your current installation and saves.', 14, width=695)
        self.text(912, 537, 'LOCAL STORAGE', 15, family=MONO)
        self.text(912, 574, str(self.session.dirs.data), 13, family=MONO, width=423)
        self.text(912, 654, 'First launch prepares the game cache. Allow extra time; keep the game open.', 17, width=420)

    def place_entry(self, widget, bounds):
        x, y, w, h = self.box(bounds)
        widget.place(x=x, y=y, width=w, height=h)
        self.entries.append(widget)

    def volume_changed(self, value):
        if hasattr(self, 'volume_item') and self.page == 'settings':
            self.canvas.itemconfigure(self.volume_item, text=f'{self.volume.get()}%')

    def set_toggle(self, variable, value):
        variable.set(value)
        self.render()

    def update_window_icon(self):
        self.window_icon = ImageTk.PhotoImage(self.art.get(
            f'desktop-icons/{self.desktop_icon}.png').resize((64, 64), Image.Resampling.LANCZOS))
        self.window.iconphoto(True, self.window_icon)

    def select_desktop_icon(self, choice):
        self.desktop_icon = choice
        self.render()

    def apply_desktop_icon(self):
        try:
            install_icon(self.desktop_icon, dirs=self.session.dirs,
                         binary=self.session.binary, desktop=True)
        except (OSError, ValueError, ImportError) as error:
            self.error('Cannot set desktop icon', str(error))
            return
        self.update_window_icon()
        self.session.status = 'Desktop icon updated'
        self.render()

    def save_preferences(self):
        if self.session.child or self.settings_error:
            return
        try:
            save_settings(self.session.dirs, {'Fullscreen': self.fullscreen.get(),
                          'TouchMode': self.touch.get(), 'Volume': self.volume.get() / 100.0})
        except (OSError, ValueError) as error:
            self.error('Cannot save settings', str(error))
            return
        self.session.status = 'Settings saved'
        self.render()

    def reset_preferences(self):
        if self.session.child:
            return
        previous = self.settings_error
        self.fullscreen.set(False)
        self.touch.set(False)
        self.volume.set(100)
        self.settings_error = None
        try:
            save_settings(self.session.dirs, {'Fullscreen': False, 'TouchMode': False, 'Volume': 1.0})
        except (OSError, ValueError) as error:
            self.settings_error = previous
            self.error('Cannot reset settings', str(error))
        else:
            self.session.status = 'Default settings restored'
        self.render()

    def navigate(self, page):
        self.wheel_remainder = 0
        self.page = page
        self.render()

    def filter_category(self, category):
        self.wheel_remainder = 0
        self.category, self.offset, self.selected = category, 0, 0
        self.render()

    def select(self, index):
        if self.selected == index and self.offset == index // 4 * 4:
            return
        self.selected = index
        self.offset = index // 4 * 4
        self.render()

    def move_selection(self, direction):
        if self.page == 'achievements':
            self.select(max(0, min(len(self.filtered()) - 1, self.selected + direction)))
            return 'break'

    def paginate(self, direction):
        if self.page == 'achievements':
            offset = max(0, min((len(self.filtered()) - 1) // 4 * 4, self.offset + direction * 4))
            self.select(offset)
            return 'break'

    def scroll_achievements(self, event):
        if self.page != 'achievements' or event.widget.winfo_toplevel() != self.window:
            return
        x = event.x_root - self.canvas.winfo_rootx()
        y = event.y_root - self.canvas.winfo_rooty()
        left, top, width, height = self.box((65, 296, 728, 384))
        if not (left <= x < left + width and top <= y < top + height):
            return
        if event.num in (4, 5):
            steps = -1 if event.num == 4 else 1
        else:
            # Tk/X11 and Windows use 120 units per detent; macOS sends small
            # deltas. Keep fractional trackpad input instead of paging on zero.
            unit = 1 if self.window.tk.call('tk', 'windowingsystem') == 'aqua' else 120
            self.wheel_remainder -= event.delta / unit
            steps = int(self.wheel_remainder)
            self.wheel_remainder -= steps
        if steps:
            limit = (len(self.filtered()) - 1) // 4 * 4
            offset = max(0, min(limit, self.offset + steps * 4))
            if offset != self.offset:
                self.offset = self.selected = offset
                # Coalesce queued wheel events and keep the row widgets alive:
                # Tk may still have input/focus events addressed to those rows.
                if self.wheel_job is None:
                    self.wheel_job = self.window.after(30, self.render)
        return 'break'

    def toggle_fullscreen(self, event=None):
        if not self.launcher_fullscreen:
            self.windowed_geometry = self.window.geometry()
        self.launcher_fullscreen = not self.launcher_fullscreen
        self.window.attributes('-fullscreen', self.launcher_fullscreen)
        if not self.launcher_fullscreen and self.windowed_geometry:
            self.window.geometry(self.windowed_geometry)
        self.schedule_render()
        return 'break'

    def minimize(self):
        if self.launcher_fullscreen:
            self.toggle_fullscreen()
        self.window.iconify()

    def start(self, operation, *args):
        try:
            started = self.session.start(operation, *args)
        except OSError as error:
            self.error('Cannot start ' + operation, f'{error}\n\nBuild the game with make build.')
            return False
        if started:
            self.render()
        return started

    def verify(self):
        return self.start('check')

    def play(self):
        if not self.session.verified or self.session.child or self.settings_error:
            if self.settings_error:
                self.error('Cannot load game settings', self.settings_error)
            return False
        return self.start('run')

    def choose_ipa(self):
        if self.session.child:
            return
        path = filedialog.askopenfilename(parent=self.window, title='Import Resident Evil Degeneration',
                                          filetypes=[('iPhone game archive', '*.ipa'), ('All files', '*')])
        if path:
            self.import_ipa(path)

    def import_ipa(self, path):
        return self.start('import', path)

    def error(self, title, detail):
        self.session.status = title
        messagebox.showerror(title, detail, parent=self.window)

    def show_logs(self):
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
        else:
            self.log_window = tk.Toplevel(self.window)
            self.log_snapshot = None
            self.log_window.title('Degeneration · Logs')
            self.log_window.geometry('940x570')
            self.log_window.minsize(600, 350)
            self.log_text = tk.Text(self.log_window, bg='#101b24', fg=IVORY,
                                    font=(MONO, 11), wrap='word', padx=18, pady=18,
                                    insertbackground=IVORY, relief='flat')
            scrollbar = ttk.Scrollbar(self.log_window, command=self.log_text.yview)
            scrollbar.pack(side='right', fill='y')
            self.log_text.configure(yscrollcommand=scrollbar.set)
            self.log_text.pack(fill='both', expand=True)
            self.log_window.bind('<Escape>', lambda e: self.log_window.destroy())
            self.log_window.bind('<Control-r>', lambda e: self.refresh_logs())
        self.refresh_logs()

    def refresh_logs(self):
        if not self.log_window or not self.log_window.winfo_exists():
            return
        try:
            runtime = tail_log(self.session.dirs.logs / 'redegpc.log')
        except OSError as error:
            runtime = str(error)
        operation = ''.join(self.session.transcript)[-65536:] if self.session.child else self.session.last_output
        text = (f'RUNTIME LOG · {self.session.dirs.logs / "redegpc.log"}\n\n{runtime}'
                f'\n\nLAUNCHER OPERATION\n\n{operation or "No operation output."}')
        if self.settings_error:
            text += '\n\nSETTINGS ERROR\n\n' + self.settings_error
        if text == self.log_snapshot:
            return
        self.log_snapshot = text
        position = self.log_text.yview()
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.insert('1.0', text)
        if position:
            self.log_text.yview_moveto(position[0])
        self.log_text.configure(state='disabled')

    def tick(self):
        result = self.session.tick()
        if result:
            operation, code = result
            if self.closing:
                self.destroy()
                return
            self.render()
            if code:
                self.error(self.session.status, self.session.last_output[-5000:] or f'{operation} exited with code {code}')
            elif operation == 'run':
                self.window.lift()
        if self.closing and self.session.child and self.stop_deadline and time.monotonic() >= self.stop_deadline:
            self.session.child.stop(force=True)
            self.stop_deadline = None
        if self.log_window and self.log_window.winfo_exists():
            self.refresh_logs()
        self.tick_job = self.window.after(100, self.tick)

    def escape(self, event=None):
        if self.launcher_fullscreen:
            self.toggle_fullscreen()
        elif self.page != 'overview':
            self.navigate('overview')
        return 'break'

    def close(self):
        if self.closing:
            return
        if self.session.child:
            if self.session.operation == 'import':
                messagebox.showinfo('Import in progress', 'Let the import finish before closing the launcher.', parent=self.window)
                return
            if self.session.operation == 'run' and not messagebox.askyesno(
                    'Close game?', 'Close the running game and launcher? Unsaved progress may be lost.', parent=self.window):
                return
            self.closing = True
            self.session.child.stop()
            self.stop_deadline = time.monotonic() + 3
        else:
            self.destroy()

    def destroy(self):
        if self.resize_job:
            self.window.after_cancel(self.resize_job)
        if self.tick_job:
            self.window.after_cancel(self.tick_job)
        if self.wheel_job:
            self.window.after_cancel(self.wheel_job)
        self.window.destroy()
