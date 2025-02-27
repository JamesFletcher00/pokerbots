import pygame as pg
pg.init()

screen_width = 1600
screen_height = 800

screen =  pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Poker")


#POKER TABLE
poker_table = pg.image.load('Assets/Poker Table.png')
#poker_table = pg.transform.scale()
#CARDS


#CHIPS



running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
            
            
pg.quit()