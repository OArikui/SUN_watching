import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Polygon
from matplotlib.transforms import Affine2D
from matplotlib.widgets import Slider

__all__ = ["OpenCircleArrow", "Visualizer"]


# 1. OpenCircleArrow クラス (描画パーツ)
class OpenCircleArrow:
    def __init__(
        self,
        ax,
        center=(0, 0),
        radius=1.0,
        gap_angle=90,
        start_angle=180,
        clockwise=True,
        edgecolor="C0",
        lw=3,
        tri_size=0.12,
        tri_color="C0",
    ):
        """
        インタラクティブにパラメーターを更新できる矢印付き円弧オブジェクト
        """
        self.ax = ax
        self.center = center
        self.radius = radius
        self.gap_angle = gap_angle
        self.start_angle = start_angle
        self.clockwise = clockwise
        self.edgecolor = edgecolor
        self.lw = lw
        self.tri_size = tri_size
        self.tri_color = tri_color

        # 描画したパッチを保持する変数
        self.arc_patch = None
        self.tri_patch = None

        # 初回描画
        self.draw()

    def draw(self):
        """現在保持しているパラメーターで再描画を行う内部メソッド"""
        # すでに描画されている古いパッチがあれば削除する
        if self.arc_patch is not None:
            self.arc_patch.remove()
        if self.tri_patch is not None:
            self.tri_patch.remove()

        cx, cy = self.center
        theta1 = self.start_angle
        theta2 = self.start_angle - (360 - self.gap_angle)

        # 円弧の生成
        self.arc_patch = Arc(
            (cx, cy),
            2 * self.radius,
            2 * self.radius,
            angle=0,
            theta1=theta2,
            theta2=theta1,
            linewidth=self.lw,
            edgecolor=self.edgecolor,
            linestyle="solid",
        )
        self.ax.add_patch(self.arc_patch)

        # 矢じりの計算
        tip_rad = np.deg2rad(theta1)
        ex = cx + self.radius * np.cos(tip_rad)
        ey = cy + self.radius * np.sin(tip_rad)

        tangent_angle = theta1 + 90
        t_rad = np.deg2rad(tangent_angle)

        s = self.tri_size * self.radius
        tri = np.array([[0.0, 0.0], [-s, s / 2], [-s, -s / 2]])

        R = np.array([[np.cos(t_rad), -np.sin(t_rad)], [np.sin(t_rad), np.cos(t_rad)]])
        tri_rot = (tri @ R.T) + np.array([ex, ey])

        # 矢じり（多角形）の生成
        self.tri_patch = Polygon(tri_rot, closed=True, color=self.tri_color)
        self.ax.add_patch(self.tri_patch)

        # 時計回りの反転処理
        if self.clockwise:
            flip = Affine2D().scale(1, -1).translate(0, 2 * cy)
            self.arc_patch.set_transform(flip + self.ax.transData)
            self.tri_patch.set_transform(flip + self.ax.transData)

        # 画面の更新を促す
        if self.ax.figure and self.ax.figure.canvas:
            self.ax.figure.canvas.draw_idle()

    def update(self, **kwargs):
        """
        外部から変数を更新するためのメソッド。
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.draw()


# 2. Visualizer クラス (メイン描画マネージャー)
class Visualizer:
    def __init__(self, width, height, acceptable, grid_color="#FFFFFF"):
        self.width = width
        self.height = height
        self.acceptable = acceptable
        self.sunline = (min(width, height) * 2 / 4) / 2

        # 描画の初期化
        plt.ion()
        self.fig, self.ax = plt.subplots()

        # ダミー画像で領域を確保
        dummy_img = np.zeros((height, width), dtype=np.uint8)
        self.ax_img = self.ax.imshow(dummy_img, cmap="gray", vmin=0, vmax=255)

        # 各種プロットオブジェクトの初期設定
        self.circle = plt.Circle((0, 0), 0, fill=True, color="skyblue", linewidth=2)
        self.ax_min2 = self.ax.add_patch(self.circle)

        (self.ax_shdw_c,) = self.ax.plot(
            [],
            [],
            "o",
            color="cyan",
            markersize=3,
            alpha=0.4,
            label="circle center track",
        )

        # グリッドの描画
        self.grid_lines = []
        for y_val in np.linspace(0, height, 5)[1:-1]:
            (line,) = self.ax.plot(
                [0, width], [y_val, y_val], color=grid_color, linewidth=3, alpha=0.4
            )
            self.grid_lines.append(line)

        (self.ax_sunline,) = self.ax.plot([], [], color="purple", linewidth=3)
        self.fig_text = self.fig.text(
            0.01, 0.5, "turn camera_0°", ha="left", fontsize=20, color="red"
        )

        # 同ファイル内に定義した OpenCircleArrow を直接使用
        self.arrow = OpenCircleArrow(
            self.ax,
            center=(0, 0.5),
            radius=100,
            gap_angle=90,
            edgecolor="purple",
            tri_color="purple",
        )

    def update(self, img, cx, cy, r, recent_pts, calculate, need_cl):
        """計算結果を受け取り、画面を更新する"""
        self.ax_img.set_data(img)
        self.ax_min2.set_center((cx, cy))
        self.ax_min2.set_radius(r)

        self.ax_shdw_c.set_data(recent_pts[:, 0], recent_pts[:, 1])

        # 許容範囲に応じて色を変更
        if 180 - abs(calculate) < self.acceptable:
            uxc = ("limegreen", "mediumseagreen")
        else:
            uxc = ("red", "purple")

        calc_rad = np.radians(calculate)
        tan_val = np.tan(calc_rad) if abs(np.tan(calc_rad)) > 1e-5 else 1e-5

        self.ax_sunline.set_xdata(
            np.linspace(cx - self.sunline * tan_val, cx + self.sunline * tan_val, 100)
        )
        self.ax_sunline.set_ydata(
            np.linspace(cy - self.sunline / tan_val, cy + self.sunline / tan_val, 100)
        )

        self.fig_text.set_text(f"turn camera_{need_cl}° clockwise")
        clockwise = True if need_cl > 0 else False

        # gapangle から gap_angle に修正し、プロパティを正確に更新
        self.arrow.update(
            gap_angle=abs(need_cl),
            clockwise=clockwise,
            edgecolor=uxc[1],
            tri_color=uxc[1],
        )

        self.ax_sunline.set_color(uxc[1])
        self.fig_text.set_color(uxc[0])

        # 描画を反映
        plt.pause(0.001)

    def is_alive(self):
        """ウィンドウが閉じられていないか判定する"""
        return plt.fignum_exists(self.fig.number)

    def close(self):
        """描画リソースを安全に閉じる"""
        plt.close(self.fig)


# テスト・デモ実行用
if __name__ == "__main__":
    from tkinter.filedialog import askopenfile
    import time
    import sys
    from pathlib import Path

    demo_mode = input("allow,west as (1or2)")
    if demo_mode == "1":
        # このスクリプトを直接実行した場合、スライダー付きの矢印デモが動作します
        fig, ax = plt.subplots(figsize=(5, 6))
        plt.subplots_adjust(bottom=0.25)

        arrow = OpenCircleArrow(
            ax, center=(0, 0), radius=1.0, gap_angle=90, clockwise=True
        )

        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.set_aspect("equal")
        ax.axis("off")

        ax_gap = plt.axes([0.2, 0.14, 0.6, 0.03])
        ax_radius = plt.axes([0.2, 0.09, 0.6, 0.03])
        ax_start = plt.axes([0.2, 0.04, 0.6, 0.03])

        slider_gap = Slider(ax_gap, "Gap Angle", 0, 360, valinit=90)
        slider_radius = Slider(ax_radius, "Radius", 0.1, 1.4, valinit=1.0)
        slider_start = Slider(ax_start, "Start Angle", 0, 360, valinit=180)

        def handle_update(val):
            arrow.update(
                gap_angle=slider_gap.val,
                radius=slider_radius.val,
                start_angle=slider_start.val,
            )

        slider_gap.on_changed(handle_update)
        slider_radius.on_changed(handle_update)
        slider_start.on_changed(handle_update)

        plt.show()
    else:
        img_shape = (1608, 1104)
        radius = 300
        acceptable = 1
        fps = 60

        footsteps = []  # 太陽位置の時系列データ [(cx1,cy1),(cxx2,cy2),(cx3,cy3)...]
        footstep_mode = input("footsteps? existing(0)/console(1)/txt(2)/csv(3)")
        if footstep_mode == "0":
            if len(footsteps) == 0:
                print("No existing footstep")
            else:
                pass
        elif footstep_mode in ["1", "2"]:
            if footstep_mode == "1":
                print("文字を入力してください（終了するには Ctrl+D [Mac/Linux] または Ctrl+Z [Windows] を押してください）:")
                # すべての入力を一括で取得
                input_footsteps = sys.stdin.read().replace("^Z", "").strip()
            elif footstep_mode == "2":
                file_path = askopenfile(mode="r", filetypes=[("Text files", "*.txt")])
                if file_path is None:
                    print("ファイルが選択されませんでした。")
                    sys.exit(1)
                input_footsteps = file_path.read().strip()
            try:
                footsteps = [
                    (
                        float(tp[1:-1].replace(" ", "").split(",")[0]),
                        float(tp[1:-1].replace(" ", "").split(",")[1]),
                    )
                    for tp in input_footsteps.split("\n")
                ]
            except Exception:
                print("format error")
            # TODO:executerのformatで受け取り
        else:
            print("your typo or yet")

        if footsteps:
            # 階層エラー対策 (find_west.py に準拠したインポート設定)
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            try:
                from RANSAC import calculate_west_angle_robust as west_angle
            except ImportError:
                print("エラー: RANSACモジュールが見つかりません。")
                sys.exit(1)

            # デモ用のダミー角度計算に必要な plturn 関数
            def plturn(n):
                if n == 0:
                    return 0
                g = 1 if n < 0 else -1
                c = 1
                n = abs(n)
                nn = n + n
                while True:
                    if nn >= 180:
                        return ((180) % (n) + n * (c - 1)) * g
                    else:
                        c += 1
                        nn = n * c

            width, height = img_shape
            black_img = np.zeros((height, width), dtype=np.uint8)

            # Numpy配列化
            pts = np.array(footsteps)

            # --- 変更点: 初めに一度だけRANSACで基準の角度を計算 ---
            print("初期軌跡データからRANSACで基準角度を計算しています...")
            base_calculate, vectorYX = west_angle(pts)

            # UI確認のため Visualizer を初期化
            viz = Visualizer(width, height, acceptable)

            # 描画範囲を画像サイズに固定
            viz.ax.set_xlim(0, width)
            viz.ax.set_ylim(height, 0)

            # スライダー用の余白を画面下部に作成し、スライダーを配置
            plt.subplots_adjust(bottom=0.2)
            ax_slider = viz.fig.add_axes([0.2, 0.05, 0.6, 0.03])
            rot_slider = Slider(ax_slider, "Rotation", -180, 180, valinit=0)

            # 回転の基準となる画像中心
            cx0, cy0 = width / 2, height / 2

            frame_idx = 0
            num_frames = len(footsteps)

            print(
                f"デモを開始します (FPS: {fps})。グラフウィンドウを閉じるかCtrl+Cで終了します。"
            )

            # アニメーションループ
            while viz.is_alive():
                start_time = time.time()

                # スライダーの値を取得
                angle_deg = rot_slider.val
                angle_rad = np.radians(angle_deg)

                # footsteps を画像中心を軸に回転
                cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
                x = pts[:, 0] - cx0
                y = pts[:, 1] - cy0
                rx = x * cos_a - y * sin_a + cx0
                ry = x * sin_a + y * cos_a + cy0
                rotated_pts = np.column_stack((rx, ry))

                # 現在のフレームで描画する軌跡 (最大直近100件程度)
                start_idx = max(0, frame_idx - 100)
                recent_pts = rotated_pts[start_idx : frame_idx + 1]

                if len(recent_pts) > 0:
                    cx, cy = recent_pts[-1]

                    # --- 変更点: 角度は「初期計算値 + スライダーの回転量」で決定 ---
                    calculate = base_calculate + angle_deg
                    need_cl = plturn(calculate)

                    # 描画更新
                    viz.update(
                        black_img, cx, cy, radius, recent_pts, calculate, need_cl
                    )

                # 次のフレームへ進める
                frame_idx = (frame_idx + 1) % num_frames

                # 指定された fps に合わせた待機処理
                elapsed = time.time() - start_time
                sleep_time = max(0.001, (1.0 / fps) - elapsed)
                plt.pause(sleep_time)
