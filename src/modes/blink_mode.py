import json
import math
import os
import random
import sys
from collections import deque

import numpy as np
import pygame as pg
from pylsl import StreamInfo, StreamOutlet

# set up pinned window on second monitor
x = -1920
y = 0
os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
os.environ["SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"] = "0"


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
        elif lang == "ru":
            text = cfg.get("rus_text")
        else:
            raise ValueError("Error in `lang`!")

        # определяем, нужны ли цифры
        if cfg.get("numbers_flag"):
            text += cfg.get("numbers")
    elif keyboard_mode == "en":
        pass
    elif keyboard_mode == "rus":
        pass
    else:
        raise ValueError("Error in `keyboard_mode`!")

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
    else:
        raise ValueError("Error in `theme`!")

    # применяем переопределения из items
    for item in items:
        idx = item.get("index")
        if idx is not None:
            if idx >= len(elems):
                elems.extend({"char": " "} for _ in range(idx - len(elems) + 1))
            elems[idx] = {
                **elems[idx],
                **{k: v for k, v in item.items() if k != "index"},
            }
        else:
            elems.append(item)  # полноценный элемент с "char"

    # устанавливаем недостающие параметры из defaults
    for elem in elems:
        elem.setdefault("buf_size", int(d.get("buf_size")))
        elem.setdefault("pause_mode", d.get("pause_mode"))
        elem.setdefault("freq", float(d.get("freq")))
        elem.setdefault("duty", float(d.get("duty")))
        elem.setdefault("pause", float(d.get("pause")))
        elem.setdefault("eps_freq", float(d.get("eps_freq")))
        elem.setdefault("eps_duty", float(d.get("eps_duty")))
        elem.setdefault("eps_pause", float(d.get("eps_pause")))

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
def get_pos_single_activation(rows, cols, n, prev_i, prev_j, char_arr, buf_mat):
    i = random.randrange(rows)
    j = random.randrange(cols)
    while (
        (i * cols + j >= n)
        or (abs(i - prev_i) <= 1 and abs(j - prev_j) <= 1)
        or char_arr[i, j] in buf_mat[i][j]
    ):
        i = random.randrange(rows)
        j = random.randrange(cols)

    for k in range(rows):
        for n in range(cols):
            if char_arr[k, n] != " ":
                buf_mat[k][n].append(char_arr[i, j])

    return i, j


