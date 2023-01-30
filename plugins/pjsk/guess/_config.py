from pathlib import Path

PJSK_GUESS = 'pjsk_guess'
PJSK_ANSWER = 'pjsk_answer'
GUESS_CARD = 'guesscard'
GUESS_MUSIC = 'guessmusic'
pjskguess = {GUESS_CARD: {}, GUESS_MUSIC: {}}
max_tips_count = 3  # 最大提示次数
guess_time = 60
SEdir = Path()