import math
import os
import random

import numpy as np
import pygame as pg
from pylsl import StreamInfo, StreamOutlet


def pinned_window(conf):
    """
    Set up pinned window on second monitor
    """
    x = conf["win_x"]
    y = conf["win_y"]
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
    os.environ["SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"] = "0"


def get_outlet():
    info = StreamInfo(
        name="annotations",
        type="Events",
        channel_count=1,
        nominal_srate=0,
        channel_format="string",
        source_id="my_marker_stream",
    )
    return StreamOutlet(info)


def set_delay(delay, is_random):
    if is_random:
        return random.random() * delay
    return delay


def set_freq(freq_mean, freq_std):
    return abs(np.random.normal(0, freq_std)) + freq_mean


def get_speed(t, freq, delay_before, delay_after):
    """
    :param t: мс
    :param freq: сек
    :param delay_before: сек
    :param delay_after: сек
    """
    t = t / 1000  # переводим в сек.

    # пауза до показа
    if 0 <= t < delay_before:
        return 0

    # показ в течении 1го периода
    elif delay_before <= t < delay_before + 1 / freq:
        return math.sin((t - delay_before) * math.tau * freq)

    # пауза после показа
    elif delay_before + 1 / freq <= t < delay_before + 1 / freq + delay_after:
        return 0

    # вышли за рамки
    else:
        raise ValueError(
            f"`t` must be between 0 and {delay_before + 1 / freq + delay_after} s"
        )


def get_move_info(speed, cfg):
    if cfg["mode"] == "blink":
        info = f"scale: {cfg["blink_scale"]}"

    elif cfg["mode"] == "move":
        is_x_move = np.sign(speed) if cfg["is_x_move"] else 0
        is_y_move = np.sign(speed) if cfg["is_y_move"] else 0
        is_z_move = np.sign(speed) if cfg["is_z_move"] else 0

        info = f"x: {is_x_move}, y: {is_y_move}, z: {is_z_move}"

    else:
        raise ValueError("Incorrect 'mode' value!")

    return info


def send(outlet, file, send_text):
    outlet.push_sample([send_text])
    file.write(f"{pg.time.get_ticks() / 1000:.3f}: " + send_text + "\n")


def get_cells(cfg, font, w, h):
    cells = {}
    for id, char in enumerate(cfg["alphabet"]):
        letter = font.render(char, True, cfg["fg"])
        cells[char] = {
            "id": id,
            "letter": letter,
            "letter_tmp": letter,
            "amp_x": (w / 2) * cfg["amp_x_scale"],
            "amp_y": (h / 2) * cfg["amp_y_scale"],
            "freq": set_freq(cfg["freq_mean"], cfg["freq_std"]),
            "delay_before": set_delay(cfg["delay_before"], cfg["is_rand_delay"]),
            "delay_after": set_delay(cfg["delay_after"], cfg["is_rand_delay"]),
            "start_t": 0,
            "prev_speed": 0,
            "is_moving": False,
        }
    return cells


def event_processing(outlet, log, is_running, is_start_exp, t0):
    """
    Обработка событий из PyGame

    :return: is_running, is_start_exp, t0
    """
    for event in pg.event.get():

        if event.type == pg.QUIT:
            is_running = False

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                is_running = False

            if event.key == pg.K_s:
                is_start_exp = True
                t0 = pg.time.get_ticks()
                send(outlet, log, "start_experiment")

            if event.key == pg.K_e:
                is_start_exp = False
                send(outlet, log, "end_experiment")

            if event.key == pg.K_SPACE:
                send(outlet, log, "pressed_space")

    return is_running, is_start_exp, t0


def _mode_processing(char, cell, speed, cfg, font):
    """
    Задание логики отображения символов в зависимости от выбранного режима работы

    :return: dx, dy, letter_tmp
    """
    if cfg["mode"] == "blink":
        # приращений нет
        dx, dy = 0, 0

        # цвет и масштаб символа зависят от того, сейчас ли фаза дв-ия
        if speed or cell["prev_speed"]:
            color = cfg["fg"]
            scale = cfg["blink_scale"]
        else:
            color = cfg["fg_light"]
            scale = 1

        letter_tmp = pg.transform.smoothscale(
            font.render(char, True, color),
            (
                cell["letter"].get_width() * scale,
                cell["letter"].get_height() * scale,
            ),
        )

    elif cfg["mode"] == "move":
        # считаем приращения
        dx = cell["amp_x"] * speed if cfg["is_x_move"] else 0
        dy = cell["amp_y"] * speed if cfg["is_y_move"] else 0

        # новый отмасштабированный рендер буквы
        letter_tmp = (
            pg.transform.smoothscale(
                cell["letter"],
                (
                    # [-1, 1] -> [0, 2] - увеличение размера до 2ух раз
                    cell["letter"].get_width() * (speed + 1),
                    cell["letter"].get_height() * (speed + 1),
                ),
            )
            if cfg["is_z_move"]
            else cell["letter"]
        )

    else:
        raise ValueError("Incorrect 'mode' value!")

    return dx, dy, letter_tmp


