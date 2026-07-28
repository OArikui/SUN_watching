import logging
import traceback

logger = logging.getLogger(__name__)

if "__main__" == __name__:
    logger.info("--- starting as main process ---")
else:
    logger.info("--- starting as module process ---")

try:
    import os
    import sys
    import time
    import zwoasi as asi
except ImportError:
    logger.error("Failed to import standard module")
    logger.error(traceback.format_exc())
    raise

logger.info("standard modules imported successfully")

def connect_camera(dll_path):
    """
    ASIカメラの初期化と接続待機を行うモジュール
    """
    # 1. DLLパスの存在確認
    if not os.path.exists(dll_path):
        print(f"【エラー】DLLファイルが見つかりません。")
        print(f"指定されたパス: {dll_path}")
        print("上記パスに 64bit版の ASICamera2.dll を配置してください。")
        input("\nEnterキーを押して終了します...")
        sys.exit(1)

    # 2. SDKの初期化
    try:
        # すでに初期化されている場合の対策
        try:
            asi.get_num_cameras()
        except (asi.ZWO_Error, AttributeError):  # ★ ここに AttributeError を追加
            asi.init(str(dll_path))
        print("SDKの初期化に成功しました。")
    except Exception as e:
        print(f"SDKの初期化に失敗しました（32bit/64bitの不一致など）: {e}")
        input("\nEnterキーを押して終了します...")
        sys.exit(1)

    # 3. カメラ接続の待機ループ
    print("カメラの接続を待機しています... (中断するには Ctrl+C)")
    camera_index = None

    try:
        while True:
            try:
                cameras = asi.list_cameras()
            except:
                cameras = []

            if len(cameras) > 0:
                print(f"\nカメラが検出されました！ 検出数: {len(cameras)}")
                print(f"検出されたカメラリスト: {cameras}")
                camera_index = 0
                break
            else:
                print(".", end="", flush=True)
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n接続待機がユーザーによって中断されました。")
        sys.exit(0)

    # 4. カメラの初期化と基本設定
    try:
        camera = asi.Camera(camera_index)
        camera_info = camera.get_camera_property()
        print(f"使用カメラ: {camera_info['Name']}")

        # 汎用的な基本設定
        camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 40)
        camera.disable_dark_subtract()

        return camera
    except Exception as e:
        print(f"カメラの初期化中にエラーが発生しました: {e}")
        input("\nEnterキーを押して終了します...")
        sys.exit(1)

logger.info("--- finish ---")