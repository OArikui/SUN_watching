import os
import sys
from pathlib import Path
from collections import deque
import cv2
import numpy as np
from tkinter.filedialog import askopenfilename

# 0. 階層エラー対策 (パスの自動追加)
current_dir = Path(__file__).resolve().parent
project_root = current_dir
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from lib.MIN2ver2 import MIN2_ignore_sunspots as MIN2  # noqa: E402
from lib.RANSAC import calculate_west_angle_robust as west_angle  # noqa: E402
from lib.drawer import Visualizer  # noqa: E402

# ==================
# パラメータ設定
# analyzing 
acceptable = 1  # 許容誤差(degree 0~)
buf_lookback = 100  # 前何フレームを軌道推定に使うか (frame 2~)

video_path = askopenfilename()

# interface
grid_param={
    grid_color : "#FFFFFF" #grid_color(hex16)
    ,grid_alpha:0.4 #grid_alpha(0.0-1.0)
    ,grid_ny:2  #splitting y (2~)
    ,grid_nx:4  #splitting x (2~)
    ,grid_r:300 #center guide circle radian(pix)
    }

# =====================

# parameter結集
viz_init_params={"acceptable":acceptable}
viz_init_params.update(grid_param)


# トラックバー用のダミーコールバック関数
def nothing(x):
    pass


# 1. AVIファイルの読み込み設定
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(
        f"エラー: 動画ファイル '{video_path}' を開けませんでした。パスを確認してください。"
    )
    sys.exit(1)

# フレームサイズを取得
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# コントロール用ウィンドウと回転スライダー(0〜360度)の作成
cv2.namedWindow("Control Panel")
cv2.createTrackbar("Rotation", "Control Panel", 0, 360, nothing)

buffer = deque(maxlen=500)

# 2. リアルタイム（動画）処理ループ
try:
    print("loading...")

    # 描画クラスを初期化
    viz = Visualizer(width, height,**viz_init_params)

    print("complete loading")
    print(
        "デモ処理を開始します。'q' キーで終了するか、グラフウィンドウを閉じてください。"
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            print(
                "動画の再生が終了したか、フレームを取得できませんでした。ループを終了します。"
            )
            break

        # ASIカメラのRAW8（1チャンネル）入力に合わせるためグレースケール変換
        if len(frame.shape) == 3:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            img = frame

        # トラックバーから現在の回転角度を取得
        angle = cv2.getTrackbarPos("Rotation", "Control Panel")

        # 3. 画像の回転処理（RANSACの計算前に行う）
        if angle != 0:
            # 画像の中心を軸にして回転
            center = (width / 2, height / 2)
            # 回転行列の取得
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            # アフィン変換を適用（余白は0で補完）
            img = cv2.warpAffine(img, M, (width, height), borderValue=0)

        # 4. 計算処理（回転後の画像データを使用）
        cx, cy, r = MIN2(img)
        buffer.append([cx, cy])

        buf_arr = np.array(buffer)
        recent_pts = buf_arr[-buf_lookback:]

        # RANSACによる west_angle 計算
        result = west_angle(
            recent_pts
        )  # NOTE:fpsと対応させることでより移動に即した矢印が作製可能に
        if result is None:
            robust_angle = False
            vectorYX = (0.0, 0.0)
        else:
            robust_angle, vectorYX = result

        # 5. 描画更新
        viz.update(img, cx, cy, r, recent_pts, robust_angle, frame_idx=len(buffer))

        # 終了判定（動画再生速度に合わせて30ms待機）
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break

        # ウィンドウが閉じられたかどうかも Visualizer に判定させる
        if not viz.is_alive():
            break

finally:
    # 例外発生時も確実にリソースを解放
    print("リソースを解放しています...")
    try:
        cap.release()
    except:  # noqa: E722
        pass
    cv2.destroyAllWindows()
    if "viz" in locals():
        viz.close()
    print("デモを安全に終了しました。")
