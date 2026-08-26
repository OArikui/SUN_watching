print("Booting up the system…")
print("Setting up logger…")
import datetime
import logging
import traceback

current = Path(__file__).resolve()
# current.parent から最上階までループ
for parent in [current.parent, *current.parents]:
    if parent.name == "sun_find_west_v2":
        root_path = parent
        sys.path.append(root_path)
        break
dt = datetime.now().strftime("%Y%m%d")
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
reports_path = root_path.parent / f"report_{dt}"
reports_path.mkdir(parents=True, exist_ok=True)

logfile = reports_path / logs / f"sunfindwestV2_{ts}.log"  # noqa: DTZ005
logfile.parent.mkdir(parents=True, exist_ok=True)

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
    from time import time
except ImportError:
    logger.error("Failed to import standard modules.")
    logger.error(traceback.format_exc())
    cancel_process()
else:
    logger.debug("All standard modules imported successfully.")

try:
    import cv2
    import csv
    import numpy as np
    import zwoasi as asi

except ImportError:
    logger.error("Failed to import third-party modules.")
    logger.error(traceback.format_exc())
    raise
else:
    logger.info("Third-party modules imported successfully.")


try:
    from sun_find_west_v2.camera.controller import (
        apply_camera_config,
        connect_camera,
        handle_config,
    )
    from sun_find_west_v2.config.config_manager import parameter
    from sun_find_west_v2.core.drawer import Visualizer
    from sun_find_west_v2.core.MIN2ver2 import MIN2_ignore_sunspots as MIN2
    from sun_find_west_v2.core.ransac import calculate_west_angle_robust as west_angle
except ImportError:
    logger.error("Failed to import custom modules.")
    logger.error(traceback.format_exc())
    cancel_process()
else:
    logger.debug("All custom modules imported successfully.")

try:
    print("__loading parameter...")

    camera_param = parameter["Camera"]
    main_param = parameter["sun_find_west_v2"]
    visualizer_constract_param = main_param["Visualizer"]
    visualizer_constract_param["acceptable"] = main_param["Analyzer"]["acceptable"]

except RuntimeError:
    logger.exception("__filed to load parameter")
    cancel_process()
logger.info("__sucessful __loading parameter")

print("__setting parameter...")


logger.info("Attempting to connect to the camera...")
camera = None
try:
    env_filename = str(root_path / "camera" / "bin" / "ASICamera2.dll")
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
    flatten_param = {}
    for hhv in camera_param.values():
        flatten_param.update(hhv)

    apply_camera_config(camera, flatten_param)
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

# 変数読み込み
buf_lookback = main_param["buf_lookback"]

# 変数初期化
logger.debug("Initializing visualization variables...")
frame_count = 0
dropped_frames = 0
st_time = time()
buffer_c = deque[list[float]](maxlen=500)
buffer_t = deque[float](maxlen=500)
cx, cy, r = 0.0, 0.0, 1.0
viz = None