# получить случ. координаты символа
def get_pos(rows, cols):
    i = random.randrange(rows)
    j = random.randrange(cols)
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

    font = pg.font.SysFont(None, int(min(cell_w, cell_h) * 0.8), bold=True)

    cells = {}
    for i, elem in enumerate(elems):
        # яркая и приглушённая версии символов
        bg = view["bg"]
        fg = view["fg"]
        if view["mute_mode"] == "coeff":
            mg = tuple(
                int(
                    fg[k] * view["mute_coeff"]
                    + bg[k] * (1 - view["mute_coeff"])
                )
                for k in range(3)
            )
        elif view["mute_mode"] == "color":
            mg = view["mg"]
        else:
            raise ValueError("Error in `mute_mode`!")
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
        surf_fg_scale = pg.transform.smoothscale(
            surf_fg, (surf_w_scale, surf_h_scale)
        ).convert_alpha()
        base_x_scale, base_y_scale = (
            cell_x - surf_w_scale // 2,
            cell_y - surf_h_scale // 2,
        )

        # создание прямоугольников, которыми будем закрашивать
        rect_bg = pg.Surface(surf_fg.get_size())
        rect_bg.fill(bg)
        rect_bg_scale = pg.Surface(surf_fg_scale.get_size())
        rect_bg_scale.fill(bg)

        cells[elem["char"]] = {
            "rect": rect,
            "corner_radius": corner_radius,
            "rect_bg": rect_bg,
            "rect_bg_scale": rect_bg_scale,
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

    info = StreamInfo(
        name="annotations",
        type="Events",
        channel_count=1,
        nominal_srate=0,
        channel_format="string",
        source_id="my_marker_stream",
    )
    outlet = StreamOutlet(info)

    # матрица символов
    chars = list(view["text"] + " " * (rows * cols - len(view["text"])))
    char_arr = np.array(chars).reshape((rows, cols))

    # матрицы флагов
    is_off_arr = np.ones((rows, cols), dtype=bool)
    is_period_arr = np.zeros((rows, cols), dtype=bool)

    # матрицы параметров
    t0_arr = np.zeros((rows, cols))
    freq_arr = np.zeros((rows, cols))
    duty_arr = np.zeros((rows, cols))
    pause_arr = np.zeros((rows, cols))
    buf_mat = [[None for _ in range(cols)] for _ in range(rows)]
    pause_mode_mat = [[None for _ in range(cols)] for _ in range(rows)]

    # инициализация матриц
    for i in range(rows):
        for j in range(cols):
            if char_arr[i, j] != " ":
                # буфер недавно показанных символов, для каждого символа свой (список списков)
                buf_mat[i][j] = deque(maxlen=cells[char_arr[i, j]]["buf_size"])

                pause_mode_mat[i][j] = cells[char_arr[i, j]]["pause_mode"]

                # задание freq и duty для всех символов
                freq_arr[i, j] = cells[char_arr[i, j]]["freq"] + random.uniform(
                    -cells[char_arr[i, j]]["eps_freq"],
                    cells[char_arr[i, j]]["eps_freq"],
                )
                duty_arr[i, j] = cells[char_arr[i, j]]["duty"] + random.uniform(
                    -cells[char_arr[i, j]]["eps_duty"],
                    cells[char_arr[i, j]]["eps_duty"],
                )

    # начальная отрисовка
    screen.fill(view["bg"])
    for (
        cell
    ) in cells.values():  # отрисовываем все символы приглушённо (видимы всегда)
        screen.blit(cell["surf_mg"], cell["pos"])

    # основной цикл
    is_run = True
    clock = pg.time.Clock()
    while is_run:
        # обработка событий - нажатия клавиш
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    is_run = False

                if event.key == pg.K_s:
                    outlet.push_sample(["exp_start"])

                if event.key == pg.K_e:
                    outlet.push_sample(["exp_end"])

        for i in range(rows):
            for j in range(cols):
                if char_arr[i, j] != " ":
                    if not is_period_arr[i, j]:
                        is_period_arr[i, j] = True
                        is_off_arr[i, j] = False
                        # сэмплируем паузу для каждого символа
                        pause_arr[i, j] = cells[char_arr[i, j]][
                            "pause"
                        ] + random.uniform(
                            -cells[char_arr[i, j]]["eps_pause"],
                            cells[char_arr[i, j]]["eps_pause"],
                        )
                        outlet.push_sample(["stim_on_" + char_arr[i, j]])
                        t0_arr[i, j] = (
                            pg.time.get_ticks() / 1000
                        )  # сброс времени

                    t = pg.time.get_ticks() / 1000 - t0_arr[i, j]

                    if (
                        t < duty_arr[i, j] / freq_arr[i, j]
                    ):  # длительность показа
                        screen.blit(
                            cells[char_arr[i, j]]["rect_bg"],
                            cells[char_arr[i, j]]["pos"],
                        )  # закрашиваем приглушённый символ
                        screen.blit(
                            cells[char_arr[i, j]]["surf_fg_scale"],
                            cells[char_arr[i, j]]["pos_scale"],
                        )  # рисуем активный символ
                    elif (
                        pause_mode_mat[i][j] == "duty"
                        and (t < 1 / freq_arr[i, j])
                    ) or (
                        pause_mode_mat[i][j] == "pause"
                        and (
                            t
                            < duty_arr[i, j] / freq_arr[i, j] + pause_arr[i, j]
                        )
                    ):
                        if not is_off_arr[i, j]:
                            is_off_arr[i, j] = True
                            outlet.push_sample(["stim_off_" + char_arr[i, j]])
                        screen.blit(
                            cells[char_arr[i, j]]["rect_bg_scale"],
                            cells[char_arr[i, j]]["pos_scale"],
                        )  # закрашиваем активный символ
                        screen.blit(
                            cells[char_arr[i, j]]["surf_mg"],
                            cells[char_arr[i, j]]["pos"],
                        )  # снова рисуем приглушённый символ
                    elif (
                        pause_mode_mat[i][j] == "duty"
                        and not (t < 1 / freq_arr[i, j])
                    ) or (
                        pause_mode_mat[i][j] == "pause"
                        and not (
                            t
                            < duty_arr[i, j] / freq_arr[i, j] + pause_arr[i, j]
                        )
                    ):
                        is_period_arr[i, j] = False
                    else:
                        raise ValueError("Error in `pause_mode`!")

        pg.display.flip()
        clock.tick(view["fps"])


if __name__ == "__main__":
    main()
