from pathlib import Path

PJSK_GUESS = 'pjsk_guess'
PJSK_ANSWER = 'pjsk_answer'
GUESS_CARD = 'guesscard'
GUESS_MUSIC = 'guessmusic'
pjskguess = {GUESS_CARD: {}, GUESS_MUSIC: {}}
max_tips_count = 3  # 最大提示次数
max_guess_count = 3  # 最大猜测次数
guess_time = 90
SEdir = Path()