# リアルタイム処理ループ
try:
    if camera is None:
        raise RuntimeError("Cannot proceed without initialized camera")
    logger.info("Initializing Visualizer instance...")

    csv_file_path = reports_path / f"sun_data_{ts}_BYsunfindwestV2.csv"
    logger.info(f"csv_file_path: {csv_file_path}")
    # CSVヘッダーの定義
    csv_headers = [
        "timestamp_iso",  # ISOフォーマット日時 (YYYY-MM-DDTHH:MM:SS.sss)
        "timestamp_unix",  # Unixタイムスタンプ (秒)
        "frame_count",  # フレーム番号
        "temperature_c",  # カメラセンサー温度 (℃)
        "gain",  # カメラ Gain
        "exposure_us",  # カメラ 露光時間 (µs)
        "cx",  # 太陽中心 X座標
        "cy",  # 太陽中心 Y座標
        "r",  # 太陽半径
        "robust_angle",  # 計算された西偏角 (算出不能時は None)
    ]

    logger.info(f"Logging MIN2 and camera data to: {csv_file_path}")
    # 描画クラスを初期化
    viz = Visualizer(width, height, visualizer_constract_param)

    logger.info(
        "Starting real-time visualization. Press 'q' or close the window to exit."
    )

    viz.add_slider(
        name="gain",
        label="Gain (dB)",
        valmin=0,
        valmax=300,
        valinit=150,
        valfmt="%1.0f",  # 整数表示
        on_change=lambda val: handle_config(camera, asi.ASI_GAIN, val),
    )

    viz.add_slider(
        name="exposure",
        label="Exposure (µs=1e-6s)",
        valmin=1000,
        valmax=100000,
        valinit=30000,
        valfmt="%1.0f",
        on_change=lambda val: handle_config(camera, asi.ASI_EXPOSURE, val),
    )

    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(csv_headers)

        while True:
            try:
                frame = camera.capture_video_frame(timeout=500)
            except asi.ZWO_CaptureError as e:
                logger.warning(f"Frame capture failed or timed out: {e}")
                dropped_frames += 1
                continue

            img = np.frombuffer(frame, dtype=np.uint8).reshape(height, width)
            frame_count += 1

            # 1. MIN2 計算処理
            try:
                (cx, cy), r = MIN2(img)
            except Exception as e:  # TODO:MIN2独自のERRORを作製,整理  # noqa: BLE001
                logger.warning(f"MIN2 processing error: {e}")
                dropped_frames += 1
                continue

            buffer_c.append([cx, cy])
            buf_c_arr = np.array(buffer_c)
            recent_pts = buf_c_arr[-buf_lookback:]

            capture_time_unix = time()
            capture_time_iso = datetime.datetime.now().isoformat()
            buffer_t.append(capture_time_unix)
            buf_t_arr = np.array(buffer_t)
            recent_timestamps = buf_t_arr[-buf_lookback:]

            # 2. 角度計算
            if len(recent_pts) > 2:
                try:
                    result = west_angle(recent_pts, recent_timestamps)
                    if result is None:
                        raise RuntimeError
                    robust_angle, vectorYX = result
                except (ValueError, TypeError, RuntimeError) as e:
                    logger.warning(f"Error calculating robust west angle: {e}")
                    robust_angle = None
            else:
                logger.debug("Insufficient points for angle calculation (buffer <= 2).")
                robust_angle = None
                vectorYX = (0.0, 0.0)

            # 3. 現在のカメラ情報の取得
            try:
                current_gain = camera.get_control_value(asi.ASI_GAIN)[0]
                current_exposure = camera.get_control_value(asi.ASI_EXPOSURE)[0]
                temp_raw = camera.get_control_value(asi.ASI_TEMPERATURE)[0]
                current_temp = round(temp_raw / 10.0, 1)
            except asi.ZWO_Error as e:
                logger.warning(f"Failed to read camera control values: {e}")
                current_gain, current_exposure, current_temp = None, None, None

            # 4. CSVへのリアルタイム書き込み
            try:
                csv_writer.writerow(
                    [
                        capture_time_iso,
                        capture_time_unix,
                        frame_count,
                        current_fps,
                        current_temp,
                        current_gain,
                        current_exposure,
                        cx,
                        cy,
                        r,
                        robust_angle if robust_angle is not False else None,
                    ]
                )
                csv_file.flush()
            except Exception as e:
                logger.error(f"Failed to write row to CSV: {e}")

            # 5. 描画更新
            try:
                viz.update(
                    img,
                    cx,
                    cy,
                    r,
                    recent_pts,
                    robust_angle if robust_angle is not False else False,
                    frame_idx=frame_count,
                    total_frames="∞",
                )
            except Exception as e:
                logger.warning(f"Visualizer update failed: {e}")

            # 終了判定
            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger.info("Visualization loop terminated by user (keyboard input).")
                logger.debug(f"Total frames processed: {frame_count}")
                break

            if not viz.is_alive():
                logger.info("Visualization loop terminated (window closed).")
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
