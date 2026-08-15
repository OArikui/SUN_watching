print("Booting up the system…")
print("Setting up logger…")
import datetime
import logging
import traceback

logfile = rf"logs\app_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"  # noqa: DTZ005

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s"
)

# console INFO以上
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# file すべて
file_handler = logging.FileHandler(filename=logfile, mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


print(f"log={logfile}")
print("Initializing forced termination procedure…")
from typing import NoReturn


def cancel_process(camera=None, viz=None) -> NoReturn:
    logger.info("===== canceling process and cleaning up =====")

    try:
        # 渡されたリソースを解放
        if camera is not None:
            try:
                camera.stop_video_capture()
                camera.close()
                logger.debug("Camera closed in cancel_process.")
            except (asi.ZWO_CaptureError, OSError) as e:
                logger.error(f"Failed to close camera: {e}")

        cv2.destroyAllWindows()

        if viz is not None:
            try:
                viz.close()
                logger.info("Visualizer closed in cancel_process.")
            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed to close viz: {e}")

    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to release resources: {e}")
    logger.info("===== FINISHED =====")
    sys.exit(1)


logger.info("===== Processing started =====")

logger.info("Importing standard modules...")
try:
    import os
    import sys
    from collections import deque
    from pathlib import Path
    from pprint import pformat
    from time import time
except ImportError:
    logger.error("Failed to import standard modules.")
    logger.error(traceback.format_exc())
    cancel_process()
else:
    logger.debug("All standard modules imported successfully.")

try:
    import cv2
    import numpy as np
    import zwoasi as asi
    from jsonschema import ValidationError, validate

except ImportError:
    logger.error("Failed to import third-party modules.")
    logger.error(traceback.format_exc())
    raise
else:
    logger.info("Third-party modules imported successfully.")

current = Path(__file__).resolve()

# current.parent から最上階までループ
for parent in [current.parent, *current.parents]:
    if parent.name == "sun_find_west_v2":
        parent_path = str(parent)
        sys.path.append(parent_path)
        break

try:
    from camera.controller import connect_camera
    from core import drawer
    from core.drawer import Visualizer
    from core.MIN2ver2 import MIN2_ignore_sunspots as MIN2
    from core.ransac import calculate_west_angle_robust as west_angle
except ImportError as e:
    logger.error("Failed to import custom modules.")
    logger.error(traceback.format_exc())
    cancel_process()
else:
    logger.debug("All custom modules imported successfully.")


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
    viz_init_params = {"constructor": grid_param}
    validate(instance=viz_init_params, schema=drawer.get_visualizer_schema())
except ValidationError as e:
    logger.error("visualizer parameters validation failed")
    logger.error("Validation error: %s", e)
    cancel_process()
else:
    logger.debug("Visualizer parameters validated successfully.")

# zwoasiのインポートと環境変数設定


logger.info("Attempting to connect to the camera...")
camera = None
try:
    env_filename = str(Path(parent_path) / "camera" / "bin" / "ASICamera2.dll")
    os.environ["ZWO_ASI_LIB"] = env_filename
    logger.debug(f"Successfully set ZWO_ASI_LIB environment variable:{env_filename}")
    camera = connect_camera(env_filename)
except KeyboardInterrupt:
    logger.info("Connection wait interrupted by user.")
    cancel_process()
except asi.ZWO_CaptureError as e:
    logger.critical(f"Failed to connect to the camera: {e}")
    cancel_process(camera=camera)
else:
    logger.info("Successfully connected to the camera.")

if camera is not None:
    # プロジェクト特有のカメラ設定
    try:
        camera_properties = {
            "exposure": 30000,
            "gain": 150,
            "band_width": 40,
            "image_type": asi.ASI_IMG_RAW8,
        }
        camera.set_control_value(asi.ASI_EXPOSURE, camera_properties["exposure"])
        camera.set_control_value(asi.ASI_GAIN, camera_properties["gain"])
        camera.set_control_value(
            asi.ASI_BANDWIDTHOVERLOAD, camera_properties["band_width"]
        )
        camera.set_image_type(camera_properties["image_type"])
        logger.debug(
            f"Camera properties configured successfully:\n{pformat(camera_properties)}"
        )
    except asi.ZWO_Error as e:
        logger.error(f"Failed to configure camera properties: {e}")
        cancel_process(camera=camera)

    logger.info("Starting video capture...")
    try:
        camera.start_video_capture()
        width, height, binning, img_type = camera.get_roi_format()
        logger.debug(
            f"Capture status retrieved: width={width}, height={height}, binning={binning}, img_type={img_type}"
        )
    except asi.ZWO_Error as e:
        logger.critical(f"Failed to start video capture or retrieve ROI: {e}")
        cancel_process(camera=camera)

# 変数初期化
logger.debug("Initializing visualization variables...")
frame_count = 0
dropped_frames = 0
st_time = time()
buffer_c = deque(maxlen=500)
buffer_t = deque(maxlen=500)
cx, cy, r = 0, 0, 1
viz = None

# リアルタイム処理ループ
try:
    if camera is None:
        raise RuntimeError("Cannot proceed without initialized camera")
    logger.info("Initializing Visualizer instance...")

    # 描画クラスを初期化
    viz = Visualizer(width, height, **viz_init_params["constructor"])

    logger.info(
        "Starting real-time visualization. Press 'q' or close the window to exit."
    )

    while True:
        try:
            frame = camera.capture_video_frame(timeout=500)
        except asi.ZWO_CaptureError as e:
            logger.warning(f"Frame capture failed or timed out: {e}")
            dropped_frames += 1
            continue

        img = np.frombuffer(frame, dtype=np.uint8).reshape(height, width)

        frame_count += 1

        # 計算処理
        try:
            (cx, cy), r = MIN2(img)
        except Exception as e:  # TODO:MIN2独自のERRORを作製,整理
            logger.warning(f"MIN2 processing error: {e}")
            dropped_frames += 1
            continue

        buffer_c.append([cx, cy])
        buf_c_arr = np.array(buffer_c)
        recent_pts = buf_c_arr[-buf_lookback:]

        buffer_t.append(time())
        buf_t_arr = np.array(buffer_t)
        recent_timestamps = buf_t_arr[-buf_lookback:]

        if len(recent_pts) > 2:
            try:
                result = west_angle(recent_pts, recent_timestamps)
                robust_angle, vectorYX = result  # pyright: ignore[reportGeneralTypeIssues]
            except (ValueError, TypeError, RuntimeError) as e:
                logger.warning(f"Error calculating robust west angle: {e}")
        else:
            logger.debug("Insufficient points for angle calculation (buffer <= 2).")
            robust_angle = False
            vectorYX = (0.0, 0.0)

        # 描画更新
        try:
            viz.update(
                img,
                cx,
                cy,
                r,
                recent_pts,
                robust_angle,
                frame_idx=frame_count,
                total_frames="∞",
            )

        except Exception as e:  # noqa: BLE001 :visualizerのerrorは多岐にわたる
            logger.warning(f"Visualizer update failed: {e}")

        # 終了判定
        if cv2.waitKey(1) & 0xFF == ord("q"):
            logger.info("Visualization loop terminated by user (keyboard input).")
            logger.debug(f"Total frames processed: {frame_count}")
            break

        # ウィンドウが閉じられたかどうかも Visualizer に判定させる
        if not viz.is_alive():
            logger.info("Visualization loop terminated (window closed).")
            logger.debug(f"Total frames processed: {frame_count}")
            break
except KeyboardInterrupt as e:
    elapsed_time = float(time() - st_time)
    logger.info(f"Keyboard interrupt: {e}")
    logger.debug(
        f"Terminated by keyboard interrupt. Total frames: {frame_count}, Dropped: {dropped_frames}, Time: {elapsed_time:.2f}s"
    )
    cancel_process(camera=camera, viz=viz)
except RuntimeError as e:
    elapsed_time = float(time() - st_time)
    logger.error(f"Runtime error occurred: {e}")
    logger.debug(
        f"Terminated with error. Total frames: {frame_count}, Dropped: {dropped_frames}, Time: {elapsed_time:.2f}s"
    )
    cancel_process(camera=camera, viz=viz)
else:
    elapsed_time = float(time() - st_time)
    logger.debug(
        f"Completed successfully. Total frames: {frame_count}, Dropped: {dropped_frames}, Time: {elapsed_time:.2f}s"
    )
    # 例外発生時も確実にリソースを解放
    logger.info("Releasing camera and resources...")

    if camera is not None:
        try:
            camera.stop_video_capture()
            camera.close()
            logger.debug("Camera stopped and closed successfully.")
        except (asi.ZWO_CaptureError, OSError) as e:
            logger.error(f"Failed to release resources: {e}")
    else:
        logger.info("No camera instance to release.")

    cv2.destroyAllWindows()
    if "viz" in locals() and viz is not None:
        viz.close()
        logger.info("Visualizer resources released.")
    logger.info("Camera successfully disconnected.")

logger.info("===== Processing finished =====")
