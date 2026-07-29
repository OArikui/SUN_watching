import os
import sys
import time
import cv2
import zwoasi as asi

# ==============================================================================
# 設定：exe化に対応した確実なDLL絶対パスの取得
# ==============================================================================
if getattr(sys, "frozen", False):
    # exeを実行している場合
    base_dir = os.path.dirname(sys.executable)
else:
    # 通常のpythonスクリプトとして実行している場合
    base_dir = os.path.dirname(os.path.abspath(__file__))

dll_path = os.path.join(base_dir, "ASICamera2.dll")

if not os.path.exists(dll_path):
    print(f"【エラー】DLLファイルが見つかりません。")
    print(f"指定されたパス: {dll_path}")
    print("上記パスに 64bit版の ASICamera2.dll を配置してください。")
    input("\nEnterキーを押して終了します...")  # exeがすぐ閉じないように
    sys.exit(1)

# ==============================================================================
# SDKの初期化
# ==============================================================================
try:
    asi.init(dll_path)
    print("SDKの初期化に成功しました。")
except Exception as e:
    print(f"SDKの初期化に失敗しました（32bit/64bitの不一致など）: {e}")
    input("\nEnterキーを押して終了します...")
    sys.exit(1)

# ==============================================================================
# 1. while文によるカメラ接続待機
# ==============================================================================
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

# ==============================================================================
# 2. カメラの初期化と設定
# ==============================================================================
try:
    camera = asi.Camera(camera_index)
    camera_info = camera.get_camera_property()

    print(f"使用カメラ: {camera_info['Name']}")

    camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 40)
    camera.disable_dark_subtract()
    camera.start_video_capture()

except Exception as e:
    print(f"カメラの初期化中にエラーが発生しました: {e}")
    input("\nEnterキーを押して終了します...")
    sys.exit(1)

# ==============================================================================
# 3. 接続後の映像プレビュー
# ==============================================================================
print("プレビューを開始します。終了するには [q] キーを押してください。")

try:
    while True:
        image_data = camera.capture_video_frame(timeout=2000)
        cv2.imshow("ZWO ASI Camera Preview", image_data)

        if cv2.waitKey(10) & 0xFF == ord("q"):
            print("プレビューを終了します。")
            break

except Exception as e:
    print(f"\nプレビュー中にエラーが発生しました: {e}")

finally:
    # ==============================================================================
    # 後処理
    # ==============================================================================
    print("カメラとリソースを解放しています...")
    try:
        camera.stop_video_capture()
        camera.close()
    except:
        pass
    cv2.destroyAllWindows()
    print("完了。")
    time.sleep(1)