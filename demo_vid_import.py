import os
import sys
from pathlib import Path
import time
from collections import deque
import cv2
import matplotlib.pyplot as plt
import numpy as np
from tkinter import filedialog, Tk

# ==========================================
# 0. 階層エラー対策 (パスの自動追加)
# ==========================================
current_dir = Path(__file__).resolve().parent
if hasattr(sys, '_MEIPASS'):
    project_root = Path(sys._MEIPASS)
else:
    project_root = current_dir
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from lib.MIN2_ver1 import MIN2_ignore_sunspots as MIN2
from lib.RANSAC import calculate_west_angle_robust as west_angle
from lib.open_circle_arrow import OpenCircleArrow

# --- [変更] デモ用の動画ファイルパスを指定 ---
VIDEO_PATH = filedialog.askopenfilename(title="動画ファイルを選択", filetypes=[("Video files", "*.mp4 *.avi *.mov")])
acceptable = 1

# ==========================================
# 1. [変更] 動画ファイルの読み込みと設定
# ==========================================
if not os.path.exists(VIDEO_PATH):
    print(f"エラー: 動画ファイル '{VIDEO_PATH}' が見つかりません。")
    sys.exit(1)

cap = cv2.VideoCapture(VIDEO_PATH)

# 動画から解像度を取得
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"動画を読み込みました: {VIDEO_PATH} ({width}x{height})")

buffer = deque(maxlen=500)
plt_drow_waittime = 0.05

def plturn(n):
    if n == 0:
        return 0
    if n < 0:
        g = 1
    else:
        g = -1
    c = 1
    n = abs(n)
    nn = n + n
    while True:
        if nn >= 180:
            return ((180) % (n) + n * (c - 1)) * g
        else:
            c += 1
            nn = n * c

# ==========================================
# 2. リアルタイム処理ループ（動画版）
# ==========================================
try:
    print("loading...")
    plt.ion()
    fig, ax = plt.subplots()

    # 最初のフレームをダミーとして取得
    ret, frame = cap.read()
    if not ret:
        print("動画の読み込みに失敗しました。")
        sys.exit(1)
        
    # 動画がカラー(BGR)の場合、グレースケールに変換
    if len(frame.shape) == 3:
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        img = frame
    
    ax_img = ax.imshow(img, cmap='gray', vmin=0, vmax=255)
    
    circle = plt.Circle((0, 0), 0, fill=True, color='skyblue', linewidth=2,alpha=0.5)
    ax_min2 = ax.add_patch(circle)
    ax_shdw_c, = ax.plot([], [], 'o', color="cyan", markersize=3, alpha=0.4, label="circle center track")
    
    uxc = ("red", "purple")
    grid_lines = []
    for y_val in np.linspace(0, height, 5)[1:-1]:
        line, = ax.plot([0, width], [y_val, y_val], color=uxc[0], linewidth=3, alpha=0.4)
        grid_lines.append(line)
        
    sunline = min(width, height) * 3 / 4 / 2
    ax_sunline, = ax.plot([], [], color=uxc[1], linewidth=3)
    
    fig_text = fig.text(0.01, 0.5, f'turn camera_0°', ha='left', fontsize=20, color=uxc[0])
    arrow = OpenCircleArrow(ax, center=(0, 0.5), radius=100, gap_angle=90, edgecolor=uxc[1], tri_color=uxc[1])
    
    print("complete loading")
    print("デモ動画の再生を開始します。'q' キーで終了するか、グラフウィンドウを閉じてください。")
    
    while True:
        ret, frame = cap.read()
        
        # --- [重要] 動画が終了したら最初のフレームに戻す（ループ再生） ---
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # カラー動画対策（MIN2はグレースケールを想定しているため変換）
        if len(frame.shape) == 3:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            img = frame
        try:
            (cx, cy), r = MIN2(img)
        except Exception as e:
            print()
            print(f"MIN2の処理中にエラーが発生しました: {e}")
            continue
        buffer.append([cx, cy])

        buf_arr = np.array(buffer)
        recent_pts = buf_arr[-100:]

        ax_img.set_data(img)
        ax_min2.set_center((cx, cy))
        ax_min2.set_radius(r)
        
        ax_shdw_c.set_data(recent_pts[:, 0], recent_pts[:, 1])

        calculate = west_angle(recent_pts)
        
        # === [修正] calculate が None の場合の安全対策を追加 ===
        if calculate is not None:
            if 180 - abs(calculate) < acceptable:
                uxc = ("limegreen", "mediumseagreen")
            else:
                uxc = ("red", "purple")

            calc_rad = np.radians(calculate)
            tan_val = np.tan(calc_rad) if abs(np.tan(calc_rad)) > 1e-5 else 1e-5
            
            ax_sunline.set_xdata(np.linspace(cx - sunline * tan_val, cx + sunline * tan_val, 100))
            ax_sunline.set_ydata(np.linspace(cy - sunline / tan_val, cy + sunline / tan_val, 100))
            
            need_cl = plturn(calculate)
            fig_text.set_text(f'turn camera_{need_cl}° clockwise')
            clockwise = True if need_cl > 0 else False
            
            arrow.update(gapangle=abs(need_cl), clockwise=clockwise, edgecolor=uxc[1], tri_color=uxc[1])
        else:
            # データが足りず、まだ角度が計算できないときの処理
            uxc = ("red", "purple")
            fig_text.set_text('Calculating...')
        # ===================================================
        
        for gl in grid_lines:
            gl.set_color(uxc[0])
        ax_sunline.set_color(uxc[1])
        fig_text.set_color(uxc[0])

        plt.pause(0.001)
        # （下部省略）

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        
        if not plt.fignum_exists(fig.number):
            break

finally:
    # --- [変更] カメラ解放から動画解放へ ---
    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
    plt.close('all')
    print("動画再生を終了しました。")