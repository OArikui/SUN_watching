import time
import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np
try:
    import zwoasi as asi
except ImportError:
    # zwoasiがインストールされていない環境でも動くようダミーを定義
    class DummyASI:
        ZWO_CaptureError = Exception
        ZWO_Error = Exception
        ASI_GAIN = 1
        ASI_EXPOSURE = 2
        ASI_TEMPERATURE = 3
        ASI_IMG_RAW8 = 0
    asi = DummyASI()

class VideoDummyCamera:
    """
    zwoasi.Cameraクラスの動作を模倣し、指定された動画ファイルから
    フレームを提供するダミークラス。
    """
    
    def __init__(self, video_path: str = None):
        """
        Args:
            video_path (str, optional): 動画ファイルのパス。
                                       指定がない場合はファイルダイアログを表示して選択させます。
        """
        if not video_path:
            # tkinterのルートウィンドウを表示しないように隠す
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True) # ダイアログを最前面に表示
            
            video_path = filedialog.askopenfilename(
                title="再生する動画ファイルを選択してください",
                filetypes=[
                    ("動画ファイル", "*.mp4 *.avi *.mov *.mkv *.wmv *.ser"),
                    ("すべてのファイル", "*.*")
                ]
            )
            root.destroy()
            
            if not video_path:
                raise ValueError("動画ファイルが選択されませんでした。")
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"動画ファイルを開けませんでした: {video_path}")
            
        # 動画のプロパティを取得
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30.0
            
        # 仮想のコントロール値 (Gain, Exposure, Temp)
        self.controls = {
            getattr(asi, "ASI_GAIN", 1): 150,
            getattr(asi, "ASI_EXPOSURE", 2): 30000,
            getattr(asi, "ASI_TEMPERATURE", 3): 250, # 25.0℃
        }
        self.is_capturing = False

    def get_camera_property(self):
        """
        zwoasi.Camera.get_camera_property() の互換メソッド。
        必要なプロパティ情報を辞書形式で返します。
        """
        return {
            "Name": "Dummy Video Camera",
            "CameraID": -1,
            "MaxHeight": self.height,
            "MaxWidth": self.width,
            "IsColorCam": True,
            "BayerPattern": 0,
            "SupportedBins": [1, 2, 4],
            "SupportedVideoFormat": [getattr(asi, "ASI_IMG_RAW8", 0)],
            "PixelSize": 3.75,
            "MechanicalShutter": False,
            "ST4Port": False,
            "IsCoolerCam": False,
            "IsUSB3Host": True,
            "IsUSB3Camera": True,
            "ELEC_PER_ADU": 1.0,
            "BitDepth": 8,
        }
    
    def get_controls(self):
        """
        zwoasi.Camera.get_controls() の互換メソッド。
        カメラがサポートするコントロール情報 (コントロールID -> 制御パラメータ情報の辞書) を返します。
        """
        # ASIカメラで利用される主要なコントロールIDを取得
        exposure_id = getattr(asi, "ASI_EXPOSURE", 2)
        gain_id = getattr(asi, "ASI_GAIN", 1)
        offset_id = getattr(asi, "ASI_OFFSET", 3)
        bandwidth_id = getattr(asi, "ASI_BANDWIDTHOVERLOAD", 4)
        target_temp_id = getattr(asi, "ASI_TARGET_TEMP", 5)
        cooler_on_id = getattr(asi, "ASI_COOLER_ON", 6)

        # apply_camera_config での 'in' 判定を通過できるように辞書を作成
        return {
            exposure_id: {
                "Name": "Exposure",
                "MinValue": 1,
                "MaxValue": 1000000,
                "DefaultValue": 10000,
            },
            gain_id: {
                "Name": "Gain",
                "MinValue": 0,
                "MaxValue": 600,
                "DefaultValue": 100,
            },
            offset_id: {
                "Name": "Offset",
                "MinValue": 0,
                "MaxValue": 100,
                "DefaultValue": 10,
            },
            bandwidth_id: {
                "Name": "BandwidthOverload",
                "MinValue": 40,
                "MaxValue": 100,
                "DefaultValue": 40,
            },
            target_temp_id: {
                "Name": "TargetTemp",
                "MinValue": -50,
                "MaxValue": 30,
                "DefaultValue": 0,
            },
            cooler_on_id: {
                "Name": "CoolerOn",
                "MinValue": 0,
                "MaxValue": 1,
                "DefaultValue": 0,
            },
        }

    def set_roi_format(self, width=None, height=None, bins=1, image_type=0, start_x=0, start_y=0):
        """zwoasi.Camera.set_roi_format() の互換メソッド。

        ROI（関心領域）サイズやビニング、画像タイプをダミー値として保存します。
        """
        if width is not None:
            self.width = int(width)
        if height is not None:
            self.height = int(height)

        self.bins = bins
        self.image_type = image_type
        self.start_x = start_x
        self.start_y = start_y
    
    def start_video_capture(self):
        """動画キャプチャの開始を模倣"""
        self.is_capturing = True

    def stop_video_capture(self):
        """動画キャプチャの停止を模倣"""
        self.is_capturing = False

    def close(self):
        """リソースの解放"""
        self.stop_video_capture()
        if self.cap.isOpened():
            self.cap.release()

    def get_roi_format(self):
        """
        ROIフォーマットを返す。
        (width, height, binning, img_type)
        img_type = 0 は ASI_IMG_RAW8 (グレースケール1チャンネル) を想定
        """
        img_type = getattr(asi, "ASI_IMG_RAW8", 0)
        return (self.width, self.height, 1, img_type)

    def get_control_value(self, control_type):
        """コントロール値と自動設定フラグ(bool)のタプルを返す"""
        val = self.controls.get(control_type, 0)
        return (val, False)
        
    def set_control_value(self, control_type, value, auto=False):
        """UIからの設定変更を受け付けるダミーメソッド"""
        self.controls[control_type] = value

    def capture_video_frame(self, timeout=500):
        """
        動画から1フレーム読み込み、RAW8(グレースケール)のバイト列として返す。
        動画が終了した場合は最初からループする。
        """
        if not self.is_capturing:
            raise getattr(asi, "ZWO_CaptureError", Exception)("Capture not started")

        # 実際のカメラのフレームレートを模倣するための待機
        time.sleep(1.0 / self.fps)

        ret, frame = self.cap.read()
        if not ret:
            # 動画の終端に達したら最初に戻す（ループ再生）
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                raise getattr(asi, "ZWO_CaptureError", Exception)("Failed to read dummy frame")

        # オリジナルの frame_to_image が numpy.frombuffer を使って bytes をパースするため、
        # グレースケール(1チャンネル)に変換してから bytes として返す
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return gray.tobytes()
