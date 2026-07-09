import cv2
import numpy as np
import tqdm
import os
import sys
from tkinter import filedialog, Tk

# Tkinterのルートウィンドウが残るのを防ぐ
root = Tk()
root.withdraw()

# 画像フォルダのパスを選択
picpath = filedialog.askdirectory(title="画像フォルダを選択")
if not picpath:
    print("フォルダが選択されませんでした。")
    sys.exit()

# 出力パスを .avi に変更
vid_outpt = r"C:\projects\Kansoku_system\observation\dummy_videos\RTtoLB.avi"
print(f"出力先: {vid_outpt}")

def list_files(pah):
    # 画像ファイル（jpg, pngなど）のみをフィルタリングするとより安全です
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    return [f for f in os.listdir(pah)
            if os.path.isfile(os.path.join(pah, f)) and f.lower().endswith(valid_extensions)]
    
def images_to_video(image_files, output_path, fps=30):
    if not image_files:
        print("画像ファイルが見つかりません。")
        return

    # 最初の画像からサイズを取得
    dat = np.fromfile(image_files[0], dtype=np.uint8) 
    first_image = cv2.imdecode(dat, cv2.IMREAD_COLOR)
    if first_image is None:
        print(f"最初の画像が読み込めませんでした: {image_files[0]}")
        return
    height, width, _ = first_image.shape

    # AVI用のコーデック設定 (XVID が一般的ですが、環境に依存する場合は MJPG もおすすめ)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    
    # 出力先のディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # tqdmで進捗表示
    for img_path in tqdm.tqdm(image_files, desc="動画作成中", unit="枚"):
        # 日本語パス対応のため、cv2.imread ではなく np.fromfile + cv2.imdecode を使用
        try:
            img_dat = np.fromfile(img_path, dtype=np.uint8)
            img = cv2.imdecode(img_dat, cv2.IMREAD_COLOR)
        except Exception:
            img = None

        if img is None:
            print(f"\n画像が読み込めませんでした: {img_path}")
            continue
            
        resized_img = cv2.resize(img, (width, height))
        video_writer.write(resized_img)

    video_writer.release()
    print(f"\n動画を保存しました: {output_path}")

output_video = vid_outpt
pics = list_files(picpath)

# パスの結合を os.path.join で安全に行う
pics = [os.path.join(picpath, p) for p in pics]

# 並び順をファイル名順にソート（必要に応じて）
pics.sort()

images_to_video(pics, output_video, fps=120)