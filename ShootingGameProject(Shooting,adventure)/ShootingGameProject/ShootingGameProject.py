from tkinter import *
from PIL import Image, ImageTk
import random
import time
import math

WIDTH, HEIGHT = 480, 640
FPS = 30

class Game:
    def __init__(self):
        # -----------------
        # 윈도우
        # -----------------
        self.window = Tk()
        self.window.title("Shooting")
        self.window.geometry(f"{WIDTH}x{HEIGHT}")

        self.canvas = Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack(expand=True, fill=BOTH)

        # -----------------
        # 이미지 로드
        # -----------------
        self.player_frames = [PhotoImage(file=f"image/player_{i}.png") for i in range(1,3)]
        self.enemy_frames = {
            "normal": [PhotoImage(file="image/enemy_normal.png")],
            "fast": [PhotoImage(file=f"image/enemy_fast_{i}.png") for i in range(1,3)],
            "tank": [PhotoImage(file="image/enemy_tank.png")],
            "boss": [PhotoImage(file=f"image/boss_{i}.png") for i in range(1,3)]
        }
        self.bullet_img = PhotoImage(file="image/bullet.png")

        # -----------------
        # 배경 이미지 불러오기 & 리사이즈
        # -----------------
        bg_img_raw = Image.open("image/background.png")
        bg_img_resized = bg_img_raw.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        self.bg_img = ImageTk.PhotoImage(bg_img_resized)

        # -----------------
        # 키 입력
        # -----------------
        self.keys = set()
        self.window.bind("<KeyPress>", self.keyPressHandler)
        self.window.bind("<KeyRelease>", self.keyReleaseHandler)
        self.window.protocol("WM_DELETE_WINDOW", self.onClose)

        # -----------------
        # 상태
        # -----------------
        self.running = False
        self.player_frame_index = 0
        self.last_frame_time = 0

        # 최고 점수
        self.high_score = 0

        # 버튼 객체 초기화
        self.start_button = None
        self.exit_button = None

        # 시작 화면
        self.showStartScreen()

        # -----------------
        # 메인 루프
        # -----------------
        while True:
            try:
                if self.running:
                    self.gameUpdate()
            except TclError:
                return
            self.window.after(int(1000/FPS))
            self.window.update()

    # ---------------- 시작 화면 ----------------
    def showStartScreen(self):
        self.running = False
        self.canvas.delete("all")
        self.canvas.create_rectangle(0,0,WIDTH,HEIGHT, fill="lightblue")
        self.canvas.create_text(240, 150, text="Shooting", font=("Arial", 36, "bold"))

        # 최고 점수 표시 (오른쪽 위)
        if self.high_score > 0:
            self.canvas.create_text(WIDTH-10, 10, anchor="ne", text=f"최고 점수: {self.high_score}", font=("Arial", 12))

        # 시작 화면 버튼 생성
        if self.start_button is None:
            self.start_button = Button(self.window, text="시작하기", command=self.startGame)
        if self.exit_button is None:
            self.exit_button = Button(self.window, text="나가기", command=self.onClose)
        self.start_button.place(x=190, y=260, width=100, height=40)
        self.exit_button.place(x=190, y=320, width=100, height=40)

        self.canvas.create_text(240, 600, text="← → / A D 이동   Space 공격", font=("Arial", 11))

    # ---------------- 게임 시작 ----------------
    def startGame(self):
        self.canvas.delete("all")
        self.running = True

        # 시작 화면 버튼 제거
        if self.start_button:
            self.start_button.place_forget()
        if self.exit_button:
            self.exit_button.place_forget()

        # 배경
        self.canvas.create_image(0,0, image=self.bg_img, anchor="nw")

        # 플레이어
        self.player = self.canvas.create_image(240, 580, image=self.player_frames[0])
        self.player_hp = 3
        self.player_speed = 6
        self.player_attack = 1

        # 게임 상태
        self.score = 0
        self.wave = 1
        self.diff = 1
        self.enemy_speed = 2

        self.enemies = []
        self.bullets = []

        self.last_fire = 0
        self.fire_delay = 0.5

        # UI
        self.drawUI()
        self.startWave()

    # ---------------- UI ----------------
    def drawUI(self):
        self.ui_hp = self.canvas.create_text(10, 10, anchor="nw")
        self.ui_score = self.canvas.create_text(470, 10, anchor="ne")
        self.ui_wave = self.canvas.create_text(240, 10)
        self.updateUI()

    def updateUI(self):
        self.canvas.itemconfig(self.ui_hp, text=f"HP : {self.player_hp}")
        self.canvas.itemconfig(self.ui_score, text=f"Score : {self.score}")
        self.canvas.itemconfig(self.ui_wave, text=f"Wave : {self.wave}")

    # ---------------- 웨이브 ----------------
    def startWave(self):
        self.enemies.clear()
        if self.wave % 5 == 0:
            eid = self.canvas.create_image(240,60,image=self.enemy_frames["boss"][0])
            self.enemies.append(("boss", eid, 30+self.diff*5, 0, time.time()))
        else:
            for _ in range(self.wave+2):
                x = random.randint(40, WIDTH-40)
                etype = random.choice(["normal","fast","tank"])
                if etype not in self.enemy_frames or not self.enemy_frames[etype]:
                    continue
                eid = self.canvas.create_image(x, 40, image=self.enemy_frames[etype][0])
                self.enemies.append((etype, eid, 1+self.diff, 0, time.time()))

    # ---------------- 게임 업데이트 ----------------
    def gameUpdate(self):
        if time.time() - self.last_frame_time > 0.2:
            self.player_frame_index = (self.player_frame_index+1)%len(self.player_frames)
            self.canvas.itemconfig(self.player, image=self.player_frames[self.player_frame_index])
            self.last_frame_time = time.time()

        self.movePlayer()
        self.moveBullets()
        self.moveEnemies()
        self.checkCollision()

        if not self.enemies:
            self.wave +=1
            if self.wave%5 ==1:
                self.diff+=1
                self.enemy_speed+=0.5
            self.startWave()
            self.updateUI()

    # ---------------- 플레이어 이동 / 공격 ----------------
    def movePlayer(self):
        if 37 in self.keys or 65 in self.keys:
            self.canvas.move(self.player,-self.player_speed,0)
        if 39 in self.keys or 68 in self.keys:
            self.canvas.move(self.player,self.player_speed,0)
        if 32 in self.keys:
            self.fire()

    def fire(self):
        if time.time() - self.last_fire < self.fire_delay:
            return
        self.last_fire = time.time()
        x,y = self.canvas.coords(self.player)
        bullet = self.canvas.create_image(x, y-20, image=self.bullet_img)
        self.bullets.append(bullet)

    # ---------------- 이동 처리 ----------------
    def moveBullets(self):
        for b in self.bullets[:]:
            self.canvas.move(b,0,-12)
            if self.canvas.coords(b)[1]<0:
                self.canvas.delete(b)
                self.bullets.remove(b)

    def moveEnemies(self):
        for idx,e in enumerate(self.enemies[:]):
            etype,eid,hp,frame_idx,last_time = e
            try:
                x,y = self.canvas.coords(eid)
            except TclError:
                if e in self.enemies:
                    self.enemies.remove(e)
                continue

            frames = self.enemy_frames[etype]
            if time.time() - last_time > 0.2 and len(frames) >1:
                frame_idx = (frame_idx+1)%len(frames)
                self.canvas.itemconfig(eid,image=frames[frame_idx])
                last_time = time.time()
            if e in self.enemies:
                idx = self.enemies.index(e)
                self.enemies[idx]=(etype,eid,hp,frame_idx,last_time)

            if etype=="normal":
                self.canvas.move(eid,0,self.enemy_speed)
            elif etype=="fast":
                self.canvas.move(eid, 3*math.sin(time.time()*5), self.enemy_speed)
            elif etype=="tank":
                self.canvas.move(eid, 2*math.sin(time.time()*2), self.enemy_speed/2)
            elif etype=="boss":
                self.canvas.move(eid, 2*math.sin(time.time()), 0.5)

            if self.canvas.coords(eid)[1]>HEIGHT:
                self.canvas.delete(eid)
                if e in self.enemies:
                    self.enemies.remove(e)
                self.player_hp -=1
                self.updateUI()
                if self.player_hp<=0:
                    self.gameOver()

    # ---------------- 충돌 ----------------
    def checkCollision(self):
        for e in self.enemies[:]:
            etype,eid,hp,frame_idx,last_time = e
            try:
                ex,ey = self.canvas.coords(eid)
            except TclError:
                if e in self.enemies:
                    self.enemies.remove(e)
                continue

            for b in self.bullets[:]:
                bx,by = self.canvas.coords(b)
                if abs(bx-ex)<30 and abs(by-ey)<30:
                    self.canvas.delete(b)
                    self.bullets.remove(b)
                    hp -= self.player_attack
                    if hp<=0:
                        self.canvas.delete(eid)
                        if e in self.enemies:
                            self.enemies.remove(e)
                        self.score +=200 if etype=="boss" else 10
                        self.updateUI()
                    else:
                        if e in self.enemies:
                            idx = self.enemies.index(e)
                            self.enemies[idx] = (etype,eid,hp,frame_idx,last_time)
                    break

    # ---------------- 게임오버 ----------------
    def gameOver(self):
        self.running=False
        if self.score > self.high_score:
            self.high_score = self.score  # 최고 점수 갱신

        self.canvas.create_text(240,320,text="GAME OVER", font=("Arial",32),fill="red")
        self.canvas.after(2000,self.showStartScreen)

    # ---------------- 키 ----------------
    def keyPressHandler(self,event):
        if event.keycode==27:
            self.onClose()
        else:
            self.keys.add(event.keycode)

    def keyReleaseHandler(self,event):
        if event.keycode in self.keys:
            self.keys.remove(event.keycode)

    def onClose(self):
        self.window.destroy()


if __name__=="__main__":
    Game()

