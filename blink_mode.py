import numpy as np
import pygame as pg
import random, sys, os, math, json
from pylsl import StreamInfo, StreamOutlet


# set up pinned window on second monitor
x = -1920
y = 0
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"
os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'


name_json = "blink_mode.json"


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
   
    text = cfg.get("text", "")
    d = cfg.get("defaults", {})
    items = cfg.get("items", [])
    view = cfg.get("view", {})

    # построим список элементов
    elems = []
    if text:
        elems = [{"char": ch} for ch in text]

    # применим переопределения из items
    idxmap = {}
    for it in items:
        i = it.get("index")
        if i is not None:
            if i >= len(elems):
                elems.extend({"char": " "} for _ in range(i - len(elems) + 1))
            elems[i] = {**elems[i], **{k: v for k, v in it.items() if k != "index"}}
        else:
            # полноценный элемент с char
            elems.append(it)
    
    # defaults
    for i, elem in enumerate(elems):
        elem.setdefault("char", " ")
        elem.setdefault("freq", float(d.get("freq")))
        elem.setdefault("eps_freq",  float(d.get("eps_freq")))
        elem.setdefault("pause_mode",  str(d.get("pause_mode")))
        elem.setdefault("duty",  float(d.get("duty")))
        elem.setdefault("eps_duty",  float(d.get("eps_duty")))
        elem.setdefault("pause",  float(d.get("pause")))
        elem.setdefault("eps_pause",  float(d.get("eps_pause")))
    
    return elems, {
        "fullscreen": bool(view.get("fullscreen", True)),
        "text": text,
        "fps": int(view.get("fps")),
        "bg": tuple(view.get("bg")),
        "fg": tuple(view.get("fg"))
        }


# получение числа строк и столбцов
def get_rows_cols(n):
    rows = math.ceil(math.sqrt(n))
    cols = rows - 1
    if cols * rows < n:
        cols += 1
    return rows, cols


# получить случ. позицию в сетке, соотв. сущ-им эл-там, но не соседнему
def get_rand_pos_without_neighbors(rows, cols, n, prev_i, prev_j):
    i = random.randrange(rows)
    j = random.randrange(cols)
    while (i * rows + j >= n) or (abs(i - prev_i) <= 1 and abs(j - prev_j) <= 1) or (prev_i == i and prev_j == j):
        i = random.randrange(rows)
        j = random.randrange(cols)
    #print("prev:", prev_i, prev_j, "new:", i, j)
    return i, j


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else name_json
    elems, view = load_config(cfg_path)

    pg.init()
    flags = pg.FULLSCREEN if view["fullscreen"] else 0
    screen = pg.display.set_mode((0,0), flags)
    w, h = screen.get_size()
    n = len(elems)
    rows, cols = get_rows_cols(n)
    cw, ch = w // cols, h // rows

    font = pg.font.SysFont(None, int(min(ch, cw) * 0.8), bold=True)

    cells = {}
    for i, elem in enumerate(elems):
        r, c = divmod(i, cols)
        surf = font.render(elem["char"], True, view["fg"]).convert_alpha()
        
        tx, ty = surf.get_size()
        cx, cy = c*cw + cw//2, r*ch + ch//2
        bx, by = cx - tx//2, cy - ty//2  # базовая позиция (центр по ячейке)
        
        cells[elem["char"]] = {
            "surf": surf,
            "pos": (bx, by),
            "freq": elem["freq"],
            "eps_freq": elem["eps_freq"],
            "pause_mode": elem["pause_mode"],
            "duty": elem["duty"],
            "eps_duty": elem["eps_duty"],
            "pause": elem["pause"],
            "eps_pause": elem["eps_pause"]
        }

    clock = pg.time.Clock()
    t0 = pg.time.get_ticks() / 1000

    info = StreamInfo(name='annotations',
                      type='Events',
                      channel_count=1,
                      nominal_srate=0,
                      channel_format='string',
                      source_id='my_marker_stream')
    outlet = StreamOutlet(info)

    chars = list(view["text"] + ' ' * (rows * cols - len(view["text"])))
    chars_mat = np.array(chars).reshape((rows, cols))

    # основной цикл
    is_run = True
    is_print = False
    i, j = -2, -2
    while is_run:
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    is_run = False

                if event.key == pg.K_s:
                    outlet.push_sample(['exp_start'])

                if event.key == pg.K_e:
                    outlet.push_sample(['exp_end'])
        
        screen.fill(view["bg"])
        t = pg.time.get_ticks()/1000 - t0
        
        if not is_print:
            is_print = True
            i, j = get_rand_pos_without_neighbors(rows, cols, n, i, j)
            char = chars_mat[i, j]
            params = cells[char]
            freq = params["freq"] + random.uniform(-params["eps_freq"], params["eps_freq"])
            duty = params["duty"] + random.uniform(-params["eps_duty"], params["eps_duty"])
            pause = params["pause"] + random.uniform(-params["eps_pause"], params["eps_pause"])
            pause_mode = params["pause_mode"]
            outlet.push_sample(["stim_on_" + char])

        if t < duty/freq: # длительность показа
            screen.blit(params["surf"], params["pos"])
        elif (pause_mode == "duty" and not (duty/freq <= t < 1/freq)) or \
             (pause_mode == "pause" and not (t < duty/freq + pause)):
                outlet.push_sample(["stim_off_" + char])
                t0 = pg.time.get_ticks() / 1000  # сброс времени
                is_print = False

        pg.display.flip()
        clock.tick(view["fps"])

if __name__ == "__main__":
    main()
