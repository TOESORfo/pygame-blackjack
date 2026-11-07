import math, random, pygame, os

pygame.init()

WIDTH, HEIGHT  = 900, 600
CARD_W, CARD_H = 80, 120
PLAYER_Y       = 400
DEALER_Y       = 150
PILE_X, PILE_Y = 780, 240
BALANCE_FILE   = "balance.txt"

screen  = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Blackjack")
font    = pygame.font.SysFont("arial", 28)
bigfont = pygame.font.SysFont("arial", 40)
clock   = pygame.time.Clock()

RANKS  = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
SUITS  = ["clubs", "spades", "hearts", "diamonds"]
VALUES = {"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,
          "10":10,"J":10,"Q":10,"K":10,"A":11}

SUIT_ROW = {"clubs":0, "spades":1, "hearts":2, "diamonds":3}

def load_spritesheet():
    sheet = pygame.image.load("assets/cards.png").convert_alpha()
    sw, sh = sheet.get_size()
    cell_w = sw / 14
    cell_h = sh / 4
    images = {}
    for suit, row in SUIT_ROW.items():
        for col, rank in enumerate(RANKS, start=1):
            x = round(col * cell_w)
            y = round(row * cell_h)
            w = round((col + 1) * cell_w) - x
            h = round((row + 1) * cell_h) - y
            crop = sheet.subsurface((x, y, w, h))
            images[(rank, suit)] = pygame.transform.scale(crop, (CARD_W, CARD_H))
    back = sheet.subsurface((0, 0, round(cell_w), round(cell_h)))
    images["back"] = pygame.transform.scale(back, (CARD_W, CARD_H))
    return images

IMAGES = load_spritesheet()


def load_balance():
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE) as f:
            return int(f.read().strip())
    return 500

def save_balance(b):
    with open(BALANCE_FILE, "w") as f:
        f.write(str(b))


def draw_pile(surface):
    for i in range(5):
        surface.blit(IMAGES["back"], (PILE_X - i*2, PILE_Y - i*2))


class Card:
    SPEED    = 8
    FLIP_SPD = 3

    def __init__(self, rank, suit, tx, ty, hidden=False):
        self.rank        = rank
        self.suit        = suit
        self.x, self.y   = float(PILE_X), float(PILE_Y)
        self.tx, self.ty = float(tx), float(ty)
        self.hidden      = hidden
        self.sliding     = True
        self.flipping    = False
        self.flip_pct    = 0.0
        self.draw_w      = float(CARD_W)

    @property
    def done(self):
        return not self.sliding and not self.flipping

    def start_flip(self):
        if not self.sliding and self.hidden and not self.flipping:
            self.flipping = True
            self.flip_pct = 0.0

    def update(self):
        if self.sliding:
            dx, dy = self.tx - self.x, self.ty - self.y
            d = math.hypot(dx, dy)
            if d <= self.SPEED:
                self.x, self.y = self.tx, self.ty
                self.sliding = False
            else:
                self.x += dx / d * self.SPEED
                self.y += dy / d * self.SPEED
        elif self.flipping:
            self.flip_pct += self.FLIP_SPD
            if self.flip_pct >= 100:
                self.flip_pct = 100
                self.draw_w   = float(CARD_W)
                self.flipping = False
                self.hidden   = False
            elif self.flip_pct <= 50:
                self.draw_w = CARD_W * (1 - self.flip_pct / 50)
            else:
                self.hidden = False
                self.draw_w = CARD_W * ((self.flip_pct - 50) / 50)

    def draw(self, surface):
        w   = max(2, int(self.draw_w if self.flipping else CARD_W))
        ox  = int(self.x) + (CARD_W - w) // 2
        img = IMAGES["back"] if self.hidden else IMAGES[(self.rank, self.suit)]
        scaled = img if w == CARD_W else pygame.transform.scale(img, (w, CARD_H))
        surface.blit(scaled, (ox, int(self.y)))


cards = []

def busy():
    return any(not c.done for c in cards)

def make_deck():
    d = [(r, s) for r in RANKS for s in SUITS]
    random.shuffle(d)
    return d

def hand_value(hand):
    v, a = sum(VALUES[r] for r, s in hand), sum(1 for r, s in hand if r == "A")
    while v > 21 and a:
        v -= 10; a -= 1
    return v

def card_x(i):
    return 100 + i * 100

def spawn(rank, suit, tx, ty, hidden=False):
    c = Card(rank, suit, tx, ty, hidden)
    cards.append(c)
    return c


balance    = load_balance()
bet        = 0
player_won = None

deck = make_deck()
player_hand, dealer_hand   = [], []
player_cards, dealer_cards = [], []
game_over, message, state  = False, "", "betting" if balance > 0 else "kicked"


