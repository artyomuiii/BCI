import numpy as np
import pygame as pg
from collections import deque
import random, sys, os, math, json
from pylsl import StreamInfo, StreamOutlet


# set up pinned window on second monitor
x = -1920
y = 0
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"
os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'


numbers = "1234567890"
name_json = "blink_mode.json"


# загрузка конфигурации из json
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    d = cfg.get("defaults", {})
    items = cfg.get("items", [])
    view = cfg.get("view", {})

    # выбираем режим клавиатуры
    keyboard_mode = cfg.get("keyboard_mode")
    if keyboard_mode == "default":
        # задаём язык алфавита
        lang = cfg.get("language")
        if lang == "en":
            text = cfg.get("en_text")
        elif lang == "rus":
            text = cfg.get("rus_text")
        
        # определяем, нужны ли цифры
        if cfg.get("numbers_flag"):
            text += numbers
    elif keyboard_mode == "en":
        pass
    elif keyboard_mode == "rus":
        pass

    # строим список элементов
    elems = [{"char": char} for char in text]

    # задаём тему (светлая/тёмная)
    theme = view.get("theme")
    if theme == "dark":
        bg = view.get("bg_dark")
        fg = view.get("fg_dark")
        mg = view.get("mg_dark")
    elif theme == "light":
        bg = view.get("bg_light")
        fg = view.get("fg_light")
        mg = view.get("mg_light")

    # применяем переопределения из items
    for item in items:
        idx = item.get("index")
        if idx is not None:
            if idx >= len(elems):
                elems.extend({"char": " "} for _ in range(idx - len(elems) + 1))
            elems[idx] = {**elems[idx], **{k: v for k, v in item.items() if k != "index"}}
        else:
            elems.append(item) # полноценный элемент с "char"
    
    # устанавливаем недостающие параметры из defaults
    for elem in elems:
        elem.setdefault("buf_size",  int(d.get("buf_size")))
        elem.setdefault("pause_mode",  d.get("pause_mode"))
        elem.setdefault("freq", float(d.get("freq")))
        elem.setdefault("duty",  float(d.get("duty")))
        elem.setdefault("pause",  float(d.get("pause")))
        elem.setdefault("eps_freq",  float(d.get("eps_freq")))
        elem.setdefault("eps_duty",  float(d.get("eps_duty")))
        elem.setdefault("eps_pause",  float(d.get("eps_pause")))
    
    return elems, {
        "mute_mode": view.get("mute_mode"),
        "fullscreen": bool(view.get("fullscreen")),
        "text": text,
        "fps": int(view.get("fps")),
        "bg": bg,
        "fg": fg,
        "mg": mg,
        "mute_coeff": float(view.get("mute_coeff")),
        "scale": float(view.get("scale")),
        }


# получение числа строк и столбцов
def get_rows_cols(n):
    rows = math.ceil(math.sqrt(n))
    cols = rows - 1
    if cols * rows < n:
        cols += 1
    return rows, cols


