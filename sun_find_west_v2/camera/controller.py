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


logger.info("--- finish ---")
