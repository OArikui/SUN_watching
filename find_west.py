print("Booting up the system…")
print("Setting up logger…")
import datetime
import logging
import traceback

logfile = f"app_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"  # noqa: DTZ005


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s",
    filename=logfile,
    filemode="a",
)

logger = logging.getLogger(__name__)
print(f"log={logfile}")
print("Initializing forced termination procedure…")
from typing import NoReturn


def cancel_process() -> NoReturn:
    logger.info("=== process canceled ===")
    sys.exit()


logger.info("=== start processing ===")


try:
    import os
    import sys
    from collections import deque
    from pathlib import Path
    from time import time

    import cv2
    import numpy as np
    import zwoasi as asi
    from jsonschema import ValidationError, validate
except ImportError:
    logger.error("Failed to import standard modules.")
    logger.error(traceback.format_exc())
    cancel_process()
else:
    logger.info("All standard modules imported successfully.")

# 0. 階層エラー対策 (パスの自動追加)
current_dir = Path(__file__).resolve().parent
project_root = current_dir
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
logger.info("Appended project root to system path.")

try:
    from lib import drawer
    from lib.camera_utils import connect_camera
    from lib.drawer import Visualizer
    from lib.MIN2ver2 import MIN2_ignore_sunspots as MIN2
    from lib.RANSAC import calculate_west_angle_robust as west_angle
except ImportError:
    logger.error("Failed to import custom module")
    logger.error(traceback.format_exc())
    cancel_process()
else:
    logger.info("all custom modules imported successfully")


# ==================
# パラメータ設定
# analyzing
acceptable = 1  # 許容誤差(degree 0~)
buf_lookback = 100  # 前何フレームを軌道推定に使うか (frame 2~)

# interface
grid_param = {
    "grid_color": "#FFFFFF",  # grid_color(hex16)
    "grid_alpha": 0.4,  # grid_alpha(0.0-1.0)
    "grid_ny": 2,  # splitting y (2~)
    "grid_nx": 4,  # splitting x (2~)
    "grid_r": 300,  # center guide circle radian(pix)
}

# =====================


# parameter light 結集
logger.info("Validating visualizer schema parameters.")
try:
    viz_init_params = {"acceptable": acceptable, **grid_param}
    validate(instance=viz_init_params, schema=drawer.get_visualizer_schema())
except ValidationError as e:
    logger.error("visualizer parameters validation failed")
    logger.error("Validation error: %s", e)
    cancel_process()
else:
    logger.info("Visualizer parameters validated successfully.")

# zwoasiのインポートと環境変数設定
env_filename = project_root / "lib" / "ASICamera2.dll"
try:
    os.environ["ZWO_ASI_LIB"] = str(env_filename)
except asi.ZWO_CaptureError as e:
    logger.critical(
        f"Failed to set ZWO_ASI_LIB... (env_filename={env_filename!s}): {e}"
    )
    cancel_process()
else:
    logger.info("Successfully set ZWO_ASI_LIB environment variable.")

logger.info("Attempting to connect to the camera...")
try:
    camera = connect_camera(str(env_filename))
except asi.ZWO_CaptureError as e:
    logger.critical(f"Failed to connect to the camera: {e}")
    cancel_process()
else:
    logger.info("Successfully connected to the camera.")

# プロジェクト特有のカメラ設定
camera.set_control_value(asi.ASI_EXPOSURE, 30000)
camera.set_control_value(asi.ASI_GAIN, 150)
camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 40)
camera.set_image_type(asi.ASI_IMG_RAW8)

camera.start_video_capture()
width, height, binning, img_type = camera.get_roi_format()

# 変数初期化
frame_count = 0
target_fps = 30.0  # カメラの露出時間

buffer_c = deque(maxlen=500)
buffer_t = deque(maxlen=500)

# 3. リアルタイム処理ループ
try:
    print("loading...")

    # 描画クラスを初期化
    viz = Visualizer(width, height, **viz_init_params)

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

        frame_count += 1

        # 計算処理
        cx, cy, r = MIN2(img)
        buffer_c.append([cx, cy])
        buf_c_arr = np.array(buffer_c)
        recent_pts = buf_c_arr[-buf_lookback:]

        buffer_t.append(time())
        buf_t_arr = np.array(buffer_t)
        recent_timestamps = buf_t_arr[-buf_lookback:]
        if len(recent_pts) > 2:
            # west_angle may return None (e.g. not enough points); handle that safely
            result = west_angle(recent_pts, recent_timestamps)
            robust_angle, vectorYX = result  # pyright: ignore[reportGeneralTypeIssues]
        else:
            robust_angle = False
            vectorYX = (0.0, 0.0)

        # 描画更新
        viz.update(
            img,
            cx,
            cy,
            r,
            recent_pts,
            robust_angle,
            frame_idx=frame_count,
            total_frames="∞",
            target_fps=target_fps,
        )

        # 終了判定
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # ウィンドウが閉じられたかどうかも Visualizer に判定させる
        if not viz.is_alive():
            break

finally:
    # 例外発生時も確実にリソースを解放
    print("Releasing camera and resources...")
    if "camera" in locals():
        try:
            camera.stop_video_capture()
            camera.close()
        except (asi.ZWO_CaptureError, OSError) as e:
            logger.error(f"Failed to release resources: {e}")
    else:
        logger.info("No camera instance to release.")
    cv2.destroyAllWindows()
    if "viz" in locals():
        viz.close()
    print("Camera successfully disconnected.")

logger.info("=== processing finished ===")
