import logging
import traceback

logger = logging.getLogger(__name__)

if "__main__" == __name__:
    logger.info("--- starting as main process ---")
else:
    logger.info("--- starting as module process ---")

try:
    import os
    import time
except ImportError:
    logger.error("Failed to import standard module")
    logger.error(traceback.format_exc())
    raise
else:
    logger.info("standard modules imported successfully")

try:
    from vid_dummy import VideoDummyCamera

    HAS_VID_DUMMY = True
except ImportError:
    HAS_VID_DUMMY = False
    VideoDummyCamera = None

try:
    import zwoasi as asi
except ImportError:
    logger.error("Failed to import zwoasi module")
    logger.error(traceback.format_exc())
    raise
else:
    logger.info("zwoasi modules imported successfully")


def connect_camera(dll_path):
    """
    ASIカメラの初期化と接続待機を行うモジュール
    """
    # 1. DLLパスの存在確認
    if not os.path.exists(dll_path):
        logger.error(
            f"DLL not found: {dll_path}. Please place the 64-bit ASICamera2.dll at this path."
        )
        input("\nPress Enter to continue...")
        return None

    # 2. SDKの初期化
    logger.info("Initializing ASI SDK...")
    try:
        # すでに初期化されている場合の対策
        try:
            asi.get_num_cameras()
            logger.debug("ASI SDK already initialized.")
        except (asi.ZWO_Error, AttributeError):
            asi.init(str(dll_path))
        logger.info("ASI SDK initialized successfully.")
    except (asi.ZWO_Error, OSError) as e:
        # ASI SDK固有のエラーやOS関連のエラーを捕捉
        logger.error(f"Failed to initialize ASI SDK (architecture mismatch?): {e}")
        raise

    # 3. カメラ接続の待機ループ
    logger.info("Waiting for camera connection... (Press Ctrl+C to abort)")
    camera_index = None

    try:
        while True:
            # 標準入力の入力を非ブロックで確認
            user_input = check_stdin_input()
            if user_input:
                if user_input == "DUMVID":
                    if HAS_VID_DUMMY:
                        logger.info("DUMVID received. Returning VideoDummyCamera instance.")
                        try:
                            # vid_dummy (VideoDummyCamera) のインスタンスを作成して返す
                            dummy_cam = VideoDummyCamera(dummy_video_path)
                            return dummy_cam
                        except Exception as e:
                            logger.error(f"Failed to initialize VideoDummyCamera: {e}")
                    else:
                        print("\n[INFO] ダミーコード(DUMVID)が入力されましたが、vid_dummy モジュールをインポートできませんでした。")
                        logger.warning("DUMVID received, but vid_dummy is not available.")
                        
            try:
                cameras = asi.list_cameras()
            except (asi.ZWO_Error, OSError):
                # list_cameras が失敗する可能性があるため空リストにする
                cameras = []

            if len(cameras) > 0:
                logger.debug(f"Camera(s) detected (Count: {len(cameras)})")
                logger.debug(f"Available cameras: {cameras}")
                camera_index = 0
                break
            else:
                print(".", end="", flush=True)
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Connection wait interrupted by user.")
        raise

    logger.info("Camera acquired successfully.")
    # 4. カメラの初期化と基本設定
    try:
        camera = asi.Camera(camera_index)
        camera_info = camera.get_camera_property()
        logger.debug(f"Selected camera: {camera_info['Name']}")

        # 汎用的な基本設定
        camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 40)
        camera.disable_dark_subtract()
        logger.info("Camera configured successfully.")
        return camera
    except asi.ZWO_Error as e:
        logger.error(f"ASI error occurred during camera initialization: {e}")
        raise
    except Exception as e:
        # その他の予期しない例外はログに記録して終了
        logger.error("Unexpected error initializing camera: %s", traceback.format_exc())
        logger.error(f"Unexpected error occurred during camera initialization: {e}")
        raise


IMG_TYPE_MAP = {
    "RAW8": asi.ASI_IMG_RAW8,
    "RAW16": asi.ASI_IMG_RAW16,
    "RGB24": asi.ASI_IMG_RGB24,
    "Y8": asi.ASI_IMG_Y8,
}

control_map = {
    "exposure": asi.ASI_EXPOSURE,
    "gain": asi.ASI_GAIN,
    "offset": asi.ASI_OFFSET,
    "gamma": asi.ASI_GAMMA,
    "band_width": asi.ASI_BANDWIDTHOVERLOAD,
    "high_speed_mode": asi.ASI_HIGH_SPEED_MODE,
    "hardware_bin": asi.ASI_HARDWARE_BIN,
    "flip": asi.ASI_FLIP,
    "auto_max_gain": asi.ASI_AUTO_MAX_GAIN,
    "auto_max_exp": asi.ASI_AUTO_MAX_EXP,
    "auto_target_brightness": asi.ASI_AUTO_MAX_BRIGHTNESS,
    "target_temp": asi.ASI_TARGET_TEMP,
    "cooler_on": asi.ASI_COOLER_ON,
}


def apply_camera_config(cam: asi.Camera, config: dict):
    """ZWO ASIカメラの各種パラメータを一括で設定する関数

    cam: 初期化済みの zwoasi.Camera インスタンス
    config: パラメータ設定辞書
    """
    props = cam.get_camera_property()

    width = config.get("width", "max")
    if width == "max":
        width = props["MaxWidth"]
    height = config.get("height", "max")
    if height == "max":
        height = props["MaxHeight"]
    bins = config.get("bins")
    img_type_str = str(config.get("img_type", "RAW8")).upper()
    img_type = IMG_TYPE_MAP.get(img_type_str, asi.ASI_IMG_RAW8)

    cam.set_roi_format(width=width, height=height, bins=bins, image_type=img_type)

    available_controls = cam.get_controls()

    for key, control_type in control_map.items():
        if key in config:
            if control_type in available_controls:
                try:
                    val = config[key]
                except KeyError:
                    logger.warning(
                        f"__ENG{key}が設定されていません。カメラの初期値を採用します。"
                    )
                    continue
                if isinstance(val, bool):
                    val = int(val)
                try:
                    cam.set_control_value(control_type, val)
                except asi.ZWO_Error as e:
                    logger.exception(
                        f" __ENG{key} の設定に失敗しました (範囲外の値などの可能性)"
                    )
            else:
                logger.warning(f"__ENGこのカメラは{key}に対応していません")
                pass

    logger.info("__sucessful set camera config")


def handle_config(cam: asi.Camera, key: int, val: float) -> None:
    """
    - 利用可能な変数 -
    ASI_EXPOSURE
    ASI_GAIN
    ASI_OFFSET
    ASI_BRIGHTNESS
    ASI_GAMMA
    ASI_WB_R
    ASI_WB_B
    ASI_BANDWIDTHOVERLOAD
    ASI_HIGH_SPEED_MODE
    ASI_HARDWARE_BIN
    ASI_MONO_BIN
    ASI_FLIP
    ASI_AUTO_MAX_GAIN
    ASI_AUTO_MAX_EXP
    ASI_AUTO_TARGET_BRIGHTNESS
    ASI_TARGET_TEMP
    ASI_COOLER_ON
    ASI_FAN_ON
    ASI_ANTI_DEW_HEATER"""
    try:
        camset_control_value(key, int(val))
        logger.debug(f"{key} updated to: {int(val)}")
    except asi.ZWO_Error as e:
        logger.error(f"Failed to update {key}: {e}")


logger.info("--- finish ---")
