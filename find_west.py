import os
import sys
from pathlib import Path
from collections import deque
import cv2
import numpy as np

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
acceptable = 1
grid_color = "#FFFFFF"
# =====================

# zwoasiのインポートと環境変数設定
env_filename = project_root / "lib" / "ASICamera2.dll"
os.environ["ZWO_ASI_LIB"] = str(env_filename)
import zwoasi as asi  # noqa: E402
from lib.camera_utils import connect_camera  # noqa: E402

# 1. & 2. モジュールを使用してカメラを接続（待機ループ実行）
camera = connect_camera(str(env_filename))

# プロジェクト特有のカメラ設定
camera.set_control_value(asi.ASI_EXPOSURE, 30000)
camera.set_control_value(asi.ASI_GAIN, 150)
camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 40)
camera.set_image_type(asi.ASI_IMG_RAW8)

camera.start_video_capture()
width, height, binning, img_type = camera.get_roi_format()

buffer = deque(maxlen=500)

# 3. リアルタイム処理ループ
try:
    print("loading...")

    # 描画クラスを初期化
    viz = Visualizer(width, height, acceptable, grid_color)

    print("complete loading")
    print(
        "リアルタイム処理を開始します。'q' キーで終了するか、グラフウィンドウを閉じてください。"
    )

    while True:
        try:
            frame = camera.capture_video_frame(timeout=500)
        except asi.ZWO_CaptureError:
            continue

        img = np.frombuffer(frame, dtype=np.uint8).reshape(height, width)

        # 計算処理
        cx, cy, r = MIN2(img)
        buffer.append([cx, cy])

        buf_arr = np.array(buffer)
        recent_pts = buf_arr[-100:]

        # west_angle may return None (e.g. not enough points); handle that safely
        result = west_angle(recent_pts)
        if result is None:
            robust_angle = False
            vectorYX = (0.0, 0.0)
        else:
            robust_angle, vectorYX = result

        # 描画更新
        viz.update(img, cx, cy, r, recent_pts, robust_angle, frame_idx=len(buffer))

        # 終了判定
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # ウィンドウが閉じられたかどうかも Visualizer に判定させる
        if not viz.is_alive():
            break

finally:
    # 例外発生時も確実にリソースを解放
    print("カメラとリソースを解放しています...")
    try:
        camera.stop_video_capture()
        camera.close()
    except:  # noqa: E722
        pass
    cv2.destroyAllWindows()
    if "viz" in locals():
        viz.close()
    print("カメラを安全に切断しました。")
