print("Booting up the system…")
print("Setting up logger…")
import datetime
import logging
import sys
import traceback
from pathlib import Path

# --- [FIX 1] Path/sys を使う前にimportしておく (元コードはこの時点で両方未import) ---
current = Path(__file__).resolve()
# current.parent から最上階までループ
root_path = None
for parent in [current.parent, *current.parents]:
    if parent.name == "sun_find_west_v2":
        root_path = parent
        sys.path.append(str(root_path))
        break

# --- [FIX 2] "sun_find_west_v2" フォルダが見つからない場合に NameError で落ちないようにする ---
if root_path is None:
    print(
        "[FATAL] 'sun_find_west_v2' というフォルダが親ディレクトリの中に見つかりませんでした。"
    )
    sys.exit(1)

# --- [FIX 3] datetime.now() ではなく datetime.datetime.now() (元コードは module.now() で AttributeError) ---
dt = datetime.datetime.now().strftime("%Y%m%d")
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
reports_path = root_path.parent / f"report_{dt}"
reports_path.mkdir(parents=True, exist_ok=True)

# --- [FIX 4] logs -> "logs" (元コードは未定義識別子で NameError) ---
logfile = reports_path / "logs" / f"sunfindwestV2_{ts}.log"  # noqa: DTZ005
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
    from collections import deque
    from time import time
    # sys / Path はファイル先頭で既にimport済みなのでここでは行わない
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
    from camera.controller import (
        apply_camera_config,
        connect_camera,
        handle_config,
    )
    from config.config_manager import parameter
    from core.drawer import Visualizer
    from core.MIN2ver2 import MIN2_ignore_sunspots as MIN2
    from core.ransac import calculate_west_angle_robust as west_angle
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
    # --- [FIX 5] Windows専用のASICamera2.dll固定パスをOSごとに切り替え ---
    _lib_by_platform = {
        "win32": "ASICamera2.dll",
        "cygwin": "ASICamera2.dll",
        "linux": "libASICamera2.so",
        "darwin": "libASICamera2.dylib",
    }
    lib_name = _lib_by_platform.get(sys.platform, "libASICamera2.so")
    env_filename = str(root_path / "camera" / "bin" / lib_name)
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

# --- [FIX 6] img_type を実際に使ってdtype/形状を決定する (元コードは常にuint8/1chを決め打ち) ---
# ASI_IMG_RAW8=0, ASI_IMG_RGB24=1, ASI_IMG_RAW16=2, ASI_IMG_Y8=3 (zwoasiパッケージの一般的な定数値)
# ※ 実際の定数名/値はインストール済みzwoasiのバージョンで確認してください。
_frame_format_map = {
    getattr(asi, "ASI_IMG_RAW8", 0): (np.uint8, 1),
    getattr(asi, "ASI_IMG_Y8", 3): (np.uint8, 1),
    getattr(asi, "ASI_IMG_RAW16", 2): (np.uint16, 1),
    getattr(asi, "ASI_IMG_RGB24", 1): (np.uint8, 3),
}


def frame_to_image(frame: bytes, width: int, height: int, img_type: int) -> np.ndarray:
    """カメラの img_type に応じて frame バイト列を正しい dtype/形状の画像に変換する。"""
    dtype, channels = _frame_format_map.get(img_type, (np.uint8, 1))
    arr = np.frombuffer(frame, dtype=dtype)
    if channels == 1:
        return arr.reshape(height, width)
    return arr.reshape(height, width, channels)


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
capture_requested = False
quit_requested = False
cap_dir = reports_path / "captures"
cap_dir.mkdir(parents=True, exist_ok=True)

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
    # --- [FIX 7] 辞書をそのまま渡していたのを **展開に変更 (元コードは acceptable にdictが入っていた) ---
    viz = Visualizer(width, height, **visualizer_constract_param)

    logger.info(
        "Starting real-time visualization. Press the 'Quit' button or close the window to exit."
    )

    def reset_buffers():
        # --- [FIX 8] global宣言がなくローカル代入になっていた (frame_countがリセットされない) ---
        global frame_count
        frame_count = 0
        buffer_c.clear()
        buffer_t.clear()
        logger.info("軌跡バッファが手動でリセットされました。")

    def request_capture():
        # --- [FIX 9] nonlocal -> global (元コードはモジュール直下の関数でnonlocalを使いSyntaxErrorだった) ---
        global capture_requested
        capture_requested = True

    def request_quit():
        global quit_requested
        quit_requested = True
        logger.info("終了ボタンが押されました。")

    viz.add_button(
        name="reset_buffer",
        label="Reset",
        on_clicked=reset_buffers,
        position=[0.02, 0.05, 0.07, 0.04],
    )

    viz.add_button(
        name="capture_image",
        label="Capture",
        on_clicked=request_capture,
        position=[0.10, 0.05, 0.07, 0.04],
    )

    # --- [FIX 10] cv2.imshow を一度も呼んでいないため cv2.waitKey('q') が機能しない懸念があった。
    #              matplotlib側のボタンとして確実に効く終了トリガーを追加。
    viz.add_button(
        name="quit",
        label="Quit",
        on_clicked=request_quit,
        position=[0.18, 0.05, 0.07, 0.04],
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
            if quit_requested:
                logger.info("Visualization loop terminated by Quit button.")
                logger.debug(f"Total frames processed: {frame_count}")
                break

            try:
                frame = camera.capture_video_frame(timeout=500)
            except asi.ZWO_CaptureError as e:
                logger.warning(f"Frame capture failed or timed out: {e}")
                dropped_frames += 1
                continue

            # --- [FIX 6-2] 常にuint8決め打ちだった箇所を img_type 対応の変換関数に置き換え ---
            img = frame_to_image(frame, width, height, img_type)
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
                    # NOTE: ransac.py は今回未提供のため、calculate_west_angle_robust の
                    #       シグネチャ (引数の数) はここでは検証できていません。要確認。
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
                # --- [FIX 11] 未定義の current_fps を削除し、csv_headers(10列)と要素数/順序を一致させた ---
                csv_writer.writerow(
                    [
                        capture_time_iso,
                        capture_time_unix,
                        frame_count,
                        current_temp,
                        current_gain,
                        current_exposure,
                        cx,
                        cy,
                        r,
                        robust_angle,
                    ]
                )
                csv_file.flush()
            except Exception as e:
                logger.error(f"Failed to write row to CSV: {e}")

            # 5. 描画更新
            try:
                # --- [FIX 12] "is not False" は常にTrueで無意味だったため単純化 (drawer.py側でNoneに対応済み) ---
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
            except Exception as e:
                logger.warning(f"Visualizer update failed: {e}")

            # キャプチャリクエスト処理
            if capture_requested:
                capture_requested = False
                cap_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

                # 1. 生データ（画像単体）の保存
                raw_path = cap_dir / f"raw_{cap_ts}_f{frame_count}.png"
                if cv2.imwrite(str(raw_path), img):
                    logger.info(f"キャプチャ保存完了:{raw_path.name}")
                else:
                    logger.error(
                        f"キャプチャ保存失敗: \n path = {raw_path.name} \n img.size = {img.size} \n img.dtype = {img.dtype} "
                    )

            # --- [FIX 13] cv2.waitKey('q')判定と、到達不能な重複ブロックを削除。
            #              終了条件は「Quitボタン」と「ウィンドウを閉じる」の2系統に一本化。
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
