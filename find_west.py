import logging
import traceback
import datetime

logfile=f"app_{datetime.now().strftime("%Y-%m-%d")}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s",
    filename=logfile, 
    filemode="a"        
)

logger = logging.getLogger(__name__)

logger.info("=== start processing ===")

try:
    import os# noqa: E402
    import sys# noqa: E402
    import cv2# noqa: E402
    import numpy as np# noqa: E402
    import zwoasi as asi# noqa: E402
    from time import time# noqa: E402
    from pathlib import Path# noqa: E402
    from collections import deque# noqa: E402
    from jsonschema import validate, ValidationError# noqa: E402
except ImportError:
    logging.error("Failed to import standard module")
    logging.error(traceback.format_exc())
    raise

logging.info("all standard modules imported successfully")

# 0. 階層エラー対策 (パスの自動追加)
current_dir = Path(__file__).resolve().parent
project_root = current_dir
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from lib.MIN2ver2 import MIN2_ignore_sunspots as MIN2  # noqa: E402
    from lib.RANSAC import calculate_west_angle_robust as west_angle  # noqa: E402
    from lib.drawer import Visualizer,viz_schema # noqa: E402
    from lib.camera_utils import connect_camera  # noqa: E402
except ImportError:
    logging.error("Failed to import custom module")
    logging.error(traceback.format_exc())   
    raise

logging.info("all custom modules imported successfully")

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
logging.info("checking schema visualizer parameters")
try:
    viz_init_params = {"acceptable": acceptable, **grid_param}
    validate(instance=viz_init_params, schema=viz_schema)#TODO:drawerにschemaを設置
except ValidationError as e:
    logging.error("Validation error: %s", e)
    raise

logging.info("got visualizer's parameters successfully")

# zwoasiのインポートと環境変数設定
env_filename = project_root / "lib" / "ASICamera2.dll"
os.environ["ZWO_ASI_LIB"] = str(env_filename)

# 1. & 2. モジュールを使用してカメラを接続（待機ループ実行）
camera = connect_camera(str(env_filename))

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
        recent_timestamps=buf_t_arr[-buf_lookback:]
        if len(recent_pts) > 2:
            # west_angle may return None (e.g. not enough points); handle that safely
            result = west_angle(recent_pts,recent_timestamps)
            robust_angle, vectorYX = result # pyright: ignore[reportGeneralTypeIssues]
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

logger.log("=== finish processing ===")