# получить случ. координаты несоседнего с предыдущим символом символа,
#   учитывая окно заданной ширины невторяющихся символов, кот. для каждого символа своё
def get_pos(rows, cols, n, prev_i, prev_j, char_mat, buf_mat):
    i = random.randrange(rows)
    j = random.randrange(cols)
    while (i * cols + j >= n) or \
          (abs(i - prev_i) <= 1 and abs(j - prev_j) <= 1) or \
          char_mat[i, j] in buf_mat[i][j]:
        i = random.randrange(rows)
        j = random.randrange(cols)
    
    for k in range(rows):
        for n in range(cols):
            if char_mat[k, n] != ' ':
                buf_mat[k][n].append(char_mat[i, j])
    
    return i, j


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else name_json
    elems, view = load_config(cfg_path)

    pg.init()
    flag = pg.FULLSCREEN if view["fullscreen"] else 0
    screen = pg.display.set_mode((0, 0), flag)
    w, h = screen.get_size()
    n = len(elems)
    rows, cols = get_rows_cols(n)
    cell_w, cell_h = w // cols, h // rows
    print("cell size:", cell_w, cell_h)

    font = pg.font.SysFont(None, int(min(cell_w, cell_h) * 0.8), bold=True)

    cells = {}
    for i, elem in enumerate(elems):
        # яркая и приглушённая версии символов
        bg = view["bg"]
        fg = view["fg"]
        if view["mute_mode"] == "coeff":
            mg = tuple(int(fg[k] * view["mute_coeff"] +
                           bg[k] * (1 - view["mute_coeff"])) for k in range(3))
        elif view["mute_mode"] == "color":
            mg = view["mg"]
        surf_fg = font.render(elem["char"], True, fg).convert_alpha()
        surf_bg = font.render(elem["char"], True, bg).convert_alpha()
        surf_mg = font.render(elem["char"], True, mg).convert_alpha()
        
        surf_w, surf_h = surf_fg.get_size()
        quot, rem = divmod(i, cols)
        # центр ячейки
        cell_x, cell_y = rem * cell_w + cell_w // 2, quot * cell_h + cell_h // 2
        # левый верхний край символа - его прямоугольника
        base_x, base_y = cell_x - surf_w // 2, cell_y - surf_h // 2

        # клавиша: оставляем внутренний отступ (pad) от размера ячейки
        pad_w, pad_h = max(8, cell_w // 20), max(8, cell_h // 20)
        key_w, key_h = max(40, cell_w - pad_w * 2), max(40, cell_h - pad_h * 2)
        rect = pg.Rect(cell_x - key_w // 2, cell_y - key_h // 2, key_w, key_h)
        corner_radius = int(min(key_w, key_h) * 0.15)
        
        # подготовка масштабированной версии подсвеченного символа
        surf_w_scale = int(surf_w * view["scale"])
        surf_h_scale = int(surf_h * view["scale"])
        surf_fg_scale = pg.transform.smoothscale(surf_fg, (surf_w_scale,
                                                           surf_h_scale)).convert_alpha()
        base_x_scale, base_y_scale = cell_x - surf_w_scale // 2, cell_y - surf_h_scale // 2
        
        cells[elem["char"]] = {
            "rect": rect,
            "corner_radius": corner_radius,
            "surf_fg": surf_fg,
            "surf_bg": surf_bg,
            "surf_mg": surf_mg,
            "surf_fg_scale": surf_fg_scale,
            "pos": (base_x, base_y),
            "pos_scale": (base_x_scale, base_y_scale),
            "buf_size": elem["buf_size"],
            "pause_mode": elem["pause_mode"],
            "freq": elem["freq"],
            "duty": elem["duty"],
            "pause": elem["pause"],
            "eps_freq": elem["eps_freq"],
            "eps_duty": elem["eps_duty"],
            "eps_pause": elem["eps_pause"],
        }

    info = StreamInfo(name='annotations',
                      type='Events',
                      channel_count=1,
                      nominal_srate=0,
                      channel_format='string',
                      source_id='my_marker_stream')
    outlet = StreamOutlet(info)

    # матрица символов
    chars = list(view["text"] + ' ' * (rows * cols - len(view["text"])))
    char_mat = np.array(chars).reshape((rows, cols))

    # буфер недавно показанных символов (для каждого символа свой)
    buf_mat = [[None for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            if char_mat[i, j] != ' ':
                buf_mat[i][j] = deque(maxlen=cells[char_mat[i, j]]["buf_size"])
    
    # основной цикл
    is_run, is_off, is_print = True, True, False
    i, j = -2, -2
    clock = pg.time.Clock()
    t0 = pg.time.get_ticks() / 1000
    while is_run:
        # обработка событий
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    is_run = False

                if event.key == pg.K_s:
                    outlet.push_sample(['exp_start'])

                if event.key == pg.K_e:
                    outlet.push_sample(['exp_end'])
        
        screen.fill(view["bg"])
        t = pg.time.get_ticks() / 1000 - t0

        # отрисовываем все символы приглушённо (видимы всегда)
        for cell in cells.values():
            screen.blit(cell["surf_mg"], cell["pos"])
            """
            rect = cell["rect"]
            corner_radius = cell["corner_radius"]
            # лицевая часть клавиши
            key_color = view["mg"]
            border_color = tuple(max(0, v - 30) for v in key_color)
            pg.draw.rect(screen, key_color, rect, border_radius=corner_radius)
            pg.draw.rect(screen, border_color, rect, width=2, border_radius=corner_radius)
            # символ внутри клавиши (приадптируем позицию по центру rect)
            surf = cell["surf_mg"]
            sw, sh = surf.get_size()
            surf_pos = (rect.centerx - sw//2, rect.centery - sh//2)
            screen.blit(surf, surf_pos)
            """

        # выбираем текущий символ и режим его отображения
        if not is_print:
            is_print, is_off = True, False
            i, j = get_pos(rows, cols, n, i, j, char_mat, buf_mat)
            print(char_mat[i, j], end='')
            params = cells[char_mat[i, j]]
            freq = params["freq"] + random.uniform(-params["eps_freq"], params["eps_freq"])
            duty = params["duty"] + random.uniform(-params["eps_duty"], params["eps_duty"])
            pause = params["pause"] + random.uniform(-params["eps_pause"], params["eps_pause"])
            pause_mode = params["pause_mode"]
            outlet.push_sample(["stim_on_" + char_mat[i, j]])

        if t < duty/freq: # длительность показа
            screen.blit(params["surf_bg"], params["pos"]) # закрашиваем приглушённую версию
            screen.blit(params["surf_fg_scale"], params["pos_scale"])
        elif (pause_mode == "duty" and (duty/freq <= t < 1/freq)) or \
             (pause_mode == "pause" and (t < duty/freq + pause)):
            if not is_off:
                outlet.push_sample(["stim_off_" + char_mat[i, j]])
                is_off = True
        elif (pause_mode == "duty" and not (duty/freq <= t < 1/freq)) or \
             (pause_mode == "pause" and not (t < duty/freq + pause)):
                is_print = False
                t0 = pg.time.get_ticks() / 1000  # сброс времени

        pg.display.flip()
        clock.tick(view["fps"])

if __name__ == "__main__":
    main()
