import pygame as pg
import random
pg.init()

screen_width = 1600
screen_height = 800

screen =  pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Poker")


#POKER TABLE
poker_table = pg.transform.scale(pg.image.load('PokerBots/Assets/Poker_Table.png'),(screen_width, screen_height))
poker_table_rect = poker_table.get_rect()

#CARDS
suits = ["Spades", "Hearts", "Clubs", "Diamonds"]
ranks = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King"]

card_images = {}

for suit in suits:
    for rank in ranks:
        card_name = f"{rank}_of_{suit}"
        file_path = f"PokerBots/Assets/{rank} of {suit}.png"
        card_images[card_name] = pg.transform.scale(pg.image.load(file_path), (64,128))

#CHIPS
chip_values = [5, 10, 25, 50, 100, 500]

chip_images = {}

for value in chip_values:
    chip_name = f"{value} Chip"
    file_path = f"PokerBots/Assets/{value}Chip_TopDown.png"
    chip_images[chip_name] = card_images[card_name] = pg.transform.scale(pg.image.load(file_path), (64,64))


#GAME LOOP
#RANDOMISER JUST TO TEST THE IMAGE LOADING 
#NEEDS CHANGING
random_suit = random.choice(suits)
random_rank = random.choice(ranks)
random_card_name = f"{random_rank}_of_{random_suit}"
random_card_image = card_images[random_card_name]

random_chip_value = random.choice(chip_values)
random_chip_name = f"{random_chip_value} Chip"
random_chip_image = chip_images[random_chip_name]



running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
    screen.blit(poker_table, poker_table_rect)
    screen.blit(random_card_image, (500, 125))
    screen.blit(random_chip_image, (500, 425))

    pg.display.flip()        
            
pg.quit()