def cell_processing(char, cell, is_start_exp, t0, outlet, log, cfg, font):
    """
    Обработка каждого эл-та в цикле - вычисление dx, dy, пересчёт визуализации в
        зав-ти от скорости дв-я

    :return: dx, dy, letter_tmp
    """
    if is_start_exp:

        t = pg.time.get_ticks() - t0

        try:
            speed = get_speed(
                t - cell["start_t"],
                cell["freq"],
                cell["delay_before"],
                cell["delay_after"],
            )

            # начало движения символа
            if speed != 0 and not cell["is_moving"]:
                send(
                    outlet,
                    log,
                    f"{char}_start_{get_move_info(speed, cfg)}",
                )
                cell["is_moving"] = True

            # конец движения символа (дв-ие - это только фаза периода, паузы не считаются)
            if speed == 0 and cell["prev_speed"] == 0 and cell["is_moving"]:
                send(outlet, log, f"{char}_end")
                cell["is_moving"] = False

            cell["prev_speed"] = speed

        # если t вышел из допустимого диапазона
        except ValueError:
            cell["start_t"] = t
            speed = 0
            cell["prev_speed"] = 0
            cell["is_moving"] = False

            # паузы между показами букв сделать случайными
            cell["delay_before"] = set_delay(cfg["delay_before"], cfg["is_rand_delay"])
            cell["delay_after"] = set_delay(cfg["delay_after"], cfg["is_rand_delay"])

        dx, dy, letter_tmp = _mode_processing(char, cell, speed, cfg, font)

    else:
        dx, dy, letter_tmp = 0, 0, cell["letter"]

    return dx, dy, letter_tmp


def hint_processing(
    char, cur_simbol_id, is_start_exp, is_end, t_cur, cell, font, outlet, log, cfg
):
    """
    Обработка каждого символа в цикле - задание логики подсказки в виде определённой
        подсветки, чтобы испытуемый понимал, что происходит

    :return: t_cur, cur_simbol_id
    """
    text = cfg["text"]

    # переводим в мс
    t_pause = cfg["t_pause"] * 1000
    t_cont = cfg["t_cont"] * 1000
    t_show = cfg["t_show"] * 1000

    if is_start_exp and char == text[cur_simbol_id]:

        # ещё не начали демонстрацию, но теперь начинаем
        if t_cur is None:
            is_end = False
            t_cur = pg.time.get_ticks()
            send(outlet, log, f"show_{char}_start")

        # подсветка в начале, чтобы обратить внимание на букву (метка "start")
        elif t_cur < pg.time.get_ticks() <= t_cur + t_cont:
            cell["letter_tmp"] = pg.transform.smoothscale(
                font.render(char, True, cfg["start_fg"]),
                cell["letter_tmp"].get_size(),
            )

        # показ буквы (ничего не делаем)
        elif t_cur + t_cont < pg.time.get_ticks() <= t_cur + t_show - t_cont:
            pass

        # подсветка в конце, чтобы испытуемый готовился искать следующую букву
        elif t_cur + t_show - t_cont < pg.time.get_ticks() <= t_cur + t_show:
            cell["letter_tmp"] = pg.transform.smoothscale(
                font.render(char, True, cfg["end_fg"]),
                cell["letter_tmp"].get_size(),
            )

        # пауза между показами букв (метка "end")
        elif t_cur + t_show < pg.time.get_ticks() <= t_cur + t_show + t_pause:
            if not is_end:
                send(outlet, log, f"show_{char}_end")
                is_end = True

        # выбираем след. символ
        elif cur_simbol_id < len(text) - 1:
            cur_simbol_id += 1
            t_cur = None

    return t_cur, cur_simbol_id, is_end
