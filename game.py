import pygame
import chess
import subprocess
import numpy as np
import time

# ---------------- CONFIG ----------------
BOARD_SIZE = 640
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS

SIDE_SPACE = 160
WIN_WIDTH = BOARD_SIZE + SIDE_SPACE*2
WIN_HEIGHT = BOARD_SIZE + 140

WHITE_COLOR = (240, 240, 240)
BLACK_COLOR = (100, 130, 180)
HIGHLIGHT_COLOR = (255, 220, 90)
LAST_MOVE_COLOR = (255, 80, 80)
MOVE_SPEED = 20

PIECE_VALUES = {'P':1,'N':3,'B':3,'R':5,'Q':9,'K':0,
                'p':1,'n':3,'b':3,'r':5,'q':9,'k':0}

PIECES = {
    'P': 'assets/P(2).png','R': 'assets/R(2).png','N': 'assets/N(2).png',
    'B': 'assets/B(2).png','Q': 'assets/Q(2).png','K': 'assets/K(2).png',
    'p': 'assets/p.png','r': 'assets/r.png','n': 'assets/n.png',
    'b': 'assets/b.png','q': 'assets/q.png','k': 'assets/k.png'
}

STOCKFISH_PATH = r"C:\Users\USER\Downloads\stockfish\stockfish-windows-x86-64-avx2.exe"

# ---------------- INIT ----------------
pygame.init()
WIN = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption("♟ Chess with Undo/Redo & Clock & Score")
font = pygame.font.SysFont("Segoe UI", 20)
large_font = pygame.font.SysFont("Segoe UI", 28, bold=True)

for key in PIECES:
    img = pygame.image.load(PIECES[key])
    PIECES[key] = pygame.transform.scale(img,(SQUARE_SIZE,SQUARE_SIZE))

board = chess.Board()

# ---------------- VARIABLES ----------------
user_score = 0
ai_score = 0

user_time = 300  # 5 minutes
ai_time = 300
last_update_time = time.time()

move_history=[]
redo_stack=[]
message = ""
message_time = 0
MESSAGE_DURATION = 2