def new_game():
    global deck, player_hand, dealer_hand, player_cards, dealer_cards
    global game_over, message, state, player_won, bet
    cards.clear()
    deck = make_deck()
    player_hand, dealer_hand   = [], []
    player_cards, dealer_cards = [], []
    game_over, message         = False, ""
    player_won                 = None
    bet                        = 0
    state                      = "betting" if balance > 0 else "kicked"

def start_deal():
    global state
    state = "dealing"
    for who, hide in [("p",False),("d",False),("p",False),("d",True)]:
        r, s = deck.pop()
        if who == "p":
            player_cards.append(spawn(r, s, card_x(len(player_hand)), PLAYER_Y))
            player_hand.append((r, s))
        else:
            dealer_cards.append(spawn(r, s, card_x(len(dealer_hand)), DEALER_Y, hide))
            dealer_hand.append((r, s))

def hit():
    r, s = deck.pop()
    player_cards.append(spawn(r, s, card_x(len(player_hand)), PLAYER_Y))
    player_hand.append((r, s))

def dealer_hit():
    r, s = deck.pop()
    dealer_cards.append(spawn(r, s, card_x(len(dealer_hand)), DEALER_Y))
    dealer_hand.append((r, s))

def reveal():
    for c in dealer_cards:
        c.start_flip()

def evaluate():
    p, d = hand_value(player_hand), hand_value(dealer_hand)
    if d > 21: return "Dealer Busts! You Win!", True
    if p > d:  return "You Win!", True
    if p < d:  return "Dealer Wins!", False
    return "Draw!", None


running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state == "betting":
                if event.key == pygame.K_UP:
                    if bet + 10 <= balance:
                        bet += 10
                elif event.key == pygame.K_DOWN:
                    bet = max(0, bet - 10)
                elif event.key == pygame.K_RETURN and bet > 0:
                    start_deal()

            elif state == "playing" and not busy():
                if event.key == pygame.K_h:
                    hit()
                    if hand_value(player_hand) > 21:
                        message    = "Player Busts!"
                        player_won = False
                        state      = "reveal"
                elif event.key == pygame.K_s:
                    state = "reveal"

            if state == "done" and event.key == pygame.K_r:
                new_game()

    if state == "dealing" and not busy():
        state = "playing"
    elif state == "reveal":
        reveal()
        state = "dealer_turn"
    elif state == "dealer_turn" and not busy():
        if not message and hand_value(dealer_hand) < 17:
            dealer_hit()
        else:
            if not message:
                message, player_won = evaluate()
            if player_won == True:
                balance += bet
            elif player_won == False:
                balance -= bet
            save_balance(balance)
            game_over = True
            state     = "kicked" if balance <= 0 else "done"

    for c in cards:
        c.update()

    screen.fill((0, 120, 0))
    draw_pile(screen)
    screen.blit(bigfont.render("BLACKJACK", True, (255,255,255)), (320, 20))

    if state == "betting":
        screen.blit(bigfont.render("Place Your Bet", True, (255,255,255)), (290, 200))
        screen.blit(font.render(f"Balance: ${balance}", True, (255,255,255)), (350, 270))
        screen.blit(bigfont.render(f"Bet: ${bet}", True, (255,255,0)), (370, 310))
        screen.blit(font.render("UP / DOWN to adjust   ENTER to deal", True, (255,255,255)), (210, 370))

    elif state == "kicked":
        screen.blit(bigfont.render("You're broke!", True, (255,80,80)), (310, 200))
        screen.blit(font.render("The casino has asked you to leave.", True, (255,255,255)), (240, 270))
        screen.blit(font.render("Delete balance.txt to get $500 and try again.", True, (255,255,255)), (185, 310))
        screen.blit(font.render("Close the window to exit.", True, (255,255,255)), (300, 350))

    else:
        screen.blit(font.render("Dealer", True, (255,255,255)), (100, 120))
        screen.blit(font.render("Player", True, (255,255,255)), (100, 360))

        for c in cards:
            c.draw(screen)

        d_total = hand_value(dealer_hand) if game_over else VALUES.get(dealer_hand[0][0], 0)
        screen.blit(font.render(f"Total: {hand_value(player_hand)}", True, (255,255,255)), (100, 520))
        screen.blit(font.render(f"Total: {d_total}",                True, (255,255,255)), (100, 300))
        screen.blit(font.render(f"Balance: ${balance}  Bet: ${bet}", True, (255,255,255)), (100,  70))
        screen.blit(font.render("H = Hit   S = Stand   R = New Game", True, (255,255,255)), (230, 565))

        if game_over and message:
            if player_won == True:   color = (255, 255, 0)
            elif player_won == None: color = (255, 255, 255)
            else:                    color = (255, 80,  80)
            msg = bigfont.render(message, True, color)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()