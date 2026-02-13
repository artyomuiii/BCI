import pygame as pg


class EventHandler:
    def __init__(self, app):
        self.app = app

    def process(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.app.quit()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.app.quit()
                elif event.key == pg.K_s:
                    self.app.start_experiment()
                elif event.key == pg.K_e:
                    self.app.end_experiment()
                elif event.key == pg.K_SPACE:
                    self.app.send_marker("pressed_space")