# ---------------- FUNCTIONS ----------------
def choose_color():
    choosing = True
    color = None
    while choosing:
        WIN.fill((200,200,200))
        white_text = large_font.render("Play as White", True, (0,0,0))
        black_text = large_font.render("Play as Black", True, (0,0,0))
        WIN.blit(white_text,(WIN_WIDTH//2 - white_text.get_width()//2,200))
        WIN.blit(black_text,(WIN_WIDTH//2 - black_text.get_width()//2,300))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                pygame.quit(); exit()
            if event.type==pygame.MOUSEBUTTONDOWN:
                x,y=event.pos
                if 200<=y<=200+white_text.get_height():
                    color='white'; choosing=False
                elif 300<=y<=300+black_text.get_height():
                    color='black'; choosing=False
    return color

def draw_board(win):
    for row in range(ROWS):
        for col in range(COLS):
            color = WHITE_COLOR if (row+col)%2==0 else BLACK_COLOR
            pygame.draw.rect(win,color,(SIDE_SPACE + col*SQUARE_SIZE, row*SQUARE_SIZE, SQUARE_SIZE,SQUARE_SIZE))

def draw_pieces(win,board,moving_piece=None,moving_pos=None):
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            row = 7 - (square//8)
            col = square%8
            if moving_piece and (row,col)==moving_piece: continue
            win.blit(PIECES[str(piece)],(SIDE_SPACE + col*SQUARE_SIZE,row*SQUARE_SIZE))
    if moving_piece and moving_pos is not None:
        piece = board.piece_at(moving_piece[0]*8+moving_piece[1])
        if piece:
            win.blit(PIECES[str(piece)], (SIDE_SPACE + moving_pos[0], moving_pos[1]))

def highlight_square(win,row,col,color):
    pygame.draw.rect(win,color,(SIDE_SPACE + col*SQUARE_SIZE,row*SQUARE_SIZE,SQUARE_SIZE,SQUARE_SIZE),5)

def draw_button(x,y,text):
    rect = pygame.Rect(x,y,100,35)
    pygame.draw.rect(WIN,(180,180,200),rect,border_radius=6)
    pygame.draw.rect(WIN,(100,100,120),rect,2,border_radius=6)
    txt = font.render(text,True,(20,20,20))
    WIN.blit(txt,(x+10,y+5))
    return rect

def draw_clock(x,y,seconds,label):
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    txt = f"{label}: {mins:02}:{secs:02}"
    WIN.blit(large_font.render(txt,True,(0,0,0)),(x,y))

def captured_pieces(board):
    white_captured=[]
    black_captured=[]
    for p in ['P','N','B','R','Q']:
        white_on_board = sum(1 for sq in chess.SQUARES if str(board.piece_at(sq))==p)
        black_on_board = sum(1 for sq in chess.SQUARES if str(board.piece_at(sq))==p.lower())
        total_count = {'P':8,'N':2,'B':2,'R':2,'Q':1}[p]
        white_captured.append((p, total_count - white_on_board))
        black_captured.append((p.lower(), total_count - black_on_board))
    return white_captured, black_captured

def calculate_scores(board):
    user_score = 0
    ai_score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            val = PIECE_VALUES[str(piece)]
            if piece.color == (user_color=='white'):
                user_score += val
            else:
                ai_score += val
    return user_score, ai_score

def draw_info(win):
    global user_score, ai_score
    user_score, ai_score = calculate_scores(board)

    white_cap, black_cap = captured_pieces(board)

    # Black lost on left
    y_offset = 20
    x_off = 20
    for piece,count in black_cap:
        for _ in range(count):
            small_img = pygame.transform.scale(PIECES[piece],(35,35))
            WIN.blit(small_img,(x_off, y_offset))
            y_offset += 40

    # White lost on right
    y_offset = 20
    x_off = WIN_WIDTH - SIDE_SPACE + 15
    for piece,count in white_cap:
        for _ in range(count):
            small_img = pygame.transform.scale(PIECES[piece],(35,35))
            WIN.blit(small_img,(x_off, y_offset))
            y_offset += 40

    # Clocks below board
    draw_clock(SIDE_SPACE, BOARD_SIZE + 10, int(user_time), "User")
    draw_clock(WIN_WIDTH - SIDE_SPACE - 150, BOARD_SIZE + 10, int(ai_time), "AI")

    # Scores below clocks
    WIN.blit(font.render(f"Score: {user_score}", True, (0,0,0)), (SIDE_SPACE, BOARD_SIZE + 50))
    WIN.blit(font.render(f"Score: {ai_score}", True, (0,0,0)), (WIN_WIDTH - SIDE_SPACE - 150, BOARD_SIZE + 50))

    # Undo/Redo buttons
    undo_rect = draw_button(WIN_WIDTH//2 - 120, BOARD_SIZE + 60, "Undo")
    redo_rect = draw_button(WIN_WIDTH//2 + 20, BOARD_SIZE + 60, "Redo")

    # Message
    if message and time.time() - message_time < MESSAGE_DURATION:
        msg_text = font.render(message, True, (200,0,0))
        WIN.blit(msg_text, (WIN_WIDTH//2 - msg_text.get_width()//2, BOARD_SIZE + 30))

    return undo_rect, redo_rect

def animate_move(board,start,end):
    start_px = np.array([start[1]*SQUARE_SIZE,start[0]*SQUARE_SIZE],dtype=float)
    end_px = np.array([end[1]*SQUARE_SIZE,end[0]*SQUARE_SIZE],dtype=float)
    direction = end_px - start_px
    steps = max(abs(direction[0]),abs(direction[1]))//MOVE_SPEED +1
    step_vector = direction/steps
    pos = start_px.copy()
    for _ in range(int(steps)):
        pos += step_vector
        draw_board(WIN)
        draw_pieces(WIN,board,moving_piece=start,moving_pos=pos)
        draw_info(WIN)
        pygame.display.update()
        pygame.time.delay(20)

def ai_move(board):
    stockfish = subprocess.Popen(
        STOCKFISH_PATH,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        bufsize=1
    )
    stockfish.stdin.write(f"position fen {board.fen()}\n")
    stockfish.stdin.flush()
    stockfish.stdin.write("go movetime 300\n")
    stockfish.stdin.flush()
    move=None
    while True:
        output=stockfish.stdout.readline().strip()
        if output.startswith("bestmove"):
            move=output.split()[1]
            break
    stockfish.terminate()
    if move:
        start=((7-int(move[1])),ord(move[0])-97)
        end=((7-int(move[3])),ord(move[2])-97)
        return start,end,move
    return None,None,None

# ---------------- MAIN ----------------
user_color = choose_color()
player_turn = user_color=='white'
selected_square = None
last_move = None
player_start_time = time.time()
ai_start_time = time.time()

running = True
while running:
    # Update clocks
    now = time.time()
    delta = now - last_update_time
    last_update_time = now
    if player_turn:
        user_time -= delta
    else:
        ai_time -= delta

    WIN.fill((200,200,200))
    draw_board(WIN)
    draw_pieces(WIN,board)
    undo_rect, redo_rect = draw_info(WIN)
    if selected_square:
        highlight_square(WIN,selected_square[0],selected_square[1],HIGHLIGHT_COLOR)
    if last_move:
        highlight_square(WIN,last_move[0][0],last_move[0][1],LAST_MOVE_COLOR)
        highlight_square(WIN,last_move[1][0],last_move[1][1],LAST_MOVE_COLOR)
    pygame.display.update()

    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False
        elif event.type==pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            # Undo
            if undo_rect.collidepoint(mx,my) and move_history:
                last = move_history.pop()
                board.pop()
                redo_stack.append(last)
                player_turn = (user_color=='white') if len(move_history)%2==0 else (user_color=='black')
                continue
            # Redo
            elif redo_rect.collidepoint(mx,my) and redo_stack:
                move = redo_stack.pop()
                board.push(move)
                move_history.append(move)
                player_turn = not player_turn
                continue
            # Player move
            if player_turn and SIDE_SPACE <= mx < SIDE_SPACE + BOARD_SIZE:
                row = my//SQUARE_SIZE
                col = (mx - SIDE_SPACE)//SQUARE_SIZE
                piece = board.piece_at((7-row)*8+col)

                if selected_square:
                    start_row,start_col=selected_square
                    move = chess.Move.from_uci(f"{chr(start_col+97)}{8-start_row}{chr(col+97)}{8-row}")
                    if move in board.legal_moves:
                        animate_move(board,selected_square,(row,col))
                        board.push(move)
                        move_history.append(move)
                        redo_stack.clear()
                        last_move=(selected_square,(row,col))
                        selected_square=None
                        player_turn=False
                        ai_start_time=time.time()
                        message = ""
                    else:
                        message = "Illegal move!"
                        message_time = time.time()
                        selected_square=None
                else:
                    if piece:
                        if (user_color=='white' and not piece.color) or (user_color=='black' and piece.color):
                            message = "Cannot move opponent's piece!"
                            message_time = time.time()
                        else:
                            selected_square=(row,col)
                    else:
                        message = "No piece at this square!"
                        message_time = time.time()

    # AI Move
    if not player_turn:
        ai_start,ai_end,ai_uci = ai_move(board)
        if ai_start and ai_end:
            animate_move(board,ai_start,ai_end)
            board.push_uci(ai_uci)
            move_history.append(board.peek())
            redo_stack.clear()
            last_move=(ai_start,ai_end)
        player_turn=True
        player_start_time=time.time()

pygame.quit()
