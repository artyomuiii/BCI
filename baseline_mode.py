# pip install pygame, pylsl
import pygame, sys, math, json, time
from random import random
#from pylsl import StreamInfo, StreamOutlet

# --- utils ---
def near_square(n):
    r = int(math.sqrt(n))
    while r>1 and n%r:
        r-=1
    if r>1:
        return r, n//r
    r = int(math.sqrt(n)); c = math.ceil(n/r)
    return r, c

def load_config(path):
    with open(path, "r", encoding="utf-8") as f: cfg = json.load(f)
    d = cfg.get("defaults", {})
    view = cfg.get("view", {})
    text = cfg.get("text", "")
    items = cfg.get("items", [])
    # построим список элементов
    elems = []
    if text:
        elems = [{"char": ch} for ch in text]
    # применим overrides из items
    idxmap = {}
    for it in items:
        i = it.get("index")
        if i is not None:
            if i>=len(elems): elems.extend({"char":" "} for _ in range(i-len(elems)+1))
            elems[i] = {**elems[i], **{k:v for k,v in it.items() if k!="index"}}
        else:
            elems.append(it)  # полноценный элемент с char
    # defaults
    for i,e in enumerate(elems):
        e.setdefault("char", " ")
        e.setdefault("mode", d.get("mode","h"))
        e.setdefault("freq", float(d.get("freq",1.0)))
        e.setdefault("amp",  int(d.get("amp",120)))
        e.setdefault("phase", float(d.get("phase",0.0)) + i*float(d.get("phase_step",0.0)))
        e.setdefault("angle", float(d.get("angle",45)))
        e.setdefault("size",  int(d.get("size",0)))
    return elems, {
        "fullscreen": bool(view.get("fullscreen", True)),
        "fps": int(view.get("fps", 60)),
        "bg": tuple(view.get("bg", [0,0,0])),
        "fg": tuple(view.get("fg", [255,255,255]))
    }

# --- main ---
cfg_path = sys.argv[1] if len(sys.argv)>1 else "config.json"

#info = StreamInfo(name='annotations', type='Events', channel_count=1, nominal_srate=0, channel_format='string', source_id='my_marker_stream')

#outlet = StreamOutlet(info)



elems, view = load_config(cfg_path)

pygame.init()
flags = pygame.FULLSCREEN if view["fullscreen"] else 0
#flags = pygame.RESIZABLE
screen = pygame.display.set_mode(flags = flags)
w, h = screen.get_size()
N = len(elems)
rows, cols = near_square(N)
cw, ch = w//cols, h//rows

# шрифт будем кэшировать по размеру
font_cache = {}
def get_font(sz):
    if sz not in font_cache:
        font_cache[sz] = pygame.font.SysFont(None, sz, bold=True)
    return font_cache[sz]

# предрасчёт спрайтов и базовых позиций
cells = []
for i,e in enumerate(elems):
    r, c = divmod(i, cols)
    # авто-размер символа от ячейки, если size=0
    fsize = e["size"] or int(min(ch, cw)*0.8)
    font = get_font(fsize)
    surf = font.render(e["char"], True, view["fg"]).convert_alpha()
    surf_stat = font.render(e["char"], True, [255,255,255]).convert_alpha()
    tx, ty = surf.get_size()
    cx, cy = c*cw + cw//2, r*ch + ch//2
    bx, by = cx - tx//2, cy - ty//2  # базовая позиция (центр по ячейке)
    mode = e["mode"].lower()
    if mode.startswith("h"): dx, dy = 1.0, 0.0
    elif mode.startswith("v"): dx, dy = 0.0, 1.0
    else:  # диагональ
        ang = math.radians(e["angle"])
        dx, dy = math.cos(ang), math.sin(ang)
    # нормализуем вектор (на всякий)
    norm = (dx*dx + dy*dy) ** 0.5 or 1.0
    dx, dy = dx/norm, dy/norm
    cells.append((
        surf_stat, surf, bx, by,
        float(e["freq"]), int(e["amp"]), float(e["phase"]),
        dx, dy, True
    ))

#print(cells)


N_first = 10
N_last = 10

wait_millisec = 1000

'''
for i in range(N_first):
    outlet.push_sample([f'start_empty_{i}'])
    pygame.time.wait(wait_millisec)
    
outlet.push_sample(['start_trial'])
pygame.time.wait(wait_millisec)
'''

clock = pygame.time.Clock()
t0 = pygame.time.get_ticks()/1000.0
TWOPI = 2*math.pi


# цикл
while True:
    for e in pygame.event.get():
        if e.type==pygame.QUIT or (e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE) or (e.type==pygame.KEYDOWN and e.key==pygame.K_q):
            #end of stream
            #print("Now I'm become Death")
            #print("The destoyer of worlds")
            #outlet.push_sample(['end_trial'])
            #pygame.time.wait(wait_millisec)
            #for i in range(N_last):
            #    outlet.push_sample([f'last_empty_{i}'])
            #    pygame.time.wait(wait_millisec)
            
            pygame.quit()
            sys.exit()
        if e.type==pygame.KEYDOWN and e.key==pygame.K_s:
            print('start')
        if e.type==pygame.KEYDOWN and e.key==pygame.K_d:
            print('end')
        
            
    t = pygame.time.get_ticks()/1000.0 - t0
    #print(t)
    s = math.sin
    screen.fill(view["bg"])
    for index, (surf_stat, surf, bx, by, f, amp, ph, dx, dy, flg) in enumerate(cells):
        disp = amp * s(TWOPI*f*t + ph)
        if abs(disp) < 1 and flg:
            dx, dy = math.cos(TWOPI * random()), math.sin(TWOPI * random())
            cells[index] = (surf_stat, surf, bx, by, f, amp, ph, dx, dy, False)
        if abs(disp) >= 1 and not flg:
            cells[index] = (surf_stat, surf, bx, by, f, amp, ph, dx, dy, True)
        #if abs(disp) < 1e-13:
        #    print(disp)        
        #print(disp)
        #dx, dy = math.cos(TWOPI * random()), math.sin(TWOPI * random())
        
        x = int(bx + disp*dx)
        y = int(by + disp*dy)
        screen.blit(surf, (x, y))
        screen.blit(surf_stat, (bx, by))
    pygame.display.flip()
    clock.tick(view["fps"])

#print("end")

"""
# mode: "h" | "v" | "d" (диагональ). для "d" угол angle в градусах от оси X.
# • freq — Гц, amp — пиксели, phase — радианы. phase_step добавляется к фазе по индексу i (удобно для «волны»).
# • size: 0 — авто по ячейке; иначе размер шрифта в пикселях.
# • items: список переопределений по index (позиция в строке text), либо можно задать полностью: { "char": "X", ... } — тогда символ берётся из этого поля.

# автоматическая раскладка стремится к квадратной матрице и равномерно делит экран на ячейки.
#  • каждый символ отрисовывается один раз (поверхности кэшируются), в цикле — только синус и быстрый blit.
#  • phase_step удобно использовать для «бегущей волны» по индексам.
#  • выход — ESC.
"""
